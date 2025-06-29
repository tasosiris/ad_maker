import ffmpeg
import os
import time
from typing import List
from src.config import VIDEO_RESOLUTION, VIDEO_FPS

TEMP_DIR = "temp/ffmpeg_temp"
os.makedirs(TEMP_DIR, exist_ok=True)

def get_video_resolution(resolution_str: str) -> (int, int):
    """Parses a resolution string like '1080p' into (width, height)."""
    if 'p' in resolution_str:
        height = int(resolution_str[:-1])
        # Assuming a 16:9 aspect ratio
        width = int(height * 16 / 9)
        return width, height
    # Add more formats if needed
    raise ValueError(f"Unsupported resolution format: {resolution_str}")

def compose_video(video_assets: List[str], audio_clips: List[str], output_path: str):
    """
    Constructs a video from assets and audio using real FFmpeg commands.
    Uses a simpler approach to avoid filter graph issues.
    """
    print("\n--- Starting Video Composition with FFmpeg ---")
    start_time = time.time()

    if not video_assets or not audio_clips:
        print("Error: No video or audio assets provided.")
        return None
    
    # Use a two-pass approach to avoid complex filter graphs:
    # 1. First concatenate all videos
    # 2. Then add audio to the concatenated video

    try:
        # Debug information
        print(f"DEBUG: Number of video assets: {len(video_assets)}")
        print(f"DEBUG: Number of audio clips: {len(audio_clips)}")
        
        # Check files and get durations
        video_durations = []
        for i, asset in enumerate(video_assets):
            if os.path.exists(asset):
                try:
                    video_info = ffmpeg.probe(asset)
                    video_duration = float(video_info['format']['duration'])
                    print(f"DEBUG: Video asset {i}: {asset} (Duration: {video_duration:.2f}s)")
                    video_durations.append(video_duration)
                except Exception as e:
                    print(f"DEBUG: Error probing video asset {i}: {asset} - {str(e)}")
            else:
                print(f"DEBUG: Video asset file not found: {asset}")
        
        audio_durations = []
        for i, clip in enumerate(audio_clips):
            if os.path.exists(clip):
                try:
                    audio_info = ffmpeg.probe(clip)
                    audio_duration = float(audio_info['format']['duration'])
                    print(f"DEBUG: Audio clip {i}: {clip} (Duration: {audio_duration:.2f}s)")
                    audio_durations.append(audio_duration)
                except Exception as e:
                    print(f"DEBUG: Error probing audio clip {i}: {clip} - {str(e)}")
            else:
                print(f"DEBUG: Audio clip file not found: {clip}")
        
        if not video_durations or not audio_durations:
            print("Error: Failed to get durations of assets")
            return None
            
        # Get total durations
        total_video_duration = sum(video_durations)
        total_audio_duration = sum(audio_durations)
        print(f"Total video duration: {total_video_duration:.2f} seconds")
        print(f"Total audio duration: {total_audio_duration:.2f} seconds")
        
        if total_audio_duration < 1.0:
            print("WARNING: Total audio duration is very short (less than 1 second)!")
            total_audio_duration = max(total_audio_duration, 3.0)
            print(f"Setting minimum duration to {total_audio_duration} seconds")
        
        # Loop videos if needed to match audio duration
        if total_video_duration < total_audio_duration:
            print(f"DEBUG: Video duration shorter than audio. Will loop videos.")
            repeat_factor = int(total_audio_duration / total_video_duration) + 1
            video_assets = video_assets * repeat_factor
            print(f"DEBUG: Extended video assets to {len(video_assets)} clips")
        
        # STEP 1: First concatenate all videos to a temporary file
        os.makedirs(TEMP_DIR, exist_ok=True)
        temp_video_path = os.path.join(TEMP_DIR, f"temp_concatenated_{int(time.time())}.mp4")
        
        # Create a concatenation file for ffmpeg
        concat_file_path = os.path.join(TEMP_DIR, f"concat_{int(time.time())}.txt")
        with open(concat_file_path, 'w') as f:
            for video in video_assets:
                # Use absolute paths to avoid issues
                abs_path = os.path.abspath(video) if not os.path.isabs(video) else video
                # Escape special characters
                escaped_path = abs_path.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
                f.write(f"file '{escaped_path}'\n")
        
        print(f"DEBUG: Created concat file with {len(video_assets)} entries at {concat_file_path}")
        
        # Step 1A: Use ffmpeg command to concatenate videos
        concat_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file_path,
            '-c:v', 'copy',  # Copy video codec to speed up processing
            '-an',  # No audio in this step
            '-y',   # Overwrite output
            temp_video_path
        ]
        print(f"Running concat command: {' '.join(concat_cmd)}")
        os.system(' '.join(concat_cmd))
        
        if not os.path.exists(temp_video_path):
            print(f"ERROR: Failed to create concatenated video at {temp_video_path}")
            return None
            
        # Check the duration of the concatenated video
        concat_video_info = ffmpeg.probe(temp_video_path)
        concat_duration = float(concat_video_info['format']['duration'])
        print(f"DEBUG: Concatenated video duration: {concat_duration:.2f}s")
        
        # STEP 2: Prepare audio - instead of using concat which can be problematic,
        # simply use the first audio clip if there's only one, or combine them with filter_complex
        if len(audio_clips) == 1:
            # Just use the single audio file directly
            temp_audio_path = audio_clips[0]
            print(f"Using single audio clip: {temp_audio_path}")
        else:
            # Use filter_complex to concatenate audio files
            temp_audio_path = os.path.join(TEMP_DIR, f"temp_audio_{int(time.time())}.mp3")
            
            # Build filter_complex command for audio concat
            filter_inputs = []
            for i in range(len(audio_clips)):
                filter_inputs.append(f"-i {audio_clips[i]}")
            
            filter_concat = f"\"concat=n={len(audio_clips)}:v=0:a=1[a]\" -map \"[a]\""
            
            audio_concat_cmd = f"ffmpeg {' '.join(filter_inputs)} -filter_complex {filter_concat} {temp_audio_path} -y"
            print(f"Running audio concat command: {audio_concat_cmd}")
            os.system(audio_concat_cmd)
            
            if not os.path.exists(temp_audio_path):
                print(f"ERROR: Failed to create concatenated audio at {temp_audio_path}")
                # Fallback to using just the first audio clip
                if audio_clips and os.path.exists(audio_clips[0]):
                    print(f"Falling back to using first audio clip only")
                    temp_audio_path = audio_clips[0]
                else:
                    print(f"No usable audio clips found")
                    return None
        
        # Check audio duration
        try:
            audio_info = ffmpeg.probe(temp_audio_path)
            audio_duration = float(audio_info['format']['duration'])
            print(f"DEBUG: Final audio duration: {audio_duration:.2f}s")
        except Exception as e:
            print(f"WARNING: Error probing audio: {e}")
            audio_duration = total_audio_duration  # Use the sum as fallback
        
        # STEP 3: Combine video and audio, and ensure it matches the audio duration
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Final output command with duration limiting
        final_cmd = [
            'ffmpeg',
            '-i', temp_video_path,
            '-i', temp_audio_path,
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',  # End when shortest input (likely the audio) ends
            '-pix_fmt', 'yuv420p',
            '-y',
            output_path
        ]
        print(f"Running final command: {' '.join(final_cmd)}")
        os.system(' '.join(final_cmd))
        
        # Clean up temporary files (except for audio if we're using an original clip)
        try:
            os.remove(concat_file_path)
            if len(audio_clips) > 1 and temp_audio_path not in audio_clips:
                os.remove(temp_audio_path)
            os.remove(temp_video_path)
        except Exception as e:
            print(f"Warning: Could not clean up temp files: {e}")
        
        # Verify output
        if os.path.exists(output_path):
            try:
                output_info = ffmpeg.probe(output_path)
                output_duration = float(output_info['format']['duration'])
                print(f"DEBUG: Output video duration: {output_duration:.2f} seconds")
                
                # Check that the duration matches what we expect
                if output_duration < 1.0:
                    print(f"WARNING: Final video is too short ({output_duration:.2f}s)")
                
                end_time = time.time()
                render_time = end_time - start_time
                print(f"Video composed successfully in {render_time:.2f} seconds.")
                print("---------------------------------")
                return output_path
            except Exception as e:
                print(f"DEBUG: Error probing output video: {str(e)}")
                return None
        else:
            print(f"DEBUG: Output file doesn't exist: {output_path}")
            return None

    except Exception as e:
        print(f"An error occurred during video composition: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Demonstrates composing a video from dummy asset files."""
    print("NOTE: This main function requires real media files to exist.")
    # In a real run, these paths would come from the fetcher and tts modules.
    
    # Create dummy files for demonstration if they don't exist.
    dummy_assets_dir = "temp/ffmpeg_demo/assets"
    dummy_audio_dir = "temp/ffmpeg_demo/audio"
    os.makedirs(dummy_assets_dir, exist_ok=True)
    os.makedirs(dummy_audio_dir, exist_ok=True)

    # This part requires FFmpeg to be installed to create silent assets
    try:
        # Create a dummy video and audio file
        dummy_video = os.path.join(dummy_assets_dir, "dummy_video.mp4")
        dummy_audio = os.path.join(dummy_audio_dir, "dummy_audio.mp3")
        if not os.path.exists(dummy_video):
            ffmpeg.input('color=c=black:s=1280x720:d=5', f='lavfi').output(dummy_video).run(overwrite_output=True)
        if not os.path.exists(dummy_audio):
            ffmpeg.input('anullsrc=r=44100:cl=mono', f='lavfi').output(dummy_audio, t=3).run(overwrite_output=True)

        video_files = [dummy_video] * 3  # Use the same clip 3 times
        audio_files = [dummy_audio] * 4  # Use the same audio 4 times
        output_file = "output/ffmpeg_demo_video.mp4"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
        compose_video(video_files, audio_files, output_file)

    except ffmpeg.Error:
        print("\nCould not create dummy assets. FFmpeg might not be installed or in the system's PATH.")
        print("Please install FFmpeg to run this demo.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main() 