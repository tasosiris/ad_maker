# File Organization System

## Overview

The AI video generation system now includes a comprehensive file organization system that automatically organizes all generated files into structured directories with proper naming conventions. This eliminates the clutter of scattered files and makes it easy to find and manage your generated content.

## New Directory Structure

### Hierarchical Organization
```
output/
├── [PROJECT_NAME]/
│   ├── [SCRIPT_TYPE]/
│   │   ├── [TIMESTAMP]/
│   │   │   ├── images/           # Generated or source images
│   │   │   ├── audio/            # Voice clips and audio files
│   │   │   ├── video_clips/      # Individual scene clips
│   │   │   ├── final_video/      # Final composed video
│   │   │   ├── metadata/         # Project metadata and summaries
│   │   │   ├── scripts/          # Script files and content
│   │   │   └── temp/             # Temporary files (cleaned up)
│   │   └── [ANOTHER_TIMESTAMP]/
│   └── [ANOTHER_SCRIPT_TYPE]/
└── [ANOTHER_PROJECT]/
```

### Example Structure
```
output/
├── The_Story_of_the_Rosetta_Stone/
│   ├── short_form/
│   │   └── 20250705_225453/
│   │       ├── images/
│   │       │   ├── scene_01_In_the_heart_of.png
│   │       │   ├── scene_02_Under_the_gentle.png
│   │       │   └── scene_03_Bathed_in_soft.png
│   │       ├── audio/
│   │       │   ├── scene_01_In_the_heart_of.mp3
│   │       │   ├── scene_02_Under_the_gentle.mp3
│   │       │   └── scene_03_Bathed_in_soft.mp3
│   │       ├── video_clips/
│   │       │   ├── scene_01_In_the_heart_of.mp4
│   │       │   ├── scene_02_Under_the_gentle.mp4
│   │       │   └── scene_03_Bathed_in_soft.mp4
│   │       ├── final_video/
│   │       │   └── The_Story_of_the_Rosetta_Stone_short_form_final.mp4
│   │       └── metadata/
│   │           ├── project_metadata.json
│   │           └── project_summary.txt
│   └── long_form/
│       └── 20250705_143022/
│           └── [similar structure]
└── The_Rise_and_Fall_of_the_Concorde/
    └── short_form/
        └── 20250705_162145/
            └── [similar structure]
```

## Key Features

### 1. Descriptive File Names
- **Images**: `scene_01_In_the_heart_of.png` (based on voice clip content)
- **Audio**: `scene_01_In_the_heart_of.mp3` (matches corresponding image)
- **Video Clips**: `scene_01_In_the_heart_of.mp4` (matches scene content)
- **Final Video**: `Project_Name_script_type_final.mp4`

### 2. Timestamp-Based Versioning
- Each generation run gets its own timestamp directory
- Format: `YYYYMMDD_HHMMSS` (e.g., `20250705_225453`)
- Prevents overwrites and maintains history
- Easy to identify when content was generated

### 3. Comprehensive Metadata
Each project includes detailed metadata files:

#### project_metadata.json
```json
{
  "video_info": {
    "title": "The Story of the Rosetta Stone",
    "script_type": "short_form",
    "generation_method": "image_generation"
  },
  "script_content": {
    "full_script": "Complete script text...",
    "script_id": 123,
    "job_id": 45
  },
  "generation_info": {
    "idea": "The_Story_of_the_Rosetta_Stone",
    "research_summary": "Research content...",
    "created_at": "2025-07-05T22:54:53",
    "total_scenes": 20,
    "successful_scenes": 18
  },
  "assets_info": {
    "images_generated": 18,
    "audio_clips": 20,
    "video_clips": 18
  },
  "file_inventory": {
    "images": [
      {"filename": "scene_01_In_the_heart_of.png", "size": "1.2 MB"},
      {"filename": "scene_02_Under_the_gentle.png", "size": "1.1 MB"}
    ],
    "audio": [...],
    "video_clips": [...],
    "final_video": [...]
  }
}
```

#### project_summary.txt
```
=== PROJECT SUMMARY ===

Project: The Story of the Rosetta Stone
Type: short_form
Created: 2025-07-05 22:54:53

=== FILE INVENTORY ===

IMAGES:
  - scene_01_In_the_heart_of.png (1.2 MB)
  - scene_02_Under_the_gentle.png (1.1 MB)
  - scene_03_Bathed_in_soft.png (1.0 MB)

AUDIO:
  - scene_01_In_the_heart_of.mp3 (245 KB)
  - scene_02_Under_the_gentle.mp3 (189 KB)
  - scene_03_Bathed_in_soft.mp3 (267 KB)

VIDEO_CLIPS:
  - scene_01_In_the_heart_of.mp4 (2.1 MB)
  - scene_02_Under_the_gentle.mp4 (1.8 MB)
  - scene_03_Bathed_in_soft.mp4 (2.3 MB)

FINAL_VIDEO:
  - The_Story_of_the_Rosetta_Stone_short_form_final.mp4 (15.2 MB)

=== SCRIPT CONTENT ===
[Complete script text here...]
```

