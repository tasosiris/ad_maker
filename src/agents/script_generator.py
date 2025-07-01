import asyncio
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader
from openai import AsyncOpenAI, OpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.database import get_db, Job, Script as DbScript
from sqlalchemy.orm import Session

# Initialize OpenAI client
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = "\n".join([
    "You are an expert scriptwriter for viral social media videos.",
    "Your goal is to create a script that is engaging, informative, and optimized for the specified platform (long-form or short-form).",
    "Your output MUST be ONLY the script text. Do not include any headers, explanations, or markdown formatting.",
    "Use section markers like [HOOK], [INTRO], [VALUE], and [CTA] to structure the script, but these are for the video editor and should not be spoken.",
    "The tone should be enthusiastic and persuasive, designed to capture and hold the viewer's attention."
])

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

async def generate_single_script(template, idea: str, category: str, script_type: str, revision_notes: str = "", product: Optional[Dict[str, str]] = None) -> str:
    """Generates a single script using a given template and idea."""
    
    # New vlog-style prompt instructions
    style_prompt = (
        "The script MUST be written in a personal, first-person, vlog-style tone. "
        "It should sound like a real person sharing their genuine experience with the product. "
        "Include personal anecdotes and specific examples of when the product was useful. "
        "Make it conversational, authentic, and engaging."
    )

    if product:
        # If a product is provided, create a more specific prompt
        product_details = f"The script MUST be about this specific product: **{product['name']}**.\n"
        if product.get('url'):
            product_details += f"Use this URL for reference: {product.get('url')}\n"
        if product.get('details'):
            product_details += f"Here are some details about it: {product.get('details')}\n"

        prompt_text = (
            f"Create a {script_type} vlog-style video script for the following product idea: '{idea}'.\n"
            f"{product_details}"
            f"{style_prompt}\n"
            "Here's an example of the tone: 'I was skeptical at first, but this thing has been a lifesaver. "
            "Last week, I was on a business trip, and I actually used it to...'."
        )
    else:
        # Generic prompt if no specific product is found
        prompt_text = (
            f"Create a {script_type} vlog-style video script for the following product idea: '{idea}'.\n"
            f"The category is '{category}'.\n"
            f"{style_prompt}\n"
            "Even though there's no specific product, invent one and talk about it from a personal perspective. "
            "For example: 'I've been using this new smart blender for a month now, and it's completely changed my morning routine...'"
        )

    if revision_notes:
        final_prompt = f"{prompt_text}\n\nPlease revise the script based on these notes: {revision_notes}"
    else:
        final_prompt = prompt_text

    print(f"Generating {script_type} script for '{idea}'...")
    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": final_prompt}],
        temperature=0.8,
    )
    generated_content = response.choices[0].message.content
    print(f"Finished generating {script_type} script for '{idea}'.")
    return generated_content if generated_content else ""

async def generate_scripts_for_idea(job: Job, num_long: int, num_short: int, product: Optional[Dict[str, str]] = None) -> ScriptBundle:
    """
    Generates and saves a bundle of scripts for a single idea.
    """
    jinja_env = setup_jinja_env()
    long_form_template = jinja_env.get_template("long_form.jinja2")
    short_form_template = jinja_env.get_template("short_form.jinja2")

    tasks = []
    # Generate long-form scripts
    for _ in range(num_long):
        tasks.append(generate_single_script(long_form_template, job.idea, job.category, 'long_form', product=product))
    
    # Generate short-form scripts
    for _ in range(num_short):
        tasks.append(generate_single_script(short_form_template, job.idea, job.category, 'short_form', product=product))

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