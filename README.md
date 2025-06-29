# Ads AI

An AI-powered system for automatically generating video advertisements.

## Overview

This project uses AI to create video advertisements by:
1. Generating creative ad ideas
2. Creating scripts for those ideas
3. Fetching relevant video clips
4. Generating voiceovers using text-to-speech
5. Composing final videos with proper timing and synchronization

## Features

- **Idea Generation**: Uses AI to generate creative ad concepts
- **Script Writing**: Creates both long-form and short-form ad scripts
- **Asset Collection**: Automatically fetches relevant video clips from Pexels
- **Text-to-Speech**: Converts scripts to high-quality voiceovers
- **Video Composition**: Assembles all elements into the final advertisement

## Installation

### Prerequisites

- Python 3.8+
- FFmpeg
- SQLite

### Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd Ads_AI
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```
   cp .env.example .env
   ```

5. Edit the `.env` file to add your API keys:
   - OpenAI API key for GPT models
   - ElevenLabs API key for voice synthesis
   - Pexels API key for video assets

## Usage

### Running the Application

```
python main.py
```

### Creating a Demo Video

```
python create_demo_video.py
```

### Testing Video Fetching

```
python test_video_fetcher.py
```

## Project Structure

- `src/agents/`: AI components for different tasks
- `src/assets/`: Asset fetching and management
- `src/tts/`: Text-to-speech functionality
- `src/editing/`: Video editing and composition
- `src/templates/`: Script templates
- `src/utils/`: Utility functions
- `db/`: Database files
- `output/`: Generated videos
- `temp/`: Temporary files and cache

## Configuration

Edit `config.yaml` to adjust settings like:
- Model selection
- Output formats
- Video parameters
- Asset preferences

## Docker

You can also run this application using Docker:

```
docker-compose up
```

## License

[Specify your license here]

## Credits

- Uses OpenAI's GPT models for text generation
- Uses ElevenLabs for voice synthesis
- Uses Pexels for video assets
- FFmpeg for video processing