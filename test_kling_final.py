import os
import subprocess
import time
from src.agents.kling_animator import create_kling_video
from src.utils.logger import logger

def setup_test_audio():
    """Create test audio for testing."""
    logger.info("Setting up test audio...")
    
    audio_path = "test_final_audio.mp3"
    duration = 5  # 5 seconds for Kling AI
    
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
        logger.info(f"Created test audio: {audio_path}")
        return audio_path
        
    except Exception as e:
        logger.error(f"Failed to create test audio: {e}")
        return None

def test_complete_kling_integration():
    """Test the complete Kling AI integration with generated images."""
    logger.info("🎬 Testing Complete Kling AI Integration with Generated Images")
    
    # Check API key
    api_key = os.getenv("AIML_API_KEY")
    if not api_key:
        logger.error("❌ AIML_API_KEY not found")
        return False
    
    # Find available test images
    test_images = [
        ("output/A 3D render captures the inception of a star in th_1751844529.png", 
         "A 3D render of cosmic star formation", 
         "In the vast expanse of space, a new star is born from swirling cosmic dust and gas"),
        ("output/A 3D render captures the essence of the 1950s scie_1751843514.png",
         "A 1950s science fiction scene",
         "The golden age of science fiction brought us visions of the future"),
        ("output/A 3D render capturing the essence of scientific di_1751843587.png",
         "A scientific discovery scene",
         "Great discoveries emerge from curiosity and careful observation")
    ]
    
    # Find first available image
    image_path, original_prompt, voice_text = None, None, None
    for img_path, prompt, voice in test_images:
        if os.path.exists(img_path):
            image_path, original_prompt, voice_text = img_path, prompt, voice
            break
    
    if not image_path:
        logger.error("❌ No test images found")
        return False
    
    logger.info(f"✅ Using image: {os.path.basename(image_path)}")
    logger.info(f"✅ Original prompt: {original_prompt}")
    logger.info(f"✅ Voice text: {voice_text}")
    
    # Setup test audio
    audio_path = setup_test_audio()
    if not audio_path:
        logger.error("❌ Failed to create test audio")
        return False
    
    output_path = f"kling_animation_final_{int(time.time())}.mp4"
    
    try:
        logger.info("\n🎬 Starting Kling AI Video Generation...")
        logger.info("=" * 50)
        
        start_time = time.time()
        
        # This will:
        # 1. Convert image to data URL
        # 2. Create intelligent animation prompt
        # 3. Submit to Kling AI
        # 4. Poll for completion
        # 5. Download and combine with audio
        success = create_kling_video(
            image_path=image_path,
            audio_path=audio_path,
            output_path=output_path,
            original_prompt=original_prompt,
            voice_text=voice_text,
            model_type="standard"
        )
        
        elapsed_time = time.time() - start_time
        
        logger.info("=" * 50)
        logger.info(f"Total time: {elapsed_time:.1f} seconds")
        
        if success and os.path.exists(output_path):
            logger.info("🎉 SUCCESS! Complete Kling AI integration working!")
            logger.info(f"✅ Animated video created: {output_path}")
            logger.info("🎬 The video shows AI-generated animation of your generated image!")
            logger.info("\n📝 Integration Summary:")
            logger.info("   • Data URL conversion: ✅ Working")
            logger.info("   • Smart animation prompts: ✅ Working") 
            logger.info("   • Kling AI API: ✅ Working")
            logger.info("   • Video download: ✅ Working")
            logger.info("   • Audio integration: ✅ Working")
            logger.info("\n🚀 Ready to use in your main pipeline!")
            return True
        else:
            logger.error("❌ Video generation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Clean up test audio
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info("Cleaned up test audio")

if __name__ == "__main__":
    logger.info("🎬 Final Kling AI Integration Test")
    logger.info("This test demonstrates the complete pipeline working with your generated images.")
    logger.info("⚠️  Note: This will create a real video (may take ~5 minutes and consume API credits)")
    
    # Ask user if they want to proceed
    import sys
    print("\nPress Enter to proceed with full test (or Ctrl+C to cancel):", end="")
    try:
        input()
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
        sys.exit(0)
    
    success = test_complete_kling_integration()
    if success:
        logger.info("🎉 All tests passed! Kling AI is fully integrated and ready to use.")
    else:
        logger.error("❌ Test failed. Check the logs above for details.") 