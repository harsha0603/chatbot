import re
from app.core.db_connector import execute_query

def extract_price(user_query):
    """Extracts price from user query using regex."""
    price_match = re.search(r'₹?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', user_query)
    if price_match:
        price = float(price_match.group(1).replace(',', ''))
        return price
    return None

def find_similar_properties(original_query, user_query):
    """Finds properties within ±5% price range if no exact match is found."""
    
    price = extract_price(user_query)
    
    if price is None:
        return "No price found in query."

    # Define the 5% price range
    lower_bound = price * 0.95
    upper_bound = price * 1.05

    # Modify query to search within the price range
    modified_query = f"""
    SELECT * FROM properties
    WHERE price BETWEEN {lower_bound} AND {upper_bound}
    ORDER BY ABS(price - {price}) ASC
    LIMIT 5;
    """

    # Execute the modified query
    results = execute_query(modified_query)

    if results:
        return results
    else:
        return "No similar properties found in the price range."

