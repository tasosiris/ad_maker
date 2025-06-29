import asyncio
import json
from typing import List
from openai import OpenAI, AsyncOpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL

# Initialize OpenAI client
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generate_ideas(category: str, n: int = 5) -> List[str]:
    """
    Generates high-paying, low-competition affiliate product ideas using OpenAI.
    """
    prompt = f"""
    Generate {n} high-paying, low-competition affiliate product ideas in the "{category}" niche.
    Your response MUST be a JSON object with a single key "ideas" which contains an array of strings.
    Each string should be a compelling, specific product idea.

    Example:
    {{
      "ideas": [
        "Self-healing screen protectors for foldable phones",
        "AI-powered posture correction device for office workers",
        "Smart hydroponic garden with automated nutrient delivery"
      ]
    }}
    """

    retries = 3
    for attempt in range(retries):
        try:
            print(f"Generating ideas for category: {category} (Attempt {attempt + 1})")
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=1.1, # Higher temperature for more creative ideas
            )
            
            response_text = response.choices[0].message.content
            if not response_text:
                raise ValueError("LLM returned an empty response.")

            ideas_data = json.loads(response_text)
            
            if "ideas" in ideas_data and isinstance(ideas_data["ideas"], list):
                print("Successfully generated ideas.")
                return ideas_data["ideas"]
            else:
                raise ValueError("LLM returned JSON in an unexpected format.")

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Error processing LLM response: {e}")
        except Exception as e:
            print(f"An unexpected error occurred with OpenAI API: {e}")

        if attempt < retries - 1:
            backoff_time = 2 ** (attempt + 1)
            print(f"Retrying in {backoff_time} seconds...")
            await asyncio.sleep(backoff_time)

    # Fallback if all retries fail
    print("LLM failed to generate ideas after multiple retries. Using fallback.")
    return [f"Fallback Idea for {category} #{i+1}" for i in range(n)]

async def main():
    category = "Home Gadgets"
    ideas = await generate_ideas(category, n=3)
    print("\n--- Generated Ideas ---")
    for idea in ideas:
        print(f"- {idea}")

if __name__ == "__main__":
    asyncio.run(main()) 