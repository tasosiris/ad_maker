import os
import re
import asyncio
from typing import List
import requests
from src.config import DEEPGRAM_API_KEY
from dataclasses import dataclass
from deepgram import DeepgramClient, SpeakOptions

# Initialize Deepgram
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY is not set. Please check your .env file.")

deepgram = DeepgramClient(DEEPGRAM_API_KEY)

@dataclass
class VoiceClip:
    """Represents a segment of voiceover with its corresponding text."""
    text: str
    audio_path: str

def _clean_text_for_tts(text: str) -> str:
    """Removes non-spoken artifacts from the script text."""
    text = text.replace("[PAUSE]", ".")
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\{\{.*?\}\}', '', text)
    text = re.sub(r'\{%.*?%\}', '', text)
    text = re.sub(r"^\s*Sure, here's the script:?\s*", '', text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*([A-Za-z\s'’.-]+)(\s*\(.*?\))?:\s*,?", '', text, flags=re.MULTILINE)
    lines = [line.strip() for line in text.split('\n')]
    cleaned_text = "\n".join(line for line in lines if line)
    return cleaned_text

def split_script_into_sentences(text: str) -> List[str]:
    """Splits a script into a list of sentences, respecting newlines as deliberate breaks."""
    if not text:
        return []
    sentences = []
    chunks = text.split('\n')
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        sub_sentences = re.split(r'(?<=[.?!])\s+', chunk)
        for s in sub_sentences:
            clean_s = s.strip()
            if clean_s:
                sentences.append(clean_s)
    return [s for s in sentences if len(s) > 1]

async def generate_voice(job_context: dict, script_name: str, text_content: str) -> List[VoiceClip]:
    """
    Generates voiceover audio using Deepgram, tracks costs, and saves to the job's output directory.
    """
    output_manager = job_context['output_manager']
    cost_tracker = job_context['cost_tracker']
    
    print(f"Generating voiceover with Deepgram for script '{script_name}'...")
    
    if not text_content:
        print(f"Warning: Script content for {script_name} is empty. Skipping TTS.")
        return []

    cleaned_text = _clean_text_for_tts(text_content)
    sentences = split_script_into_sentences(cleaned_text)
    print(f"Found {len(sentences)} sentences in the script.")
    voice_clips: List[VoiceClip] = []

    audio_dir = output_manager.get_audio_directory()

    for i, sentence in enumerate(sentences):
        file_path = audio_dir / f"{script_name}_sentence_{i}.mp3"
        
        if not file_path.exists():
            try:
                print(f"Generating audio for: \"{sentence[:50]}...\"")
                
                # New implementation using deepgram-sdk
                options = SpeakOptions(
                    model="aura-2-jupiter-en",
                    encoding="mp3"
                )
                response = deepgram.speak.rest.v("1").stream_memory(
                    {"text": sentence},
                    options
                )
                with open(file_path, "wb") as f:
                    f.write(response.stream.getvalue())

                # Old implementation using requests (commented out)
                # url = "https://api.deepgram.com/v1/speak?model=aura-2-thalia-en"
                # headers = {
                #     "Authorization": f"Bearer {DEEPGRAM_API_KEY}",
                #     "Content-Type": "application/json"
                # }
                # payload = {"text": sentence}
                
                # response = requests.post(url, json=payload, headers=headers)
                # response.raise_for_status()

                # with open(file_path, 'wb') as f:
                #     f.write(response.content)

                cost_tracker.add_cost(
                    "deepgram",
                    model="aura-2-jupiter-en",
                    characters=len(sentence),
                )
                
                voice_clips.append(VoiceClip(text=sentence, audio_path=str(file_path)))
            except Exception as e:
                print(f"An error occurred with Deepgram API: {e}")
                continue
        else:
            print(f"Using cached audio: {file_path}")
            voice_clips.append(VoiceClip(text=sentence, audio_path=str(file_path)))

    print(f"Finished generating {len(voice_clips)} audio segments.")
    return voice_clips

def main():
    """Demonstrates generating real voiceover from a script."""
    from src.utils.output_manager import OutputManager
    from src.utils.cost_calculator import CostTracker

    long_script = (
        "Hello and welcome to the future of technology! Today, we are diving deep into a revolutionary new gadget. "
        "It promises to change the way we interact with our digital world. But does it live up to the hype? "
        "Let's find out together. We will explore its features, test its limits, and give you our final verdict."
    )
    
    idea = "tech_demo"
    script_name = "long_form_1"
    output_manager = OutputManager(idea=idea)
    cost_tracker = CostTracker(output_dir=output_manager.get_job_directory())
    job_context = {
        "output_manager": output_manager,
        "cost_tracker": cost_tracker,
    }

    print("--- Attempting to generate real audio from Deepgram ---")
    voice_clips = asyncio.run(generate_voice(job_context, script_name, long_script))
    
    if voice_clips:
        print(f"\nSuccessfully generated {len(voice_clips)} audio clips:")
        for clip in voice_clips:
            print(f"- Text: \"{clip.text}\" -> File: {clip.audio_path}")
    else:
        print("\nCould not generate audio clips. Please check API key and script content.")

    cost_tracker.save_costs()
    print(f"\nCosts tracked and saved in: {output_manager.get_job_directory()}")

if __name__ == "__main__":
    main() 