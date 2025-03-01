from app.core.intent_classifier import classify_intent
from app.core.query_generator import generate_sql_query
from app.core.db_connector import execute_query
from app.core.similarity import find_similar_properties
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import os
import re

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4", temperature=0.7, openai_api_key=OPENAI_API_KEY)

# Required details for query execution
REQUIRED_DETAILS = ["location", "budget", "property_type"]

def gather_missing_details(collected_info):
    """Identify missing details and ask the user accordingly."""
    missing_details = [detail for detail in REQUIRED_DETAILS if detail not in collected_info]
    
    if not missing_details:
        return None  # All necessary details are present
    
    # Generate a follow-up question for missing details
    question_prompt = PromptTemplate(
        input_variables=["missing_details"],
        template="""
        You are an AI real estate assistant. The user is looking for a property but has not provided the following details: {missing_details}. 
        Ask a friendly, natural question to collect this missing information. Ensure that you only ask for what is missing.
        """
    )
    
    return llm.predict(question_prompt.format(missing_details=", ".join(missing_details))).strip()

def extract_info(user_input):
    """Extracts key details like location, budget, and property type from the user input."""
    collected_info = {}

    # Extract budget (e.g., "5000 SGD")
    budget_match = re.search(r'(\d+)\s*SGD', user_input, re.IGNORECASE)
    if budget_match:
        collected_info["budget"] = int(budget_match.group(1))

    # Extract location (basic approach: look for "in <location>")
    location_match = re.search(r'in\s+([\w\s]+)', user_input, re.IGNORECASE)
    if location_match:
        collected_info["location"] = location_match.group(1).strip()

    # Extract property type (basic matching for common types)
    property_types = ["apartment", "condo", "house", "studio", "villa"]
    for prop in property_types:
        if prop in user_input.lower():
            collected_info["property_type"] = prop
            break

    return collected_info

def process_user_query(user_input, collected_info):
    """Handles user queries, asks for missing details, and executes the appropriate SQL query."""
    intent = classify_intent(user_input)
    
    if intent == "General Query":
        return llm.predict(user_input)
    
    # Extract details from user input
    extracted_info = extract_info(user_input)
    collected_info.update(extracted_info)

    # Check for missing details
    missing_query = gather_missing_details(collected_info)
    if missing_query:
        return missing_query
    
    # Generate SQL query once enough details are available
    sql_query = generate_sql_query(collected_info)
    results = execute_query(sql_query)
    
    if results:
        return f"Here are the properties matching your criteria: {results}"
    
    # If no results, suggest similar properties based on budget
    similar_properties = find_similar_properties(collected_info.get("budget"), user_input)
    if similar_properties:
        return f"No exact matches found, but here are some similar properties: {similar_properties}"
    
    return "Sorry, we couldn't find any matching properties. Let me know if you'd like to adjust your criteria!"

# Example Usage
collected_info = {}
user_input = "Fetch me the address of property with id 69 and also mention the houses present in it"
response = process_user_query(user_input, collected_info)
print(response)
