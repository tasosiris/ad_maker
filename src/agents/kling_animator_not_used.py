import os
import requests
import time
import base64
from typing import Optional
from dotenv import load_dotenv
from src.utils.logger import logger

load_dotenv()

class KlingAnimator:
    def __init__(self, job_context: dict, config: dict):
        self.job_context = job_context
        self.output_manager = job_context['output_manager']
        self.cost_tracker = job_context['cost_tracker']
        self.api_key = config['aimlapi_key']
        self.api_host = config.get('aimlapi_host', 'https://api.aimlapi.com')
        self.generation_url = f"{self.api_host}/v2/generate/video/kling/generation"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_video(self, 
                      image_path: str, 
                      prompt: str, 
                      video_name: str,
                      duration: int = 5,
                      model_type: str = "standard") -> Optional[str]:
        try:
            image_url = self._upload_image_to_service(image_path)
            
            model = "kling-video/v1/pro/image-to-video" if model_type.lower() == "pro" else "kling-video/v1/standard/image-to-video"
            
            payload = {"model": model, "prompt": prompt, "image_url": image_url, "duration": str(duration)}
            
            logger.info(f"Starting Kling AI video generation for '{video_name}'...")
            
            response = requests.post(self.generation_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            generation_id = result.get("id")
            if not generation_id:
                logger.error(f"No generation ID received: {result}")
                return None
            
            logger.info(f"Generation started with ID: {generation_id}")
            
            video_url = self._poll_for_completion(generation_id)
            if not video_url:
                logger.error("Video generation failed or timed out")
                return None
            
            video_path = self._download_video(video_url, video_name)
            
            self.cost_tracker.add_cost("aimlapi", model=model, seconds=duration)
            self.output_manager.save_prompt(
                agent_name=f"kling_animator_{video_name}",
                prompt_data={"prompt": prompt, "model": model, "duration": duration},
                cost_info=self.cost_tracker.get_last_cost()
            )

            return video_path
            
        except Exception as e:
            logger.error(f"Error generating video with Kling AI: {e}")
            return None
    
    def _upload_image_to_service(self, image_path: str) -> str:
        import base64
        from PIL import Image
        import io

        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            max_size = 1024
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr = img_byte_arr.getvalue()
            img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
            return f"data:image/jpeg;base64,{img_base64}"

    def _poll_for_completion(self, generation_id: str) -> Optional[str]:
        """Polls for video completion and returns the video URL."""
        status_url = f"{self.api_host}/v2/generate/video/kling/generation"
        params = {"generation_id": generation_id}
        
        timeout = 600  # 10 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(status_url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                status = data.get("status")
                if status == "completed":
                    video_url = data.get("video", {}).get("url")
                    if video_url:
                        logger.info("Video generation succeeded.")
                        return video_url
                    else:
                        logger.error(f"Video generation finished but no URL found: {data}")
                        return None
                elif status in ["failed", "cancelled"]:
                    logger.error(f"Video generation failed with status: {status}. Response: {data}")
                    return None
                else:
                    logger.info(f"Polling... status is {status}")
                    time.sleep(10)
            except requests.exceptions.RequestException as e:
                logger.error(f"An error occurred while polling: {e}")
                time.sleep(10)
        
        logger.error("Polling timed out after 10 minutes.")
        return None

    def _download_video(self, video_url: str, video_name: str) -> str:
        video_path = self.output_manager.get_videos_directory() / f"{video_name}.mp4"
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Video downloaded and saved to: {video_path}")
        return str(video_path)

def create_animation_prompt(original_prompt: str, voice_text: str) -> str:
    # Simplified prompt generation
    return f"{original_prompt}, in a cinematic style. The character could be saying: '{voice_text[:100]}...'"

def create_kling_video(job_context: dict, image_path: str, audio_path: str, output_path: str, 
                      original_prompt: str = "", voice_text: str = "",
                      model_type: str = "standard") -> bool:
    """
    Create an animated video using Kling AI image-to-video.
    """
    animated_video_path = None
    extended_video_path = None
    try:
        # Get audio duration
        import ffmpeg
        audio_info = ffmpeg.probe(audio_path)
        duration = float(audio_info['format']['duration'])
        
        # Limit duration to Kling AI's supported range (5-10 seconds)
        kling_duration = min(10, max(5, int(duration)))
        
        # Initialize Kling animator
        config = {
            "aimlapi_key": os.getenv("AIMLAPI_KEY")
        }
        animator = KlingAnimator(job_context, config)
        
        # Create animation prompt
        animation_prompt = create_animation_prompt(original_prompt, voice_text)
        
        # Generate animated video
        video_name = os.path.splitext(os.path.basename(output_path))[0]
        animated_video_path = animator.generate_video(
            image_path=image_path,
            prompt=animation_prompt,
            video_name=f"{video_name}_animated",
            duration=kling_duration,
            model_type=model_type
        )
        
        if not animated_video_path:
            logger.error("Failed to generate animated video")
            return False
        
        video_to_combine = animated_video_path
        # If the generated video is shorter than audio, we need to handle this
        if kling_duration < duration:
            # Loop or extend the video to match audio duration
            extended_video_path = _extend_video_to_duration(animated_video_path, duration, job_context['output_manager'])
            if extended_video_path:
                video_to_combine = extended_video_path
        
        # Combine animated video with audio
        success = _combine_video_with_audio(video_to_combine, audio_path, output_path)
        
        return success
        
    except Exception as e:
        logger.error(f"Error creating Kling video: {e}")
        return False
    finally:
        # Clean up temporary files
        if animated_video_path and os.path.exists(animated_video_path):
            os.remove(animated_video_path)
        if extended_video_path and os.path.exists(extended_video_path):
            os.remove(extended_video_path)


def _extend_video_to_duration(video_path: str, target_duration: float, output_manager) -> Optional[str]:
    """
    Extend a video to match the target duration by looping or slowing down.
    """
    try:
        import ffmpeg
        
        video_info = ffmpeg.probe(video_path)
        video_duration = float(video_info['format']['duration'])
        
        if video_duration >= target_duration:
            return video_path
        
        loops_needed = int(target_duration / video_duration) + 1
        
        output_path = output_manager.get_videos_directory() / f"extended_{os.path.basename(video_path)}"
        
        (
            ffmpeg
            .input(video_path)
            .filter('loop', loop=loops_needed-1, size=32767)
            .output(str(output_path), t=target_duration)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        logger.info(f"Extended video from {video_duration}s to {target_duration}s")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Error extending video: {e}")
        return None


def _combine_video_with_audio(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Combine the animated video with the audio file.
    """
    try:
        import ffmpeg
        
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

if __name__ == '__main__':
    from src.utils.output_manager import OutputManager
    from src.utils.cost_calculator import CostTracker
    import logging

    logging.basicConfig(level=logging.INFO)
    
    # Create a dummy image file for testing
    from PIL import Image
    dummy_img_path = "temp/dummy_kling_image.jpg"
    os.makedirs("temp", exist_ok=True)
    Image.new('RGB', (512, 512), color = 'red').save(dummy_img_path)

    idea = "kling_test"
    video_name = "test_animation"
    
    output_manager = OutputManager(idea=idea)
    cost_tracker = CostTracker(output_dir=output_manager.get_job_directory())
    job_context = {
        "output_manager": output_manager,
        "cost_tracker": cost_tracker,
    }

    animator = KlingAnimator(job_context=job_context)
    
    video_path = animator.generate_video(
        image_path=dummy_img_path,
        prompt="A red square rotating in space.",
        video_name=video_name,
        duration=5
    )

    if video_path:
        print(f"Video generation successful: {video_path}")
    else:
        print("Video generation failed.")
    
    cost_tracker.save_costs()
    print(f"\nCosts tracked and saved in: {output_manager.get_job_directory()}") 