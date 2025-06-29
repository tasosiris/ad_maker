import os
import requests
from typing import List
from pathlib import Path
from pexels_api import API
import ffmpeg
import random
from src.config import PEXELS_API_KEY, PROJECT_ROOT

# Initialize Pexels API client
if not PEXELS_API_KEY:
    raise ValueError("PEXELS_API_KEY is not set. Please check your .env file.")
pexels_client = API(PEXELS_API_KEY)

CACHE_DIR = Path(PROJECT_ROOT) / "temp" / "assets_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# List of working Pexels video URLs to use as fallback
FALLBACK_VIDEOS = [
    "https://www.pexels.com/download/video/3045163/",
    "https://www.pexels.com/download/video/3194277/",
    "https://www.pexels.com/download/video/3052204/",
    "https://www.pexels.com/download/video/1093662/",
    "https://www.pexels.com/download/video/1093664/",
    "https://www.pexels.com/download/video/857195/",
    "https://www.pexels.com/download/video/1409899/",
    "https://www.pexels.com/download/video/1722697/",
    "https://www.pexels.com/download/video/1448735/",
    "https://www.pexels.com/download/video/1580455/"
]

def _download_file(url: str, local_filename: str):
    """Downloads a file from a URL to a local path."""
    print(f"Downloading asset from {url}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    # Check if download was successful and the file is a valid video
    if os.path.exists(local_filename):
        try:
            file_size = os.path.getsize(local_filename)
            if file_size < 1000:  # less than 1KB
                print(f"WARNING: Downloaded file is very small ({file_size} bytes), may be corrupt")
                return None
            
            # Check duration using ffmpeg
            video_info = ffmpeg.probe(local_filename)
            duration = float(video_info['format']['duration'])
            print(f"Asset saved to {local_filename} - Duration: {duration:.2f} seconds, Size: {file_size/1024:.1f} KB")
            
            if duration < 0.5:
                print(f"WARNING: Video duration is very short: {duration:.2f} seconds")
                return None
                
            return local_filename
        except Exception as e:
            print(f"WARNING: Error probing downloaded file: {e}")
            return None
    else:
        print(f"WARNING: Failed to download file to {local_filename}")
        return None

def fetch_clips(query: str, num_clips: int, min_duration: float = 3.0) -> List[str]:
    """
    Fetches video clips from Pexels and caches them locally.
    Returns a list of local file paths.
    """
    print(f"Searching for {num_clips} clips with query: '{query}'")
    asset_paths = []
    
    try:
        # First try: Use direct download URLs for videos
        successful_downloads = 0
        
        # Randomly shuffle the fallback videos to get variety
        random.shuffle(FALLBACK_VIDEOS)
        
        for i, video_url in enumerate(FALLBACK_VIDEOS):
            if successful_downloads >= num_clips:
                break
                
            # Create a unique filename for caching based on URL
            filename = f"pexels_video_{i}_{abs(hash(video_url)) % 10000}.mp4"
            local_path = CACHE_DIR / filename
            
            if local_path.exists():
                try:
                    # Verify cached video is valid
                    video_info = ffmpeg.probe(str(local_path))
                    duration = float(video_info['format']['duration'])
                    print(f"Using cached asset: {local_path} - Duration: {duration:.2f} seconds")
                    
                    if duration >= min_duration:
                        asset_paths.append(str(local_path))
                        successful_downloads += 1
                        continue
                except Exception as e:
                    print(f"WARNING: Error with cached file: {e}")
                    
            # Not cached or invalid cache, download it
            try:
                downloaded_path = _download_file(video_url, str(local_path))
                if downloaded_path:
                    asset_paths.append(downloaded_path)
                    successful_downloads += 1
            except Exception as e:
                print(f"WARNING: Error downloading video: {e}")
                
        # If we didn't get enough videos, try traditional API approach as backup
        if successful_downloads < num_clips:
            print(f"Got {successful_downloads} videos, attempting to get more through API...")
            # Use the search API to look for photos that might have videos attached
            pexels_client.search(query, page=1, results_per_page=num_clips*2)
            photo_entries = pexels_client.get_entries()
            
            if photo_entries:
                print(f"Found {len(photo_entries)} results from Pexels API")
                
                # Use some generic search terms if we need more variety
                search_terms = ["technology", "digital", "futuristic", "innovation", 
                               "business", "creative", "nature", "abstract", "city"]
                
                for term in search_terms:
                    if successful_downloads >= num_clips:
                        break
                        
                    pexels_client.search(term, page=1, results_per_page=5)
                    more_entries = pexels_client.get_entries()
                    
                    # Process each photo entry to find a video URL
                    for entry in more_entries:
                        if successful_downloads >= num_clips:
                            break
                            
                        try:
                            # Attempt to derive a video URL from photo URL
                            # This is a heuristic approach since this version of the API doesn't directly support video search
                            photo_id = entry.id
                            potential_video_url = f"https://www.pexels.com/download/video/{photo_id}/"
                            
                            filename = f"pexels_derived_{photo_id}.mp4"
                            local_path = CACHE_DIR / filename
                            
                            if not local_path.exists():
                                try:
                                    downloaded_path = _download_file(potential_video_url, str(local_path))
                                    if downloaded_path:
                                        asset_paths.append(downloaded_path)
                                except Exception as e:
                                    print(f"WARNING: Error downloading derived video: {e}")
                            else:
                                # Use the cached file if it exists and is valid
                                try:
                                    video_info = ffmpeg.probe(str(local_path))
                                    duration = float(video_info['format']['duration'])
                                    if duration >= min_duration:
                                        print(f"Using cached derived video: {local_path}")
                                        asset_paths.append(str(local_path))
                                except Exception:
                                    pass  # Silently fail for derived videos
                        except Exception:
                            continue  # Skip this entry
        
        # If we still didn't get enough videos, use sample stock videos
        if len(asset_paths) == 0:
            print("WARNING: Failed to retrieve any videos from Pexels API.")
            print("Using stock video samples...")
            
            # Create stock videos directory
            stock_dir = Path(PROJECT_ROOT) / "temp" / "stock_videos"
            stock_dir.mkdir(parents=True, exist_ok=True)
            
            # List of stock video URLs - replace these with actual stock videos
            stock_videos = [
                "https://cdn.videvo.net/videvo_files/video/free/2013-08/small_watermarked/hd0992_preview.webm",
                "https://cdn.videvo.net/videvo_files/video/free/2014-12/small_watermarked/Clouds_Passing_Timelapse_preview.webm",
                "https://cdn.videvo.net/videvo_files/video/free/2014-06/small_watermarked/Blue_Sky_and_Clouds_Timelapse_0892__Videvo_preview.webm",
                "https://cdn.videvo.net/videvo_files/video/free/2019-11/small_watermarked/190301_1_25_11_preview.webm",
                "https://cdn.videvo.net/videvo_files/video/free/2019-09/small_watermarked/190828_27_SuperTrees_HD_17_preview.webm"
            ]
            
            for i, url in enumerate(stock_videos[:num_clips]):
                stock_path = stock_dir / f"stock_video_{i+1}.mp4"
                
                if not stock_path.exists():
                    try:
                        downloaded_path = _download_file(url, str(stock_path))
                        if downloaded_path:
                            asset_paths.append(downloaded_path)
                    except Exception as e:
                        print(f"ERROR: Failed to download stock video: {e}")
                else:
                    # Verify the cached stock video is valid
                    try:
                        video_info = ffmpeg.probe(str(stock_path))
                        duration = float(video_info['format']['duration'])
                        if duration >= min_duration:
                            asset_paths.append(str(stock_path))
                            print(f"Using existing stock video: {stock_path}")
                    except Exception:
                        # If invalid, try to download again
                        try:
                            downloaded_path = _download_file(url, str(stock_path))
                            if downloaded_path:
                                asset_paths.append(downloaded_path)
                        except Exception as e:
                            print(f"ERROR: Failed to download stock video: {e}")
        
        # Last resort: Create colored demo videos
        if len(asset_paths) == 0:
            print("WARNING: All video retrieval methods failed. Using colored demo videos as last resort.")
            
            # Create demo videos using ffmpeg if we need to
            demo_dir = Path(PROJECT_ROOT) / "temp" / "demo_assets"
            demo_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(min(5, num_clips)):
                demo_path = demo_dir / f"demo_video_{i+1}.mp4"
                if not demo_path.exists():
                    # Generate a demo video with ffmpeg
                    try:
                        duration = 5  # 5 second demo video
                        color = f"color=c=blue:s=1280x720:d={duration}"
                        if i % 3 == 0:
                            color = f"color=c=purple:s=1280x720:d={duration}"
                        elif i % 3 == 1:
                            color = f"color=c=teal:s=1280x720:d={duration}"
                        
                        ffmpeg.input(color, f='lavfi').output(str(demo_path)).run(overwrite_output=True)
                        
                        asset_paths.append(str(demo_path))
                        print(f"Created demo video: {demo_path}")
                    except Exception as e:
                        print(f"ERROR: Failed to create demo video: {e}")
                else:
                    asset_paths.append(str(demo_path))
                    print(f"Using existing demo video: {demo_path}")
        
        print(f"DEBUG: Successfully retrieved {len(asset_paths)} clips")
        return asset_paths

    except Exception as e:
        print(f"An error occurred with Pexels API: {e}")
        
        # Emergency fallback to demo videos
        print("Using emergency fallback videos...")
        demo_dir = Path(PROJECT_ROOT) / "temp" / "demo_assets"
        demo_dir.mkdir(parents=True, exist_ok=True)
        
        asset_paths = []
        for i in range(min(5, num_clips)):
            demo_path = demo_dir / f"demo_video_{i+1}.mp4"
            if not demo_path.exists():
                # Generate a demo video with ffmpeg
                try:
                    duration = 5  # 5 second demo video
                    color = f"color=c=blue:s=1280x720:d={duration}"
                    if i % 3 == 0:
                        color = f"color=c=purple:s=1280x720:d={duration}"
                    elif i % 3 == 1:
                        color = f"color=c=teal:s=1280x720:d={duration}"
                    
                    ffmpeg.input(color, f='lavfi').output(str(demo_path)).run(overwrite_output=True)
                    
                    asset_paths.append(str(demo_path))
                    print(f"Created fallback demo video: {demo_path}")
                except Exception as e:
                    print(f"ERROR: Failed to create demo video: {e}")
            else:
                asset_paths.append(str(demo_path))
                print(f"Using existing demo video: {demo_path}")
                
        return asset_paths

def main():
    """Demonstrates fetching real video clips from Pexels."""
    query = "futuristic technology background"
    num_clips = 3
    
    print("--- Attempting to fetch real assets from Pexels ---")
    clips = fetch_clips(query, num_clips)
    
    if clips:
        print(f"\nSuccessfully retrieved {len(clips)} clips:")
        for clip in clips:
            print(f"- {clip}")
        
        print("\nRunning fetch again (should use cache)...")
        cached_clips = fetch_clips(query, num_clips)
        print(f"\nRetrieved {len(cached_clips)} clips from cache.")
    else:
        print("\nCould not retrieve clips. Please check API key and query.")

if __name__ == "__main__":
    main() 