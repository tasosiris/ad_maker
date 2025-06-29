import asyncio
import os
from dataclasses import dataclass, field
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader
from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.database import get_db, Job, Script as DbScript
from sqlalchemy.orm import Session

# Initialize OpenAI client
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

@dataclass
class Script:
    id: int
    idea: str
    content: str
    script_type: str # 'long_form' or 'short_form'

@dataclass
class ScriptBundle:
    job_id: int
    idea: str
    long_form_scripts: List[Script] = field(default_factory=list)
    short_form_scripts: List[Script] = field(default_factory=list)

def setup_jinja_env():
    """Sets up the Jinja2 environment."""
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    return Environment(loader=FileSystemLoader(template_dir))

async def generate_single_script(template, idea: str, category: str, script_type: str, revision_notes: str = "") -> str:
    """Generates a single script using a template and OpenAI."""
    base_prompt = template.render(idea=idea, category=category)
    
    if revision_notes:
        final_prompt = f"{base_prompt}\n\nPlease revise the script based on these notes: {revision_notes}"
    else:
        final_prompt = base_prompt

    print(f"Generating {script_type} script for '{idea}'...")
    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": final_prompt}],
        temperature=0.8,
    )
    generated_content = response.choices[0].message.content
    print(f"Finished generating {script_type} script for '{idea}'.")
    return generated_content if generated_content else ""

async def generate_scripts_for_idea(job: Job, num_long: int, num_short: int) -> ScriptBundle:
    """
    Generates and saves a bundle of scripts for a single idea.
    """
    jinja_env = setup_jinja_env()
    long_form_template = jinja_env.get_template("long_form.jinja2")
    short_form_template = jinja_env.get_template("short_form.jinja2")

    tasks = []
    # Generate long-form scripts
    for _ in range(num_long):
        tasks.append(generate_single_script(long_form_template, job.idea, job.category, 'long_form'))
    
    # Generate short-form scripts
    for _ in range(num_short):
        tasks.append(generate_single_script(short_form_template, job.idea, job.category, 'short_form'))

    generated_contents = await asyncio.gather(*tasks)
    
    db: Session = next(get_db())
    bundle = ScriptBundle(job_id=job.id, idea=job.idea)
    
    script_idx = 0
    for i in range(num_long):
        content = generated_contents[script_idx]
        db_script = DbScript(job_id=job.id, script_type='long_form', content=content, status='pending')
        db.add(db_script)
        db.commit()
        db.refresh(db_script)
        bundle.long_form_scripts.append(Script(id=db_script.id, idea=job.idea, content=content, script_type='long_form'))
        script_idx += 1

    for i in range(num_short):
        content = generated_contents[script_idx]
        db_script = DbScript(job_id=job.id, script_type='short_form', content=content, status='pending')
        db.add(db_script)
        db.commit()
        db.refresh(db_script)
        bundle.short_form_scripts.append(Script(id=db_script.id, idea=job.idea, content=content, script_type='short_form'))
        script_idx += 1

    job.status = 'feedback'
    db.commit()
    db.close()
    
    return bundle

async def main():
    db: Session = next(get_db())
    # Create a dummy job for testing
    dummy_job = Job(idea="AI-Powered Smart Backpack", category="Tech Gadgets", status="scripting")
    db.add(dummy_job)
    db.commit()
    db.refresh(dummy_job)
    
    print(f"\n--- Generating scripts for job {dummy_job.id}: {dummy_job.idea} ---")
    script_bundle = await generate_scripts_for_idea(dummy_job, num_long=1, num_short=2)
    
    print(f"\n--- Generated {len(script_bundle.long_form_scripts)} Long-Form Scripts ---")
    for script in script_bundle.long_form_scripts:
        print(f"ID: {script.id}, Excerpt: {script.content[:100]}...")
        
    print(f"\n--- Generated {len(script_bundle.short_form_scripts)} Short-Form Scripts ---")
    for script in script_bundle.short_form_scripts:
        print(f"ID: {script.id}, Excerpt: {script.content[:100]}...")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main()) 