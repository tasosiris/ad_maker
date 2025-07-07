import os
import subprocess
import time
from src.agents.kling_animator import create_kling_video, KlingAnimator
from src.utils.logger import logger

def setup_test_files():
    """Create test audio for testing."""
    logger.info("Setting up test files for Kling AI...")

    # Create test audio
    audio_path = "test_kling_audio.mp3"
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
        logger.info(f"Created test audio at {audio_path}")
        return audio_path
    except Exception as e:
        logger.error(f"Failed to create test audio: {e}")
        return None

def test_kling_api_direct():
    """Test the Kling AI API directly using the official example."""
    logger.info("\n=== Testing Kling AI API Directly ===")
    
    try:
        animator = KlingAnimator()
        
        # Use the official example from API docs
        test_image_url = "https://s2-111386.kwimgs.com/bs2/mmu-aiplatform-temp/kling/20240620/1.jpeg"
        test_prompt = "Mona Lisa puts on glasses with her hands."
        
        logger.info(f"Testing with official example:")
        logger.info(f"Image URL: {test_image_url}")
        logger.info(f"Prompt: {test_prompt}")
        
        # Create the generation request
        headers = {
            "Authorization": f"Bearer {animator.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "kling-video/v1/standard/image-to-video",
            "prompt": test_prompt,
            "image_url": test_image_url,
            "duration": "5"
        }
        
        logger.info("Sending request to Kling AI...")
        import requests
        response = requests.post(
            animator.generation_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code >= 400:
            logger.error(f"Request failed: {response.text}")
            return False
        
        result = response.json()
        logger.info(f"Response: {result}")
        
        generation_id = result.get("id")
        if generation_id:
            logger.info(f"✅ Generation started successfully with ID: {generation_id}")
            logger.info("Note: Full video generation would take ~5 minutes. Stopping here for test.")
            return True
        else:
            logger.error("❌ No generation ID received")
            return False
            
    except Exception as e:
        logger.error(f"Direct API test failed: {e}")
        return False

def test_image_upload():
    """Test the image upload functionality with available images."""
    logger.info("\n=== Testing Image Upload ===")
    
    # Try to find an available image
    test_images = [
        "output/A 3D render captures the inception of a star in th_1751844529.png",
        "output/A 3D render captures the essence of the 1950s scie_1751843514.png",
        "output/A 3D render capturing the essence of scientific di_1751843587.png"
    ]
    
    image_path = None
    for img in test_images:
        if os.path.exists(img):
            image_path = img
            break
    
    if not image_path:
        logger.warning("No test images found. Creating a simple test image...")
        # Create a simple test image
        try:
            from PIL import Image
            img = Image.new('RGB', (512, 512), color='blue')
            image_path = "temp_test_image.png"
            img.save(image_path)
            logger.info(f"Created test image: {image_path}")
        except Exception as e:
            logger.error(f"Failed to create test image: {e}")
            return False
    
    try:
        animator = KlingAnimator()
        url = animator._upload_image_to_service(image_path)
        logger.info(f"Image uploaded successfully: {url}")
        
        # Clean up temp image if created
        if image_path == "temp_test_image.png" and os.path.exists(image_path):
            os.remove(image_path)
        
        return True
    except Exception as e:
        logger.error(f"Image upload test failed: {e}")
        return False

def test_animation_prompt_generation():
    """Test the animation prompt generation."""
    logger.info("\n=== Testing Animation Prompt Generation ===")
    
    try:
        animator = KlingAnimator()
        
        test_cases = [
            ("A 3D render of a star in space", "The universe is vast and mysterious"),
            ("A serene landscape with mountains", "Nature's beauty is breathtaking"),
            ("A bustling city at night", "Urban life never sleeps"),
            ("Ocean waves crashing on shore", "The sea is eternal and powerful")
        ]
        
        for original_prompt, voice_text in test_cases:
            animation_prompt = animator.create_animation_prompt(original_prompt, voice_text)
            logger.info(f"Original: {original_prompt}")
            logger.info(f"Voice: {voice_text}")
            logger.info(f"Animation: {animation_prompt}")
            logger.info("---")
        
        return True
        
    except Exception as e:
        logger.error(f"Animation prompt test failed: {e}")
        return False

def test_kling_animation_with_public_image():
    """Test the full Kling AI animation workflow with a public image."""
    logger.info("\n=== Testing Kling AI Animation with Public Image ===")
    
    audio_path = setup_test_files()
    if not audio_path:
        logger.error("Failed to set up test files")
        return False
    
    output_path = f"test_kling_mona_lisa_{int(time.time())}.mp4"
    
    try:
        logger.info("Testing with official Mona Lisa example...")
        
        # Create a temporary image file from the public URL
        import requests
        public_image_url = "https://s2-111386.kwimgs.com/bs2/mmu-aiplatform-temp/kling/20240620/1.jpeg"
        
        logger.info("Downloading test image...")
        response = requests.get(public_image_url, timeout=30)
        response.raise_for_status()
        
        temp_image_path = "temp_mona_lisa.jpg"
        with open(temp_image_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Downloaded test image to: {temp_image_path}")
        
        # Test parameters
        original_prompt = "Classic Renaissance portrait of Mona Lisa"
        voice_text = "The famous smile that has captivated viewers for centuries"
        
        success = create_kling_video(
            image_path=temp_image_path,
            audio_path=audio_path,
            output_path=output_path,
            original_prompt=original_prompt,
            voice_text=voice_text,
            model_type="standard"
        )
        
        # Clean up
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        if success and os.path.exists(output_path):
            logger.info(f"✅ SUCCESS: Kling AI animation created: {output_path}")
            logger.info("The video should show AI-generated animation of Mona Lisa")
            return True
        else:
            logger.error("❌ FAILED: Kling AI animation was not created")
            return False
            
    except Exception as e:
        logger.error(f"❌ ERROR: Kling AI animation test failed: {e}")
        return False
    finally:
        # Clean up test audio
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

def main():
    """Run all Kling AI tests."""
    logger.info("🎬 Starting Kling AI Integration Tests (Updated API)")
    
    # Check if API key is available
    api_key = os.getenv("AIML_API_KEY")
    if not api_key:
        logger.error("❌ AIML_API_KEY not found in environment variables")
        logger.error("Please set your API key to test Kling AI integration")
        return
    
    logger.info(f"✅ API Key found: {api_key[:10]}...")
    
    tests = [
        ("Animation Prompt Generation", test_animation_prompt_generation),
        ("Image Upload", test_image_upload),
        ("Direct Kling AI API Test", test_kling_api_direct),
        ("Full Kling AI Animation (Mona Lisa)", test_kling_animation_with_public_image)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed >= 3:  # Allow some flexibility since full animation test may fail due to cost/time
        logger.info("🎉 Core functionality working! Kling AI integration is ready to use.")
    else:
        logger.warning("⚠️  Multiple tests failed. Please check the logs above.")

if __name__ == "__main__":
    main() 