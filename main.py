import click
import asyncio
from sqlalchemy.orm import Session

from src.agents.idea_selector import select_category
from src.agents.idea_generator import generate_ideas
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
    click.echo("Database initialized successfully.")

@cli.command()
@click.option('--category', default=None, help='Specify the category directly.')
@click.option('--num-ideas', default=1, help='Number of initial ideas to generate.')
@click.option('--num-long-scripts', default=1, help='Number of long-form scripts per idea.')
@click.option('--num-short-scripts', default=1, help='Number of short-form scripts per idea.')
def run_full_pipeline(category, num_ideas, num_long_scripts, num_short_scripts):
    """Runs the full video generation pipeline from idea to video."""
    click.echo("--- Starting the full video generation pipeline ---")
    db: Session = next(get_db())

    try:
        # 1. Idea Selection
        if not category:
            category = select_category()
        if not category:
            click.echo("No category selected. Exiting.")
            return

        # 2. Idea Generation
        click.echo(f"\nGenerating {num_ideas} idea(s) for category: {category}...")
        ideas = asyncio.run(generate_ideas(category, n=num_ideas))
        if not ideas:
            click.echo("Could not generate ideas. Exiting.")
            return
        
        for idea_text in ideas:
            # Create a Job for each idea
            job = db.query(Job).filter_by(idea=idea_text).first()
            if not job:
                job = Job(idea=idea_text, category=category, status='scripting')
                db.add(job)
                db.commit()
                db.refresh(job)
                click.echo(f"Created new job {job.id} for idea: '{idea_text}'")
            else:
                click.echo(f"Job for idea '{idea_text}' already exists. Skipping script generation if not needed.")
                if job.status != 'scripting':
                    continue

            # 3. Script Generation
            click.echo(f"Generating {num_long_scripts} long and {num_short_scripts} short scripts for '{idea_text}'...")
            script_bundle = asyncio.run(generate_scripts_for_idea(job, num_long_scripts, num_short_scripts))

            # 4. Feedback Loop
            click.echo("\n--- Entering Interactive Feedback Loop ---")
            for script in script_bundle.long_form_scripts + script_bundle.short_form_scripts:
                db_script = db.query(Script).filter_by(id=script.id).one()
                display_script_summary(db_script)
                result = collect_feedback(db, db_script)
                if result == 'quit':
                    click.echo("Exiting feedback loop.")
                    break
        
        # 5. Video Composition (process all approved jobs)
        click.echo("\n--- Checking for approved jobs to render ---")
        approved_jobs = db.query(Job).filter(Job.status == 'approved').all()
        if not approved_jobs:
            click.echo("No jobs are approved for rendering.")
        
        for job in approved_jobs:
            approved_scripts = db.query(Script).filter(Script.job_id == job.id, Script.status == 'approved').all()
            for script in approved_scripts:
                run_video_composition(db, script)

    finally:
        db.close()

    click.echo("\n--- Pipeline run finished. ---")


@cli.command()
@click.option('--category', prompt='Enter a category', help='The category to generate ideas for.')
@click.option('--n', default=5, help='Number of ideas to generate.')
def run_idea_generation(category, n):
    """Runs only the idea generation agent."""
    click.echo(f"Generating {n} ideas for '{category}'...")
    ideas = asyncio.run(generate_ideas(category, n))
    click.echo("Generated Ideas:")
    for i, idea in enumerate(ideas):
        click.echo(f"{i+1}. {idea}")

if __name__ == "__main__":
    cli() 