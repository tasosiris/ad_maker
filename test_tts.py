import os
from src.tts.voice import split_script_into_sentences, generate_voice
from src.config import TTS_CACHE_DIR

def test_tts():
    # Create a test script with multiple sentences
    test_content = """
    Introducing the Portable AR Headset - the ultimate tool for remote engineering and design collaboration.
    
    This lightweight, powerful headset combines high-resolution holographic displays with precision hand tracking.
    
    Engineers can manipulate 3D models in real-time while communicating with team members across the globe.
    
    Built-in spatial mapping creates shared virtual workspaces, enabling multiple users to collaborate on the same project simultaneously.
    
    With 6-hour battery life and industrial-grade durability, it's ready for any worksite.
    
    The Portable AR Headset - transforming how design teams work together, no matter the distance.
    """
    
    print(f"Original content:\n{test_content}")
    
    # Try splitting the content into sentences
    sentences = split_script_into_sentences(test_content)
    
    print(f"\nFound {len(sentences)} sentences:")
    for i, sentence in enumerate(sentences):
        print(f"{i+1}. {sentence}")
    
    # If previous files exist, delete them
    script_id = 999
    for i in range(10):
        file_path = os.path.join(TTS_CACHE_DIR, f"tts_{script_id}_sentence_{i}.mp3")
        if os.path.exists(file_path):
            print(f"Removing old file: {file_path}")
            os.remove(file_path)
    
    # Generate voice for the test content
    print("\nGenerating voice audio...")
    audio_paths = generate_voice(script_id, test_content)
    
    print(f"\nGenerated {len(audio_paths)} audio files:")
    for path in audio_paths:
        print(f"- {path}")

if __name__ == "__main__":
    test_tts() 