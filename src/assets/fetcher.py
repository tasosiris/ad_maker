import os
import requests
from typing import List
from pathlib import Path
import ffmpeg
import re
from src.config import PEXELS_API_KEY, PROJECT_ROOT

# Pexels API configuration
if not PEXELS_API_KEY:
    raise ValueError("PEXELS_API_KEY is not set. Please check your .env file.")
PEXELS_API_URL = "https://api.pexels.com/v1/videos/search"
PEXELS_HEADERS = {
    "Authorization": PEXELS_API_KEY
}

CACHE_DIR = Path(PROJECT_ROOT) / "temp" / "assets_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def clear_video_cache():
    """
    Clears all cached video files to free up space and ensure fresh downloads.
    """
    print("Clearing video cache...")
    cleared_count = 0
    total_size = 0
    
    if CACHE_DIR.exists():
        for file_path in CACHE_DIR.glob("*.mp4"):
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                cleared_count += 1
                total_size += file_size
                print(f"  - Removed: {file_path.name} ({file_size/1024:.1f} KB)")
            except Exception as e:
                print(f"  - Failed to remove {file_path.name}: {e}")
    
    print(f"Cache cleared: {cleared_count} files removed, {total_size/1024/1024:.1f} MB freed")

def _download_file(url: str, local_filename: Path) -> str:
    """Downloads a file from a URL to a local path."""
    print(f"Downloading asset from {url}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    file_size = local_filename.stat().st_size
    if file_size < 1000:
        print(f"WARNING: Downloaded file is very small ({file_size} bytes), may be corrupt")
        local_filename.unlink()  # Delete corrupt file
        return None
    
    try:
        video_info = ffmpeg.probe(str(local_filename))
        duration = float(video_info['format']['duration'])
        print(f"Asset saved to {local_filename} - Duration: {duration:.2f} seconds, Size: {file_size/1024:.1f} KB")
        if duration < 0.5:
            print(f"WARNING: Video duration is too short: {duration:.2f}s. Deleting.")
            local_filename.unlink()
            return None
        return str(local_filename)
    except Exception as e:
        print(f"WARNING: Error probing downloaded file {local_filename}: {e}. Deleting.")
        local_filename.unlink()
        return None

def fetch_clips(job_context: dict, query: str, num_clips: int, min_duration: float = 3.0) -> List[str]:
    """
    Fetches video clips from Pexels based on a query and caches them locally.
    Returns a list of local file paths.
    """
    cost_tracker = job_context['cost_tracker']
    print(f"Searching for {num_clips} clips with query: '{query}'")
    asset_paths = []
    
    params = {
        'query': query,
        'per_page': num_clips * 2, # Fetch more to filter by duration and quality
        'orientation': 'landscape'
    }

    try:
        response = requests.get(PEXELS_API_URL, headers=PEXELS_HEADERS, params=params)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        
        cost_tracker.add_cost("pexels", "api_call", requests=1)

        data = response.json()
        videos = data.get('videos', [])

        if not videos:
            print(f"No videos found for query: '{query}'")
            return []

        for video in videos:
            if len(asset_paths) >= num_clips:
                break

            # Find a downloadable link with a suitable resolution (e.g., HD)
            video_file = next((f for f in video.get('video_files', []) if f.get('quality') == 'hd' and 'video/mp4' in f.get('file_type', '')), None)
            if not video_file:
                continue

            # Check cache first
            cached_path = CACHE_DIR / f"pexels_{video['id']}.mp4"
            if cached_path.exists():
                try:
                    probe = ffmpeg.probe(str(cached_path))
                    duration = float(probe['format']['duration'])
                    if duration >= min_duration:
                        print(f"Using cached asset: {cached_path}")
                        asset_paths.append(str(cached_path))
                        continue
                except Exception as e:
                    print(f"Cached file {cached_path} is invalid: {e}. Re-downloading.")
            
            # Download if not cached or cache is invalid
            try:
                link = video_file.get('link')
                if not link: continue
                downloaded_path = _download_file(link, cached_path)
                if downloaded_path:
                    probe = ffmpeg.probe(downloaded_path)
                    duration = float(probe['format']['duration'])
                    if duration >= min_duration:
                        asset_paths.append(downloaded_path)
            except Exception as e:
                print(f"Error processing video {video.get('id')}: {e}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred with Pexels API request: {e}")

    if not asset_paths:
        print(f"Could not retrieve any suitable videos for query '{query}'.")

    print(f"DEBUG: Successfully retrieved {len(asset_paths)} clips for query '{query}'")
    return asset_paths

def main():
    """Demonstrates fetching video clips for a given query."""
    from src.utils.output_manager import OutputManager
    from src.utils.cost_calculator import CostTracker

    query = "technology innovation"
    num_clips_to_fetch = 5
    
    output_manager = OutputManager(idea="fetcher_test")
    cost_tracker = CostTracker(output_dir=output_manager.get_job_directory())
    job_context = {
        "output_manager": output_manager,
        "cost_tracker": cost_tracker,
    }

    print(f"--- Fetching {num_clips_to_fetch} clips for query: '{query}' ---")
    video_paths = fetch_clips(job_context, query, num_clips=num_clips_to_fetch, min_duration=5.0)
    
    if video_paths:
        print(f"\nSuccessfully fetched {len(video_paths)} video clips:")
        for path in video_paths:
            print(f"- {path}")
    else:
        print("\nCould not fetch any video clips for the query.")

    cost_tracker.save_costs()

if __name__ == "__main__":
    main() 