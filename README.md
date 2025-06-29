# AI-Powered Video Generation Agent

This project is a Python-based, modular, agent-driven pipeline that automates the end-to-end production of faceless YouTube content.

## Overview

The system is designed to:
- Generate niche product ideas for affiliate marketing.
- Produce multiple long-form and short-form scripts for each idea.
- Assemble videos using API-driven assets, AI voiceovers, and FFmpeg.
- Operate with minimal human intervention.

## Project Structure

```
.
├── src/
│   ├── agents/
│   │   ├── idea_selector.py
│   │   ├── idea_generator.py
│   │   ├── script_generator.py
│   │   └── video_composer.py
│   ├── controllers/
│   │   └── feedback.py
│   ├── utils/
│   │   └── output_manager.py
│   ├── assets/
│   ├── tts/
│   ├── editing/
│   └── templates/
├── tests/
├── output/
├── temp/
├── .env.example
├── config.yaml
├── niches.json
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── main.py
```

## Getting Started

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- FFmpeg (must be installed on the system if not using Docker)

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Create the environment file:**

    This project uses an `.env` file for managing API keys and other secrets. I am unable to create this file for you. Please create it manually:

    ```bash
    cp .env.example .env
    ```

    Now, open the `.env` file and fill in your actual API keys and configuration details.

3.  **Build and run the Docker container:**
    ```bash
    docker-compose build
    docker-compose up
    ```
    This will start the main application pipeline as defined in `docker-compose.yml`.

### Local Development (Without Docker)

1.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set Environment Variables:**
    Ensure the variables from the `.env` file are loaded into your shell. You can use a library like `python-dotenv` for this or source them manually.

3.  **Run the application:**
    The main entry point is `main.py`. You can run different parts of the pipeline using the CLI.
    ```bash
    # See available commands
    python main.py --help

    # Run the full pipeline
    python main.py run-full-pipeline

    # Run only idea generation
    python main.py run-idea-generation
    ```

## Usage

The primary way to run the agent is through the `run-full-pipeline` command, which will guide you through the process of selecting a category and generating a video.

---
*This project was bootstrapped by an AI assistant.* 