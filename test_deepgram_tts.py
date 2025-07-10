
import os
import asyncio
from dotenv import load_dotenv
from deepgram import DeepgramClient, SpeakOptions

load_dotenv()

async def main():
    """
    Main function to run the Deepgram TTS test.
    """
    try:
        # Get the Deepgram API key from the environment variable
        api_key = os.getenv("DEEPGRAM")
        if not api_key:
            print("Error: DEEPGRAM environment variable not set.")
            return

        # Initialize the Deepgram client
        deepgram = DeepgramClient(api_key)

        # Text to be converted to speech
        text = "Hello, this is a test of the Deepgram Text-to-Speech API."
        
        # Define the output directory and file
        output_dir = "audio_tests"
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, "test_audio.mp3")

        # Set the speak options
        options = SpeakOptions(
            model="aura-2-jupiter-en",
            encoding="mp3"
        )

        # Perform the TTS and save to a file
        response = deepgram.speak.rest.v("1").stream_memory(
            {"text": text},
            options
        )

        with open(filename, "wb") as f:
            f.write(response.stream.getvalue())

        print(f"Successfully created TTS audio file at: {filename}")


    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 