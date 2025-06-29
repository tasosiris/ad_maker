#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
import ffmpeg
from src.assets.fetcher import fetch_clips
from src.config import PROJECT_ROOT

def test_video_fetcher():
    """Tests the video fetcher to ensure real videos are being downloaded"""
    print("=== Testing Video Fetching Capabilities ===")
    
    # Clean up the cache to force fresh downloads
    should_clean = input("Clean video cache before testing? (y/n): ").strip().lower()
    if should_clean == 'y':
        cache_dir = Path(PROJECT_ROOT) / "temp" / "assets_cache"
        if cache_dir.exists():
            print(f"Cleaning cache directory: {cache_dir}")
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
            print("Cache cleaned.")
    
    # Test queries
    test_queries = [
        "technology innovation",
        "nature landscape",
        "business presentation",
        "city traffic",
        "abstract motion"
    ]
    
    num_clips = 3
    successful_queries = 0
    
    # Run tests for each query
    for query in test_queries:
        print(f"\n=== Testing query: '{query}' ===")
        clips = fetch_clips(query, num_clips=num_clips)
        
        if clips:
            print(f"Retrieved {len(clips)} video clips:")
            valid_clips = 0
            
            # Analyze each clip to verify it's a proper video
            for i, clip_path in enumerate(clips):
                print(f"\nVideo {i+1}: {clip_path}")
                
                try:
                    # Get video info
                    video_info = ffmpeg.probe(clip_path)
                    
                    # Extract key information
                    duration = float(video_info['format']['duration'])
                    size_bytes = os.path.getsize(clip_path)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # Check if video has video streams
                    has_video = any(stream['codec_type'] == 'video' for stream in video_info['streams'])
                    
                    # Get video dimensions if available
                    width = height = "unknown"
                    for stream in video_info['streams']:
                        if stream['codec_type'] == 'video':
                            width = stream.get('width', 'unknown')
                            height = stream.get('height', 'unknown')
                            break
                    
                    # Print video details
                    print(f"  - Duration: {duration:.2f} seconds")
                    print(f"  - Size: {size_mb:.2f} MB")
                    print(f"  - Dimensions: {width}x{height}")
                    print(f"  - Has video stream: {'Yes' if has_video else 'No'}")
                    
                    # Check if this is likely a proper video or just a colored screen
                    is_proper_video = has_video and duration > 1.0 and size_bytes > 100000
                    
                    # Look for "color" in the path as a clue it might be a generated color video
                    is_color_screen = "color=c=" in str(clip_path) or "demo_video" in str(clip_path)
                    
                    if is_proper_video and not is_color_screen:
                        print("  ✅ PROPER VIDEO DETECTED")
                        valid_clips += 1
                    elif is_color_screen:
                        print("  ⚠️ APPEARS TO BE A GENERATED COLOR SCREEN")
                    else:
                        print("  ❌ NOT A PROPER VIDEO")
                    
                except Exception as e:
                    print(f"  Error analyzing video: {e}")
            
            # Check if this query was successful
            if valid_clips > 0:
                print(f"\n✅ Query '{query}' successful: {valid_clips}/{len(clips)} proper videos")
                successful_queries += 1
            else:
                print(f"\n❌ Query '{query}' failed: No proper videos found")
                
        else:
            print(f"❌ No clips found for query '{query}'")
    
    # Final results
    print("\n=== Final Results ===")
    print(f"Successfully fetched proper videos for {successful_queries}/{len(test_queries)} queries")
    
    if successful_queries > 0:
        print("\n✅ Video fetcher is working properly!")
    else:
        print("\n❌ Video fetcher is still using fallback color videos.")
        
    # Suggest next steps
    print("\nNext Steps:")
    print("1. If proper videos were fetched, run your main application to create videos with real content.")
    print("2. If all queries still used fallback videos, check your network connection and Pexels API key.")
    print("3. Try with a different API key or video source if needed.")

if __name__ == "__main__":
    test_video_fetcher() 