import click
import json
from typing import List

def select_category() -> str:
    """
    Presents a list of niches and allows the user to select or enter a custom category.
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

    while True:
        choice = input(f"Select a niche [1-{len(niches)}] or enter a custom category: ")
        try:
            choice_int = int(choice)
            if 1 <= choice_int <= len(niches):
                return niches[choice_int - 1]['name']
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