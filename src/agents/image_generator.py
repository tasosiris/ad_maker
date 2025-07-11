import os
import requests
from dotenv import load_dotenv
import time
import logging
from openai import OpenAI, APIError, APIStatusError

load_dotenv()

AIMLAPI_BASE_URL = "https://api.aimlapi.com/v1"
API_KEY = os.getenv("AIMLAPI_KEY")

# Instantiate client once
if API_KEY:
    client = OpenAI(
        base_url=AIMLAPI_BASE_URL,
        api_key=API_KEY,
    )
else:
    client = None
    logging.error("Error: AIMLAPI_KEY not found in environment variables.")

def generate_image(job_context: dict, prompt: str, image_name: str, model: str = "flux/schnell", retries: int = 3):
    """
    Generates an image, tracks cost, and saves it to the job's output directory.
    Uses the OpenAI SDK-compatible AIMLAPI.
    """
    if not client:
        return None

    output_manager = job_context['output_manager']
    cost_tracker = job_context['cost_tracker']

    logging.info(f"Generating image '{image_name}' with prompt: '{prompt}' using model '{model}'...")

    for attempt in range(retries):
        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
            )

            image_url = None
            # Standard OpenAI response structure
            if response.data and len(response.data) > 0 and response.data[0].url:
                image_url = response.data[0].url
            # AIMLAPI-specific response structure
            elif hasattr(response, 'images') and isinstance(getattr(response, 'images', None), list) and len(response.images) > 0:
                image_info = response.images[0]
                if isinstance(image_info, dict) and 'url' in image_info:
                    image_url = image_info['url']

            if image_url:
                logging.info(f"Image generated successfully! URL: {image_url}")

                # Download the image
                image_response = requests.get(image_url, stream=True)
                image_response.raise_for_status()

                output_path = output_manager.get_images_directory() / f"{image_name}.png"

                with open(output_path, 'wb') as f:
                    for chunk in image_response.iter_content(1024):
                        f.write(chunk)

                logging.info(f"Image saved to {output_path}")

                cost_info = cost_tracker.add_cost(
                    "aimlapi",
                    model=model,
                    images=1
                )
                output_manager.save_prompt(
                    agent_name=f"image_generator_{image_name}",
                    prompt_data={"prompt": prompt, "model": model},
                    cost_info=cost_info
                )

                return str(output_path)
            else:
                logging.error(f"Could not find image URL in the API response: {response}")
                return None

        except (APIError, APIStatusError) as e:
            logging.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(1) # Simple backoff
            else:
                logging.error("All retry attempts failed.")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download image from URL {image_url}: {e}")
            return None

    return None

if __name__ == "__main__":
    from src.utils.output_manager import OutputManager
    from src.utils.cost_calculator import CostTracker

    logging.basicConfig(level=logging.INFO)

    test_prompt = "A majestic lion in the savanna at sunset, photorealistic."
    idea = "test_image_gen"
    image_name = "lion_test"

    output_manager = OutputManager(idea=idea)
    cost_tracker = CostTracker(output_dir=output_manager.get_job_directory())
    job_context = {
        "output_manager": output_manager,
        "cost_tracker": cost_tracker,
    }

    image_path = generate_image(job_context, test_prompt, image_name)
    
    if image_path:
        print(f"Image generation successful. Path: {image_path}")
    else:
        print("Image generation failed.")
    
    cost_tracker.save_costs()
    print(f"\nCosts tracked and saved in: {output_manager.get_job_directory()}") 