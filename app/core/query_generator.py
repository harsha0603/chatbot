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

# Fetch the latest schema
DB_SCHEMA = get_db_schema()

# Convert schema dictionary into formatted text
formatted_schema = "\n".join(
    [f"Table: {table}\nColumns: {', '.join(columns)}" for table, columns in DB_SCHEMA.items()]
)

# Define SQL Query Generation Prompt
generate_sql_prompt = PromptTemplate(
    input_variables=["user_query", "formatted_schema"],
    template="""
You are an AI that generates **only** SQL SELECT queries based on the user's request and the provided database schema. **You must never generate queries that modify data (INSERT, UPDATE, DELETE, DROP, etc.).**

**Database Schema:**
{formatted_schema}

**User Query:**
{user_query}

Generate a valid SQL SELECT query only. Return only the SQL query, no explanations.
"""
)

def generate_sql_query(user_query):
    """Generates a read-only SQL query based on the user's input."""
    intent = classify_intent(user_query)
    if intent != "DB Specific Query":
        return None  # If not a DB query, SQL generation isn't needed

    try:
        sql_query = llm.predict(generate_sql_prompt.format(
            user_query=user_query, formatted_schema=formatted_schema
        )).strip()

        # Ensure the query is read-only
        if not sql_query.lower().startswith("select"):
            print("❌ Invalid query generated: Only SELECT statements are allowed.")
            return None
        
        return sql_query
    except Exception as e:
        print(f"Error generating SQL query: {e}")
        return None
