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

async def generate_single_script(
    job_context: dict, 
    script_type: str, 
    script_name: str,
    revision_notes: str = ""
) -> str:
    """Generates a single documentary script, tracks cost, and saves output."""
    idea = job_context['idea']
    research_summary = job_context['research_summary']
    output_manager = job_context['output_manager']
    cost_tracker = job_context['cost_tracker']

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
        temperature=0.7,
    )
    
    content = response.choices[0].message.content.strip()
    usage = response.usage

    cost_info = cost_tracker.add_cost(
        "openai",
        model=OPENAI_MODEL,
        tokens_input=usage.prompt_tokens,
        tokens_output=usage.completion_tokens,
    )

    output_manager.save_prompt(
        agent_name=f"script_generator_{script_name}",
        prompt_data={"system_prompt": system_prompt, "user_prompt": user_prompt},
        cost_info=cost_info
    )

    script_path = output_manager.get_prompts_directory() / f"{script_name}.txt"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content

async def generate_scripts_for_idea(job_context: dict, num_long: int, num_short: int):
    """
    Generates and saves a bundle of scripts for a single idea.
    """
    job = job_context['job']
    if not job.research_summary:
        print(f"Error: Job {job.id} has no research summary. Aborting script generation.")
        return
    
    job_context['research_summary'] = job.research_summary

    tasks = []
    script_names = []
    
    for i in range(num_long):
        name = f"long_form_{i+1}"
        tasks.append(generate_single_script(job_context, 'long_form', name))
        script_names.append(name)
    
    for i in range(num_short):
        name = f"short_form_{i+1}"
        tasks.append(generate_single_script(job_context, 'short_form', name))
        script_names.append(name)

    generated_contents = await asyncio.gather(*tasks)
    
    db: Session = job_context['db_session']
    
    script_idx = 0
    for i in range(num_long):
        content = generated_contents[script_idx]
        db_script = DbScript(job_id=job.id, script_type='long_form', content=content, status='pending')
        db.add(db_script)
        script_idx += 1

    for i in range(num_short):
        content = generated_contents[script_idx]
        db_script = DbScript(job_id=job.id, script_type='short_form', content=content, status='pending')
        db.add(db_script)
        script_idx += 1

    job.status = 'feedback'
    db.commit()
    print(f"Successfully generated and saved {len(generated_contents)} scripts for job {job.id}.")

async def main():
    from src.utils.output_manager import OutputManager
    from src.utils.cost_calculator import CostTracker
    db: Session = next(get_db())

    dummy_job = Job(
        idea="The Great Emu War of 1932", 
        status="scripting",
        research_summary="In 1932, Australia faced an unusual enemy: emus..."
    )
    db.add(dummy_job)
    db.commit()
    db.refresh(dummy_job)
    
    output_manager = OutputManager(idea=dummy_job.idea)
    cost_tracker = CostTracker(output_dir=output_manager.get_job_directory())

    job_context = {
        "idea": dummy_job.idea,
        "job": dummy_job,
        "db_session": db,
        "output_manager": output_manager,
        "cost_tracker": cost_tracker,
    }
    
    print(f"\n--- Generating scripts for job {dummy_job.id}: {dummy_job.idea} ---")
    await generate_scripts_for_idea(job_context, num_long=1, num_short=1)
    
    print("\n--- Verifying scripts in DB ---")
    scripts = db.query(DbScript).filter(DbScript.job_id == dummy_job.id).all()
    for script in scripts:
        print(f"ID: {script.id}, Type: {script.script_type}, Excerpt: {script.content[:100]}...")
    
    cost_tracker.save_costs()
    print(f"\nCosts tracked and saved in: {output_manager.get_job_directory()}")
    db.close()

if __name__ == "__main__":
    asyncio.run(main()) 