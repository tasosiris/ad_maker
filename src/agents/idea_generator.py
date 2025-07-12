import json
import random
import os
from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def load_base_ideas() -> list:
    """
    Loads the base pool of ancient Greek stories from the template file.
    """
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'documentary_ideas.json')
    
    try:
        with open(template_path, 'r') as f:
            ideas = json.load(f)
        
        if not ideas:
            raise ValueError("Idea template file is empty.")
            
        return ideas
        
    except FileNotFoundError:
        print(f"Error: Idea template file not found at '{template_path}'.")
        return ["The Trojan War: The Ten-Year Siege That Changed History"] # Fallback
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error processing idea template file: {e}")
        return ["The Trojan War: The Ten-Year Siege That Changed History"] # Fallback

def generate_creative_combination(base_ideas: list) -> str:
    """
    Uses AI to create new creative combinations from the base pool of ancient Greek stories.
    """
    # Select 3-5 random ideas as inspiration
    inspiration_count = random.randint(3, 5)
    inspiration_ideas = random.sample(base_ideas, min(inspiration_count, len(base_ideas)))
    
    prompt = f"""You are a creative documentary filmmaker specializing in ancient Greek history and mythology.
    
Based on these ancient Greek stories and themes:
{chr(10).join(f"- {idea}" for idea in inspiration_ideas)}

Create a NEW and UNIQUE documentary concept that combines elements from these stories in an innovative way. 
The concept should be:
- Historically grounded but creatively presented
- Suitable for a documentary format
- Engaging and dramatic
- Focus on a specific aspect, character, or event
- Include a compelling subtitle that explains the focus

Format: "Main Title: Descriptive Subtitle"

Examples of good combinations:
- "The Women Behind the Heroes: Untold Stories of Ancient Greece"
- "Divine Punishment: When Mortals Defied the Gods"
- "The Price of Glory: Heroes Who Paid the Ultimate Cost"

Generate ONE unique documentary concept:"""

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # High creativity
            max_tokens=100
        )
        
        new_idea = response.choices[0].message.content.strip()
        print(f"Generated creative combination: \"{new_idea}\"")
        return new_idea
        
    except Exception as e:
        print(f"Error generating creative combination: {e}")
        # Fallback to manual combination
        return create_manual_combination(inspiration_ideas)

def create_manual_combination(inspiration_ideas: list) -> str:
    """
    Creates a manual combination when AI generation fails.
    """
    themes = [
        "The Untold Story of",
        "The Hidden Truth Behind",
        "The Women of",
        "The Curse of",
        "The Legacy of",
        "The Secret Alliance of",
        "The Forgotten Heroes of",
        "The Divine Intervention in"
    ]
    
    # Extract key elements from inspiration ideas
    key_elements = []
    for idea in inspiration_ideas:
        if ":" in idea:
            key_elements.append(idea.split(":")[0])
        else:
            key_elements.append(idea)
    
    theme = random.choice(themes)
    element = random.choice(key_elements)
    
    return f"{theme} {element}: A New Perspective on Ancient Greece"

def generate_documentary_idea(force_creative: bool = False) -> str:
    """
    Generates a documentary idea - either from the base pool or creates a new creative combination.
    
    Args:
        force_creative: If True, always generates a creative combination
    """
    base_ideas = load_base_ideas()
    
    if force_creative or random.random() < 0.3:  # 30% chance for creative combination
        return generate_creative_combination(base_ideas)
    else:
        # Select from base pool
        idea = random.choice(base_ideas)
        print(f"Selected idea from template: \"{idea}\"")
        return idea

def generate_multiple_ideas(count: int = 5) -> list:
    """
    Generates multiple documentary ideas for selection.
    """
    ideas = []
    base_ideas = load_base_ideas()
    
    # Always include at least one creative combination
    ideas.append(generate_creative_combination(base_ideas))
    
    # Fill the rest with mix of base and creative ideas
    for _ in range(count - 1):
        if random.random() < 0.4:  # 40% chance for creative
            ideas.append(generate_creative_combination(base_ideas))
        else:
            ideas.append(random.choice(base_ideas))
    
    return ideas

def main():
    print("=== Ancient Greek Documentary Idea Generator ===\n")
    
    # Generate a single idea
    idea = generate_documentary_idea()
    print(f"\n--- Selected Idea ---")
    print(f"- {idea}")
    
    # Generate multiple ideas for comparison
    print(f"\n--- Alternative Ideas ---")
    alternatives = generate_multiple_ideas(3)
    for i, alt_idea in enumerate(alternatives, 1):
        print(f"{i}. {alt_idea}")

if __name__ == "__main__":
    main() 