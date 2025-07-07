import os
import requests
import time
from src.agents.kling_animator import KlingAnimator
from src.utils.logger import logger

def test_data_url_with_kling():
    """Test Kling AI with data URL approach using existing generated image."""
    logger.info("🎬 Testing Kling AI with Data URL approach")
    
    # Check API key
    api_key = os.getenv("AIML_API_KEY")
    if not api_key:
        logger.error("❌ AIML_API_KEY not found in environment variables")
        return False
    
    # Find an existing generated image
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
        logger.error("❌ No test images found")
        return False
    
    logger.info(f"✅ Using image: {image_path}")
    
    try:
        # Create animator
        animator = KlingAnimator()
        
        # Convert to data URL
        logger.info("Converting image to data URL...")
        data_url = animator._convert_to_data_url(image_path)
        
        # Test that data URL is valid
        if not data_url.startswith("data:image/jpeg;base64,"):
            logger.error("❌ Invalid data URL format")
            return False
        
        logger.info(f"✅ Data URL created successfully (length: {len(data_url)} chars)")
        
        # Test with Kling AI
        logger.info("Testing with Kling AI...")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "kling-video/v1/standard/image-to-video",
            "prompt": "slow zoom in with twinkling stars and gentle cosmic movement",
            "image_url": data_url,
            "duration": "5"
        }
        
        response = requests.post(
            "https://api.aimlapi.com/v2/generate/video/kling/generation",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"Response Status: {response.status_code}")
        
        if response.status_code >= 400:
            logger.error(f"❌ API request failed: {response.text}")
            return False
        
        result = response.json()
        generation_id = result.get("id")
        status = result.get("status")
        
        if generation_id and status != "error":
            logger.info(f"✅ SUCCESS! Generation started with ID: {generation_id}")
            logger.info(f"Status: {status}")
            logger.info("🎉 Data URL approach works! The full video would complete in ~5 minutes.")
            return True
        else:
            logger.error(f"❌ Generation failed: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_data_url_with_kling()
    if success:
        logger.info("🎉 Test passed! Kling AI integration is working with data URLs.")
    else:
        logger.error("❌ Test failed. Check the logs above for details.") 