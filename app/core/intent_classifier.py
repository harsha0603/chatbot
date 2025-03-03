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
You are a real estate assistant that classifies user queries into two intent categories based on their content.

**Intent Categories:**  
- DB Specific Query: If the user is searching for properties, asking about available listings, or requesting specific property information (e.g., "Show me 2BHK flats in Mumbai", "Any properties under 50,000 in Bangalore?", "What are the available apartments in Delhi?")
- General Query: If the user is asking general questions about real estate, processes, or seeking advice (e.g., "How does the rental process work?", "What documents do I need?", "Is this a good time to rent?")

**User Query:** "{user_query}"

Return only the intent name ("DB Specific Query" or "General Query") with no explanations.
"""
)

def classify_intent(user_query):
    """Classifies the user's intent."""
    try:
        # Ensure the correct prompt formatting
        formatted_prompt = intent_prompt.format_prompt(user_query=user_query).to_string()

        # Get response from LLM
        response = llm.predict(formatted_prompt).strip()

        # Validate response
        valid_intents = {"DB Specific Query", "General Query"}
        if response not in valid_intents:
            print(f"Unexpected response: {response}")  # Log unexpected output
            return "Error"

        return response
    except Exception as e:
        print(f"Error classifying intent: {e}")
        return "Error"
