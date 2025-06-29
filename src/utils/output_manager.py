import os
import json
from typing import Dict, Any
from src.config import TTS_CACHE_DIR
from pathlib import Path

def get_tts_file_path(unique_id: str) -> Path:
    """
    Generates a standardized file path for a TTS audio clip.
    """
    filename = f"tts_{unique_id}.mp3"
    return TTS_CACHE_DIR / filename

def generate_metadata(title: str, description: str, tags: list, affiliate_links: dict) -> Dict[str, Any]:
    """Generates a metadata dictionary for the video."""
    return {
        "title": title,
        "description": f"{description}\n\nAffiliate Links:\n" + "\n".join(f"- {key}: {value}" for key, value in affiliate_links.items()),
        "tags": tags,
        "categoryId": "22",  # People & Blogs, find the right one for your content
    }

def save_video_with_metadata(job_id: str, video_path: str, metadata: Dict[str, Any]):
    """
    Saves the video and its metadata to the output directory.
    The video is already in its final location, so this function focuses on the metadata.
    """
    metadata_path = video_path.replace(".mp4", ".json")
    
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"Metadata for job '{job_id}' saved to: {metadata_path}")

def upload_to_youtube(video_path: str, metadata: Dict[str, Any]):
    """
    Uploads the video to YouTube using the YouTube Data API.
    (This is a placeholder and requires Google API client setup).
    """
    print("\n--- Simulating YouTube Upload ---")
    if not os.getenv("YOUTUBE_API_KEY"):
        print("Warning: YOUTUBE_API_KEY not found. Skipping actual upload.")
        return

    print(f"Uploading {video_path} to YouTube...")
    print(f"Title: {metadata['title']}")
    # In a real implementation:
    # from googleapiclient.discovery import build
    # from google_auth_oauthlib.flow import InstalledAppFlow
    # ... setup credentials and youtube = build('youtube', 'v3', ...)
    # ... youtube.videos().insert(...)
    time.sleep(1) # Simulate API call
    print("Upload simulation complete.")

import time

def main():
    """Demonstrates saving metadata and uploading."""
    job_id = "job_final_123"
    
    # Create a dummy video file to work with
    dummy_video_path = "output/Tech_Gadgets/The_Ultimate_Smart_Mug/long_form/1678886400.mp4"
    os.makedirs(os.path.dirname(dummy_video_path), exist_ok=True)
    with open(dummy_video_path, "w") as f:
        f.write("dummy video")
        
    title = "The Ultimate Smart Mug - Is It Worth It?"
    description = "A deep dive into the Ember Mug 2. We cover all the pros and cons."
    tags = ["ember mug", "smart mug", "tech review", "gadgets"]
    affiliate_links = {"Ember Mug 2": "https://amzn.to/xxxxxx"}
    
    # 1. Generate metadata
    metadata = generate_metadata(title, description, tags, affiliate_links)
    
    # 2. Save metadata alongside the video file
    save_video_with_metadata(job_id, dummy_video_path, metadata)
    
    # 3. (Optional) Upload to YouTube
    upload_to_youtube(dummy_video_path, metadata)
    

if __name__ == "__main__":
    main() 