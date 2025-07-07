import os
import requests
import time
import tempfile
import shutil
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from src.utils.logger import logger

# Load environment variables
load_dotenv()

class KlingAnimator:
    """
    Handles video generation using Kling AI's image-to-video API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AIML_API_KEY")
        self.base_url = "https://api.aimlapi.com/v2/generate/video/kling"
        self.generation_url = f"{self.base_url}/generation"
        
        if not self.api_key:
            raise ValueError("AIML_API_KEY not found in environment variables")
    
    def upload_image(self, image_path: str) -> str:
        """
        Upload image to a temporary hosting service or return a URL.
        For now, we'll assume the image needs to be accessible via URL.
        In production, you might want to upload to your own CDN or use a service.
        """
        # For now, we'll copy the image to a temporary location
        # In production, you'd upload to a CDN or image hosting service
        logger.warning("Image upload to CDN not implemented. Using local path.")
        return image_path
    
    def generate_video(self, 
                      image_path: str, 
                      prompt: str, 
                      duration: int = 5,
                      model_type: str = "standard") -> Optional[str]:
        """
        Generate a video from an image using Kling AI.
        
        Args:
            image_path: Path to the input image
            prompt: Text prompt describing the desired animation
            duration: Duration of the video in seconds (5 or 10)
            model_type: "standard" or "pro"
            
        Returns:
            Path to the generated video file, or None if generation failed
        """
        try:
            # First, upload the image to get a URL
            image_url = self._upload_image_to_service(image_path)
            
            # Determine the model based on type
            if model_type.lower() == "pro":
                model = "kling-video/v1/pro/image-to-video"
            else:
                model = "kling-video/v1/standard/image-to-video"
            
            # Create the generation request according to API docs
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "prompt": prompt,
                "image_url": image_url,
                "duration": str(duration)  # Duration must be a string
            }
            
            logger.info(f"Starting Kling AI video generation...")
            logger.info(f"Model: {model}")
            logger.info(f"Prompt: {prompt}")
            logger.info(f"Duration: {duration}s")
            logger.info(f"Image URL: {image_url}")
            
            # Submit generation request
            response = requests.post(
                self.generation_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            logger.info(f"API Response Status: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"Generation request failed: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            generation_id = result.get("id")
            
            if not generation_id:
                logger.error(f"No generation ID received: {result}")
                return None
            
            logger.info(f"Generation started with ID: {generation_id}")
            
            # Poll for completion
            video_url = self._poll_for_completion(generation_id)
            
            if not video_url:
                logger.error("Video generation failed or timed out")
                return None
            
            # Download the video
            video_path = self._download_video(video_url, image_path)
            
            return video_path
            
        except Exception as e:
            logger.error(f"Error generating video with Kling AI: {e}")
            return None
    
    def _upload_image_to_service(self, image_path: str) -> str:
        """
        Upload image to a hosting service and return the URL.
        This implementation uses a simple approach with multiple fallback options.
        """
        try:
            # Option 1: Convert to data URL (works best with cloud APIs)
            return self._convert_to_data_url(image_path)
            
        except Exception as e:
            logger.error(f"Failed to convert image to data URL: {e}")
            # Fallback: Try external hosting services
            try:
                return self._upload_to_tmpfiles(image_path)
            except Exception as e2:
                logger.error(f"Failed to upload image to hosting service: {e2}")
                # Final fallback: return local path (this won't work with the API but prevents crashes)
                return f"file://{os.path.abspath(image_path)}"
    
    def _convert_to_data_url(self, image_path: str) -> str:
        """
        Convert image to data URL format.
        This is the most reliable method for cloud APIs.
        """
        import base64
        from PIL import Image
        
        try:
            # Open and potentially resize the image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large (Kling AI has size limits)
                max_size = 1024  # Max dimension
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Save to bytes
                import io
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=85)
                img_byte_arr = img_byte_arr.getvalue()
                
                # Convert to base64
                img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
                
                # Create data URL
                data_url = f"data:image/jpeg;base64,{img_base64}"
                
                logger.info(f"Successfully converted image to data URL (size: {len(data_url)} chars)")
                return data_url
                
        except Exception as e:
            logger.error(f"Failed to convert image to data URL: {e}")
            raise
    
    def _upload_to_tmpfiles(self, image_path: str) -> str:
        """
        Upload image to a temporary file hosting service.
        Using 0x0.st as a simple, free hosting service.
        """
        try:
            # Use 0x0.st as a free temporary file hosting service
            url = "https://0x0.st"
            
            with open(image_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(url, files=files, timeout=30)
                
                if response.status_code == 200:
                    hosted_url = response.text.strip()
                    logger.info(f"Image uploaded to temporary hosting: {hosted_url}")
                    return hosted_url
                else:
                    raise Exception(f"Upload failed with status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to upload to 0x0.st: {e}")
            # Try alternative hosting service
            return self._upload_to_imgbb(image_path)
    
    def _upload_to_imgbb(self, image_path: str) -> str:
        """
        Upload image to ImgBB (requires API key).
        """
        try:
            imgbb_api_key = os.getenv("IMGBB_API_KEY")
            if not imgbb_api_key:
                raise Exception("IMGBB_API_KEY not found in environment")
                
            url = "https://api.imgbb.com/1/upload"
            
            with open(image_path, 'rb') as f:
                files = {'image': f}
                data = {'key': imgbb_api_key}
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        hosted_url = result['data']['url']
                        logger.info(f"Image uploaded to ImgBB: {hosted_url}")
                        return hosted_url
                    else:
                        raise Exception(f"ImgBB upload failed: {result}")
                else:
                    raise Exception(f"ImgBB upload failed with status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to upload to ImgBB: {e}")
            # Final fallback: use a simple HTTP server approach
            return self._create_temporary_server(image_path)
    
    def _create_temporary_server(self, image_path: str) -> str:
        """
        Create a temporary local HTTP server to serve the image.
        This is a last resort fallback that may not work with cloud APIs.
        """
        try:
            import threading
            import http.server
            import socketserver
            import socket
            
            # Create a temporary directory and copy the image
            temp_dir = "temp/image_server"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Copy image to temp directory with a simple name
            image_filename = f"image_{int(time.time())}.png"
            temp_image_path = os.path.join(temp_dir, image_filename)
            shutil.copy2(image_path, temp_image_path)
            
            # Find an available port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                port = s.getsockname()[1]
            
            # Start a simple HTTP server
            def start_server():
                os.chdir(temp_dir)
                handler = http.server.SimpleHTTPRequestHandler
                httpd = socketserver.TCPServer(("", port), handler)
                httpd.serve_forever()
            
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            
            # Return the URL
            # Note: This will only work if your machine is publicly accessible
            # For local development, you might need to use ngrok or similar
            local_url = f"http://localhost:{port}/{image_filename}"
            logger.warning(f"Created temporary server at {local_url}")
            logger.warning("This may not work with cloud APIs. Consider using a proper CDN.")
            
            return local_url
            
        except Exception as e:
            logger.error(f"Failed to create temporary server: {e}")
            # Ultimate fallback - just return the local path
            return f"file://{os.path.abspath(image_path)}"
    
    def _poll_for_completion(self, generation_id: str, max_wait_time: int = 600) -> Optional[str]:
        """
        Poll the API for completion of video generation.
        Based on the official API documentation.
        
        Args:
            generation_id: The ID of the generation request
            max_wait_time: Maximum time to wait in seconds (increased to 10 minutes)
            
        Returns:
            URL of the generated video, or None if failed/timed out
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        poll_interval = 10  # Poll every 10 seconds
        
        logger.info(f"Starting to poll for completion. Max wait time: {max_wait_time}s")
        
        while time.time() - start_time < max_wait_time:
            try:
                params = {"generation_id": generation_id}
                response = requests.get(
                    self.generation_url,
                    headers=headers,
                    params=params,
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"Polling failed: {response.status_code} - {response.text}")
                    time.sleep(poll_interval)
                    continue
                
                result = response.json()
                status = result.get("status")
                
                logger.info(f"Generation status: {status}")
                
                # According to API docs, possible statuses are:
                # "waiting", "active", "queued", "generating", "completed", "failed"
                if status == "completed":
                    # Extract video URL from the completed response
                    video_data = result.get("video", {})
                    video_url = video_data.get("url")
                    
                    if video_url:
                        logger.info(f"✅ Video generation completed! Video URL: {video_url}")
                        return video_url
                    else:
                        logger.error("Generation completed but no video URL provided")
                        logger.error(f"Full response: {result}")
                        return None
                
                elif status == "failed":
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Video generation failed: {error_msg}")
                    logger.error(f"Full response: {result}")
                    return None
                
                elif status == "error":
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Video generation encountered an error: {error_msg}")
                    logger.error(f"Full response: {result}")
                    return None
                
                elif status in ["waiting", "active", "queued", "generating"]:
                    elapsed = int(time.time() - start_time)
                    remaining = max_wait_time - elapsed
                    logger.info(f"Generation in progress... Elapsed: {elapsed}s, Remaining: {remaining}s")
                    time.sleep(poll_interval)
                    continue
                
                else:
                    logger.warning(f"Unknown status: {status}")
                    logger.warning(f"Full response: {result}")
                    time.sleep(poll_interval)
                    continue
                    
            except Exception as e:
                logger.error(f"Error polling for completion: {e}")
                time.sleep(poll_interval)
                continue
        
        logger.error(f"Video generation timed out after {max_wait_time} seconds")
        return None
    
    def _download_video(self, video_url: str, original_image_path: str) -> str:
        """
        Download the generated video from the URL.
        
        Args:
            video_url: URL of the generated video
            original_image_path: Path to the original image (for naming)
            
        Returns:
            Path to the downloaded video file
        """
        try:
            # Create output path based on original image
            base_name = os.path.splitext(os.path.basename(original_image_path))[0]
            output_path = f"temp/kling_animated_{base_name}_{int(time.time())}.mp4"
            
            # Ensure temp directory exists
            os.makedirs("temp", exist_ok=True)
            
            # Download the video
            logger.info(f"Downloading video from: {video_url}")
            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Video downloaded to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def create_animation_prompt(self, original_prompt: str, voice_text: str) -> str:
        """
        Create an animation prompt based on the original image prompt and voice text.
        
        Args:
            original_prompt: The original prompt used to generate the image
            voice_text: The text being spoken during this scene
            
        Returns:
            A prompt for animating the image
        """
        # Extract key elements for animation
        # This creates subtle, cinematic movements
        
        animation_prompts = [
            "gentle camera movement with subtle parallax effect",
            "slow zoom in with atmospheric elements moving",
            "cinematic panning with depth of field",
            "subtle environmental animation with natural movement",
            "gentle push in with atmospheric effects",
            "slow reveal with natural lighting changes",
            "cinematic drift with organic motion",
            "subtle zoom out with environmental animation"
        ]
        
        # Choose animation style based on content
        if any(word in original_prompt.lower() for word in ["space", "star", "galaxy", "universe"]):
            animation_style = "slow zoom in with twinkling stars and gentle cosmic movement"
        elif any(word in original_prompt.lower() for word in ["landscape", "mountain", "forest", "nature"]):
            animation_style = "gentle camera movement with swaying trees and atmospheric haze"
        elif any(word in original_prompt.lower() for word in ["ocean", "water", "sea", "wave"]):
            animation_style = "subtle waves and water movement with gentle camera drift"
        elif any(word in original_prompt.lower() for word in ["city", "building", "urban", "street"]):
            animation_style = "cinematic urban movement with subtle lights and shadows"
        else:
            # Default to gentle movement
            animation_style = "gentle cinematic movement with natural atmospheric effects"
        
        # Combine with voice context for more relevant animation
        prompt = f"{animation_style}. {voice_text[:50]}..."
        
        return prompt[:200]  # Keep prompt under 200 chars for API


