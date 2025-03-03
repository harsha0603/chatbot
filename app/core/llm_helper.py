from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_llm_response(user_input, db_results=None, context=None):
    """
    Generates a response based on the user's query, database results, and context.
    
    - If `db_results` exist, format them and provide property details.
    - If no results, suggest alternatives if available.
    - If context is provided, use it to generate a meaningful response.
    - For general queries (greetings, irrelevant queries, missing details), respond accordingly.
    """

    if db_results:
        property_details = []
        for row in db_results:
            details = f"📍 Location: {row.get('location', 'Unknown')}, " \
                      f"💰 Price: {row.get('price', 'N/A')} per month, " \
                      f"🛏️ Rooms: {row.get('bedrooms', 'N/A')}, " \
                      f"🛁 Washroom: {row.get('washroom_type', 'Shared')}, " \
                      f"📶 Wifi: {row.get('wifi', 'Not available')}, " \
                      f"🏋️ Gym: {row.get('gym', 'Not available')}, " \
                      f"🏊 Swimming Pool: {row.get('swimming_pool', 'Not available')}"
            property_details.append(details)

        user_prompt = f"""You are a helpful property assistant. 
        The user asked: "{user_input}"

        Here are the matching properties:
        {property_details}

        Generate a friendly and engaging response to present these options.
        Encourage the user to proceed if interested.
        """

    elif context:
        user_prompt = f"""You are a property assistant. 
        The user asked: "{user_input}"
        
        Context: {context}
        
        Generate an appropriate response based on this context.
        """

    else:
        user_prompt = f"""You are a property assistant.
        The user asked: "{user_input}"
        
        Unfortunately, no exact matches were found.
        Provide a polite response explaining this and suggest possible adjustments
        in budget, location, or preferences.
        """

    response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You assist users in finding rental properties."},
        {"role": "user", "content": user_prompt}
    ],
    max_tokens=300
)


    return response.choices[0].message.content.strip()

