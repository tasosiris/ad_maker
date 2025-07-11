import os
import time
import ffmpeg
from dataclasses import dataclass
from typing import List, Optional
import re
import random
from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.utils.logger import logger
from src.assets.fetcher import fetch_clips, clear_video_cache
from src.tts.voice import generate_voice, VoiceClip
from src.editing.ffmpeg_editor import compose_video
from src.database import Script, Job
from sqlalchemy.orm import Session
from src.agents.image_generator import generate_image
from src.editing.ffmpeg_editor import create_video_from_image
from src.database import get_db

openai_client = OpenAI(api_key=OPENAI_API_KEY)

@dataclass
class TimedVoiceClip(VoiceClip):
    duration: float

@dataclass
class Scene:
    voice_clip: TimedVoiceClip
    video_path: str

def generate_intelligent_video_query(job_context: dict, text: str) -> str:
    cost_tracker = job_context['cost_tracker']
    prompt = f"You are a documentary film assistant... Overall Documentary Subject: \"{job_context['idea']}\" Narration Line: \"{text}\"..."
    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.4, max_tokens=20)
        ai_query = response.choices[0].message.content.strip().replace('"', '').replace("'", '')
        cost_tracker.add_cost("openai", model=OPENAI_MODEL, tokens_input=response.usage.prompt_tokens, tokens_output=response.usage.completion_tokens)
        logger.info(f"  -> AI-generated video query: '{ai_query}'")
        return ai_query
    except Exception as e:
        logger.warning(f"Failed to generate AI query: {e}. Falling back to keyword extraction.")
        return text

def generate_intelligent_image_prompt(job_context: dict, text: str) -> str:
    """
    Generates an intelligent image prompt using an LLM to enhance creativity.
    """
    cost_tracker = job_context['cost_tracker']
    
    prompt = f"""You are a historical advisor and director for a documentary film.
Your task is to create a historically accurate and realistic image prompt for an AI image generator.
The image should be cinematic and visually represent the following narration.
The style should be photographic and realistic, avoiding any exaggerations or fantasy elements.
Focus on details that would make the scene feel authentic to the time period.

Overall Documentary Subject: "{job_context['idea']}"
Narration Line: "{text}"

Generate a single, concise image prompt that is historically accurate and realistic.
"""

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,  # Lower temperature for more realistic prompts
            max_tokens=150
        )
        ai_query = response.choices[0].message.content.strip().replace('"', '').replace("'", '')
        cost_tracker.add_cost(
            "openai",
            model=OPENAI_MODEL,
            tokens_input=response.usage.prompt_tokens,
            tokens_output=response.usage.completion_tokens
        )
        logger.info(f"  -> AI-generated image prompt: '{ai_query}'")
        return ai_query
    except Exception as e:
        logger.warning(f"Failed to generate AI image prompt: {e}. Falling back to basic prompt.")
        # Fallback to a simpler prompt format
        return f"cinematic, historically accurate, realistic, {job_context['idea']}, {text}"


def fetch_relevant_clip(job_context: dict, timed_clip: TimedVoiceClip) -> Optional[str]:
    query = generate_intelligent_video_query(job_context, timed_clip.text)
    video_assets = fetch_clips(job_context, query, num_clips=5)
    if not video_assets:
        logger.warning(f"No initial video assets found for query '{query}'.")
        return None

    best_clip = None
    smallest_duration_diff = float('inf')
    for asset_path in video_assets:
        try:
            duration = float(ffmpeg.probe(asset_path)['format']['duration'])
            if duration >= timed_clip.duration:
                duration_diff = duration - timed_clip.duration
                if duration_diff < smallest_duration_diff:
                    smallest_duration_diff = duration_diff
                    best_clip = asset_path
        except Exception as e:
            logger.error(f"Could not probe candidate video {asset_path}: {e}")
    
    if best_clip:
        logger.info(f"Found best-fit clip: {os.path.basename(best_clip)}")
    else:
        logger.warning(f"No fetched video clips met duration requirement for: {timed_clip.text}")
    return best_clip

def get_music_tracks(music_dir: str = "src/assets/music") -> List[str]:
    if not os.path.isdir(music_dir): return []
    supported_formats = ('.mp3', '.wav', '.aac', '.m4a')
    return [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(supported_formats)]

