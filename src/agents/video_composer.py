import os
import time
import ffmpeg
from dataclasses import dataclass
from typing import List

# Adjust imports to match the project structure
from src.assets.fetcher import fetch_clips
from src.tts.voice import generate_voice
from src.editing.ffmpeg_editor import compose_video
from src.database import Script, Job
from sqlalchemy.orm import Session

@dataclass
class VideoCompositionRequest:
    idea: str
    category: str
    script_content: str
    video_type: str  # 'long_form' or 'short_form'

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
    # Use the script's full content to generate audio files
    audio_clips = generate_voice(script_id=script.id, text=script.content)
    if not audio_clips:
        print(f"Error: Voiceover generation failed for script {script.id}. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return
    
    print(f"DEBUG: Generated {len(audio_clips)} audio clips")
    
    # Verify audio clips exist and have valid durations
    valid_audio_clips = []
    total_audio_duration = 0
    for audio_clip in audio_clips:
        if os.path.exists(audio_clip):
            try:
                audio_info = ffmpeg.probe(audio_clip)
                duration = float(audio_info['format']['duration'])
                print(f"DEBUG: Audio clip: {os.path.basename(audio_clip)} - Duration: {duration:.2f}s")
                total_audio_duration += duration
                valid_audio_clips.append(audio_clip)
            except Exception as e:
                print(f"WARNING: Error probing audio clip {audio_clip}: {e}")
        else:
            print(f"WARNING: Audio clip file not found: {audio_clip}")
    
    print(f"DEBUG: Total valid audio clips: {len(valid_audio_clips)}, total duration: {total_audio_duration:.2f}s")
    
    if len(valid_audio_clips) == 0:
        print("ERROR: No valid audio clips available. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return

    # 2. Fetch Video Assets based on the job's core idea
    print("\nStep 2: Fetching Video Assets...")
    # Use a query related to the main idea to get relevant b-roll
    asset_query = f"{job.idea} {job.category}"
    num_clips = 20 # Fetch more clips to have enough variety for the video length
    video_assets = fetch_clips(asset_query, num_clips=num_clips, min_duration=2.0)
    if not video_assets:
        print(f"Error: Asset fetching failed for job {job.id}. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return
    
    # Verify we have valid video assets
    valid_video_assets = []
    total_video_duration = 0
    for asset in video_assets:
        if os.path.exists(asset):
            try:
                video_info = ffmpeg.probe(asset)
                duration = float(video_info['format']['duration'])
                print(f"DEBUG: Video asset: {os.path.basename(asset)} - Duration: {duration:.2f}s")
                if duration >= 1.0:  # Only use videos with at least 1 second duration
                    total_video_duration += duration
                    valid_video_assets.append(asset)
                else:
                    print(f"WARNING: Skipping too short video asset: {duration:.2f}s")
            except Exception as e:
                print(f"WARNING: Error probing video asset {asset}: {e}")
        else:
            print(f"WARNING: Video asset file not found: {asset}")
    
    print(f"DEBUG: Total valid video assets: {len(valid_video_assets)}, total duration: {total_video_duration:.2f}s")
    
    if len(valid_video_assets) == 0:
        print("ERROR: No valid video assets available. Aborting.")
        job.status = 'render_failed'
        db.commit()
        return

    # 3. Compose the final video
    print("\nStep 3: Composing Video with FFmpeg...")
    timestamp = int(time.time())
    output_dir = f"output/{job.category.replace(' ', '_')}/{job.idea.replace(' ', '_')}/{script.script_type}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"script_{script.id}_{timestamp}.mp4")
    
    # If needed, loop video assets to ensure we have enough content
    if total_video_duration < total_audio_duration:
        print(f"DEBUG: Video duration ({total_video_duration:.2f}s) shorter than audio ({total_audio_duration:.2f}s)")
        # Loop videos until we have enough content
        repeat_factor = int(total_audio_duration / total_video_duration) + 1
        valid_video_assets = valid_video_assets * repeat_factor
        print(f"DEBUG: Extended video assets to {len(valid_video_assets)} clips")
    
    final_video_path = compose_video(valid_video_assets, valid_audio_clips, output_path)
    
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
                job.status = 'done'
                db.commit()
                print(f"\n===== Finished Video Composition for: {job.idea} =====")
                print(f"Final video saved to: {final_video_path}")
        except Exception as e:
            print(f"ERROR: Failed to probe final video: {e}")
            job.status = 'render_failed'
            db.commit()
    else:
        job.status = 'render_failed'
        db.commit()
        print(f"\n===== Video Composition FAILED for: {job.idea} =====")

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