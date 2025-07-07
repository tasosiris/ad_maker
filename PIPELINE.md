# AI Documentary Generation Pipeline (V2)

This document provides a detailed, code-level explanation of the AI-powered documentary generation pipeline. It reflects the current architecture, which has evolved from ad generation to creating short-form and long-form documentaries using a sophisticated multi-agent system.

## High-Level Overview

The pipeline is a sequential, yet modular, process that transforms a single concept into a fully-produced video. It is orchestrated by a central Python script and leverages a database to manage state between different stages.

The major steps are:

1.  **Idea Generation**: The pipeline begins by selecting a random documentary topic from a predefined list.
2.  **AI-Powered Research**: A research agent uses a Large Language Model (LLM) to gather detailed, factual information about the chosen topic.
3.  **Database Job Creation**: A "job" is created in a database to track the entire lifecycle of the video, from scripting to rendering.
4.  **AI-Powered Scriptwriting**: A scriptwriting agent, guided by a high-quality example transcript, transforms the research summary into a theatrical and engaging narrative. The user can choose between long or short-form scripts.
5.  **Interactive Feedback Loop**: The generated script is presented to the user for review. The user can approve the script for production or request revisions.
6.  **Automated Video Composition**: Once approved, the video composer agent takes over. This is a multi-step process that involves:
    *   **Text-to-Speech (TTS)**: Generating a realistic voiceover for the script.
    *   **AI Image Generation**: Creating custom visual assets (images) for each sentence of the script.
    *   **Parallax Motion**: Turning static images into dynamic video clips with subtle motion effects.
    *   **Final Editing**: Assembling the voiceover, visual clips, and background music into a final video file.

---

## Detailed Step-by-Step Breakdown

### 1. The Orchestrator: `main.py`

The entire process is coordinated by `main.py`, which uses the `click` library to provide a command-line interface (CLI). The main command, `run_full_pipeline`, executes the entire sequence.

-   **Entry Point**: `run_full_pipeline` function.
-   **Responsibilities**:
    -   Calls each agent/module in the correct order.
    -   Handles database sessions (`get_db`).
    -   Manages the overall state of the pipeline run.
    -   Provides a command (`setup_database`) to initialize the database schema.
    -   Provides a utility command (`organize_files`) to clean up the output directory.

### 2. The Backbone: The Database (`src/database.py`)

The pipeline relies on a database (configurable as SQLite or PostgreSQL) to persist state and manage data. SQLAlchemy is used as the Object-Relational Mapper (ORM).

-   **Key Models**:
    -   `Job`: Represents a single documentary project. It tracks the `idea`, the current `status` (e.g., `scripting`, `approved`, `rendering`), and the `research_summary`.
    -   `Script`: Each `Job` can have multiple scripts. This table stores the script `content`, its `script_type` (`long_form` or `short_form`), and its individual `status` (`pending`, `approved`).
    -   `Feedback`: Stores the user's decision (`approved` or `revised`) and any textual `notes` for a specific script.

This relational structure ensures that all data related to a single video project is organized and interconnected.

### 3. Step 1: Idea Generation (`src/agents/idea_generator.py`)

The pipeline kicks off by generating an idea.

-   **Function**: `generate_documentary_idea()`
-   **Process**:
    1.  It reads a list of predefined topics from `src/templates/documentary_ideas.json`.
    2.  It uses Python's `random.choice()` to select a single idea from the list.
    3.  A fallback idea ("The History of the Internet") is used if the JSON file is missing or invalid.
-   **Example Ideas Source (`documentary_ideas.json`):**
    ```json
    [
        "The Rise and Fall of the Concorde Supersonic Jet",
        "A Day in the Life of a Storm Chaser",
        "The Forgotten Story of the First Female Computer Programmer",
        ...
    ]
    ```

### 4. Step 2: AI-Powered Research (`src/agents/researcher.py`)

Once an idea is selected, it's passed to the research agent to gather source material.

-   **Function**: `async research_subject(subject: str)`
-   **Process**:
    1.  **Prompt Engineering**: It constructs a detailed prompt that instructs an OpenAI model (e.g., GPT-4) to act as a "world-class researcher."
    2.  **Specific Instructions**: The prompt explicitly asks for key historical events, figures, interesting facts, and the subject's lasting legacy, ensuring a comprehensive summary.
    3.  **API Call**: It makes an `async` call to the OpenAI Chat Completions API.
    4.  **Output**: It returns a detailed, well-organized text summary that serves as the factual foundation for the script.

