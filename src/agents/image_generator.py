import os
import requests
from dotenv import load_dotenv
import time
import logging

# Load environment variables from .env file
load_dotenv()

API_URL = "https://api.aimlapi.com/v1/images/generations/"
API_KEY = os.getenv("AIML_API_KEY")

def generate_image(prompt: str, model: str = "flux/schnell", retries: int = 3):
    """
    Generates an image using the AIML API and returns the path to the saved image.

    Args:
        prompt (str): The text prompt for image generation.
        model (str): The model to use for generation.
        retries (int): The number of times to retry the request.

    Returns:
        str: The file path of the generated image, or None if generation failed.
    """
    if not API_KEY:
        logging.error("Error: AIML_API_KEY not found in environment variables.")
        return None

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "model": model,
    }

    logging.info(f"Generating image with prompt: '{prompt}' using model: {model}...")

    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()  # Raise an exception for bad status codes

            data = response.json()
            
            if "images" in data and len(data["images"]) > 0 and "url" in data["images"][0]:
                image_url = data["images"][0]["url"]
                logging.info(f"Image generated successfully! URL: {image_url}")
                
                # Download the image
                image_response = requests.get(image_url, stream=True)
                image_response.raise_for_status()

                # Create a filename from the prompt
                safe_prompt = "".join(c for c in prompt if c.isalnum() or c in " ._").rstrip()
                filename = f"{safe_prompt[:50]}_{int(time.time())}.png"
                output_path = os.path.join("output", filename)
                
                os.makedirs("output", exist_ok=True)
                with open(output_path, 'wb') as f:
                    for chunk in image_response.iter_content(1024):
                        f.write(chunk)
                
                logging.info(f"Image saved to {output_path}")
                return output_path
            else:
                logging.error(f"Could not find image URL in the API response: {data}")
                return None

        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt + 1}/{retries} failed with error: {e}")
            if attempt < retries - 1:
                logging.info("Waiting 1 second before retrying...")
                time.sleep(1)
            else:
                logging.error("All retry attempts failed.")
                return None

    return None

if __name__ == "__main__":
    # This part is for testing the function directly
    import argparse
    parser = argparse.ArgumentParser(description="Generate an image using the AIML API.")
    parser.add_argument("prompt", type=str, help="The prompt to generate the image from.")
    args = parser.parse_args()

    image_path = generate_image(args.prompt)
    if image_path:
        print(f"Image generation successful. Path: {image_path}")
    else:
        print("Image generation failed.") 