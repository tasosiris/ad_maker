import os
from typing import List
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from src.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, TTS_CACHE_DIR
from src.utils.output_manager import get_tts_file_path

# Initialize ElevenLabs client
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY is not set. Please check your .env file.")
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

def split_script_into_sentences(text) -> List[str]:
    """Splits a long script into a list of sentences."""
    # Convert SQLAlchemy Text object to string if necessary
    if text is None:
        return [""]
        
    # Fix: Properly convert SQLAlchemy Text type to a Python string
    if str(type(text)).find('sqlalchemy') >= 0:
        # This is a SQLAlchemy type that needs special handling
        from sqlalchemy import inspect
        # Try to extract the actual text content
        try:
            # For SQLAlchemy Text type, we need to get the actual Python string
            text_str = str(text)
            if text_str.startswith("<class 'sqlalchemy"):
                # If we're getting the class name instead of the value, try to extract from database
                return ["Error: Could not extract text content"]
        except Exception as e:
            print(f"Error converting SQLAlchemy type to string: {e}")
            return ["Error: Could not extract text content"]
    else:
        text_str = str(text)
    
    # A more robust implementation might use NLTK for sentence tokenization
    # For now, a simple split on punctuation will suffice.
    import re
    sentences = re.split(r'(?<=[.?!])\s+', text_str.replace("\n", " "))
    return [s.strip() for s in sentences if s.strip()]

def generate_voice(script_id: int, text) -> List[str]:
    """
    Generates voiceover audio for the given text using ElevenLabs.
    Saves audio sentence by sentence to allow for more granular editing.
    """
    print(f"Generating voiceover with voice '{ELEVENLABS_VOICE_ID}' for script {script_id}...")
    
    # Fix: Get the actual text content
    if text is None:
        print("Warning: Script content is None")
        text = "No content available."
    elif str(type(text)).find('sqlalchemy') >= 0:
        # Direct access to the actual script content
        from sqlalchemy.orm import Session
        from src.database import get_db, Script
        db = next(get_db())
        try:
            script = db.query(Script).filter_by(id=script_id).one()
            # Get the actual content from the database
            text = script.content
            db.close()
        except Exception as e:
            print(f"Error retrieving script content from database: {e}")
            text = "Error retrieving content."
    
    print(f"Script content (first 100 chars): \"{str(text)[:100]}...\"")
    
    sentences = split_script_into_sentences(text)
    print(f"Found {len(sentences)} sentences in the script")
    audio_paths = []

    for i, sentence in enumerate(sentences):
        # Construct a unique file path for each sentence
        file_path = get_tts_file_path(f"{script_id}_sentence_{i}")
        
        if not file_path.exists():
            try:
                print(f"Generating audio for: \"{sentence[:50]}...\"")
                audio = client.text_to_speech.convert(
                    voice_id=ELEVENLABS_VOICE_ID,
                    text=sentence,
                )
                save(audio, str(file_path))
                audio_paths.append(str(file_path))
            except Exception as e:
                print(f"An error occurred with ElevenLabs API: {e}")
                continue
        else:
            print(f"Using cached audio: {file_path}")
            audio_paths.append(str(file_path))

    print(f"Finished generating {len(audio_paths)} audio segments.")
    return audio_paths

def main():
    """Demonstrates generating real voiceover from a script."""
    long_script = (
        "Hello and welcome to the future of technology! Today, we are diving deep into a revolutionary new gadget. "
        "It promises to change the way we interact with our digital world. But does it live up to the hype? "
        "Let's find out together. We will explore its features, test its limits, and give you our final verdict."
    )
    
    script_id_for_demo = 999
    
    print("--- Attempting to generate real audio from ElevenLabs ---")
    voice_clips = generate_voice(script_id_for_demo, long_script)
    
    if voice_clips:
        print(f"\nSuccessfully generated {len(voice_clips)} audio clips:")
        for clip in voice_clips:
            print(f"- {clip}")
    else:
        print("\nCould not generate audio clips. Please check API key and script content.")

if __name__ == "__main__":
    main() 