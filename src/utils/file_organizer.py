import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from src.utils.logger import logger

class FileOrganizer:
    """
    Organizes all generated files into structured directories with proper naming conventions.
    Creates a hierarchical structure: output/[PROJECT_NAME]/[SCRIPT_TYPE]/[TIMESTAMP]/
    """
    
    def __init__(self, base_output_dir: str = "output"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
    
    def create_project_structure(self, project_name: str, script_type: str, timestamp: Optional[str] = None) -> Dict[str, Path]:
        """
        Creates a structured directory for a project with subdirectories for different asset types.
        
        Returns a dictionary with paths to different asset directories.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean project name for filesystem
        safe_project_name = self._sanitize_filename(project_name)
        
        # Create main project directory structure
        project_dir = self.base_output_dir / safe_project_name / script_type / timestamp
        
        # Create subdirectories
        directories = {
            'project_root': project_dir,
            'images': project_dir / 'images',
            'audio': project_dir / 'audio',
            'video_clips': project_dir / 'video_clips',
            'final_video': project_dir / 'final_video',
            'metadata': project_dir / 'metadata',
            'scripts': project_dir / 'scripts',
            'temp': project_dir / 'temp'
        }
        
        # Create all directories
        for dir_path in directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"Created project structure for '{project_name}' at: {project_dir}")
        return directories
    
    def organize_generated_images(self, image_paths: List[str], project_dirs: Dict[str, Path], 
                                 voice_clips: List = None) -> List[str]:
        """
        Organizes generated images with descriptive names and proper structure.
        
        Args:
            image_paths: List of paths to generated images
            project_dirs: Dictionary of project directories from create_project_structure
            voice_clips: Optional list of voice clips to use for naming
            
        Returns:
            List of new organized image paths
        """
        organized_paths = []
        images_dir = project_dirs['images']
        
        for i, image_path in enumerate(image_paths):
            if not os.path.exists(image_path):
                logger.warning(f"Image file not found: {image_path}")
                continue
                
            # Generate descriptive filename
            if voice_clips and i < len(voice_clips):
                # Use first few words of the voice clip for naming
                scene_description = self._create_scene_description(voice_clips[i].text, max_words=5)
                filename = f"scene_{i+1:02d}_{scene_description}.png"
            else:
                filename = f"scene_{i+1:02d}_generated_image.png"
            
            # Clean filename
            filename = self._sanitize_filename(filename)
            new_path = images_dir / filename
            
            try:
                shutil.copy2(image_path, new_path)
                organized_paths.append(str(new_path))
                logger.info(f"Organized image: {filename}")
                
                # Clean up original if it's in temp/output root
                if self._is_temp_file(image_path):
                    os.remove(image_path)
                    logger.info(f"Cleaned up temporary image: {image_path}")
                    
            except Exception as e:
                logger.error(f"Failed to organize image {image_path}: {e}")
                organized_paths.append(image_path)  # Keep original path if copy fails
        
        return organized_paths
    
    def organize_audio_files(self, audio_paths: List[str], project_dirs: Dict[str, Path], 
                           voice_clips: List = None) -> List[str]:
        """
        Organizes audio files with descriptive names.
        """
        organized_paths = []
        audio_dir = project_dirs['audio']
        
        for i, audio_path in enumerate(audio_paths):
            if not os.path.exists(audio_path):
                logger.warning(f"Audio file not found: {audio_path}")
                continue
                
            # Generate descriptive filename
            if voice_clips and i < len(voice_clips):
                scene_description = self._create_scene_description(voice_clips[i].text, max_words=5)
                filename = f"scene_{i+1:02d}_{scene_description}.mp3"
            else:
                filename = f"scene_{i+1:02d}_audio.mp3"
            
            filename = self._sanitize_filename(filename)
            new_path = audio_dir / filename
            
            try:
                shutil.copy2(audio_path, new_path)
                organized_paths.append(str(new_path))
                logger.info(f"Organized audio: {filename}")
                
                # Don't clean up TTS cache files as they might be reused
                
            except Exception as e:
                logger.error(f"Failed to organize audio {audio_path}: {e}")
                organized_paths.append(audio_path)
        
        return organized_paths
    
    def organize_video_clips(self, video_clip_paths: List[str], project_dirs: Dict[str, Path], 
                           voice_clips: List = None) -> List[str]:
        """
        Organizes individual video clips before final composition.
        """
        organized_paths = []
        clips_dir = project_dirs['video_clips']
        
        for i, clip_path in enumerate(video_clip_paths):
            if not os.path.exists(clip_path):
                logger.warning(f"Video clip not found: {clip_path}")
                continue
                
            # Generate descriptive filename
            if voice_clips and i < len(voice_clips):
                scene_description = self._create_scene_description(voice_clips[i].text, max_words=5)
                filename = f"scene_{i+1:02d}_{scene_description}.mp4"
            else:
                filename = f"scene_{i+1:02d}_clip.mp4"
            
            filename = self._sanitize_filename(filename)
            new_path = clips_dir / filename
            
            try:
                shutil.move(clip_path, new_path)  # Move instead of copy for temp files
                organized_paths.append(str(new_path))
                logger.info(f"Organized video clip: {filename}")
                
            except Exception as e:
                logger.error(f"Failed to organize video clip {clip_path}: {e}")
                organized_paths.append(clip_path)
        
        return organized_paths
    
    def save_final_video(self, video_path: str, project_dirs: Dict[str, Path], 
                        project_name: str, script_type: str) -> str:
        """
        Saves the final video with a descriptive name.
        """
        if not os.path.exists(video_path):
            logger.error(f"Final video not found: {video_path}")
            return video_path
            
        final_dir = project_dirs['final_video']
        safe_name = self._sanitize_filename(project_name)
        filename = f"{safe_name}_{script_type}_final.mp4"
        final_path = final_dir / filename
        
        try:
            shutil.move(video_path, final_path)
            logger.info(f"Final video saved: {final_path}")
            return str(final_path)
        except Exception as e:
            logger.error(f"Failed to save final video: {e}")
            return video_path
    
    def save_project_metadata(self, project_dirs: Dict[str, Path], metadata: Dict, 
                             project_name: str, script_type: str):
        """
        Saves comprehensive project metadata including file inventory.
        """
        metadata_dir = project_dirs['metadata']
        
        # Add file inventory to metadata
        file_inventory = self._create_file_inventory(project_dirs)
        metadata['file_inventory'] = file_inventory
        metadata['project_structure'] = {
            'project_name': project_name,
            'script_type': script_type,
            'created_at': datetime.now().isoformat(),
            'directory_structure': {k: str(v) for k, v in project_dirs.items()}
        }
        
        # Save main metadata file
        metadata_file = metadata_dir / 'project_metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Save human-readable summary
        summary_file = metadata_dir / 'project_summary.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"=== PROJECT SUMMARY ===\n\n")
            f.write(f"Project: {project_name}\n")
            f.write(f"Type: {script_type}\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("=== FILE INVENTORY ===\n")
            for category, files in file_inventory.items():
                f.write(f"\n{category.upper()}:\n")
                for file_info in files:
                    f.write(f"  - {file_info['filename']} ({file_info['size']})\n")
            
            if 'script_content' in metadata:
                f.write(f"\n=== SCRIPT CONTENT ===\n")
                f.write(metadata['script_content'].get('full_script', 'No script content'))
        
        logger.info(f"Project metadata saved: {metadata_file}")
        logger.info(f"Project summary saved: {summary_file}")
    
    def cleanup_temp_files(self, project_dirs: Dict[str, Path]):
        """
        Cleans up temporary files and directories.
        """
        temp_dir = project_dirs.get('temp')
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitizes filename for filesystem compatibility.
        """
        # Replace problematic characters
        sanitized = filename.replace(' ', '_')
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c in '._-')
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized
    
    def _create_scene_description(self, text: str, max_words: int = 5) -> str:
        """
        Creates a short description from text for filename.
        """
        words = text.split()[:max_words]
        description = '_'.join(words)
        return self._sanitize_filename(description)
    
    def _is_temp_file(self, file_path: str) -> bool:
        """
        Checks if a file is in a temporary location that should be cleaned up.
        """
        path = Path(file_path)
        temp_indicators = ['temp', 'tmp', 'output'] # Files directly in output root
        return any(indicator in str(path.parent).lower() for indicator in temp_indicators)
    
    def _create_file_inventory(self, project_dirs: Dict[str, Path]) -> Dict[str, List]:
        """
        Creates an inventory of all files in the project.
        """
        inventory = {}
        
        for category, dir_path in project_dirs.items():
            if category == 'project_root' or not dir_path.exists():
                continue
                
            files = []
            for file_path in dir_path.glob('*'):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    size_str = self._format_file_size(size)
                    files.append({
                        'filename': file_path.name,
                        'size': size_str,
                        'path': str(file_path)
                    })
            
            if files:
                inventory[category] = files
        
        return inventory
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Formats file size in human-readable format.
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def organize_existing_output_files():
    """
    Utility function to organize existing scattered files in the output directory.
    """
    organizer = FileOrganizer()
    output_dir = Path("output")
    
    # Find all scattered image files
    scattered_images = list(output_dir.glob("*.png"))
    scattered_videos = list(output_dir.glob("*.mp4"))
    
    if not scattered_images and not scattered_videos:
        logger.info("No scattered files found to organize.")
        return
    
    # Create a cleanup project
    cleanup_dirs = organizer.create_project_structure("Cleanup_Scattered_Files", "mixed", 
                                                     datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    # Organize scattered images
    if scattered_images:
        logger.info(f"Found {len(scattered_images)} scattered images to organize...")
        for i, img_path in enumerate(scattered_images):
            filename = f"scattered_image_{i+1:03d}_{img_path.name}"
            new_path = cleanup_dirs['images'] / filename
            try:
                shutil.move(str(img_path), new_path)
                logger.info(f"Moved: {img_path.name} -> {new_path}")
            except Exception as e:
                logger.error(f"Failed to move {img_path}: {e}")
    
    # Organize scattered videos
    if scattered_videos:
        logger.info(f"Found {len(scattered_videos)} scattered videos to organize...")
        for i, video_path in enumerate(scattered_videos):
            filename = f"scattered_video_{i+1:03d}_{video_path.name}"
            new_path = cleanup_dirs['final_video'] / filename
            try:
                shutil.move(str(video_path), new_path)
                logger.info(f"Moved: {video_path.name} -> {new_path}")
            except Exception as e:
                logger.error(f"Failed to move {video_path}: {e}")
    
    # Save cleanup metadata
    cleanup_metadata = {
        'cleanup_info': {
            'images_organized': len(scattered_images),
            'videos_organized': len(scattered_videos),
            'cleanup_date': datetime.now().isoformat()
        }
    }
    
    organizer.save_project_metadata(cleanup_dirs, cleanup_metadata, "Cleanup_Scattered_Files", "mixed")
    logger.info("Cleanup completed. Scattered files have been organized.")


if __name__ == "__main__":
    organize_existing_output_files() 