### 5. Step 3: Script Generation (`src/agents/script_generator.py`)

This agent transforms the factual research into a compelling narrative.

-   **Function**: `async generate_single_script(...)`
-   **Process**:
    1.  **Style Guidance (One-Shot Prompting)**: The agent first loads an example transcript from `src/templates/example_transcript.txt`. This provides the AI with a concrete example of the desired theatrical tone, emotional depth, and narrative pacing.
    2.  **Advanced Prompt Engineering**: It uses a sophisticated system prompt that defines the AI's persona ("world-class documentary scriptwriter") and provides a strict set of rules:
        -   Write in a dramatic, emotionally resonant style.
        -   Build a narrative arc with a strong hook.
        -   Use `[PAUSE]` markers for dramatic effect.
        -   Adhere to specific word counts for `long_form` and `short_form` videos.
        -   Focus *only* on the narrative text, excluding visual cues.
    3.  **Creative API Call**: The `temperature` parameter is set to `0.7` to encourage more creative and less deterministic output from the AI.
    4.  **Database Integration**: The generated script content is saved as a new `Script` record in the database, linked to the parent `Job`. The job's status is then updated to `feedback`.

### 6. Step 4: Interactive Feedback Loop (`src/controllers/feedback.py`)

This controller acts as a crucial quality gate, ensuring user approval before production.

-   **Function**: `collect_feedback(db: Session, script: Script)`
-   **Process**:
    1.  **Display Summary**: It first calls `display_script_summary()` to show the user a brief excerpt of the script.
    2.  **Timed Input**: It uses `inputimeout` to prompt the user for an action: `approve`, `revise`, or `quit`. It defaults to `approve` after 3 seconds, allowing for unattended runs.
    3.  **`approve`**: Updates the script status to `approved`. If all scripts for the job are approved, the job's master status is also set to `approved`, unlocking the final video composition stage.
    4.  **`revise`**: Prompts the user for notes, saves them to the `Feedback` table, and sets the script status to `revision_needed`.
    5.  **`quit`**: Halts the process.

### 7. Step 5: Video Composition (`src/agents/video_composer.py`)

This is the final, multi-stage assembly line where the video is created. The master function `compose_video_from_images` orchestrates the following sub-processes for an approved job.

#### 7.1. Text-to-Speech (`src/tts/voice.py`)

-   **Function**: `generate_voice()`
-   **Process**: The script text is split into sentences. Each sentence (and any `[PAUSE]` marker) is converted into an individual `.mp3` audio file using a TTS service. This segmentation is vital for synchronizing visuals.

#### 7.2. AI Image Generation (`src/agents/image_generator.py`)

-   **Function**: `generate_image()`
-   **Process**: For each sentence of narration, a unique visual is created.
    1.  **Prompt Enhancement (`src/agents/prompt_enhancer.py`)**: The raw sentence is first sent to the `enhance_prompt` function. This utility uses an LLM to embellish the simple sentence into a rich, descriptive prompt optimized for an image generation model (e.g., transforming "The car was fast" into "cinematic shot of a vintage red sports car blurring down a coastal highway at sunset, photorealistic, high-speed motion").
    2.  **Image Creation**: The enhanced prompt is then used to generate a high-resolution image via an AI image service like DALL-E.

#### 7.3. Creating Motion (`src/editing/parallax.py`)

-   **Function**: `create_parallax_video()`
-   **Process**: To avoid static, boring visuals, each generated image is converted into a short video clip. This function applies a "Ken Burns" effect—a slow, subtle pan and zoom—that gives the image a sense of motion and depth. The duration of each parallax clip is timed to match its corresponding voiceover sentence.

#### 7.4. Final Assembly (`src/editing/ffmpeg_editor.py`)

-   **Function**: `compose_video()`
-   **Process**: The `ffmpeg_editor` is the final assembler. It uses the powerful `ffmpeg` command-line tool to:
    1.  Concatenate all the parallax video clips in the correct order.
    2.  Overlay the corresponding voiceover clip for each scene, ensuring perfect synchronization.
    3.  Randomly select a background music track from `src/assets/music`.
    4.  Mix the background music into the final audio track at a lower volume.
    5.  Encode and render the final `.mp4` video file.
    6.  Save the video and a comprehensive metadata JSON file into a neatly organized folder structure within the `output/` directory.

---

This detailed pipeline showcases a modern approach to content creation, where multiple specialized AI agents collaborate, managed by a central orchestrator and stateful database, to automate the production of complex creative work. 