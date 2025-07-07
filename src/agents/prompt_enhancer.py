import os
from openai import OpenAI
from src.utils.logger import logger

def enhance_prompt(phrase: str, client: OpenAI) -> str:
    """
    Enhances a simple phrase from the script into a detailed, descriptive prompt
    for an image generation model.
    """
    logger.info(f"Enhancing prompt for phrase: '{phrase}'")

    system_prompt = (
        "You are an expert prompt engineer for text-to-image models, specializing in a modern educational documentary style. "
        "Your task is to take a short phrase from a documentary script and expand it into a rich, detailed, and evocative prompt that describes a 3D scene."
        "\n\n"
        "**RULES:**"
        "\n1.  **Core Focus**: The generated prompt MUST be a direct and faithful visualization of the provided phrase. Do not introduce concepts or characters not mentioned in the original phrase."
        "\n2.  **Artistic Style & Render**: The visual aesthetic is a sleek, 3D-rendered scene with a low-poly aesthetic, creating a modern and clean educational documentary vibe. Describe the scene using these specific keywords and concepts:"
        "\n    - **Geometry**: 'low-poly aesthetic', 'clean geometry', 'minimal but well-defined detail'."
        "\n    - **Materials**: 'soft PBR materials', 'subtle ambient occlusion'."
        "\n    - **Render Style**: '3D render', 'clean, crisp anti-aliased edges', 'no cartoonish colors'."
        "\n3.  **Lighting**: Describe a professional lighting setup. Use terms like '3-point lighting', 'soft fill light', 'gentle backlight rim for depth', 'neutral key light', 'no harsh contrast', 'neutral diffused lighting'."
        "\n4.  **Color Palette**: The prompt must specify a color scheme. Use keywords like 'muted color palette', 'teal and gray tones', 'warm accent highlights' to convey a calm, authoritative tone."
        "\n5.  **Environment & Composition**: Describe a minimal environment, such as a 'minimal surface' or 'abstract ground plane' with 'faint soft shadows'. You can optionally include 'floating labeled text overlays in a modern sans-serif font'."
        "\n6.  **Camera**: Define the camera properties. Use terms like 'cinematic 16:9 framing', 'shallow depth-of-field', and 'slight motion blur on edges' for a dynamic, high-quality look."
        "\n7.  **Output Format**: The output must be a single paragraph containing the detailed prompt. Do not add any extra text, titles, or explanations."
    )
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the phrase: \"{phrase}\""}
            ],
            temperature=0.7,
            max_tokens=500,
        )
        
        enhanced_prompt = response.choices[0].message.content.strip()
        logger.info(f"Enhanced prompt: {enhanced_prompt}")
        return enhanced_prompt

    except Exception as e:
        logger.error(f"Failed to enhance prompt: {e}")
        # Fallback to the original phrase if enhancement fails
        return phrase

if __name__ == '__main__':
    # Example usage for testing
    test_phrase = "The Roman Empire's rise to power."
    test_topic = "The History of Ancient Rome"
    enhanced = enhance_prompt(test_phrase, test_topic)
    print("\n--- Final Enhanced Prompt ---")
    print(enhanced) 