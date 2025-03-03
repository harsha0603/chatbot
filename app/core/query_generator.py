from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
from app.core.intent_classifier import classify_intent 
from app.config.db_config import get_db_schema 

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize LLM
llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=OPENAI_API_KEY)

# Fetch and validate schema
def get_validated_schema():
    """Fetch and validate the database schema, ensuring required tables exist."""
    schema = get_db_schema()
    if not schema:
        raise Exception("Failed to fetch database schema")
    
    required_tables = {'properties', 'rooms'}
    missing_tables = required_tables - set(schema.keys())
    if missing_tables:
        raise Exception(f"Missing required tables: {missing_tables}")
    
    # Print the actual schema for debugging
    print("Available Database Schema:")
    for table, columns in schema.items():
        print(f"Table: {table}")
        print(f"Columns: {', '.join(columns)}\n")
    
    return schema

# Fetch the schema once at module load
try:
    DB_SCHEMA = get_validated_schema()
    # Convert schema dictionary into formatted text
    formatted_schema = "\n".join(
        [f"Table: {table}\nColumns: {', '.join(columns)}" for table, columns in DB_SCHEMA.items()]
    )
except Exception as e:
    print(f"Error initializing schema: {e}")
    raise

# Define SQL Query Generation Prompt with explicit schema information
generate_sql_prompt = PromptTemplate(
    input_variables=["user_query", "formatted_schema", "requirements"],
    template="""
You are a real estate database expert that generates SQL SELECT queries based on property search requirements.

**COMPLETE Database Schema:**
{formatted_schema}

**Key Tables and Their Relationships:**
- rooms table contains rental listings with prices and details
- properties table contains property information
- Tables are linked by propertyid

**Important Search Fields:**
1. Location-related:
   - properties: add1, add2, city, state, zone, district, buildingname
   - rooms: nearestmrt, nearestbusstop

2. Price/Rent:
   - rooms: rentmonth

3. Property Details:
   - rooms: roomtype, propertytype, status
   - properties: propertyname

4. Amenities (in rooms):
   - airconditioned
   - wifi
   - tv
   - fridge
   - washer
   - gym
   - swimming

**User Requirements:**
{requirements}

**User Query:**
{user_query}

Generate a SQL SELECT query that:
1. JOINs rooms and properties tables using propertyid
2. Includes all relevant columns for a complete property listing
3. Uses appropriate WHERE conditions based on requirements:
   - For rent/budget: rooms.rentmonth <= [amount]
   - For location: Multiple LIKE conditions on location fields
   - For room type: rooms.roomtype or rooms.propertytype
   - For status: rooms.status = 'available' (always include this)
4. Orders by rooms.rentmonth ASC
5. Limits to 5 results

Return only the SQL query, no explanations.
"""
)

def generate_sql_query(user_query, requirements=None):
    """Generates a read-only SQL query based on the user's input and requirements."""
    try:
        sql_query = """
        SELECT r.*, p.*
        FROM rooms r
        JOIN properties p ON r.propertyid = p.propertyid
        WHERE 1=1
        """

        # Add conditions based on requirements
        if requirements:
            if requirements.get('budget'):
                sql_query += f"\nAND r.rentmonth > 0"  # Ensure rent is set
                sql_query += f"\nAND r.rentmonth <= {float(requirements['budget'])}"

            if requirements.get('location'):
                location_terms = requirements['location'].lower().split()
                location_conditions = []
                for term in location_terms:
                    location_conditions.extend([
                        f"LOWER(p.add1) LIKE '%{term}%'",
                        f"LOWER(p.city) LIKE '%{term}%'",
                        f"LOWER(p.zone) LIKE '%{term}%'"
                    ])
                sql_query += f"\nAND ({' OR '.join(location_conditions)})"

            if requirements.get('property_type'):
                prop_type = requirements['property_type'].lower()
                sql_query += f"\nAND (LOWER(r.roomtype) LIKE '%{prop_type}%' OR LOWER(r.propertytype) LIKE '%{prop_type}%')"

        # Status condition - active/available rooms
        sql_query += """
        AND r.rentmonth > 0  -- Only rooms with set rental prices
        AND r.status NOT IN ('i', 'I', 'inactive', 'INACTIVE')  -- Exclude inactive rooms
        """

        # Add ordering and limit
        sql_query += """
        ORDER BY r.rentmonth ASC
        LIMIT 5
        """

        print(f"Generated SQL Query: {sql_query}")  # Debug print
        return sql_query

    except Exception as e:
        print(f"Error generating SQL query: {e}")
        return None

def debug_generated_query(query: str):
    """Helper function to debug and validate generated queries."""
    if not query:
        return
    
    print("\nDebug Information:")
    print("=" * 50)
    print("Generated Query:", query)
    print("\nValidating Query Structure:")
    print("- SELECT statement:", query.lower().startswith("select"))
    print("- JOIN present:", "join" in query.lower())
    print("- WHERE conditions:", "where" in query.lower())
    print("- ORDER BY present:", "order by" in query.lower())
    print("- LIMIT present:", "limit" in query.lower())
    print("=" * 50)
