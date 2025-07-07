import os
import subprocess
from PIL import Image
from src.editing.parallax import create_parallax_video
from src.utils.logger import logger
import time

def setup_test_files():
    """Uses an existing generated image and creates audio for testing."""
    logger.info("Setting up test files...")
    
    # Use existing generated image - try a landscape scene
    image_path = "output/In the heart of ancient Japan the serene landscape_1751819400.png"
    if not os.path.exists(image_path):
        # Fallback to star scene if landscape not found
        image_path = "output/A 3D render captures the inception of a star in th_1751844529.png"
        if not os.path.exists(image_path):
            logger.error(f"Test image not found: {image_path}")
            return None, None
    
    logger.info(f"Using existing generated image: {image_path}")

    # Create dummy silent audio
    audio_path = "test_audio.mp3"
    duration = 5  # seconds - longer duration to better see the parallax effect
    try:
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'anullsrc=r=44100:cl=mono',
            '-t', str(duration),
            '-q:a', '9',
            '-acodec', 'libmp3lame',
            '-y',
            audio_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Created dummy audio at {audio_path}")
    except Exception as e:
        logger.error(f"Failed to create dummy audio. Make sure ffmpeg is installed. Error: {e}")
        return None, None

    return image_path, audio_path

def cleanup_test_files(image_path, audio_path, output_path):
    """Keeps the generated test files for inspection."""
    logger.info("Keeping test files for inspection...")
    logger.info(f"Test image: {image_path}")
    logger.info(f"Test audio: {audio_path}")
    logger.info(f"Output video: {output_path}")
    
    # Don't delete the original image, but clean up temporary audio
    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
            logger.info(f"Removed temporary audio: {audio_path}")
        except OSError as e:
            logger.error(f"Error removing audio file {audio_path}: {e}")

def main():
    """Main test function."""
    image_path, audio_path = None, None
    output_path = f"test_parallax_landscape_{int(time.time())}.mp4"

    try:
        image_path, audio_path = setup_test_files()
        
        if not image_path or not audio_path:
            logger.error("Test setup failed. Aborting.")
            return

        logger.info("--- Starting Parallax Test with Generated Image ---")
        logger.info("Testing with landscape scene that should have good foreground/background depth...")
        create_parallax_video(image_path, audio_path, output_path)
        logger.info("--- Parallax Test Finished ---")

        if os.path.exists(output_path):
            logger.info(f"SUCCESS: Parallax video created successfully at {output_path}")
            logger.info("The video should show a 2.5D parallax effect with different depth layers moving at different speeds.")
        else:
            logger.error("FAILURE: Output video was not created.")

    except Exception as e:
        logger.error(f"An error occurred during the parallax test: {e}", exc_info=True)
    
    finally:
        cleanup_test_files(image_path, audio_path, output_path)

if __name__ == "__main__":
    main() 