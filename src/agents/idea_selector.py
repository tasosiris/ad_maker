import click
import json
from typing import List
from inputimeout import inputimeout, TimeoutOccurred

def select_category() -> str:
    """
    Presents a list of niches and allows the user to select or enter a custom category.
    Includes a 3-second timeout that defaults to 'Credit Cards'.
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
        # Credit Cards is now option 6
        default_choice = 6
        prompt = f"Select a niche [1-{len(niches)}] or enter a custom category (default: {default_choice}): "
        choice = inputimeout(prompt=prompt, timeout=3)
    except TimeoutOccurred:
        choice = str(default_choice)
        print(f"\nTimeout occurred. Defaulting to niche #{default_choice}.")

    try:
        default_choice_index = 5  # 'Credit Cards' is at index 5
        if not choice: # Handle empty input
            print(f"No input received. Defaulting to niche #{default_choice_index + 1}.")
            return niches[default_choice_index]['name']
            
        choice_int = int(choice)
        if 1 <= choice_int <= len(niches):
            return niches[choice_int - 1]['name']
        else:
            # If the number is out of range, default to Credit Cards
            print(f"Invalid number. Defaulting to niche #{default_choice_index + 1}.")
            return niches[default_choice_index]['name']
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