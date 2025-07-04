import os
import time
import ffmpeg
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re
import random
import json

from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.utils.logger import logger
from src.assets.fetcher import fetch_clips, clear_video_cache
from src.tts.voice import generate_voice, VoiceClip
from src.editing.ffmpeg_editor import compose_video
from src.database import Script, Job
from src.utils.output_manager import generate_metadata, save_video_with_metadata
from sqlalchemy.orm import Session

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

def generate_intelligent_video_query(text: str, category: str, idea: str) -> str:
    """
    Uses GPT to intelligently determine what type of video would be most appropriate 
    for the given narration segment, then creates a targeted search query.
    """
    try:
        prompt = f"""
You are a video content strategist. Given a narration segment from a video script, determine what type of background video would be most visually engaging and appropriate.

Narration segment: "{text}"
Product category: "{category}"
Overall video idea: "{idea}"

Your task:
1. Analyze the narration to understand what's being communicated
2. Determine what type of visual would best support this narration
3. Create a short, specific search query (3-5 words) that would find the perfect background video

Guidelines:
- For product demonstrations: focus on the product in use
- For emotional appeals: focus on people, lifestyle, or scenarios
- For statistics/facts: focus on relevant contexts or environments
- For problems/solutions: focus on the problem scenario or solution in action
- Keep it simple and specific - avoid generic terms

Respond with ONLY the search query, nothing else.

Examples:
- Narration: "Tired of struggling with dull knives that can't even cut a tomato?"
  Query: "struggling cutting tomato knife"
  
- Narration: "This revolutionary blender changed my morning routine completely"
  Query: "person making smoothie blender"
  
- Narration: "Studies show that 80% of people don't get enough sleep"
  Query: "tired person bedroom insomnia"

Your search query:"""

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=20  # Keep it short
        )
        
        ai_query = response.choices[0].message.content.strip()
        
        # Clean up the query and add category for better results
        ai_query = ai_query.replace('"', '').replace("'", '').strip()
        final_query = f"{ai_query} {category}"
        
        logger.info(f"  -> AI-generated video query: '{final_query}'")
        return final_query
        
    except Exception as e:
        logger.warning(f"Failed to generate AI query: {e}. Falling back to keyword extraction.")
        # Fallback to original method
        keywords = extract_keywords(text)
        return f"{keywords} {category}" if keywords else f"{idea} {category}"

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
    timestamp = int(time.time())
    # Shorten the directory path to avoid filesystem limits
    safe_category = job.category.replace(' ', '_')[:20]
    safe_idea = job.idea.replace(' ', '_')[:30]
    output_dir = f"output/{safe_category}/{safe_idea}/{script.script_type}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"script_{script.id}_{timestamp}.mp4")
    
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
                db.commit()
            else:
                # Save metadata alongside the video
                save_video_metadata(job, script, final_video_path, scene_mappings)
                
                job.status = 'done'
                db.commit()
                logger.info(f"===== Finished Video Composition for: {job.idea} =====")
                logger.info(f"Final video saved to: {final_video_path}")
                logger.info(f"Metadata saved to: {final_video_path.replace('.mp4', '.json')}")
        except Exception as e:
            logger.error(f"Failed to probe final video: {e}")
            job.status = 'render_failed'
            db.commit()
    else:
        job.status = 'render_failed'
        db.commit()
        logger.error(f"===== Video Composition FAILED for: {job.idea} =====")

