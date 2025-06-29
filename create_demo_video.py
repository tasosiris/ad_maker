import os
import time
from sqlalchemy.orm import Session
from src.database import get_db, Script, Job
from src.tts.voice import generate_voice
from src.assets.fetcher import fetch_clips
from src.editing.ffmpeg_editor import compose_video

def create_demo_video():
    """
    Create a demo video using hardcoded script content
    """
    print("Creating demo video with hardcoded script content...")
    
    # Use script ID 10 for consistency
    script_id = 10
    
    # Hardcoded script content
    script_content = """
    Introducing the Portable AR Headset - the ultimate tool for remote engineering and design collaboration.
    
    This lightweight, powerful headset combines high-resolution holographic displays with precision hand tracking.
    
    Engineers can manipulate 3D models in real-time while communicating with team members across the globe.
    
    Built-in spatial mapping creates shared virtual workspaces, enabling multiple users to collaborate on the same project simultaneously.
    
    With 6-hour battery life and industrial-grade durability, it's ready for any worksite.
    
    The Portable AR Headset - transforming how design teams work together, no matter the distance.
    """
    
    # Clear any existing TTS files for this script
    tts_dir = "temp/tts"
    for file in os.listdir(tts_dir):
        if file.startswith(f"tts_{script_id}_"):
            file_path = os.path.join(tts_dir, file)
            print(f"Removing old TTS file: {file_path}")
            os.remove(file_path)
    
    # 1. Generate voice clips
    print("\nStep 1: Generating voiceover...")
    audio_clips = generate_voice(script_id, script_content)
    if not audio_clips:
        print("Error: Failed to generate audio clips.")
        return
    
    # Verify audio clips
    total_audio_duration = 0
    valid_audio_clips = []
    for audio_clip in audio_clips:
        if os.path.exists(audio_clip):
            try:
                import ffmpeg
                audio_info = ffmpeg.probe(audio_clip)
                duration = float(audio_info['format']['duration'])
                print(f"Audio clip: {os.path.basename(audio_clip)} - Duration: {duration:.2f}s")
                total_audio_duration += duration
                valid_audio_clips.append(audio_clip)
            except Exception as e:
                print(f"Warning: Error probing audio clip {audio_clip}: {e}")
        else:
            print(f"Warning: Audio clip file not found: {audio_clip}")
    
    print(f"Total valid audio clips: {len(valid_audio_clips)}, total duration: {total_audio_duration:.2f}s")
    
    # 2. Use the existing demo videos
    print("\nStep 2: Using demo video assets...")
    demo_dir = "temp/demo_assets"
    os.makedirs(demo_dir, exist_ok=True)
    
    video_assets = []
    for i in range(1, 6):  # Use 5 demo videos
        video_path = os.path.join(demo_dir, f"demo_video_{i}.mp4")
        if os.path.exists(video_path):
            video_assets.append(video_path)
        else:
            # Create a demo video if it doesn't exist
            try:
                import ffmpeg
                duration = 5  # 5 second demo video
                color = f"color=c=blue:s=1280x720:d={duration}"
                if i % 3 == 0:
                    color = f"color=c=purple:s=1280x720:d={duration}"
                elif i % 3 == 1:
                    color = f"color=c=teal:s=1280x720:d={duration}"
                
                ffmpeg.input(color, f='lavfi').output(video_path).run(overwrite_output=True)
                video_assets.append(video_path)
                print(f"Created demo video: {video_path}")
            except Exception as e:
                print(f"Error: Failed to create demo video: {e}")
    
    if not video_assets:
        print("Error: Failed to get any video assets.")
        return
    
    # 3. Compose the video
    print("\nStep 3: Composing video...")
    timestamp = int(time.time())
    output_dir = "output/Demo_Video"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"demo_video_{timestamp}.mp4")
    
    final_video = compose_video(video_assets, valid_audio_clips, output_path)
    
    if final_video and os.path.exists(final_video):
        print(f"\nSuccessfully created demo video: {final_video}")
    else:
        print("\nFailed to create demo video.")

if __name__ == "__main__":
    create_demo_video() 