def create_kling_video(image_path: str, audio_path: str, output_path: str, 
                      original_prompt: str = "", voice_text: str = "",
                      model_type: str = "standard") -> bool:
    """
    Create an animated video using Kling AI image-to-video.
    
    Args:
        image_path: Path to the input image
        audio_path: Path to the audio file
        output_path: Path for the output video
        original_prompt: Original prompt used to generate the image
        voice_text: Text being spoken in this scene
        model_type: "standard" or "pro"
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get audio duration
        import ffmpeg
        audio_info = ffmpeg.probe(audio_path)
        duration = float(audio_info['format']['duration'])
        
        # Limit duration to Kling AI's supported range (5-10 seconds)
        kling_duration = min(10, max(5, int(duration)))
        
        # Initialize Kling animator
        animator = KlingAnimator()
        
        # Create animation prompt
        animation_prompt = animator.create_animation_prompt(original_prompt, voice_text)
        
        # Generate animated video
        animated_video_path = animator.generate_video(
            image_path=image_path,
            prompt=animation_prompt,
            duration=kling_duration,
            model_type=model_type
        )
        
        if not animated_video_path:
            logger.error("Failed to generate animated video")
            return False
        
        # If the generated video is shorter than audio, we need to handle this
        if kling_duration < duration:
            # Loop or extend the video to match audio duration
            extended_video_path = _extend_video_to_duration(animated_video_path, duration)
            if extended_video_path:
                animated_video_path = extended_video_path
        
        # Combine animated video with audio
        success = _combine_video_with_audio(animated_video_path, audio_path, output_path)
        
        # Clean up temporary files
        if os.path.exists(animated_video_path):
            os.remove(animated_video_path)
        
        return success
        
    except Exception as e:
        logger.error(f"Error creating Kling video: {e}")
        return False


def _extend_video_to_duration(video_path: str, target_duration: float) -> Optional[str]:
    """
    Extend a video to match the target duration by looping or slowing down.
    """
    try:
        import ffmpeg
        
        # Get video info
        video_info = ffmpeg.probe(video_path)
        video_duration = float(video_info['format']['duration'])
        
        if video_duration >= target_duration:
            return video_path
        
        # Calculate how many loops we need
        loops_needed = int(target_duration / video_duration) + 1
        
        output_path = f"temp/extended_{os.path.basename(video_path)}"
        
        # Create a looped version
        (
            ffmpeg
            .input(video_path)
            .filter('loop', loop=loops_needed-1, size=32767)
            .output(output_path, t=target_duration)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        logger.info(f"Extended video from {video_duration}s to {target_duration}s")
        return output_path
        
    except Exception as e:
        logger.error(f"Error extending video: {e}")
        return None


def _combine_video_with_audio(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Combine the animated video with the audio file.
    """
    try:
        import ffmpeg
        
        # Combine video and audio
        (
            ffmpeg
            .output(
                ffmpeg.input(video_path),
                ffmpeg.input(audio_path),
                output_path,
                vcodec='copy',
                acodec='aac',
                shortest=None
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        logger.info(f"Successfully combined video and audio: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error combining video and audio: {e}")
        return False 