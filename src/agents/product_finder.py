from typing import List, Dict
import re
import requests
from bs4 import BeautifulSoup
from src.utils.logger import logger
import os
import json

def extract_commission_info(text: str) -> str:
    """
    Attempts to extract affiliate commission information from product titles/descriptions.
    Returns a default range if no specific commission is found.
    """
    # Common patterns for commission rates
    commission_patterns = [
        r'(\d+(?:\.\d+)?%?\s*-\s*\d+(?:\.\d+)?%)',  # "5-8%" or "5%-8%"
        r'(\d+(?:\.\d+)?%\s*commission)',            # "5% commission"
        r'(up to \d+(?:\.\d+)?%)',                   # "up to 8%"
        r'(\d+(?:\.\d+)?%\s*affiliate)',             # "5% affiliate"
    ]
    
    text_lower = text.lower()
    for pattern in commission_patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1)
    
    # Default commission ranges based on common affiliate programs
    if any(keyword in text_lower for keyword in ['amazon', 'amzn']):
        return "1-10%"  # Amazon Associates typical range
    elif any(keyword in text_lower for keyword in ['kitchen', 'home', 'gadget']):
        return "3-8%"   # Typical for home/kitchen products
    elif any(keyword in text_lower for keyword in ['tech', 'electronic']):
        return "2-6%"   # Typical for electronics
    else:
        return "3-7%"   # General default range

def find_real_products(idea: str, category: str, max_products: int = 5) -> List[Dict[str, str]]:
    """
    Searches for real products. First checks for a local JSON file in the 'products'
    directory. If not found, falls back to searching Google.
    """
    # Sanitize category name to create a valid filename
    sanitized_category = category.replace(" ", "_").replace("&", "and")
    product_file = f"products/{sanitized_category}.json"

    # 1. Check for a local product file first
    if os.path.exists(product_file):
        logger.info(f"Found local product file for category '{category}'. Loading from '{product_file}'.")
        try:
            with open(product_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            logger.info(f"Successfully loaded {len(products)} products from local file.")
            return products[:max_products]
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading or parsing local product file '{product_file}': {e}. Falling back to web search.")

    # 2. If no local file, fall back to Google search
    logger.info(f"No local product file found for '{category}'. Starting web search.")
    
    query = f"top affiliate products for {idea} in {category}"
    logger.info(f"Web search query: \"{query}\"")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(f"https://www.google.com/search?q={query}", headers=headers)
        response.raise_for_status()
        logger.info("Successfully fetched Google search results.")

        soup = BeautifulSoup(response.text, 'html.parser')
        
        products = []
        logger.info("Parsing search results for product titles...")
        # Look for search result titles (typically in h3 tags)
        for header in soup.find_all('h3', limit=max_products * 2):
            title = header.get_text()
            logger.info(f"  - Found potential title: '{title}'")
            # Basic filtering to avoid irrelevant results
            if "›" in title or "»" in title or "·" in title or len(title.split()) < 3:
                logger.warning(f"    - Skipping title (irrelevant): '{title}'")
                continue

            # Try to get the parent link
            parent_a = header.find_parent('a')
            if parent_a and parent_a.has_attr('href'):
                url = parent_a['href']
                # Clean up Google's redirect URL
                if url.startswith("/url?q="):
                    url = url.split('&')[0][7:]
                
                # Try to extract affiliate commission info from the title/description
                commission = extract_commission_info(title)
                
                products.append({
                    "name": title, 
                    "url": url,
                    "commission": commission
                })
                logger.info(f"    - Extracted Product: Name='{title}', URL='{url}', Commission='{commission}'")
                if len(products) >= max_products:
                    logger.info("Maximum number of products reached.")
                    break
        
        if not products:
            logger.warning("Could not extract any suitable products from the search results.")
            return []

        logger.info(f"Found {len(products)} potential products. Saving to '{product_file}' for future use.")
        # Save the new products to a local file for next time
        try:
            with open(product_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            logger.info("Successfully saved products to local cache.")
        except Exception as e:
            logger.error(f"Failed to save products to local cache file '{product_file}': {e}")
            
        return products

    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred during web search: {e}")
        return []
    except Exception as e:
        logger.error(f"An error occurred while parsing search results: {e}")
        return []

def main():
    """Demonstrates finding real products."""
    idea = "premium travel rewards card"
    category = "Credit Cards"
    
    products = find_real_products(idea, category)
    
    if products:
        logger.info("\n--- Found Products ---")
        for i, product in enumerate(products):
            logger.info(f"{i+1}. {product['name']} ({product.get('url', 'N/A')}) - Commission: {product.get('commission', 'N/A')}")
    else:
        logger.warning("\nNo products found for the given idea.")

if __name__ == "__main__":
    main() 