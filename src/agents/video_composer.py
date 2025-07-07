import os
import time
import ffmpeg
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re
import random
import json
import subprocess
import shutil
from datetime import datetime

from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.utils.logger import logger
from src.assets.fetcher import fetch_clips, clear_video_cache
from src.tts.voice import generate_voice, VoiceClip
from src.editing.ffmpeg_editor import compose_video
from src.database import Script, Job
from src.utils.output_manager import generate_metadata, save_video_with_metadata
from sqlalchemy.orm import Session
from src.agents.prompt_enhancer import enhance_prompt
from src.agents.image_generator import generate_image
from src.agents.kling_animator import create_kling_video
from src.agents.text_overlay import create_video_with_text_overlay
from src.database import get_db, Job
from src.utils.file_organizer import FileOrganizer

# Initialize OpenAI client
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

COMMON_WORDS = set([
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'being', 'been',
    'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at',
    'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
    'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then',
    'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any',
    'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't',
    'can', 'will', 'just', 'don', 'should', 'now', 'd', 'll', 'm', 'o', 're',
    've', 'y', 'ain', 'aren', 'couldn', 'didn', 'doesn', 'hadn', 'hasn',
    'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn',
    'wasn', 'weren', 'won', 'wouldn', 'let', 's'
])

def extract_keywords(text: str, max_keywords: int = 5) -> str:
    """Extracts the most relevant keywords from a text sentence."""
    # Remove bracketed content like [HOOK]
    text = re.sub(r'\[.*?\]', '', text)
    # Remove punctuation and convert to lowercase
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter out common words
    keywords = [word for word in words if word not in COMMON_WORDS]
    
    # Return the most relevant keywords, joined into a string
    return ' '.join(keywords[:max_keywords])

def generate_intelligent_video_query(text: str, subject: str) -> str:
    """
    Uses GPT to intelligently determine what type of video would be most appropriate 
    for the given narration segment, then creates a targeted search query.
    """
    try:
        prompt = f"""
You are a documentary film assistant. Your task is to find the perfect B-roll footage for a specific line of narration.

Overall Documentary Subject: "{subject}"
Narration Line: "{text}"

Your task:
1. Analyze the narration line to understand its core meaning and visual potential.
2. Think about what visuals would best complement this narration in a documentary context.
3. Create a short, specific search query (3-5 words) for a stock video website.

Guidelines:
- For historical topics, think about archival footage, maps, or dramatic reenactments.
- For biographical topics, think about lifestyle shots, interviews, and locations.
- For scientific topics, think about animations, lab footage, or nature shots.
- Be specific. Instead of "car", try "vintage 1920s car". Instead of "space", try "nebula animation" or "saturn rings".

Respond with ONLY the search query, nothing else.

Examples:
- Narration: "In the heart of ancient Rome, gladiators battled for their lives."
  Query: "Colosseum historical reenactment"
  
- Narration: "The Great Barrier Reef is home to thousands of species of marine life."
  Query: "coral reef vibrant fish"
  
- Narration: "He trained relentlessly, day and night, for his shot at the championship."
  Query: "boxer training intense gym"

Your search query:"""

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,  # Lower temperature for more consistent results
            max_tokens=20  # Keep it short
        )
        
        ai_query = response.choices[0].message.content.strip().replace('"', '').replace("'", '')
        
        logger.info(f"  -> AI-generated video query: '{ai_query}'")
        return ai_query
        
    except Exception as e:
        logger.warning(f"Failed to generate AI query: {e}. Falling back to keyword extraction.")
        # Fallback to original method
        keywords = extract_keywords(text)
        return f"{keywords} {subject}" if keywords else subject

@dataclass
class TimedVoiceClip:
    """Extends VoiceClip to include the audio duration."""
    text: str
    audio_path: str
    duration: float

@dataclass
class Scene:
    """Represents a scene with synchronized audio and video."""
    voice_clip: TimedVoiceClip
    video_path: str

