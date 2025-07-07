import os
import subprocess
import ffmpeg
from src.utils.logger import logger
import tempfile
import glob
import shutil
from PIL import Image, ImageFilter
import numpy as np
import random
from scipy import ndimage, signal

# Attempt to import parallax_maker. This will only work if the user has installed it.
try:
    from parallax_maker import AppState, depth, camera
    from parallax_maker.depth import DepthEstimationModel
    PARALLAX_MAKER_AVAILABLE = True
    logger.info("parallax-maker library successfully loaded!")
except ImportError:
    PARALLAX_MAKER_AVAILABLE = False
    logger.warning("`parallax-maker` library not found. Parallax effect will be disabled.")
    logger.warning("Please install it by running: pip install git+https://github.com/provos/parallax-maker.git")

def create_parallax_video(image_path: str, audio_path: str, output_path: str):
    """
    Creates a parallax video from an image and audio.
    It attempts to use the advanced parallax-maker library for a true 2.5D effect,
    and falls back to a simpler Ken Burns effect if the library is not available.
    """
    logger.info(f"Creating parallax video for {image_path}")
    
    # Get audio duration first, as it's needed in both cases
    try:
        audio_info = ffmpeg.probe(audio_path)
        duration = float(audio_info['format']['duration'])
    except Exception as e:
        logger.error(f"Failed to get audio duration for {audio_path}: {e}")
        # If we can't get duration, we can't create a video, so we should exit.
        return

    if PARALLAX_MAKER_AVAILABLE:
        try:
            logger.info("Using parallax-maker for true 2.5D effect.")
            create_true_parallax_video(image_path, audio_path, output_path, duration)
        except Exception as e:
            logger.error(f"Failed to create true parallax video with parallax-maker: {e}")
            logger.warning("Falling back to enhanced Ken Burns effect.")
            create_enhanced_ken_burns_video(image_path, audio_path, output_path, duration)
    else:
        logger.warning("parallax-maker not available, falling back to enhanced Ken Burns effect.")
        create_enhanced_ken_burns_video(image_path, audio_path, output_path, duration)


