import click
import json
from typing import List
from inputimeout import inputimeout, TimeoutOccurred

def select_category() -> str:
    """
    Presents a list of niches and allows the user to select or enter a custom category.
    Includes a 3-second timeout that defaults to 'Health & Fitness'.
    """
    try:
        with open("niches.json", "r") as f:
            niches = json.load(f)
    except FileNotFoundError:
        print("Error: niches.json not found.")
        return ""
    except json.JSONDecodeError:
        print("Error: Could not decode niches.json.")
        return ""

    print("Available niches:")
    for i, niche in enumerate(niches, 1):
        print(f"{i}. {niche['name']}")

    choice = ''
    try:
        prompt = f"Select a niche [1-{len(niches)}] or enter a custom category (default: 3): "
        choice = inputimeout(prompt=prompt, timeout=3)
    except TimeoutOccurred:
        choice = '3'
        print(f"\nTimeout occurred. Defaulting to niche #3.")

    try:
        if not choice: # Handle empty input
            print("No input received. Defaulting to niche #3.")
            return niches[2]['name']
            
        choice_int = int(choice)
        if 1 <= choice_int <= len(niches):
            return niches[choice_int - 1]['name']
        else:
            # If the number is out of range, default to 3
            print(f"Invalid number. Defaulting to niche #3.")
            return niches[2]['name']
    except ValueError:
        # This means it's a custom category
        return choice

@click.command()
def main():
    """Idea Selector Agent CLI."""
    category = select_category()
    if category:
        print(f"Selected category: {category}")

if __name__ == "__main__":
    main() 