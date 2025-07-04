import click
import asyncio
from sqlalchemy.orm import Session
from inputimeout import inputimeout, TimeoutOccurred

from src.utils.logger import logger
from src.agents.idea_selector import select_category
from src.agents.idea_generator import generate_ideas
from src.agents.product_finder import find_real_products
from src.agents.script_generator import generate_scripts_for_idea
from src.controllers.feedback import display_script_summary, collect_feedback
from src.agents.video_composer import run_video_composition
from src.database import init_db, get_db, Job, Script

@click.group()
def cli():
    """AI-Powered Video Generation Agent."""
    pass

@cli.command()
def setup_database():
    """Initializes the database and creates tables."""
    init_db()
    logger.info("Database initialized successfully.")

@cli.command()
@click.option('--category', default=None, help='Specify the category directly.')
@click.option('--num-ideas', default=1, help='Number of initial ideas to generate.')
def run_full_pipeline(category, num_ideas):
    """Runs the full video generation pipeline from idea to video."""
    logger.info("--- Starting the full video generation pipeline ---")
    db: Session = next(get_db())

    try:
        # 1. Idea Selection
        logger.info("Step 1: Selecting Category...")
        if not category:
            category = select_category()
        if not category:
            logger.warning("No category selected. Exiting.")
            return
        logger.info(f"Category selected: {category}")

        # 2. Idea Generation
        logger.info(f"Step 2: Generating {num_ideas} idea(s) for category: {category}...")
        ideas = asyncio.run(generate_ideas(category, n=num_ideas))
        if not ideas:
            logger.error("Could not generate ideas. Exiting.")
            return
        
        logger.info("\n--- Please Select an Idea ---")
        for i, idea in enumerate(ideas):
            logger.info(f"{i+1}. {idea}")
        
        selected_idea_text = None
        try:
            # Default to idea 4 if available, otherwise the last one.
            default_choice = 4 if len(ideas) >= 4 else len(ideas)
            prompt = f"Select an idea [1-{len(ideas)}] (default: {default_choice}): "
            choice_str = inputimeout(prompt=prompt, timeout=3)
            
            if choice_str:
                choice_int = int(choice_str)
                if 1 <= choice_int <= len(ideas):
                    selected_idea_text = ideas[choice_int - 1]
                else:
                    logger.warning("Invalid selection. Defaulting.")
                    selected_idea_text = ideas[default_choice - 1]
            else: # Handle empty input
                logger.warning("No input received. Defaulting.")
                selected_idea_text = ideas[default_choice - 1]

        except (TimeoutOccurred, ValueError):
            default_choice = 4 if len(ideas) >= 4 else len(ideas)
            selected_idea_text = ideas[default_choice - 1]
            logger.info(f"Timeout or invalid input. Defaulting to idea {default_choice}: '{selected_idea_text}'")

        # Find real products for the selected idea
        logger.info(f"Step 3: Finding real products for idea: '{selected_idea_text}'")
        products = find_real_products(selected_idea_text, category)
        selected_product = None

        if products:
            logger.info("\n--- Please Select a Product ---")
            for i, product in enumerate(products):
                logger.info(f"{i+1}. {product['name']}")
            
            try:
                prompt = f"Select a product [1-{len(products)}] (default: 1, or press Enter to skip): "
                choice_str = inputimeout(prompt=prompt, timeout=3)
                
                if choice_str:
                    choice_int = int(choice_str)
                    if 1 <= choice_int <= len(products):
                        selected_product = products[choice_int - 1]
                    else:
                        logger.warning("Invalid selection. Defaulting to product 1.")
                        selected_product = products[0]
                else: # Handle empty input
                    logger.warning("No product selected. Generating a generic script.")
            
            except (TimeoutOccurred, ValueError):
                selected_product = products[0]
                logger.warning(f"Timeout or invalid input. Defaulting to product 1: '{selected_product['name']}'")
        else:
            logger.info("No real products found. Generating a generic script for the idea.")

        # Ask for script type
        logger.info("Step 4: Selecting script type...")
        script_type_choice = 'short'  # Default value
        try:
            prompt = "Select script type (long, short) [short]: "
            choice_str = inputimeout(prompt=prompt, timeout=3).lower().strip()
            if choice_str in ['long', 'short']:
                script_type_choice = choice_str
                logger.info(f"Selected script type: {script_type_choice}")
            else:
                # This handles empty or invalid input
                logger.warning("Invalid or empty selection. Defaulting to 'short'.")
        except TimeoutOccurred:
            logger.warning("Timeout occurred. Defaulting to 'short' form script.")
        
        num_long_scripts = 1 if script_type_choice == 'long' else 0
        num_short_scripts = 1 if script_type_choice == 'short' else 0

        # Create a Job for the selected idea
        job = db.query(Job).filter_by(idea=selected_idea_text).first()
        if not job:
            # Store product information if available
            product_name = selected_product['name'] if selected_product else None
            product_url = selected_product['url'] if selected_product else None
            affiliate_commission = selected_product['commission'] if selected_product else None
            
            job = Job(
                idea=selected_idea_text, 
                category=category, 
                status='scripting',
                product_name=product_name,
                product_url=product_url,
                affiliate_commission=affiliate_commission
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            logger.info(f"Created new job {job.id} for idea: '{selected_idea_text}'")
            if selected_product:
                logger.info(f"  Product: {product_name} | URL: {product_url} | Commission: {affiliate_commission}")
        else:
            logger.info(f"Job for idea '{selected_idea_text}' already exists. Skipping script generation if not needed.")
            if job.status != 'scripting':
                # If job exists but is not in scripting, we might want to exit or handle it.
                # For now, we'll just skip to the next phase, though no scripts will be generated.
                pass

        # 3. Script Generation (only for the selected job)
        if job.status == 'scripting':
            logger.info(f"Step 5: Generating scripts for '{selected_idea_text}'...")
            script_bundle = asyncio.run(generate_scripts_for_idea(job, num_long_scripts, num_short_scripts, product=selected_product))

            # 4. Feedback Loop
            logger.info("Step 6: Entering Interactive Feedback Loop...")
            for script in script_bundle.long_form_scripts + script_bundle.short_form_scripts:
                db_script = db.query(Script).filter_by(id=script.id).one()
                display_script_summary(db_script)
                result = collect_feedback(db, db_script)
                if result == 'quit':
                    logger.info("Exiting feedback loop.")
                    break
        else:
            logger.info("Skipping script generation and feedback as job is not in 'scripting' status.")

        # 5. Video Composition (process all approved jobs)
        logger.info("Step 7: Checking for approved jobs to render...")
        approved_jobs = db.query(Job).filter(Job.status == 'approved').all()
        if not approved_jobs:
            logger.info("No jobs are approved for rendering.")
        
        for job in approved_jobs:
            logger.info(f"Found approved job {job.id} ('{job.idea}') for rendering.")
            approved_scripts = db.query(Script).filter(Script.job_id == job.id, Script.status == 'approved').all()
            for script in approved_scripts:
                run_video_composition(db, script)

    finally:
        db.close()

    logger.info("--- Pipeline run finished. ---")


@cli.command()
@click.option('--category', prompt='Enter a category', help='The category to generate ideas for.')
@click.option('--n', default=5, help='Number of ideas to generate.')
def run_idea_generation(category, n):
    """Runs only the idea generation agent."""
    logger.info(f"Generating {n} ideas for '{category}'...")
    ideas = asyncio.run(generate_ideas(category, n))
    logger.info("Generated Ideas:")
    for i, idea in enumerate(ideas):
        logger.info(f"{i+1}. {idea}")

if __name__ == "__main__":
    cli() 