def create_true_parallax_video(image_path: str, audio_path: str, output_path: str, duration: float):
    """
    Uses the parallax-maker library to create a video with a genuine 2.5D effect.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # The library is file-based. We must save the image and work with paths.
        
        # Create a temporary project directory for parallax-maker
        project_dir = os.path.join(temp_dir, "parallax_project")
        os.makedirs(project_dir)
        
        # Define paths for the state file and the image inside the project dir
        state_file = os.path.join(project_dir, "appstate.json")
        temp_image_path = os.path.join(project_dir, "input_image.png")

        # Save the image to the temporary path
        try:
            shutil.copy(image_path, temp_image_path)
        except Exception as e:
            logger.error(f"Failed to copy image to temp directory: {e}")
            raise

        # 1. Initialize AppState. It creates an empty state.
        app_state = AppState()
        # 2. Set the filename property to the project directory path
        app_state.filename = project_dir
        # 3. Load the image data into the state object.
        app_state.set_img_data(Image.open(temp_image_path))

        logger.info("Generating depth map using DINOv2...")
        # Convert PIL image to numpy array for depth estimation
        image_array = np.array(app_state.imgData)
        depth_model = DepthEstimationModel("dinov2")
        depth_map = depth_model.depth_map(image_array)
        app_state.depthMapData = depth_map
        
        # Generate image slices based on depth
        logger.info("Creating depth-based image slices...")
        create_depth_slices(app_state)
        
        # Create 2.5D animation frames
        fps = 24
        num_frames = int(duration * fps)
        
        logger.info(f"Rendering {num_frames} frames for 2.5D animation...")
        frames_dir = os.path.join(temp_dir, 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        
        # Create parallax animation frames
        create_parallax_frames(app_state, frames_dir, num_frames, duration)

        # Combine frames into video
        temp_video = os.path.join(temp_dir, 'temp_video.mp4')
        frames_pattern = os.path.join(frames_dir, 'frame_%04d.png')
        
        cmd = [
            'ffmpeg', '-framerate', str(fps), '-i', frames_pattern,
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', temp_video
        ]
        logger.info("Combining 2.5D frames into video...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Add audio
        cmd_audio = [
            'ffmpeg', '-i', temp_video, '-i', audio_path,
            '-c:v', 'copy', '-c:a', 'aac', '-shortest', '-y', output_path
        ]
        logger.info("Adding audio to 2.5D video...")
        result = subprocess.run(cmd_audio, capture_output=True, text=True, check=True)
        
        logger.info(f"Successfully created true parallax video: {output_path}")


def create_depth_slices(app_state):
    """
    Create image slices based on depth map for 2.5D effect.
    This function segments the image into different depth layers with better object understanding.
    """
    if app_state.depthMapData is None:
        logger.error("No depth map data available for slicing")
        return
    
    # Import ImageSlice here to avoid circular imports
    from parallax_maker.slice import ImageSlice
    
    # Clear existing slices
    app_state.reset_image_slices()
    
    # Analyze the depth map to create adaptive thresholds
    depth_map = app_state.depthMapData
    depth_flat = depth_map.flatten()
    
    # Use histogram analysis to find natural depth boundaries
    hist, bin_edges = np.histogram(depth_flat, bins=50)
    
    # Find peaks in the histogram to identify natural depth layers
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(hist, height=np.max(hist) * 0.1)  # At least 10% of max height
    
    # Create adaptive thresholds based on histogram peaks
    if len(peaks) > 1:
        # Use peaks to define depth boundaries
        peak_depths = bin_edges[peaks]
        # Normalize to 0-1 range
        depth_min = np.min(peak_depths)
        depth_max = np.max(peak_depths)
        if depth_max > depth_min:
            peak_depths = (peak_depths - depth_min) / (depth_max - depth_min)
        else:
            peak_depths = np.array([0.0, 1.0])
        
        # Add boundaries at 0 and 1 if not present
        depth_thresholds = np.concatenate([[0.0], peak_depths, [1.0]])
        depth_thresholds = np.unique(depth_thresholds)  # Remove duplicates
        depth_thresholds = np.sort(depth_thresholds)
    else:
        # Fallback to fixed thresholds with fewer layers for better quality
        depth_thresholds = [0.0, 0.25, 0.5, 0.75, 1.0]
    
    # Limit the number of slices to avoid too many thin layers
    max_slices = 4
    if len(depth_thresholds) > max_slices + 1:
        # Keep first, last, and evenly spaced intermediate thresholds
        indices = np.linspace(0, len(depth_thresholds) - 1, max_slices + 1).astype(int)
        depth_thresholds = depth_thresholds[indices]
    
    app_state.imgThresholds = depth_thresholds.tolist()
    
    logger.info(f"Using adaptive depth thresholds: {depth_thresholds}")
    
    # Create slices for each depth layer
    for i in range(len(depth_thresholds) - 1):
        depth_min = depth_thresholds[i]
        depth_max = depth_thresholds[i + 1]
        depth_value = (depth_min + depth_max) / 2.0
        
        # Create mask for this depth range
        mask = create_depth_mask(app_state.depthMapData, depth_min, depth_max)
        
        # Skip slices with very few pixels (less than 1% of image)
        mask_pixels = np.sum(mask > 0)
        total_pixels = mask.shape[0] * mask.shape[1]
        if mask_pixels < total_pixels * 0.01:
            logger.info(f"Skipping depth slice {i} (too few pixels: {mask_pixels}/{total_pixels})")
            continue
        
        # Create image slice
        slice_image = apply_depth_mask(app_state.imgData, mask)
        
        # Create ImageSlice object
        image_slice = ImageSlice(depth=depth_value)
        # Convert PIL Image to numpy array for ImageSlice
        image_slice.image = np.array(slice_image)
        
        # Add slice to app_state
        app_state.add_slice(image_slice)
        
        logger.info(f"Created depth slice {i}: depth={depth_value:.2f}, pixels={mask_pixels}")
    
    logger.info(f"Created {len(app_state.image_slices)} depth slices with adaptive thresholds")


def create_depth_mask(depth_map, depth_min, depth_max):
    """
    Create a mask for pixels within a specific depth range.
    """
    # First, normalize depth map to 0-1 range properly
    # DINOv2 and other models may output different ranges
    depth_min_val = np.min(depth_map)
    depth_max_val = np.max(depth_map)
    
    # Avoid division by zero
    if depth_max_val == depth_min_val:
        # If depth is uniform, create a single mask
        mask = np.ones_like(depth_map, dtype=np.uint8) * 255
        return mask
    
    # Normalize to 0-1 range
    depth_normalized = (depth_map - depth_min_val) / (depth_max_val - depth_min_val)
    
    # Create mask for pixels in depth range with some overlap to avoid gaps
    overlap = 0.05  # 5% overlap between slices
    mask = np.logical_and(
        depth_normalized >= (depth_min - overlap), 
        depth_normalized <= (depth_max + overlap)
    )
    
    # Apply morphological operations to clean up the mask
    from scipy import ndimage
    mask = ndimage.binary_opening(mask, iterations=1)
    mask = ndimage.binary_closing(mask, iterations=2)
    
    # Convert to uint8 mask with smooth edges
    mask_uint8 = (mask * 255).astype(np.uint8)
    
    # Apply slight blur to soften edges and reduce hard transitions
    mask_blurred = ndimage.gaussian_filter(mask_uint8.astype(np.float32), sigma=1.0)
    mask_uint8 = np.clip(mask_blurred, 0, 255).astype(np.uint8)
    
    return mask_uint8


def apply_depth_mask(image, mask):
    """
    Apply a depth mask to an image, creating a slice with better edge handling.
    """
    # Convert PIL image to numpy array
    img_array = np.array(image)
    
    # Create RGBA image if not already
    if img_array.shape[2] == 3:
        # Add alpha channel
        alpha = np.ones((img_array.shape[0], img_array.shape[1], 1), dtype=np.uint8) * 255
        img_array = np.concatenate([img_array, alpha], axis=2)
    
    # Apply mask to alpha channel
    img_array[:, :, 3] = mask
    
    # For areas where mask is zero, fill with a neutral color instead of black
    # This prevents black lines when compositing
    zero_mask = mask == 0
    if np.any(zero_mask):
        # Use the average color of the visible pixels as fill
        visible_pixels = img_array[~zero_mask]
        if len(visible_pixels) > 0:
            avg_color = np.mean(visible_pixels[:, :3], axis=0).astype(np.uint8)
            img_array[zero_mask, :3] = avg_color
    
    # Convert back to PIL image
    return Image.fromarray(img_array, 'RGBA')


def create_parallax_frames(app_state, frames_dir, num_frames, duration):
    """
    Create parallax animation frames by moving depth slices at different speeds.
    """
    if not app_state.image_slices:
        logger.error("No image slices available for parallax animation")
        return
    
    # Get image dimensions
    img_width, img_height = app_state.imgData.size
    
    # Animation parameters
    max_parallax_offset = 0.03  # Reduced for smoother motion
    
    # Create a base background from the original image
    base_background = app_state.imgData.copy()
    
    for frame_idx in range(num_frames):
        # Calculate animation progress (0 to 1)
        progress = frame_idx / (num_frames - 1) if num_frames > 1 else 0
        
        # Start with the original image as background to avoid black areas
        frame = base_background.copy()
        
        # Sort slices by depth (far to near) for proper layering
        sorted_slices = sorted(app_state.image_slices, key=lambda s: s.depth, reverse=True)
        
        # Render each slice with parallax offset
        for slice_idx, image_slice in enumerate(sorted_slices):
            if image_slice.image is None:
                continue
            
            # Calculate parallax offset based on depth
            # Closer objects (lower depth) move more
            depth_factor = 1.0 - image_slice.depth  # Invert so closer = higher factor
            parallax_offset = max_parallax_offset * depth_factor
            
            # Use smooth sine wave for natural motion
            # Add slight phase offset for each slice to create more interesting motion
            phase_offset = slice_idx * 0.2
            offset_x = int(parallax_offset * img_width * 
                          np.sin(progress * 2 * np.pi + phase_offset))
            
            # Ensure offset doesn't go beyond image bounds
            offset_x = max(-img_width // 4, min(img_width // 4, offset_x))
            
            # Convert numpy array to PIL Image for compositing
            if isinstance(image_slice.image, np.ndarray):
                slice_pil = Image.fromarray(image_slice.image)
            else:
                slice_pil = image_slice.image
            
            # Composite slice onto frame with better blending
            if slice_pil.mode == 'RGBA':
                # Create extended canvas for offset rendering
                extended_width = img_width + abs(offset_x * 2)
                extended_canvas = Image.new('RGBA', (extended_width, img_height), (0, 0, 0, 0))
                
                # Paste the slice with offset
                paste_x = max(0, offset_x) + img_width // 2
                extended_canvas.paste(slice_pil, (paste_x, 0), slice_pil)
                
                # Crop back to original size
                crop_x = extended_width // 2 - img_width // 2
                cropped_slice = extended_canvas.crop((crop_x, 0, crop_x + img_width, img_height))
                
                # Composite onto frame
                frame = Image.alpha_composite(frame.convert('RGBA'), cropped_slice).convert('RGB')
            else:
                # For non-transparent slices, use a mask-based approach
                if offset_x != 0:
                    # Create a shifted version of the slice
                    shifted_slice = Image.new('RGB', (img_width, img_height), (0, 0, 0))
                    if offset_x > 0:
                        shifted_slice.paste(slice_pil, (offset_x, 0))
                    else:
                        shifted_slice.paste(slice_pil, (0, 0))
                        shifted_slice = shifted_slice.crop((-offset_x, 0, img_width - offset_x, img_height))
                        shifted_slice = shifted_slice.resize((img_width, img_height))
                    
                    # Blend with frame
                    frame = Image.blend(frame, shifted_slice, 0.8)
        
        # Save frame
        frame_path = os.path.join(frames_dir, f'frame_{frame_idx:04d}.png')
        frame.save(frame_path, quality=95)
    
    logger.info(f"Created {num_frames} parallax animation frames")


def create_enhanced_ken_burns_video(image_path: str, audio_path: str, output_path: str, duration: float):
    """
    Creates an enhanced Ken Burns effect video with subtle parallax-like movement.
    """
    logger.info(f"Creating enhanced Ken Burns video for {duration:.2f}s")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Load and prepare the image
        image = Image.open(image_path).convert('RGB')
        width, height = image.size
        
        # Calculate frame rate and number of frames
        fps = 24
        num_frames = int(duration * fps)
        
        logger.info(f"Generating {num_frames} frames at {fps}fps")
        
        # Create frames with enhanced Ken Burns effect
        frame_dir = os.path.join(temp_dir, 'frames')
        os.makedirs(frame_dir, exist_ok=True)
        
        # --- Randomized Ken Burns Parameters ---
        # Subtler cinematic motion
        zoom_start = 1.0
        zoom_end = 1.15  # Max zoom of 15%
        
        # 50% chance to zoom out instead of in for more variety
        if random.random() < 0.5:
            zoom_start, zoom_end = zoom_end, zoom_start

        # Reduced pan distance for smoother drift
        pan_x_start = 0.0
        pan_x_end = random.uniform(-0.05, 0.05)
        pan_y_start = 0.0
        pan_y_end = random.uniform(-0.05, 0.05)
        
        # Disabled rotation for a cleaner, more stable look
        rotation_start = 0.0
        rotation_end = 0.0 # No rotation
        
        for frame_idx in range(num_frames):
            progress = frame_idx / (num_frames - 1) if num_frames > 1 else 0
            
            # Smooth easing function (ease-in-out)
            progress_eased = 0.5 * (1 - np.cos(np.pi * progress))
            
            # Calculate current transformation values
            current_zoom = zoom_start + (zoom_end - zoom_start) * progress_eased
            current_pan_x = pan_x_start + (pan_x_end - pan_x_start) * progress_eased
            current_pan_y = pan_y_start + (pan_y_end - pan_y_start) * progress_eased
            current_rotation = rotation_start + (rotation_end - rotation_start) * progress_eased
            
            # Create transformed frame
            frame = create_transformed_frame(image, current_zoom, current_pan_x, current_pan_y, current_rotation)
            
            # Save frame
            frame_path = os.path.join(frame_dir, f"frame_{frame_idx:06d}.png")
            frame.save(frame_path)
        
        logger.info(f"Generated {num_frames} frames")
        
        # Combine frames into video using subprocess (more reliable)
        temp_video = os.path.join(temp_dir, 'temp_video.mp4')
        
        # Use subprocess to call ffmpeg directly
        frames_pattern = os.path.join(frame_dir, 'frame_%06d.png')
        
        cmd = [
            'ffmpeg',
            '-framerate', str(fps),
            '-i', frames_pattern,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-t', str(duration),
            '-y',
            temp_video
        ]
        
        logger.info("Combining frames into video...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg frame combination failed: {result.stderr}")
        
        # Add audio to video
        cmd_audio = [
            'ffmpeg',
            '-i', temp_video,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',
            '-y',
            output_path
        ]
        
        logger.info("Adding audio to video...")
        result = subprocess.run(cmd_audio, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg audio addition failed: {result.stderr}")
        
        logger.info(f"Successfully created enhanced Ken Burns video: {output_path}")

def create_transformed_frame(image: Image.Image, zoom: float, pan_x: float, pan_y: float, angle: float) -> Image.Image:
    """
    Creates a transformed frame with zoom, pan, and rotation effects.
    This version uses high-precision floating-point arithmetic to eliminate jitter.
    """
    width, height = image.size

    # --- 1. Rotation ---
    # Rotate the image first. `expand=True` ensures the new image is large enough
    # to hold the entire rotated original.
    rotated_image = image.rotate(angle, resample=Image.BICUBIC, expand=True)
    rw, rh = rotated_image.size
    
    # --- 2. Scaling (Zoom) ---
    # Calculate the size of the final crop box on the rotated image
    crop_width_f = width / zoom
    crop_height_f = height / zoom

    # --- 3. Panning ---
    # Calculate the center of the crop, including the pan offset.
    # The pan is relative to the *original* image dimensions.
    center_x_f = (rw / 2.0) + (pan_x * width)
    center_y_f = (rh / 2.0) + (pan_y * height)

    # --- 4. High-Precision Crop Box Calculation ---
    # Calculate all four corners in floating point *before* rounding.
    # This is the key to preventing jitter.
    left_f = center_x_f - (crop_width_f / 2.0)
    top_f = center_y_f - (crop_height_f / 2.0)
    right_f = left_f + crop_width_f
    bottom_f = top_f + crop_height_f

    # --- 5. Final Crop and Resize ---
    # Round at the very last moment to get integer coordinates for the crop.
    crop_box = (
        int(round(left_f)),
        int(round(top_f)),
        int(round(right_f)),
        int(round(bottom_f))
    )
    
    cropped = rotated_image.crop(crop_box)
    
    # Resize the final cropped image back to the original dimensions.
    # This ensures all frames are the same size for the video.
    resized = cropped.resize((width, height), Image.LANCZOS)
    
    return resized

def create_static_video(image_path: str, audio_path: str, output_path: str):
    """
    Creates a static video from an image and audio. Used as a fallback.
    """
    try:
        audio_info = ffmpeg.probe(audio_path)
        duration = float(audio_info['format']['duration'])

        # Use subprocess to call ffmpeg directly, similar to create_video_from_image
        command = [
            'ffmpeg',
            '-loop', '1',
            '-i', image_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-t', str(duration),
            '-y',
            output_path
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        logger.info(f"Created a fallback static video at {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to create static video: {e}")
        raise 