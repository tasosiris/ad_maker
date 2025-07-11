import click
import asyncio
from sqlalchemy.orm import Session
from inputimeout import inputimeout, TimeoutOccurred

from src.utils.logger import logger
from src.agents.idea_generator import generate_documentary_idea
from src.agents.researcher import research_subject
from src.agents.script_generator import generate_scripts_for_idea
from src.controllers.feedback import display_script_summary, collect_feedback
from src.agents.video_composer import compose_video_from_images, run_video_composition
from src.database import init_db, get_db, Job, Script
from src.utils.output_manager import OutputManager
from src.utils.cost_calculator import CostTracker

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
@click.option('--re-run', is_flag=True, help="Re-run the pipeline by deleting the existing job first.")
def run_full_pipeline(re_run: bool):
    """Runs the full documentary generation pipeline from idea to video."""
    
    async def _run_async_pipeline(re_run: bool):
        logger.info("--- Starting the full documentary generation pipeline ---")
        db: Session = next(get_db())
        output_manager = None
        cost_tracker = None

        try:
            logger.info("Step 1: Generating Documentary Idea...")
            idea = generate_documentary_idea()
            if not idea:
                logger.error("Could not generate an idea. Exiting."); return
            logger.info(f"Generated Idea: '{idea}'")

            output_manager = OutputManager(idea=idea)
            cost_tracker = CostTracker(output_dir=output_manager.get_job_directory())
            output_manager.save_prompt("idea_generator", {"selected_idea": idea})

            existing_job = db.query(Job).filter(Job.idea == idea).first()
            if existing_job:
                logger.warning(f"A job for '{idea}' already exists (Status: {existing_job.status}).")
                if re_run:
                    logger.info("Re-run flag detected. Deleting existing job and all related data.")
                    db.delete(existing_job); db.commit()
                    logger.info("Existing job deleted. Proceeding with a new run.")
                else:
                    logger.info("This job has already been processed. To re-run, use the --re-run flag. Exiting.")
                    return

            job_context = { "idea": idea, "output_manager": output_manager, "cost_tracker": cost_tracker, "db_session": db }

            logger.info(f"Step 2: Researching subject: '{idea}'...")
            research_summary = await research_subject(job_context)
            if not research_summary or "Error:" in research_summary:
                logger.error(f"Could not gather research for the idea. Exiting. Reason: {research_summary}")
                job = Job(idea=idea, status='failed', research_summary=research_summary)
                db.add(job); db.commit()
                return

            job = Job(idea=idea, status='scripting', research_summary=research_summary)
            db.add(job); db.commit(); db.refresh(job)
            job_context["job"] = job
            
            logger.info(f"Step 3: Generating Scripts for Job ID: {job.id}...")
            choice = 'short'
            try:
                choice = inputimeout(prompt="Long or short form video? (long/short) [short]: ", timeout=3).lower()
            except TimeoutOccurred:
                logger.info("No input, defaulting to short form.")
            
            num_long = 1 if choice == 'long' else 0
            num_short = 1 if choice != 'long' else 0
            await generate_scripts_for_idea(job_context, num_long, num_short)

            logger.info("Step 4: Entering Interactive Feedback Loop...")
            generated_scripts = db.query(Script).filter(Script.job_id == job.id).all()
            if not generated_scripts:
                logger.error("No scripts were generated. Exiting feedback loop.")
            else:
                for script in generated_scripts:
                    display_script_summary(script)
                    if collect_feedback(db, script) == 'quit':
                        logger.info("Exiting feedback loop."); break
            
            logger.info(f"Step 5: Checking for approved scripts for job {job.id} to render...")
            approved_script = db.query(Script).filter(Script.job_id == job.id, Script.status == 'approved').first()

            if approved_script:
                composition_method = 'images'
                try:
                    choice = inputimeout(
                        prompt="Which composition method? (image/stock) [image]: ",
                        timeout=3
                    ).lower()
                    if choice == 'stock':
                        composition_method = 'stock'
                    elif choice == 'image':
                        composition_method = 'images'

                except TimeoutOccurred:
                    logger.info("No input received, defaulting to 'images' composition.")

                logger.info(f"Script {approved_script.id} is approved for rendering using '{composition_method}' method.")
                if composition_method == 'images':
                    await compose_video_from_images(job_context, approved_script)
                else:
                    await run_video_composition(job_context, approved_script)
            else:
                logger.info(f"No scripts for job '{job.idea}' were approved. Skipping video composition.")

        finally:
            if cost_tracker:
                cost_tracker.save_costs()
                logger.info(f"Costs saved to {cost_tracker.output_dir}")
            if db:
                db.close()
            logger.info("--- Pipeline run finished. ---")

    asyncio.run(_run_async_pipeline(re_run))

if __name__ == "__main__":
    cli() 