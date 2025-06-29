from typing import List, Dict
import re
import requests
from bs4 import BeautifulSoup

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
    Searches Google to find real products based on an idea and category.

    Args:
        idea: The core idea for the video.
        category: The product category.
        max_products: The maximum number of products to return.

    Returns:
        A list of dictionaries, where each dictionary represents a product.
    """
    print(f"\n--- Searching for real products related to: '{idea}' ---")
    
    query = f"top affiliate products for {idea} in {category}"
    print(f"Web search query: \"{query}\"")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(f"https://www.google.com/search?q={query}", headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        
        products = []
        # Look for search result titles (typically in h3 tags)
        for header in soup.find_all('h3', limit=max_products * 2):
            title = header.get_text()
            # Basic filtering to avoid irrelevant results
            if "›" in title or "»" in title or "·" in title or len(title.split()) < 3:
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
                if len(products) >= max_products:
                    break
        
        if not products:
            print("Could not extract any suitable products from the search results.")
            return []

        print(f"Found {len(products)} potential products.")
        return products

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during web search: {e}")
        return []
    except Exception as e:
        print(f"An error occurred while parsing search results: {e}")
        return []

def main():
    """Demonstrates finding real products."""
    idea = "mood-enhancing smart light"
    category = "Productivity Tools"
    
    products = find_real_products(idea, category)
    
    if products:
        print("\n--- Found Products ---")
        for i, product in enumerate(products):
            print(f"{i+1}. {product['name']} ({product['url']})")
    else:
        print("\nNo products found for the given idea.")

if __name__ == "__main__":
    main() 