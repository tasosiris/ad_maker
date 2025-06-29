import os
import time
import ffmpeg
from dataclasses import dataclass
from typing import List, Optional
import re

# Adjust imports to match the project structure
from src.assets.fetcher import fetch_clips
from src.tts.voice import generate_voice, VoiceClip
from src.editing.ffmpeg_editor import compose_video
from src.database import Script, Job
from src.utils.output_manager import generate_metadata, save_video_with_metadata
from sqlalchemy.orm import Session
import json

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

def get_script(db: Session, script_id: int) -> Script:
    """Retrieves a script from the database."""
    return db.query(Script).filter(Script.id == script_id).first()

def run_video_composition(db: Session, script: Script):
    """
    Orchestrates the entire video creation process for a single approved script.
    """
    job = script.job
    print(f"\n===== Starting Video Composition for Script ID: {script.id} (Job: {job.idea}) =====")
    job.status = 'rendering'
    db.commit()

    # 1. Generate Voiceover from the script content
    print("\nStep 1: Generating Voiceover...")
    script_content = str(script.content or '')
    voice_clips = generate_voice(script_id=script.id, text=script_content)
    if not voice_clips:
        print(f"Error: Voiceover generation failed for script {script.id}. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return
    
    print(f"DEBUG: Generated {len(voice_clips)} audio clips from script sentences.")
    
    # 2. Measure audio clips and prepare scenes
    print("\nStep 2: Measuring audio clips and preparing scenes...")
    scenes: List[Scene] = []
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
                print(f"DEBUG: Audio clip '{os.path.basename(clip.audio_path)}' - Duration: {duration:.2f}s - Text: '{clip.text[:30]}...'")

                # 3. Fetch a relevant video for this specific sentence
                print(f"  -> Fetching video for: '{timed_clip.text}'")
                video_asset = fetch_relevant_clip(timed_clip, job)
                
                if video_asset:
                    scenes.append(Scene(voice_clip=timed_clip, video_path=video_asset))
                else:
                    print(f"  WARNING: Could not find a suitable video for the sentence. It will be skipped.")

            except Exception as e:
                print(f"WARNING: Error probing audio clip {clip.audio_path}: {e}")
        else:
            print(f"WARNING: Audio clip file not found: {clip.audio_path}")
    
    if not scenes:
        print("ERROR: No scenes could be created. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return

    print(f"DEBUG: Created {len(scenes)} scenes for the video. Total audio duration: {total_audio_duration:.2f}s")
    
    # 4. Compose the final video from scenes
    print("\n--- Voice Clips for Final Video ---")
    for i, scene in enumerate(scenes):
        print(f"Clip {i+1}: \"{scene.voice_clip.text}\"")
    print("------------------------------------")
    
    print("\nStep 4: Composing Video with FFmpeg...")
    timestamp = int(time.time())
    output_dir = f"output/{job.category.replace(' ', '_')}/{job.idea.replace(' ', '_')}/{script.script_type}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"script_{script.id}_{timestamp}.mp4")
    
    # Extract paths for the editor function
    video_paths = [scene.video_path for scene in scenes]
    audio_paths = [scene.voice_clip.audio_path for scene in scenes]
    
    final_video_path = compose_video(video_paths, audio_paths, output_path)
    
    if final_video_path and os.path.exists(final_video_path):
        try:
            # Verify the output video has a reasonable duration
            output_info = ffmpeg.probe(final_video_path)
            output_duration = float(output_info['format']['duration'])
            print(f"DEBUG: Final output video duration: {output_duration:.2f}s")
            
            if output_duration < 1.0:
                print(f"WARNING: Final video is too short ({output_duration:.2f}s)!")
                job.status = 'render_failed'
                db.commit()
            else:
                # Save metadata alongside the video
                save_video_metadata(job, script, final_video_path)
                
                job.status = 'done'
                db.commit()
                print(f"\n===== Finished Video Composition for: {job.idea} =====")
                print(f"Final video saved to: {final_video_path}")
                print(f"Metadata saved to: {final_video_path.replace('.mp4', '.json')}")
        except Exception as e:
            print(f"ERROR: Failed to probe final video: {e}")
            job.status = 'render_failed'
            db.commit()
    else:
        job.status = 'render_failed'
        db.commit()
        print(f"\n===== Video Composition FAILED for: {job.idea} =====")

def fetch_relevant_clip(timed_clip: TimedVoiceClip, job: Job) -> Optional[str]:
    """
    Fetches a video clip relevant to the sentence text. It aims to find a clip
    with a duration as close as possible to the audio duration, but not shorter.
    """
    keywords = extract_keywords(timed_clip.text)
    query = f"{keywords} {job.category}" if keywords else f"{job.idea} {job.category}"
    print(f"  -> Asset search query: '{query}'")

    video_assets = fetch_clips(query, num_clips=5)
    
    if not video_assets:
        print(f"  -> No initial video assets found. Trying a broader search...")
        fallback_query = f"{job.idea} {job.category}"
        video_assets = fetch_clips(fallback_query, num_clips=5)

    if not video_assets:
        print(f"  -> Fallback search also failed. No suitable clips found.")
        return None

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
                print(f"  -> WARNING: Could not probe candidate video {asset_path}: {e}")

    if best_clip:
        print(f"  -> Found best-fit clip: {os.path.basename(best_clip)} (Duration diff: {smallest_duration_diff:.2f}s)")
        return best_clip
    
    print(f"  -> WARNING: No fetched video clips met the duration requirement of {timed_clip.duration:.2f}s.")
    return None

def save_video_metadata(job: Job, script: Script, video_path: str):
    """
    Saves comprehensive metadata alongside the video file, including:
    - Script content
    - Product information
    - Affiliate details
    - Video metadata
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
        }
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
    
    print(f"  -> Saved metadata: {metadata_path}")
    print(f"  -> Saved script text: {script_path}")

def main(db: Session):
    """Demonstrates a full video composition workflow with a database script."""
    print("--- Finding an approved script to render ---")
    
    # Find an approved script that hasn't been rendered
    approved_script = db.query(Script).join(Job).filter(Job.status == 'approved', Script.status == 'approved').first()

    if not approved_script:
        print("No approved scripts ready for video composition.")
        # Create a dummy job and script for demonstration
        print("Creating a dummy approved job/script for demonstration...")
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
        print(f"Created dummy script with ID: {approved_script.id}")

    run_video_composition(db, approved_script)
    

if __name__ == "__main__":
    from src.database import get_db
    db_session = next(get_db())
    try:
        main(db_session)
    finally:
        db_session.close() 