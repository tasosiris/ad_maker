import os
import re
import tempfile
import subprocess
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from openai import OpenAI
from src.utils.logger import logger
from src.config import OPENAI_API_KEY, OPENAI_MODEL

# Initialize OpenAI client
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@dataclass
class TextOverlay:
    """Represents a text overlay with positioning and styling."""
    text: str
    start_time: float
    end_time: float
    position: str  # 'top', 'center', 'bottom'
    style: str  # 'title', 'subtitle', 'emphasis', 'key_point'
    font_size: int
    color: str
    background: bool = False

class TextOverlayGenerator:
    """Generates intelligent text overlays for video content."""
    
    def __init__(self):
        self.client = openai_client
    
    def should_add_text_overlay(self, voice_text: str, enhanced_prompt: str) -> Dict[str, Any]:
        """
        Uses GPT to determine if text overlay would enhance the video segment.
        
        Args:
            voice_text: The narration text
            enhanced_prompt: The enhanced image prompt
            
        Returns:
            Dictionary with overlay decision and details
        """
        try:
            system_prompt = "You are a helpful video editor AI that only responds in clean, valid JSON."
            user_prompt = f"""
You are a video editor AI that decides when to add text overlays to documentary videos.

Analyze this video segment:
- Narration: "{voice_text}"
- Visual context: "{enhanced_prompt}"

Determine if adding text overlay would enhance viewer understanding or engagement.

Text overlays are helpful for:
- Key statistics, dates, or numbers
- Technical terms or scientific concepts
- Names of people, places, or things
- Emphasis on important points
- Titles or section headers
- Complex information that benefits from visual reinforcement

Text overlays should NOT be used for:
- Simple descriptive narration
- Conversational speech
- Information that's already visually clear
- Redundant information

Respond with a JSON object with the following schema:
{{
    "add_overlay": boolean,
    "overlay_type": "title" | "subtitle" | "emphasis" | "key_point" | "statistic" | "definition",
    "overlay_text": string (max 50 characters),
    "reasoning": string (brief explanation of why/why not),
    "timing": "start" | "middle" | "end"
}}

Examples:
- "In 1969, Neil Armstrong became the first person to walk on the moon" -> {{"add_overlay": true, "overlay_type": "statistic", "overlay_text": "1969", "reasoning": "Date is key historical fact", "timing": "start"}}
- "The scientist looked through his microscope" -> {{"add_overlay": false, "reasoning": "Simple action, no key info to highlight", "overlay_type": "none", "overlay_text": "none", "timing": "none"}}
- "Photosynthesis converts carbon dioxide into oxygen" -> {{"add_overlay": true, "overlay_type": "definition", "overlay_text": "Photosynthesis", "reasoning": "Scientific term benefits from visual emphasis", "timing": "start"}}

Your response (JSON only):"""

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=250,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content.strip())
            logger.info(f"Text overlay decision: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate text overlay decision: {e}")
            return {"add_overlay": False, "reasoning": "Error in processing"}
    
    def create_text_overlay(self, overlay_info: Dict[str, Any], duration: float) -> Optional[TextOverlay]:
        """
        Creates a TextOverlay object from the GPT decision.
        
        Args:
            overlay_info: Dictionary from should_add_text_overlay
            duration: Duration of the video clip in seconds
            
        Returns:
            TextOverlay object or None
        """
        if not overlay_info.get("add_overlay", False):
            return None
        
        overlay_type = overlay_info.get("overlay_type", "subtitle")
        overlay_text = overlay_info.get("overlay_text", "")
        timing = overlay_info.get("timing", "middle")
        
        # Determine positioning and styling based on overlay type
        style_config = {
            "title": {
                "position": "top",
                "font_size": 48,
                "color": "white",
                "background": True
            },
            "subtitle": {
                "position": "bottom",
                "font_size": 32,
                "color": "white",
                "background": True
            },
            "emphasis": {
                "position": "center",
                "font_size": 40,
                "color": "yellow",
                "background": False
            },
            "key_point": {
                "position": "bottom",
                "font_size": 36,
                "color": "white",
                "background": True
            },
            "statistic": {
                "position": "top",
                "font_size": 44,
                "color": "cyan",
                "background": True
            },
            "definition": {
                "position": "bottom",
                "font_size": 34,
                "color": "lightblue",
                "background": True
            }
        }
        
        config = style_config.get(overlay_type, style_config["subtitle"])
        
        # Calculate timing
        if timing == "start":
            start_time = 0.5
            end_time = min(duration - 0.5, 3.0)
        elif timing == "end":
            start_time = max(0.5, duration - 3.0)
            end_time = duration - 0.5
        else:  # middle
            start_time = duration * 0.3
            end_time = duration * 0.7
        
        return TextOverlay(
            text=overlay_text,
            start_time=start_time,
            end_time=end_time,
            position=config["position"],
            style=overlay_type,
            font_size=config["font_size"],
            color=config["color"],
            background=config["background"]
        )
    
    def add_text_overlay_to_video(self, video_path: str, overlay: TextOverlay, output_path: str) -> bool:
        """
        Adds text overlay to a video using FFmpeg.
        
        Args:
            video_path: Path to input video
            overlay: TextOverlay object with text and styling
            output_path: Path for output video
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build the FFmpeg drawtext filter
            drawtext_filter = self._build_drawtext_filter(overlay)
            
            # Run FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', drawtext_filter,
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-y',  # Overwrite output file
                output_path
            ]
            
            logger.info(f"Adding text overlay: '{overlay.text}' to {video_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully added text overlay to {output_path}")
                return True
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding text overlay: {e}")
            return False
    
    def _build_drawtext_filter(self, overlay: TextOverlay) -> str:
        """
        Builds the FFmpeg drawtext filter string.
        
        Args:
            overlay: TextOverlay object
            
        Returns:
            FFmpeg drawtext filter string
        """
        # Position calculations
        position_map = {
            "top": "x=(w-text_w)/2:y=50",
            "center": "x=(w-text_w)/2:y=(h-text_h)/2",
            "bottom": "x=(w-text_w)/2:y=h-text_h-50"
        }
        
        position = position_map.get(overlay.position, position_map["bottom"])
        
        # Clean text for FFmpeg (escape special characters)
        clean_text = overlay.text.replace("'", "\\'").replace(":", "\\:")
        
        # Build filter
        filter_parts = [
            f"text='{clean_text}'",
            f"fontsize={overlay.font_size}",
            f"fontcolor={overlay.color}",
            position,
            f"enable='between(t,{overlay.start_time},{overlay.end_time})'",
            "fontfile='/System/Library/Fonts/Helvetica.ttc'"  # macOS default font
        ]
        
        # Add background if specified
        if overlay.background:
            filter_parts.extend([
                "box=1",
                "boxcolor=black@0.7",
                "boxborderw=5"
            ])
        
        return f"drawtext={':'.join(filter_parts)}"


def create_video_with_text_overlay(video_path: str, voice_text: str, enhanced_prompt: str, 
                                 duration: float, output_path: str) -> bool:
    """
    Main function to add intelligent text overlay to a video.
    
    Args:
        video_path: Path to input video
        voice_text: The narration text
        enhanced_prompt: The enhanced image prompt
        duration: Duration of the video in seconds
        output_path: Path for output video
        
    Returns:
        True if successful (with or without overlay), False if failed
    """
    try:
        generator = TextOverlayGenerator()
        
        # Check if text overlay should be added
        overlay_decision = generator.should_add_text_overlay(voice_text, enhanced_prompt)
        
        if not overlay_decision.get("add_overlay", False):
            logger.info("No text overlay needed. Using original video.")
            # Copy original video to output path
            import shutil
            shutil.copy2(video_path, output_path)
            return True
        
        # Create text overlay
        overlay = generator.create_text_overlay(overlay_decision, duration)
        if not overlay:
            logger.warning("Failed to create text overlay. Using original video.")
            import shutil
            shutil.copy2(video_path, output_path)
            return True
        
        # Add text overlay to video
        success = generator.add_text_overlay_to_video(video_path, overlay, output_path)
        
        if not success:
            logger.warning("Failed to add text overlay. Using original video.")
            import shutil
            shutil.copy2(video_path, output_path)
            return True
        
        return True
        
    except Exception as e:
        logger.error(f"Error in text overlay process: {e}")
        return False 