import re
from app.core.db_connector import execute_query
from typing import Dict, List, Optional

def extract_price(user_query: str) -> Optional[float]:
    """Extracts price from user query using regex."""
    price_match = re.search(r'₹?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', user_query)
    if price_match:
        price = float(price_match.group(1).replace(',', ''))
        return price
    return None

def extract_property_type(user_query: str) -> Optional[str]:
    """Extracts property type from user query."""
    property_types = ['apartment', 'condo', 'condominium', 'house', 'room', 'studio']
    query_lower = user_query.lower()
    
    for prop_type in property_types:
        if prop_type in query_lower:
            return prop_type
    return None

def find_similar_properties(original_query: str, user_query: str) -> List[Dict]:
    """
    Finds properties with similar characteristics if no exact match is found.
    Uses multiple criteria including price, location, and property type for matching.
    """
    price = extract_price(user_query)
    property_type = extract_property_type(user_query)
    
    # Base query parts
    select_clause = """
    SELECT DISTINCT p.*, r.*
    FROM properties p
    JOIN rooms r ON p.property_id = r.property_id
    WHERE 1=1
    """
    
    conditions = []
    params = []
    
    # Price similarity
    if price is not None:
        percentage = 0.10 if price < 25000 else 0.05
        lower_bound = price * (1 - percentage)
        upper_bound = price * (1 + percentage)
        conditions.append("r.rentmonth BETWEEN %s AND %s")
        params.extend([lower_bound, upper_bound])

    # Location matching
    location_match = re.search(r'in\s+([a-zA-Z\s]+)', user_query, re.IGNORECASE)
    if location_match:
        location = location_match.group(1).strip()
        conditions.append("(p.add1 LIKE %s OR p.zone LIKE %s)")
        params.extend([f"%{location}%", f"%{location}%"])

    # Property type matching
    if property_type:
        conditions.append("(LOWER(r.roomtype) LIKE %s OR LOWER(r.propertytype) LIKE %s)")
        params.extend([f"%{property_type}%", f"%{property_type}%"])

    # Combine conditions
    if conditions:
        select_clause += " AND " + " AND ".join(conditions)

    # Order by relevance
    order_clause = """
    ORDER BY 
        CASE 
            WHEN r.status = 'available' THEN 0
            ELSE 1
        END,
    """
    
    if price is not None:
        order_clause += f"""
        CASE 
            WHEN ABS(r.rentmonth - {price}) <= 1000 THEN 0
            ELSE 1
        END,
        ABS(r.rentmonth - {price}),
        """

    order_clause += "r.rentmonth ASC LIMIT 5"

    # Complete query
    query = select_clause + order_clause

    try:
        results = execute_query(query, params)
        if not results:
            return []
        return results
    except Exception as e:
        print(f"Error in similarity search: {e}")
        return []

