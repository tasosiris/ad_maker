import json
import random
import os

def generate_documentary_idea() -> str:
    """
    Selects a random documentary idea from the template file.
    """
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'documentary_ideas.json')
    
    try:
        with open(template_path, 'r') as f:
            ideas = json.load(f)
        
        if not ideas:
            raise ValueError("Idea template file is empty.")
            
        idea = random.choice(ideas)
        print(f"Selected idea from template: \"{idea}\"")
        return idea
        
    except FileNotFoundError:
        print(f"Error: Idea template file not found at '{template_path}'.")
        return "The History of the Internet" # Fallback
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error processing idea template file: {e}")
        return "The History of the Internet" # Fallback

def main():
    idea = generate_documentary_idea()
    print("\n--- Selected Idea ---")
    print(f"- {idea}")

if __name__ == "__main__":
    main() 