import asyncio
from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.utils.logger import logger

async def research_subject(job_context: dict) -> str:
    """
    Researches a given subject using the OpenAI API and tracks costs.
    """
    subject = job_context['idea']
    output_manager = job_context['output_manager']
    cost_tracker = job_context['cost_tracker']
    
    # Initialize OpenAI client
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

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
        usage = response.usage

        # Track cost
        cost_info = cost_tracker.add_cost(
            "openai",
            model=OPENAI_MODEL,
            tokens_input=usage.prompt_tokens,
            tokens_output=usage.completion_tokens
        )
        
        # Save prompt and cost details
        output_manager.save_prompt(
            agent_name="researcher",
            prompt_data={"prompt": prompt},
            cost_info=cost_info
        )
        
        # Save the research summary to its own file
        summary_path = output_manager.get_job_directory() / "research_summary.txt"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
            
        logger.info(f"Successfully generated research summary for '{subject}'.")
        logger.info(f"Research summary saved to: {summary_path}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating research summary with OpenAI: {e}")
        # Re-raise to be handled by the main pipeline
        raise Exception("Failed to generate research summary.")

async def main():
    """Main function for testing the researcher agent."""
    from src.utils.output_manager import OutputManager
    from src.utils.cost_calculator import CostTracker

    test_subject = "The Great Emu War of 1932"
    
    # Set up a dummy context for testing
    try:
        output_manager = OutputManager(idea=test_subject)
        cost_tracker = CostTracker(output_dir=output_manager.get_job_directory())
        job_context = {
            "idea": test_subject,
            "output_manager": output_manager,
            "cost_tracker": cost_tracker,
        }
        
        summary = await research_subject(job_context)
        print("\n--- Research Summary ---")
        print(summary)

        # Save the final cost report
        cost_tracker.save_costs()
        print(f"\nCosts tracked and saved in: {output_manager.get_job_directory()}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())