def fetch_relevant_clip(timed_clip: TimedVoiceClip, job: Job) -> tuple[Optional[str], SceneMapping]:
    """
    Fetches a video clip relevant to the sentence text using AI-powered query generation.
    Returns both the video path and detailed mapping information.
    """
    # Use AI to generate an intelligent search query
    query = generate_intelligent_video_query(timed_clip.text, job.category, job.idea)
    
    video_assets = fetch_clips(query, num_clips=5)
    
    fallback_query = None
    if not video_assets:
        logger.warning(f"No initial video assets found. Trying a broader search...")
        # Try with just keywords as fallback
        keywords = extract_keywords(timed_clip.text)
        fallback_query = f"{keywords} {job.category}" if keywords else f"{job.idea} {job.category}"
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
    - Product information
    - Affiliate details
    - Video metadata
    - Detailed scene mappings (queries and videos used)
    """
    # Generate a clean title from the job idea
    title = job.idea.replace('_', ' ').title()
    if len(title) > 100:  # YouTube title limit
        title = title[:97] + "..."
    
    # Create description with script content
    script_content = str(script.content or '')
    description_parts = []
    
    if script_content:
        # Extract first few sentences for description
        sentences = script_content.split('.')[:3]  # First 3 sentences
        short_description = '. '.join(sentences).strip()
        if short_description and not short_description.endswith('.'):
            short_description += '.'
        description_parts.append(short_description)
    
    if job.product_name:
        description_parts.append(f"\n🛍️ Featured Product: {job.product_name}")
        if job.product_url:
            description_parts.append(f"🔗 Product Link: {job.product_url}")
        if job.affiliate_commission:
            description_parts.append(f"💰 Affiliate Commission: {job.affiliate_commission}")
    
    description = '\n'.join(description_parts)
    
    # Generate tags from the idea and category
    tags = []
    if job.category:
        tags.extend(job.category.lower().replace('_', ' ').split())
    if job.product_name:
        # Extract meaningful words from product name
        product_words = [word.lower() for word in job.product_name.split() 
                        if len(word) > 2 and word.lower() not in COMMON_WORDS]
        tags.extend(product_words[:3])  # Limit to avoid too many tags
    
    # Add general tags
    tags.extend(['review', 'affiliate', 'product'])
    tags = list(set(tags))[:10]  # Remove duplicates and limit to 10 tags
    
    # Prepare affiliate links
    affiliate_links = {}
    if job.product_name and job.product_url:
        affiliate_links[job.product_name] = job.product_url
    
    # Convert scene mappings to serializable format
    scene_details = []
    for i, mapping in enumerate(scene_mappings):
        scene_details.append({
            "scene_number": i + 1,
            "sentence": mapping.sentence,
            "ai_query": mapping.query_used,
            "fallback_query": mapping.fallback_query,
            "video_used": mapping.video_filename,
            "video_path": mapping.video_path,
            "duration_match_seconds": mapping.duration_match
        })
    
    # Generate comprehensive metadata
    metadata = {
        "video_info": {
            "title": title,
            "description": description,
            "tags": tags,
            "category": job.category,
            "script_type": script.script_type,
            "duration_seconds": None  # Will be filled if needed
        },
        "script_content": {
            "full_script": script_content,
            "script_id": script.id,
            "job_id": job.id
        },
        "product_info": {
            "name": job.product_name,
            "url": job.product_url,
            "affiliate_commission": job.affiliate_commission
        },
        "affiliate_links": affiliate_links,
        "generation_info": {
            "idea": job.idea,
            "category": job.category,
            "created_at": str(job.created_at),
            "script_status": script.status
        },
        "scene_mappings": scene_details
    }
    
    # Save metadata to JSON file
    metadata_path = video_path.replace('.mp4', '.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Also save a simple text file with just the script for easy reading
    script_path = video_path.replace('.mp4', '_script.txt')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(f"TITLE: {title}\n")
        f.write(f"CATEGORY: {job.category}\n")
        f.write(f"IDEA: {job.idea}\n")
        if job.product_name:
            f.write(f"PRODUCT: {job.product_name}\n")
            f.write(f"COMMISSION: {job.affiliate_commission}\n")
            f.write(f"LINK: {job.product_url}\n")
        f.write(f"\n{'='*50}\n")
        f.write(f"SCRIPT CONTENT:\n")
        f.write(f"{'='*50}\n\n")
        f.write(script_content)
    
    # Save detailed scene mapping as a separate readable file
    mapping_path = video_path.replace('.mp4', '_scene_mapping.txt')
    with open(mapping_path, 'w', encoding='utf-8') as f:
        f.write(f"SCENE MAPPING REPORT\n")
        f.write(f"{'='*50}\n\n")
        f.write(f"Video: {os.path.basename(video_path)}\n")
        f.write(f"Total Scenes: {len(scene_details)}\n\n")
        
        for scene in scene_details:
            f.write(f"Scene {scene['scene_number']}:\n")
            f.write(f"  Sentence: \"{scene['sentence']}\"\n")
            f.write(f"  AI Query: \"{scene['ai_query']}\"\n")
            if scene['fallback_query']:
                f.write(f"  Fallback Query: \"{scene['fallback_query']}\"\n")
            f.write(f"  Video Used: {scene['video_used']}\n")
            f.write(f"  Duration Match: {scene['duration_match_seconds']:.2f}s\n")
            f.write(f"  {'-'*40}\n\n")
    
    logger.info(f"  -> Saved metadata: {metadata_path}")
    logger.info(f"  -> Saved script text: {script_path}")
    logger.info(f"  -> Saved scene mapping: {mapping_path}")

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
    

if __name__ == "__main__":
    from src.database import get_db
    db_session = next(get_db())
    try:
        main(db_session)
    finally:
        db_session.close() 