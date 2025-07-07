import asyncio
import os
from typing import List, Dict, Optional
from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.database import get_db, Job, Script as DbScript
from sqlalchemy.orm import Session

# Initialize OpenAI client
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generate_single_script(idea: str, research_summary: str, script_type: str, revision_notes: str = "") -> str:
    """Generates a single documentary script based on research."""
    
    # Load the example transcript to guide the AI's style
    example_transcript = ""
    try:
        transcript_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'example_transcript.txt')
        with open(transcript_path, 'r', encoding='utf-8') as f:
            example_transcript = f.read()
    except Exception as e:
        print(f"Warning: Could not load example transcript. {e}")

    system_prompt = f"""
    You are a world-class documentary scriptwriter. Your task is to write a script that is engaging, theatrical, and emotionally resonant.
    The script should be based on the provided research summary.

    Follow these instructions:
    - Write in a style that is dramatic and suitable for a documentary. Use vivid language and strong storytelling.
    - Weave the information from the research summary into a compelling narrative. Pay attention to the narrative arc, build tension, and create an emotional journey for the viewer.
    - Use pauses for dramatic effect. When the story calls for a moment of reflection or to build suspense, insert a `[PAUSE]` marker. Use this sparingly but effectively.
    - Start with a strong hook to grab the viewer's attention.
    - Ensure the script's length is appropriate for a {script_type} video. For 'long_form', this means a 3-5 minute video (approximately 450-750 words). For 'short_form', aim for a 60-90 second video (approximately 150-225 words).
    - DO NOT include scene numbers, visual cues like `[SCENE START]`, or camera directions. Focus purely on the narrative text and dramatic pauses.

    Here is an example of the tone and quality I expect:
    ---
    {example_transcript}
    ---
    """

    user_prompt = f"""
    Here is the research summary for the documentary topic: "{idea}"
    Please write the complete {script_type} script based on this information.
    
    Research Summary:
    ---
    {research_summary}
    ---
    """
    
    if revision_notes:
        user_prompt += f"\n\nPlease revise the script based on the following feedback:\n{revision_notes}"

    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7, # Slightly higher temperature for more creative/theatrical output
    )
    
    return response.choices[0].message.content.strip()

async def generate_scripts_for_idea(job: Job, num_long: int, num_short: int):
    """
    Generates and saves a bundle of scripts for a single idea.
    """
    if not job.research_summary:
        print(f"Error: Job {job.id} has no research summary. Aborting script generation.")
        return

    tasks = []
    # Generate long-form scripts
    for _ in range(num_long):
        tasks.append(generate_single_script(job.idea, job.research_summary, 'long_form'))
    
    # Generate short-form scripts
    for _ in range(num_short):
        tasks.append(generate_single_script(job.idea, job.research_summary, 'short_form'))

    generated_contents = await asyncio.gather(*tasks)
    
    db: Session = next(get_db())
    
    script_idx = 0
    # Save long-form scripts
    for i in range(num_long):
        content = generated_contents[script_idx]
        db_script = DbScript(job_id=job.id, script_type='long_form', content=content, status='pending')
        db.add(db_script)
        script_idx += 1

    # Save short-form scripts
    for i in range(num_short):
        content = generated_contents[script_idx]
        db_script = DbScript(job_id=job.id, script_type='short_form', content=content, status='pending')
        db.add(db_script)
        script_idx += 1

    job.status = 'feedback'
    db.commit()
    print(f"Successfully generated and saved {len(generated_contents)} scripts for job {job.id}.")
    db.close()

async def main():
    db: Session = next(get_db())
    # Create a dummy job for testing
    dummy_job = Job(
        idea="The Great Emu War of 1932", 
        status="scripting",
        research_summary="""In 1932, Australia faced an unusual enemy: emus. After World War I, soldiers were given land for farming, but a drought brought 20,000 emus to the area, destroying crops. The farmers, many of them veterans, asked for military help. The government sent Major G.P.W. Meredith with two Lewis machine guns and 10,000 rounds of ammunition. The 'war' began in November 1932, but the emus proved to be surprisingly difficult targets. They were fast, dodged bullets, and split into small groups, making them hard to hit. After a few embarrassing attempts and very few emus killed, the military withdrew. The media had a field day, mocking the army's defeat. A second attempt was made later, with slightly more success, but ultimately the 'war' was a failure. The government turned to a bounty system instead, which proved more effective in controlling the emu population."""
    )
    db.add(dummy_job)
    db.commit()
    db.refresh(dummy_job)
    
    print(f"\n--- Generating scripts for job {dummy_job.id}: {dummy_job.idea} ---")
    await generate_scripts_for_idea(dummy_job, num_long=1, num_short=1)
    
    print("\n--- Verifying scripts in DB ---")
    scripts = db.query(DbScript).filter(DbScript.job_id == dummy_job.id).all()
    for script in scripts:
        print(f"ID: {script.id}, Type: {script.script_type}, Excerpt: {script.content[:100]}...")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main()) 