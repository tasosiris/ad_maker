import os
import yaml
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Load config.yaml ---
CONFIG_PATH = Path(PROJECT_ROOT) / "config.yaml"
try:
    with open(CONFIG_PATH, 'r') as f:
        _config = yaml.safe_load(f)
except FileNotFoundError:
    print("FATAL: config.yaml not found. Make sure it exists in the root directory.")
    exit(1)
except yaml.YAMLError as e:
    print(f"FATAL: Error parsing config.yaml: {e}")
    exit(1)

# --- API Keys ---
# It's recommended to load sensitive keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") # Placeholder for future use

# --- OpenAI Model ---
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# --- Database ---
DB_CONFIG = _config.get('database', {})
DB_TYPE = DB_CONFIG.get('type', 'sqlite')
DB_PATH = Path(PROJECT_ROOT) / DB_CONFIG.get('path', 'db/state.db')
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING") or DB_CONFIG.get('connection_string')

# --- Logging ---
LOG_CONFIG = _config.get('logging', {})
LOG_LEVEL = LOG_CONFIG.get('level', 'INFO')
LOG_FILE = Path(PROJECT_ROOT) / LOG_CONFIG.get('file', 'logs/app.log')
LOG_FORMAT = LOG_CONFIG.get('format', 'text')

# --- Video Defaults ---
VIDEO_DEFAULTS = _config.get('video_defaults', {})
VIDEO_RESOLUTION = VIDEO_DEFAULTS.get('resolution', '1080p')
VIDEO_FPS = VIDEO_DEFAULTS.get('fps', 30)

# --- Cache Directories ---
CACHE_CONFIG = _config.get('cache', {})
ASSET_CACHE_DIR = Path(PROJECT_ROOT) / CACHE_CONFIG.get('asset_dir', 'temp/assets')
TTS_CACHE_DIR = Path(PROJECT_ROOT) / CACHE_CONFIG.get('tts_dir', 'temp/tts')

# --- TTS Defaults ---
TTS_DEFAULTS = _config.get('tts_defaults', {})
# Ensure ELEVENLABS_VOICE_ID is prioritized if available
if not ELEVENLABS_VOICE_ID:
    ELEVENLABS_VOICE_ID = TTS_DEFAULTS.get('voice_id', 'Adam')

# --- Ensure required directories exist ---
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
ASSET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# --- Validation ---
if not all([OPENAI_API_KEY, PEXELS_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID]):
    print("FATAL: One or more required API keys (OPENAI_API_KEY, PEXELS_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID) are missing.")
    print("Please check your .env file.")
    exit(1) 