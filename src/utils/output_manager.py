import datetime
from pathlib import Path
import json

class OutputManager:
    """
    Manages the output directory structure for a single video generation job.
    
    Creates a unique directory for each job, containing subdirectories for 
    images, videos, audio, prompts, and cost reports.
    """
    def __init__(self, idea: str):
        sanitized_idea = "".join(c for c in idea if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.job_id = f"{sanitized_idea}_{timestamp}"
        
        # All output is stored in the `output` directory in the project root.
        self.base_dir = Path("output")
        self.job_dir = self.base_dir / self.job_id
        
        # Define paths for all subdirectories
        self.images_dir = self.job_dir / "images"
        self.videos_dir = self.job_dir / "videos"
        self.audio_dir = self.job_dir / "audio"
        self.prompts_dir = self.job_dir / "prompts"
        
        # Create all necessary directories
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(exist_ok=True)
        self.prompts_dir.mkdir(exist_ok=True)

    def get_job_directory(self) -> Path:
        """Returns the root directory for the current job."""
        return self.job_dir

    def get_images_directory(self) -> Path:
        """Returns the directory for storing images."""
        return self.images_dir

    def get_videos_directory(self) -> Path:
        """Returns the directory for storing final videos."""
        return self.videos_dir

    def get_audio_directory(self) -> Path:
        """Returns the directory for storing audio files."""
        return self.audio_dir
        
    def get_prompts_directory(self) -> Path:
        """Returns the directory for storing agent prompts."""
        return self.prompts_dir

    def save_prompt(self, agent_name: str, prompt_data: dict, cost_info: dict = None):
        """
        Saves an agent's prompt and (optionally) cost details to a file.
        
        Args:
            agent_name: The name of the agent (e.g., 'idea_generator').
            prompt_data: A dictionary containing the prompt details.
            cost_info: A dictionary containing cost information for the API call.
        """
        filename = f"{agent_name}_prompt.txt"
        filepath = self.prompts_dir / filename
        
        content = f"--- PROMPT: {agent_name} ---\n"
        content += json.dumps(prompt_data, indent=4)
        
        if cost_info:
            content += f"\n\n--- COST ---\n"
            content += json.dumps(cost_info, indent=4)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def save_json(self, filename: str, data: dict, subdir: str = None):
        """
        Saves a dictionary to a JSON file within the job directory.

        Args:
            filename: The name of the file (e.g., 'metadata.json').
            data: The dictionary to save.
            subdir: An optional subdirectory within the job directory.
        """
        if subdir:
            target_dir = self.job_dir / subdir
            target_dir.mkdir(exist_ok=True)
        else:
            target_dir = self.job_dir
        
        filepath = target_dir / filename
        with open(filepath, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=4) 