@dataclass
class SceneMapping:
    """Represents detailed information about how a scene was created."""
    sentence: str
    query_used: str
    fallback_query: Optional[str]
    video_path: str
    video_filename: str
    duration_match: float

def get_script(db: Session, script_id: int) -> Script:
    """Retrieves a script from the database."""
    return db.query(Script).filter(Script.id == script_id).first()

def get_music_tracks(music_dir: str = "src/assets/music") -> List[str]:
    """Finds available music tracks in the specified directory."""
    if not os.path.isdir(music_dir):
        return []
    
    supported_formats = ('.mp3', '.wav', '.aac', '.m4a')
    music_files = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(supported_formats)]
    
    if music_files:
        logger.info(f"Found {len(music_files)} music tracks: {', '.join(os.path.basename(p) for p in music_files)}")
    else:
        logger.warning(f"No music tracks found in '{music_dir}'.")
        
    return music_files

def run_video_composition(db: Session, script: Script):
    """
    Orchestrates the entire video creation process for a single approved script.
    """
    job = script.job
    logger.info(f"===== Starting Video Composition for Script ID: {script.id} (Job: {job.idea}) =====")
    job.status = 'rendering'
    db.commit()

    # Clear video cache before starting
    clear_video_cache()

    # 1. Generate Voiceover from the script content
    logger.info("Step 1: Generating Voiceover...")
    script_content = str(script.content or '')
    voice_clips = generate_voice(script_id=script.id, text=script_content)
    if not voice_clips:
        logger.error(f"Voiceover generation failed for script {script.id}. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return
    
    logger.info(f"Generated {len(voice_clips)} audio clips from script sentences.")
    
    # 2. Measure audio clips and prepare scenes
    logger.info("Step 2: Measuring audio clips and preparing scenes...")
    scenes: List[Scene] = []
    scene_mappings: List[SceneMapping] = []
    total_audio_duration = 0
    
    for clip in voice_clips:
        if os.path.exists(clip.audio_path):
            try:
                audio_info = ffmpeg.probe(clip.audio_path)
                duration = float(audio_info['format']['duration'])
                timed_clip = TimedVoiceClip(
                    text=clip.text, 
                    audio_path=clip.audio_path, 
                    duration=duration
                )
                total_audio_duration += duration
                logger.info(f"Audio clip '{os.path.basename(clip.audio_path)}' - Duration: {duration:.2f}s - Text: '{clip.text[:30]}...'")

                # 3. Fetch a relevant video for this specific sentence
                logger.info(f"  -> Fetching video for: '{timed_clip.text}'")
                video_asset, mapping = fetch_relevant_clip(timed_clip, job)
                scene_mappings.append(mapping)
                
                if video_asset:
                    scenes.append(Scene(voice_clip=timed_clip, video_path=video_asset))
                else:
                    logger.warning(f"Could not find a suitable video for the sentence. It will be skipped.")

            except Exception as e:
                logger.error(f"Error probing audio clip {clip.audio_path}: {e}")
        else:
            logger.warning(f"Audio clip file not found: {clip.audio_path}")
    
    if not scenes:
        logger.error("No scenes could be created. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return

    logger.info(f"Created {len(scenes)} scenes for the video. Total audio duration: {total_audio_duration:.2f}s")
    
    # 4. Compose the final video from scenes
    logger.info("--- Voice Clips for Final Video ---")
    for i, scene in enumerate(scenes):
        logger.info(f"Clip {i+1}: \"{scene.voice_clip.text}\"")
    logger.info("------------------------------------")
    
    logger.info("Step 4: Composing Video with FFmpeg...")
    
    # Initialize file organizer for stock video composition
    organizer = FileOrganizer()
    project_dirs = organizer.create_project_structure(
        project_name=job.idea,
        script_type=script.script_type,
        timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    
    output_path = str(project_dirs['temp'] / f"temp_final_video.mp4")
    
    # Extract paths for the editor function
    video_paths = [scene.video_path for scene in scenes]
    audio_paths = [scene.voice_clip.audio_path for scene in scenes]
    
    # 5. Select background music
    logger.info("Step 5: Selecting Background Music...")
    music_tracks = get_music_tracks()
    background_music = random.choice(music_tracks) if music_tracks else None
    
    if background_music:
        logger.info(f"Selected background music: {os.path.basename(background_music)}")
    else:
        logger.info("No background music will be added.")

    final_video_path = compose_video(
        video_paths, 
        audio_paths, 
        output_path,
        background_music_path=background_music
    )
    
    if final_video_path and os.path.exists(final_video_path):
        try:
            # Verify the output video has a reasonable duration
            output_info = ffmpeg.probe(final_video_path)
            output_duration = float(output_info['format']['duration'])
            logger.info(f"Final output video duration: {output_duration:.2f}s")
            
            if output_duration < 1.0:
                logger.warning(f"Final video is too short ({output_duration:.2f}s)!")
                job.status = 'render_failed'
            else:
                # Organize assets and save final video
                logger.info("Step 6: Organizing assets and saving final video...")
                
                # Organize video assets that were fetched
                video_assets = [scene.video_path for scene in scenes if scene.video_path]
                if video_assets:
                    # Copy video assets to project structure (they're from stock video cache)
                    asset_dir = project_dirs['video_clips']
                    for i, asset_path in enumerate(video_assets):
                        if os.path.exists(asset_path):
                            asset_filename = f"stock_video_{i+1:02d}_{os.path.basename(asset_path)}"
                            new_asset_path = asset_dir / asset_filename
                            try:
                                shutil.copy2(asset_path, new_asset_path)
                                logger.info(f"Organized stock video: {asset_filename}")
                            except Exception as e:
                                logger.warning(f"Failed to organize stock video {asset_path}: {e}")
                
                # Organize audio files
                audio_paths = [scene.voice_clip.audio_path for scene in scenes]
                voice_clips = [scene.voice_clip for scene in scenes]
                organized_audio_paths = organizer.organize_audio_files(audio_paths, project_dirs, voice_clips)
                
                # Save final video with organized structure
                organized_final_path = organizer.save_final_video(final_video_path, project_dirs, job.idea, script.script_type)
                
                # Create comprehensive metadata
                metadata = {
                    "video_info": {
                        "title": job.idea.replace('_', ' ').title(),
                        "script_type": script.script_type,
                        "generation_method": "stock_video_composition"
                    },
                    "script_content": {
                        "full_script": str(script.content or ''),
                        "script_id": script.id,
                        "job_id": job.id
                    },
                    "generation_info": {
                        "idea": job.idea,
                        "research_summary": job.research_summary,
                        "created_at": str(job.created_at),
                        "total_scenes": len(scenes),
                        "video_duration": output_duration
                    },
                    "scene_mappings": [m.__dict__ for m in scene_mappings],
                    "assets_info": {
                        "stock_videos_used": len(video_assets),
                        "audio_clips": len(organized_audio_paths),
                        "background_music": background_music is not None
                    }
                }
                
                # Save project metadata
                organizer.save_project_metadata(project_dirs, metadata, job.idea, script.script_type)
                
                # Clean up temporary files
                organizer.cleanup_temp_files(project_dirs)
                
                job.video_path = organized_final_path
                job.status = 'done'
                logger.info(f"===== Finished Video Composition for: {job.idea} =====")
                logger.info(f"Final video saved at: {organized_final_path}")
                logger.info(f"📁 Project organized at: {project_dirs['project_root']}")
        except Exception as e:
            logger.error(f"Failed to process final video: {e}")
            job.status = 'render_failed'
        finally:
            db.commit()
    else:
        job.status = 'render_failed'
        db.commit()
        logger.error(f"===== Video Composition FAILED for: {job.idea} =====")

def fetch_relevant_clip(timed_clip: TimedVoiceClip, job: Job) -> tuple[Optional[str], SceneMapping]:
    """
    Fetches the most relevant video clip for a sentence and returns its path and mapping info.
    """
    query = generate_intelligent_video_query(timed_clip.text, subject=job.idea)
    
    # Try to find a video that's slightly longer than the audio
    target_duration = timed_clip.duration

    video_assets = fetch_clips(query, num_clips=5)
    
    fallback_query = None
    if not video_assets:
        logger.warning(f"No initial video assets found. Trying a broader search...")
        # Try with just keywords as fallback
        keywords = extract_keywords(timed_clip.text)
        fallback_query = f"{keywords} {job.idea}" if keywords else f"{job.idea}"
        logger.info(f"  -> Fallback query: '{fallback_query}'")
        video_assets = fetch_clips(fallback_query, num_clips=5)

    if not video_assets:
        logger.warning(f"Fallback search also failed. No suitable clips found.")
        mapping = SceneMapping(
            sentence=timed_clip.text,
            query_used=query,
            fallback_query=fallback_query,
            video_path="",
            video_filename="No video found",
            duration_match=0.0
        )
        return None, mapping

    # Find the best-fitting clip
    best_clip = None
    smallest_duration_diff = float('inf')

    for asset_path in video_assets:
        if os.path.exists(asset_path):
            try:
                video_info = ffmpeg.probe(asset_path)
                duration = float(video_info['format']['duration'])
                
                if duration >= timed_clip.duration:
                    duration_diff = duration - timed_clip.duration
                    if duration_diff < smallest_duration_diff:
                        smallest_duration_diff = duration_diff
                        best_clip = asset_path
            except Exception as e:
                logger.error(f"  -> Could not probe candidate video {asset_path}: {e}")

    if best_clip:
        logger.info(f"  -> Found best-fit clip: {os.path.basename(best_clip)} (Duration diff: {smallest_duration_diff:.2f}s)")
        mapping = SceneMapping(
            sentence=timed_clip.text,
            query_used=query,
            fallback_query=fallback_query,
            video_path=best_clip,
            video_filename=os.path.basename(best_clip),
            duration_match=smallest_duration_diff
        )
        return best_clip, mapping
    
    logger.warning(f"No fetched video clips met the duration requirement of {timed_clip.duration:.2f}s.")
    mapping = SceneMapping(
        sentence=timed_clip.text,
        query_used=query,
        fallback_query=fallback_query,
        video_path="",
        video_filename="No suitable video found",
        duration_match=0.0
    )
    return None, mapping

def save_video_metadata(job: Job, script: Script, video_path: str, scene_mappings: List[SceneMapping]):
    """
    Saves comprehensive metadata alongside the video file, including:
    - Script content
    - Research summary
    - Detailed scene mappings (queries and videos used)
    """
    # Generate a clean title from the job idea
    title = job.idea.replace('_', ' ').title()
    if len(title) > 100:  # YouTube title limit
        title = title[:97] + "..."
    
    script_content = str(script.content or '')
    
    # Generate comprehensive metadata
    metadata = {
        "video_info": {
            "title": title,
            "script_type": script.script_type
        },
        "script_content": {
            "full_script": script_content,
            "script_id": script.id
        },
        "generation_info": {
            "idea": job.idea,
            "research_summary": job.research_summary,
            "created_at": str(job.created_at)
        },
        "scene_mappings": [m.__dict__ for m in scene_mappings]
    }
    
    # Save metadata to JSON file
    metadata_path = video_path.replace('.mp4', '.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Also save a simple text file with just the script for easy reading
    script_path = video_path.replace('.mp4', '_script.txt')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(f"--- DOCUMENTARY SCRIPT ---\n\n")
        f.write(f"TITLE: {title}\n")
        f.write(f"IDEA: {job.idea}\n\n")
        f.write(f"{'='*50}\n")
        f.write(f"SCRIPT CONTENT (SENT TO TTS):\n")
        f.write(f"{'='*50}\n\n")
        f.write(script_content)

    logger.info(f"  -> Saved metadata: {metadata_path}")
    logger.info(f"  -> Saved script text: {script_path}")

def main(db: Session):
    """Demonstrates a full video composition workflow with a database script."""
    logger.info("--- Finding an approved script to render ---")
    
    # Find an approved script that hasn't been rendered
    approved_script = db.query(Script).join(Job).filter(Job.status == 'approved', Script.status == 'approved').first()

    if not approved_script:
        logger.warning("No approved scripts ready for video composition.")
        # Create a dummy job and script for demonstration
        logger.info("Creating a dummy approved job/script for demonstration...")
        dummy_job = Job(idea="Live Demo Smart Pen", category="Productivity Tools", status="approved")
        db.add(dummy_job)
        db.commit()
        db.refresh(dummy_job)
        
        approved_script = Script(
            job_id=dummy_job.id,
            script_type='long_form',
            content="This is a live test of the video composer. Let's see if it can take this text, generate a voice, find some clips about 'smart pens' and 'productivity', and combine them all into a video. This sentence adds a bit more length to the audio.",
            status='approved'
        )
        db.add(approved_script)
        db.commit()
        db.refresh(approved_script)
        logger.info(f"Created dummy script with ID: {approved_script.id}")

    run_video_composition(db, approved_script)
    

def compose_video_from_images(job_id: int):
    """
    Main function to compose the video from generated images.
    Orchestrates the video creation process from script to final video.
    """
    db = next(get_db())
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job with id {job_id} not found.")
        return

    script = next((s for s in job.scripts if s.status == 'approved'), None)
    if not script:
        logger.error(f"No approved script found for job {job_id}")
        return

    logger.info(f"===== Starting Image-Based Video Composition for Job ID: {job.id} (Idea: {job.idea}) =====")
    job.status = 'rendering_images'
    db.commit()

    # Initialize file organizer
    organizer = FileOrganizer()
    project_dirs = organizer.create_project_structure(
        project_name=job.idea,
        script_type=script.script_type,
        timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    # 1. Generate Voiceover from the script content
    logger.info("Step 1: Generating Voiceover...")
    script_content = str(script.content or '')
    voice_clips = generate_voice(script_id=script.id, text=script_content)
    if not voice_clips:
        logger.error(f"Voiceover generation failed for script {script.id}. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return
    logger.info(f"Generated {len(voice_clips)} audio clips from script sentences.")

    # Organize audio files
    audio_paths = [clip.audio_path for clip in voice_clips]
    organized_audio_paths = organizer.organize_audio_files(audio_paths, project_dirs, voice_clips)
    
    generated_images = []
    video_clips = []
    
    for i, clip in enumerate(voice_clips):
        logger.info(f"\n--- Processing scene {i+1}/{len(voice_clips)} ---")
        logger.info(f"Phrase: {clip.text}")

        # Step 2: Enhance prompt
        logger.info("Step 2: Enhancing prompt...")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        enhanced_prompt = enhance_prompt(clip.text, client)
        
        # Step 3: Generate image
        logger.info(f"Step 3: Generating image for prompt: '{enhanced_prompt[:50]}...'")
        generated_image_path = generate_image(enhanced_prompt)

        if not generated_image_path:
            logger.error("Image generation failed. Skipping this scene.")
            continue
            
        generated_images.append(generated_image_path)
        
        # 4. Create animated video using Kling AI
        logger.info("Step 4: Creating animated video clip using Kling AI...")
        clip_output_path = str(project_dirs['temp'] / f"scene_{i}.mp4")
        
        try:
            success = create_kling_video(
                image_path=generated_image_path,
                audio_path=clip.audio_path,
                output_path=clip_output_path,
                original_prompt=enhanced_prompt,
                voice_text=clip.text,
                model_type="standard"  # Use "pro" for higher quality but higher cost
            )
            
            if success:
                # 5. Add intelligent text overlay to the video
                logger.info("Step 5: Adding intelligent text overlay...")
                overlay_output_path = str(project_dirs['temp'] / f"scene_{i}_with_text.mp4")
                
                # Get video duration from the audio clip
                try:
                    import ffmpeg
                    audio_info = ffmpeg.probe(clip.audio_path)
                    duration = float(audio_info['format']['duration'])
                except Exception as e:
                    logger.warning(f"Could not determine audio duration: {e}. Using default 5 seconds.")
                    duration = 5.0
                
                # Add text overlay if appropriate
                overlay_success = create_video_with_text_overlay(
                    video_path=clip_output_path,
                    voice_text=clip.text,
                    enhanced_prompt=enhanced_prompt,
                    duration=duration,
                    output_path=overlay_output_path
                )
                
                if overlay_success:
                    video_clips.append(overlay_output_path)
                    logger.info(f"Successfully created video with text overlay: {overlay_output_path}")
                else:
                    # Fallback to original video if text overlay fails
                    video_clips.append(clip_output_path)
                    logger.info(f"Using original Kling AI video: {clip_output_path}")
            else:
                logger.error(f"Kling AI video generation failed for scene {i}")
        except Exception as e:
            logger.error(f"Failed to create Kling AI video for {generated_image_path}: {e}")

    if not video_clips:
        logger.error("No video clips were created. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return

    # Organize generated images
    logger.info("Step 5.1: Organizing generated images...")
    organized_image_paths = organizer.organize_generated_images(generated_images, project_dirs, voice_clips)

    # Organize video clips
    logger.info("Step 5.2: Organizing video clips...")
    organized_video_clips = organizer.organize_video_clips(video_clips, project_dirs, voice_clips)

    # 6. Combine all video clips into one
    logger.info("\nStep 6: Combining all video clips into final video...")
    temp_final_path = str(project_dirs['temp'] / "temp_final_video.mp4")
    
    # Use the organized audio paths that correspond to successful video clips
    successful_audio_paths = [organized_audio_paths[i] for i in range(len(organized_video_clips))]

    final_video = compose_video(organized_video_clips, successful_audio_paths, temp_final_path)

    if final_video and os.path.exists(final_video):
        # Save final video with organized structure
        logger.info("Step 7: Saving final video with organized structure...")
        final_video_path = organizer.save_final_video(final_video, project_dirs, job.idea, script.script_type)
        
        # Create comprehensive metadata
        metadata = {
            "video_info": {
                "title": job.idea.replace('_', ' ').title(),
                "script_type": script.script_type,
                "generation_method": "kling_ai_animation"
            },
            "script_content": {
                "full_script": script_content,
                "script_id": script.id,
                "job_id": job.id
            },
            "generation_info": {
                "idea": job.idea,
                "research_summary": job.research_summary,
                "created_at": str(job.created_at),
                "total_scenes": len(voice_clips),
                "successful_scenes": len(organized_video_clips)
            },
            "assets_info": {
                "images_generated": len(organized_image_paths),
                "audio_clips": len(organized_audio_paths),
                "video_clips": len(organized_video_clips)
            }
        }
        
        # Save project metadata
        organizer.save_project_metadata(project_dirs, metadata, job.idea, script.script_type)
        
        # Clean up temporary files
        organizer.cleanup_temp_files(project_dirs)
        
        job.video_path = final_video_path
        job.status = 'done'
        db.commit()
        logger.info(f"\n✅ Video composition complete! Final video saved at: {final_video_path}")
        logger.info(f"📁 Project organized at: {project_dirs['project_root']}")
    else:
        job.status = 'render_failed'
        db.commit()
        logger.error("Failed to compose the final video.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        job_id = int(sys.argv[1])
        compose_video_from_images(job_id)
    else:
        print("Please provide a job ID.") 