import click
import asyncio
from sqlalchemy.orm import Session
from inputimeout import inputimeout, TimeoutOccurred

from src.utils.logger import logger
from src.agents.idea_generator import generate_documentary_idea
from src.agents.researcher import research_subject
from src.agents.script_generator import generate_scripts_for_idea
from src.controllers.feedback import display_script_summary, collect_feedback
from src.agents.video_composer import compose_video_from_images
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
@click.option('--re-run', is_flag=True, help="Re-run the pipeline by deleting the existing job first.")
def run_full_pipeline(re_run: bool):
    """Runs the full documentary generation pipeline from idea to video."""
    logger.info("--- Starting the full documentary generation pipeline ---")
    db: Session = next(get_db())

    try:
        # 1. Idea Generation
        logger.info("Step 1: Generating Documentary Idea...")
        idea = generate_documentary_idea()
        if not idea:
            logger.error("Could not generate an idea. Exiting.")
            return
        logger.info(f"Generated Idea: '{idea}'")
        
        # Check for existing job and handle re-run
        existing_job = db.query(Job).filter(Job.idea == idea).first()
        if existing_job:
            logger.warning(f"A job for '{idea}' already exists (Status: {existing_job.status}).")
            if re_run:
                logger.info("Re-run flag detected. Deleting existing job and all related data.")
                # Important: This will cascade delete scripts and feedback due to relationships
                db.delete(existing_job)
                db.commit()
                logger.info("Existing job deleted. Proceeding with a new run.")
            else:
                logger.info("This job has already been processed. To re-run, use the --re-run flag. Exiting.")
                return
        
        # 2. Research
        logger.info(f"Step 2: Researching subject: '{idea}'...")
        research_summary = asyncio.run(research_subject(idea))
        if not research_summary or "Error:" in research_summary:
            logger.error(f"Could not gather research for the idea. Exiting. Reason: {research_summary}")
            # Optionally create a failed job
            if not existing_job: # Use existing_job here
                existing_job = Job(idea=idea, status='failed', research_summary=research_summary)
                db.add(existing_job)
                db.commit()
            return

        # 3. Create or Update Job
        job = db.query(Job).filter(Job.idea == idea).first()
        if not job:
            job = Job(idea=idea, status='scripting', research_summary=research_summary)
            db.add(job)
            logger.info(f"Created new job for idea: '{idea}'")
            db.commit() # Commit here to make the job persistent
            db.refresh(job)
        else: # Update existing pending/failed job
            job.status = 'scripting'
            job.research_summary = research_summary
            logger.info(f"Updated job for idea: '{idea}'")
            db.commit()
            db.refresh(job)

        # 4. Script Generation
        logger.info(f"Step 4: Generating Scripts for Job ID: {job.id}...")
        
        num_long_scripts = 0
        num_short_scripts = 0
        
        try:
            choice = inputimeout(
                prompt="Do you want a long or short form video? (long/short) [short]: ", 
                timeout=3
            ).lower()
            if choice == 'long':
                num_long_scripts = 1
            else:
                num_short_scripts = 1
        except TimeoutOccurred:
            logger.info("No input received, defaulting to short form video.")
            num_short_scripts = 1
        
        if num_long_scripts > 0:
            logger.info(f"Generating {num_long_scripts} long form script(s)...")
        if num_short_scripts > 0:
            logger.info(f"Generating {num_short_scripts} short form script(s)...")

        asyncio.run(generate_scripts_for_idea(job, num_long_scripts, num_short_scripts))

        # 5. Feedback Loop
        logger.info("Step 5: Entering Interactive Feedback Loop...")
        generated_scripts = db.query(Script).filter(Script.job_id == job.id).all()
        
        if not generated_scripts:
            logger.error("No scripts were generated. Exiting feedback loop.")
        else:
            for script in generated_scripts:
                display_script_summary(script)
                result = collect_feedback(db, script)
                if result == 'quit':
                    logger.info("Exiting feedback loop.")
                    break
        
        # 6. Video Composition (process all approved scripts for this job)
        logger.info(f"Step 6: Checking for approved scripts for job {job.id} to render...")
        
        if job.status == 'approved':
            logger.info(f"Job {job.id} ('{job.idea}') is approved for rendering.")
            # Since all approved scripts belong to the same job, we can just trigger composition once.
            compose_video_from_images(job_id=job.id)
        else:
            logger.info(f"Job '{job.idea}' was not approved. Skipping video composition.")

    finally:
        db.close()

    logger.info("--- Pipeline run finished. ---")

@cli.command()
def organize_files():
    """Organize scattered files in the output directory into structured folders."""
    logger.info("Starting file organization...")
    from src.utils.file_organizer import organize_existing_output_files
    organize_existing_output_files()
    logger.info("File organization completed.")


if __name__ == "__main__":
    cli() 