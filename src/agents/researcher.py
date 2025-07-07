import asyncio
from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.utils.logger import logger

# Initialize OpenAI client
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def research_subject(subject: str) -> str:
    """
    Researches a given subject by generating a detailed summary using the OpenAI API.
    """
    logger.info(f"--- Generating research summary for subject: '{subject}' ---")
    
    prompt = f"""
    You are a world-class researcher. Your task is to generate a detailed, factual, and engaging summary for a short documentary about the following subject: "{subject}".

    Please provide a comprehensive overview covering the most important aspects of this topic. Structure your response with clear paragraphs, and ensure the information is accurate and well-organized. The summary should be detailed enough to serve as the primary source material for a 3-5 minute documentary script.

    Include the following:
    - Key historical events, dates, and figures.
    - The main points of interest or significance.
    - Any interesting or little-known facts.
    - The lasting impact or legacy of the subject.

    Please write the summary directly. Do not include any introductory or concluding remarks like "Here is the summary...".
    """

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"Successfully generated research summary for '{subject}'.")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating research summary with OpenAI: {e}")
        raise Exception("Failed to generate research summary.")

async def main():
    """Main function for testing the researcher agent."""
    test_subject = "The Great Emu War of 1932"
    try:
        summary = await research_subject(test_subject)
        print("\n--- Research Summary ---")
        print(summary)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(main()) 