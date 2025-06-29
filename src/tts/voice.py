import os
import re
import glob
from typing import List
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from src.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, TTS_CACHE_DIR
from src.utils.output_manager import get_tts_file_path
from dataclasses import dataclass

# Initialize ElevenLabs client
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY is not set. Please check your .env file.")
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

@dataclass
class VoiceClip:
    """Represents a segment of voiceover with its corresponding text."""
    text: str
    audio_path: str

def _clean_text_for_tts(text: str) -> str:
    """Removes non-spoken artifacts from the script text."""
    # Remove bracketed tags like [HOOK], [TITLE], etc.
    text = re.sub(r'\[.*?\]', '', text)
    # Remove markdown like **...** but keep the text
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Remove any jinja artifacts if they slip through
    text = re.sub(r'\{\{.*?\}\}', '', text)
    text = re.sub(r'\{%.*?%\}', '', text)
    # Remove potential conversational filler from the LLM
    text = re.sub(r"^\s*Sure, here's the script:?\s*", '', text, flags=re.IGNORECASE)
    
    # Remove speaker cues (e.g., "NARRATOR (V.O.)", "JOHN:")
    # This will remove the cue if it's on its own line or at the start of a line of dialogue.
    text = re.sub(r"^\s*([A-Za-z\s'’.-]+)(\s*\(.*?\))?:?", '', text, flags=re.MULTILINE)

    # Strip leading/trailing whitespace from each line and remove empty lines
    lines = [line.strip() for line in text.split('\n')]
    cleaned_text = "\n".join(line for line in lines if line)

    return cleaned_text

def split_script_into_sentences(text: str) -> List[str]:
    """Splits a script into a list of sentences, handling both newlines and punctuation."""
    if not text:
        return []
    
    all_sentences = []
    # First, split the text into lines/paragraphs
    lines = text.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        # Then, split each line by sentence-ending punctuation
        sentences = re.split(r'(?<=[.?!])\s+', line)
        all_sentences.extend([s.strip() for s in sentences if s.strip()])
        
    return [s for s in all_sentences if len(s) > 1]

def generate_voice(script_id: int, text: any) -> List[VoiceClip]:
    """
    Generates voiceover audio for the given text using ElevenLabs.
    Saves audio sentence by sentence to allow for more granular editing.
    Returns a list of VoiceClip objects, each containing the text and path to the audio.
    """
    print(f"Generating voiceover with voice '{ELEVENLABS_VOICE_ID}' for script {script_id}...")
    
    # Clean up any old voice clips for this script_id
    print(f"Cleaning up old voice clips for script ID: {script_id}...")
    for old_clip in glob.glob(f"{TTS_CACHE_DIR}/tts_{script_id}_sentence_*.mp3"):
        try:
            os.remove(old_clip)
            print(f"  - Removed old clip: {os.path.basename(old_clip)}")
        except OSError as e:
            print(f"  - Error removing old clip {old_clip}: {e}")

    # Ensure text is a string
    text_content = str(text or "")

    if not text_content or text_content.startswith("<class 'sqlalchemy"):
        print(f"Warning: Script content for {script_id} is invalid or empty. Skipping TTS.")
        return []

    print(f"Original script content (first 100 chars): \"{text_content[:100]}...\"")
    
    cleaned_text = _clean_text_for_tts(text_content)
    print("\n--- Cleaned Script for Voice Generation ---")
    print(cleaned_text)
    print("-------------------------------------------")
    
    sentences = split_script_into_sentences(cleaned_text)
    print(f"Found {len(sentences)} sentences in the script")
    voice_clips: List[VoiceClip] = []

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
                voice_clips.append(VoiceClip(text=sentence, audio_path=str(file_path)))
            except Exception as e:
                print(f"An error occurred with ElevenLabs API: {e}")
                continue
        else:
            print(f"Using cached audio: {file_path}")
            voice_clips.append(VoiceClip(text=sentence, audio_path=str(file_path)))

    print(f"Finished generating {len(voice_clips)} audio segments.")
    return voice_clips

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
            print(f"- Text: \"{clip.text}\" -> File: {clip.audio_path}")
    else:
        print("\nCould not generate audio clips. Please check API key and script content.")

if __name__ == "__main__":
    main() 