async def run_video_composition(job_context: dict, script: Script):
    db = job_context['db_session']
    job = script.job
    logger.info(f"===== Starting Video Composition for Script ID: {script.id} =====")
    job.status = 'rendering'; db.commit()
    clear_video_cache()

    logger.info("Step 1: Generating Voiceover...")
    voice_clips = await generate_voice(job_context, f"script_{script.id}", str(script.content or ''))
    if not voice_clips:
        job.status = 'render_failed'; db.commit(); return
    
    logger.info("Step 2: Preparing scenes...")
    scenes: List[Scene] = []
    for clip in voice_clips:
        try:
            duration = float(ffmpeg.probe(clip.audio_path)['format']['duration'])
            timed_clip = TimedVoiceClip(text=clip.text, audio_path=clip.audio_path, duration=duration)
            video_asset = fetch_relevant_clip(job_context, timed_clip)
            if video_asset:
                scenes.append(Scene(voice_clip=timed_clip, video_path=video_asset))
            else:
                logger.warning(f"Could not find a suitable video for sentence: '{clip.text}'. Skipping.")
        except Exception as e:
            logger.error(f"Error processing clip {clip.audio_path}: {e}")

    if not scenes:
        job.status = 'render_failed'; db.commit(); return
    
    logger.info("Step 3: Composing Video...")
    output_path = str(job_context['output_manager'].get_videos_directory() / f"final_video_{script.id}.mp4")
    video_paths = [scene.video_path for scene in scenes]
    audio_paths = [scene.voice_clip.audio_path for scene in scenes]
    music_tracks = get_music_tracks()
    background_music = random.choice(music_tracks) if music_tracks else None
    
    final_video_path = compose_video(video_paths, audio_paths, output_path, background_music)

    if final_video_path:
        job.status = 'completed'; job.video_path = final_video_path
        logger.info(f"Video composition successful! Final video at: {final_video_path}")
    else:
        job.status = 'render_failed'; logger.error("Video composition failed.")
    db.commit()

async def compose_video_from_images(job_context: dict, script: Script):
    db = job_context['db_session']
    job = script.job
    output_manager = job_context['output_manager']
    logger.info(f"===== Starting Image-to-Video Composition for Script ID: {script.id} =====")
    job.status = 'rendering'; db.commit()

    logger.info("Step 1: Generating Voiceover...")
    voice_clips = await generate_voice(job_context, f"script_{script.id}", str(script.content or ''))
    if not voice_clips:
        job.status = 'render_failed'; db.commit(); return

    video_clips = []
    motion_effects = ['zoom_in', 'pan_right', 'pan_left']
    for i, clip in enumerate(voice_clips):
        image_prompt = generate_intelligent_image_prompt(job_context, clip.text)
        image_path = generate_image(job_context, image_prompt, f"scene_{i}")
        if not image_path: continue
        
        video_output_path = str(output_manager.get_videos_directory() / f"scene_{i}.mp4")
        
        try:
            motion_type = motion_effects[i % len(motion_effects)]
            create_video_from_image(image_path, clip.audio_path, video_output_path, motion_type=motion_type)
            video_clips.append(video_output_path)
        except Exception as e:
            logger.error(f"Failed to create video from image for scene {i}: {e}")


    if not video_clips:
        job.status = 'render_failed'; db.commit(); return

    final_video_path = str(output_manager.get_videos_directory() / f"final_image_video_{script.id}.mp4")
    file_list_path = str(output_manager.get_job_directory() / "file_list.txt")
    with open(file_list_path, "w") as f:
        for vc in video_clips: f.write(f"file '{os.path.relpath(vc, output_manager.get_job_directory())}'\n")
    
    (ffmpeg.input(file_list_path, format='concat', safe=0)
     .output(final_video_path, c='copy').run(overwrite_output=True, capture_stdout=True, capture_stderr=True))
    os.remove(file_list_path)

    job.status = 'completed'; job.video_path = final_video_path
    db.commit()
    logger.info(f"Image-to-video composition successful! Final video at: {final_video_path}")

def main():
    from src.utils.output_manager import OutputManager
    from src.utils.cost_calculator import CostTracker

    db: Session = next(get_db())
    dummy_job = Job(idea="The History of AI", status="approved")
    db.add(dummy_job); db.commit(); db.refresh(dummy_job)
    dummy_script = Script(job_id=dummy_job.id, script_type='long_form', content="AI has a long and storied history. It all started with a simple question: Can machines think?", status='approved')
    db.add(dummy_script); db.commit(); db.refresh(dummy_script)

    output_manager = OutputManager(idea=dummy_job.idea)
    cost_tracker = CostTracker(output_dir=output_manager.get_job_directory())

    job_context = {"idea": dummy_job.idea, "job": dummy_job, "db_session": db, "output_manager": output_manager, "cost_tracker": cost_tracker}

    asyncio.run(run_video_composition(job_context, dummy_script))
    # compose_video_from_images(job_context, dummy_script)
    
    cost_tracker.save_costs()
    db.close()

if __name__ == "__main__":
    main() 