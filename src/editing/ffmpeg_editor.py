import ffmpeg
import os
import time
from typing import List
from src.config import VIDEO_RESOLUTION, VIDEO_FPS
import subprocess

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

def compose_video(video_assets: List[str], audio_clips: List[str], output_path: str, background_music_path: str = None):
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
        
        # STEP 1: First normalize all videos to the same resolution and framerate
        normalized_videos = []
        target_width, target_height = get_video_resolution(VIDEO_RESOLUTION)
        
        for i, video in enumerate(video_assets):
            if not os.path.exists(video):
                continue
                
            # Create a normalized version of each video
            normalized_path = os.path.join(TEMP_DIR, f"normalized_{i}_{int(time.time())}.mp4")
            
            try:
                # Get video dimensions
                probe = ffmpeg.probe(video)
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
                
                if video_stream:
                    width = int(video_stream['width'])
                    height = int(video_stream['height'])
                    
                    # Calculate scaling parameters to fill the target frame while maintaining aspect ratio
                    if width / height > target_width / target_height:
                        # Video is wider than target aspect ratio, scale by height
                        scale_params = {'w': -2, 'h': target_height}
                    else:
                        # Video is taller or same aspect ratio, scale by width
                        scale_params = {'w': target_width, 'h': -2}

                    try:
                        (
                            ffmpeg.input(video)
                            .filter('scale', **scale_params)
                            .filter('crop', w=target_width, h=target_height, x='(in_w-out_w)/2', y='(in_h-out_h)/2')
                            .output(
                                normalized_path, 
                                r=str(VIDEO_FPS), 
                                preset='fast', 
                                **{'c:v': 'libx264', 'pix_fmt': 'yuv420p'}
                            )
                            .overwrite_output()
                            .run(capture_stdout=True, capture_stderr=True)
                        )
                        if os.path.exists(normalized_path):
                            normalized_videos.append(normalized_path)
                            print(f"Successfully normalized video {i}: {video}")
                        else:
                            print(f"WARNING: Failed to normalize video {i}, output file not found.")

                    except ffmpeg.Error as e:
                        print(f"WARNING: Error normalizing video {i} ({video}) with ffmpeg-python: {e.stderr.decode()}")

                else:
                    print(f"WARNING: No video stream found in {video}")
            except Exception as e:
                print(f"WARNING: Error processing video {i} ({video}): {e}")
        
        if not normalized_videos:
            print("ERROR: Failed to normalize any videos")
            return None
        
        # STEP 2: Concatenate all normalized videos
        temp_video_path = os.path.join(TEMP_DIR, f"temp_concatenated_{int(time.time())}.mp4")
        
        try:
            # Create a list of input streams
            input_streams = [ffmpeg.input(v) for v in normalized_videos]
            
            # Concatenate them
            (
                ffmpeg.concat(*input_streams, v=1, a=0)
                .output(temp_video_path, **{'c:v': 'libx264'})
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            print(f"Successfully concatenated {len(normalized_videos)} videos.")
        except ffmpeg.Error as e:
            print(f"ERROR: Failed to concatenate videos: {e.stderr.decode()}")
            # Clean up normalized videos before returning
            for video in normalized_videos:
                if os.path.exists(video):
                    os.remove(video)
            return None
            
        if not os.path.exists(temp_video_path):
            print(f"ERROR: Failed to create concatenated video at {temp_video_path}")
            return None
            
        # Check the duration of the concatenated video
        concat_video_info = ffmpeg.probe(temp_video_path)
        concat_duration = float(concat_video_info['format']['duration'])
        print(f"DEBUG: Concatenated video duration: {concat_duration:.2f}s")
        
        # STEP 3: Prepare audio - instead of using concat which can be problematic,
        # simply use the first audio clip if there's only one, or combine them with filter_complex
        if len(audio_clips) == 1:
            # Just use the single audio file directly
            temp_audio_path = audio_clips[0]
            print(f"Using single audio clip: {temp_audio_path}")
        else:
            # Use filter_complex to concatenate audio files
            temp_audio_path = os.path.join(TEMP_DIR, f"temp_audio_{int(time.time())}.mp3")
            
            try:
                audio_streams = [ffmpeg.input(f) for f in audio_clips]
                (
                    ffmpeg.concat(*audio_streams, v=0, a=1)
                    .output(temp_audio_path)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                print(f"Successfully concatenated {len(audio_clips)} audio files.")
            except ffmpeg.Error as e:
                print(f"ERROR: Failed to create concatenated audio: {e.stderr.decode()}")
                # Fallback to using just the first audio clip
                if audio_clips and os.path.exists(audio_clips[0]):
                    print("Falling back to using first audio clip only")
                    temp_audio_path = audio_clips[0]
                else:
                    print("No usable audio clips found")
                    return None
            
            if not os.path.exists(temp_audio_path):
                print(f"ERROR: Failed to create concatenated audio at {temp_audio_path}")
                # Fallback to using just the first audio clip
        
        # Check audio duration
        try:
            audio_info = ffmpeg.probe(temp_audio_path)
            audio_duration = float(audio_info['format']['duration'])
            print(f"DEBUG: Final audio duration: {audio_duration:.2f}s")
        except Exception as e:
            print(f"WARNING: Error probing audio: {e}")
            audio_duration = total_audio_duration  # Use the sum as fallback
        
        # STEP 4: Combine video and audio, and ensure it matches the audio duration
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            video_input = ffmpeg.input(temp_video_path)
            voice_audio_input = ffmpeg.input(temp_audio_path)
            
            if background_music_path and os.path.exists(background_music_path):
                print(f"Adding background music: {background_music_path}")
                music_input = ffmpeg.input(background_music_path, stream_loop=-1) # Loop infinitely
                
                # Mix audio streams
                voice_stream = voice_audio_input.audio.filter('volume', 1.0)
                music_stream = music_input.audio.filter('volume', 0.15)
                mixed_audio = ffmpeg.filter([voice_stream, music_stream], 'amix', inputs=2, duration='first')
                
                (
                    ffmpeg.output(
                        video_input['v'], 
                        mixed_audio, 
                        output_path,
                        t=audio_duration,
                        **{'c:v': 'libx264', 'c:a': 'aac', 'pix_fmt': 'yuv420p'}
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

            else:
                (
                    ffmpeg.output(
                        video_input['v'], 
                        voice_audio_input['a'], 
                        output_path,
                        t=audio_duration,
                        **{'c:v': 'libx264', 'c:a': 'aac', 'pix_fmt': 'yuv420p'}
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

            print(f"Successfully created final video at {output_path}")

        except ffmpeg.Error as e:
            print(f"ERROR: Failed to create final video: {e.stderr.decode()}")
            # Set output_path to None to indicate failure
            output_path = None
        
        finally:
            # Clean up all temporary files
            try:
                if len(audio_clips) > 1 and temp_audio_path not in audio_clips and os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                for video in normalized_videos:
                    if os.path.exists(video):
                        os.remove(video)
            except Exception as cleanup_e:
                print(f"Warning: Could not clean up temp files: {cleanup_e}")

        if not output_path or not os.path.exists(output_path):
            print(f"DEBUG: Output file creation failed or file does not exist: {output_path}")
            return None

        # Verify output
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

    except Exception as e:
        print(f"An error occurred during video composition: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_video_from_image(image_path: str, audio_path: str, output_path: str, motion_type: str = 'zoom_in'):
    """
    Creates a video from a single image and an audio file with a dynamic motion effect.
    Motion can be 'zoom_in', 'pan_left', or 'pan_right'.
    """
    if not os.path.exists(image_path) or not os.path.exists(audio_path):
        print(f"Error: Image or audio path does not exist. Image: {image_path}, Audio: {audio_path}")
        return

    try:
        probe = ffmpeg.probe(audio_path)
        duration = float(probe['format']['duration'])
    except ffmpeg.Error as e:
        print(f"Error probing audio file {audio_path}: {e.stderr.decode('utf8')}")
        return
    except (KeyError, IndexError):
        print(f"Error: Could not extract duration from {audio_path}")
        return

    target_width, target_height = get_video_resolution(VIDEO_RESOLUTION)
    video_fps_int = int(VIDEO_FPS)
    duration_in_frames = int(duration * video_fps_int)
    
    # Ensure duration_in_frames is at least 2 to avoid division by zero in expressions
    if duration_in_frames < 2:
        duration_in_frames = 2

    stream = ffmpeg.input(image_path, loop=1, framerate=VIDEO_FPS)

    if motion_type == 'zoom_in':
        # Smooth zoom in with easing curve
        stream = stream.filter(
            'zoompan',
            z='min(1+0.5*sin(2*PI*t/{:.2f})/2+0.5*t/{:.2f},1.3)'.format(duration, duration),
            x='iw/2-(iw/zoom/2)',
            y='ih/2-(ih/zoom/2)',
            d=duration_in_frames,
            s=f'{target_width}x{target_height}'
        )
    elif motion_type == 'pan_left':
        # Smooth pan left with easing
        stream = stream.filter(
            'zoompan',
            z='1.2',
            x='(iw-ow)*(1-pow(t/{:.2f},0.7))'.format(duration),
            y='ih/2-(ih/zoom/2)',
            d=duration_in_frames,
            s=f'{target_width}x{target_height}'
        )
    elif motion_type == 'pan_right':
        # Smooth pan right with easing
        stream = stream.filter(
            'zoompan',
            z='1.2',
            x='(iw-ow)*pow(t/{:.2f},0.7)'.format(duration),
            y='ih/2-(ih/zoom/2)',
            d=duration_in_frames,
            s=f'{target_width}x{target_height}'
        )

    audio_stream = ffmpeg.input(audio_path)
    
    try:
        (
            ffmpeg
            .concat(stream.filter('setdar', dar='16/9'), audio_stream, v=1, a=1)
            .output(output_path, acodec='aac', vcodec='libx264', video_bitrate='2000k', r=VIDEO_FPS, t=duration)
            .run(overwrite_output=True, quiet=True)
        )
        print(f"Successfully created video with {motion_type} effect: {output_path}")
    except ffmpeg.Error as e:
        print(f"Error creating video from image '{output_path}': {e.stderr.decode('utf8')}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while creating {output_path}: {e}")
        raise

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