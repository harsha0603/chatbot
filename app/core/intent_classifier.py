from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=OPENAI_API_KEY)

# Define intent classification prompt
intent_prompt = PromptTemplate(
    input_variables=["user_query"],
    template="""
You are an AI assistant that classifies user queries into two intent categories based on their content.  

**Intent Categories:**  
- DB Specific Query: If the user wants to retrieve data or information from a database (e.g., asking for records, filtering data, or querying specific fields).  
- General Query: If the user is asking a question or making a request unrelated to retrieving data from a database (e.g., asking for explanations, opinions, or general information).

**User Query:** "{user_query}"  

Return only the intent name ("DB Specific Query" or "General Query") with no explanations.
"""
)

def classify_intent(user_query):
    """Classifies the user's intent."""
    try:
        response = llm.predict(intent_prompt.format(user_query=user_query)).strip()
        return response
    except Exception as e:
        print(f"Error classifying intent: {e}")
        return "Error"