### 4. Automatic Cleanup
- Temporary files are automatically cleaned up after successful generation
- Original scattered files are moved to organized locations
- Duplicate prevention through intelligent file handling

## Usage

### Automatic Organization
The file organization system is automatically integrated into the video generation pipeline. When you run:

```bash
python main.py run-full-pipeline
```

All generated files will be automatically organized according to the new structure.

### Manual Organization
You can also organize existing scattered files:

```bash
# Organize scattered files in output directory
python main.py organize-files

# Or use the test script
python test_file_organizer.py cleanup
```

### Testing the System
Test the organization system with sample data:

```bash
python test_file_organizer.py
```

## Benefits

### 1. Easy Navigation
- **Hierarchical structure**: Find projects by name, then by type, then by date
- **Consistent naming**: All files follow predictable naming conventions
- **Clear categorization**: Images, audio, video clips, and final videos are separated

### 2. Version Control
- **Timestamp directories**: Each generation run is preserved
- **No overwrites**: Previous versions are maintained
- **Easy comparison**: Compare different versions side by side

### 3. Professional Organization
- **Clean structure**: No more scattered files in the root directory
- **Comprehensive metadata**: Complete information about each project
- **File inventory**: Know exactly what files were generated

### 4. Automation Ready
- **JSON metadata**: Perfect for automation and integration
- **Consistent paths**: Predictable file locations for scripts
- **Detailed tracking**: Complete audit trail of generation process

## File Naming Conventions

### Images
- Format: `scene_[NUMBER]_[DESCRIPTION].png`
- Example: `scene_01_In_the_heart_of.png`
- Description: First 5 words of the voice clip text

### Audio Files
- Format: `scene_[NUMBER]_[DESCRIPTION].mp3`
- Example: `scene_01_In_the_heart_of.mp3`
- Matches corresponding image naming

### Video Clips
- Format: `scene_[NUMBER]_[DESCRIPTION].mp4`
- Example: `scene_01_In_the_heart_of.mp4`
- Matches corresponding scene content

### Final Video
- Format: `[PROJECT_NAME]_[SCRIPT_TYPE]_final.mp4`
- Example: `The_Story_of_the_Rosetta_Stone_short_form_final.mp4`

### Stock Video Assets
- Format: `stock_video_[NUMBER]_[ORIGINAL_NAME]`
- Example: `stock_video_01_ancient_temple.mp4`
- Preserves original filename for reference

## Migration from Old System

### Automatic Migration
The system automatically handles scattered files:

1. **Detection**: Finds all `.png` and `.mp4` files in the root output directory
2. **Organization**: Moves them to a `Cleanup_Scattered_Files` project
3. **Cataloging**: Creates metadata for the organized files
4. **Cleanup**: Removes files from the root directory

### Manual Migration
If you have specific projects you want to organize:

1. Create the project structure manually
2. Move files to appropriate directories
3. Use the file organizer to generate metadata

## Configuration

### Customization Options
You can customize the file organization by modifying `src/utils/file_organizer.py`:

- **Directory names**: Change the subdirectory names
- **Naming conventions**: Modify the file naming patterns
- **Metadata format**: Customize the metadata structure
- **Cleanup behavior**: Adjust what gets cleaned up

### Integration Points
The file organizer integrates with:

- **Video Composer**: Automatically organizes generated content
- **Image Generator**: Organizes generated images
- **TTS System**: Organizes audio files
- **FFmpeg Editor**: Organizes video clips

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Ensure write permissions to output directory
   - Check file locks on Windows systems

2. **Path Length Issues**
   - Project names are automatically truncated to prevent path length issues
   - Use shorter project names if needed

3. **Cleanup Failures**
   - Temporary files may remain if cleanup fails
   - Manually delete temp directories if needed

### Recovery
If organization fails:

1. Check the logs for specific error messages
2. Verify file permissions
3. Ensure sufficient disk space
4. Try organizing files manually

## Future Enhancements

### Planned Features
- **Archive mode**: Compress old projects to save space
- **Search functionality**: Search across all projects
- **Web interface**: Browse organized files through a web UI
- **Export options**: Export projects in different formats
- **Cloud sync**: Sync organized projects to cloud storage

### Integration Opportunities
- **Database tracking**: Store file organization in database
- **Analytics**: Track file sizes and generation statistics
- **Backup system**: Automatic backup of organized projects
- **Sharing**: Easy sharing of organized projects 