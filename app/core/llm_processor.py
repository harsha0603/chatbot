from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
import json
from typing import Dict, List, Optional, Tuple
import re

from app.core.intent_classifier import classify_intent
from app.core.query_generator import generate_sql_query
from app.core.db_connector import execute_query
from app.core.similarity import find_similar_properties

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize LLM
llm = ChatOpenAI(model="gpt-4", temperature=0.2, openai_api_key=OPENAI_API_KEY)

# Define prompts for different purposes
follow_up_classifier_prompt = PromptTemplate(
    input_variables=["user_query", "property_context"],
    template="""
You are a real estate assistant analyzing if a user's question is a follow-up about a specific property.

Current Property Context:
{property_context}

User Query: {user_query}

Determine:
1. Is this a follow-up question about the current property? (true/false)
2. What aspect of the property is being asked about? (e.g., amenities, location, price, rules, etc.)
3. Can this question be answered with the available property data? (true/false)

Return a JSON object with these fields:
{
    "is_follow_up": boolean,
    "aspect": string,
    "can_answer": boolean
}

Return only the JSON object, no explanations.
"""
)

follow_up_response_prompt = PromptTemplate(
    input_variables=["user_query", "property_data", "aspect"],
    template="""
You are a helpful real estate assistant answering questions about a specific property. You must ONLY use the information provided in the property data and NEVER make assumptions or provide information that isn't explicitly available.

Property Details:
{property_data}

User's Question: {user_query}
Question relates to: {aspect}

Rules for generating response:
1. ONLY use information that is explicitly provided in the Property Details
2. If specific information isn't available, acknowledge this fact
3. DO NOT make assumptions or provide information not present in the data
4. Keep responses factual and based solely on the provided data
5. If asked about something not in the data, suggest asking about available information instead

Generate a natural response following these rules strictly.
"""
)

general_response_prompt = PromptTemplate(
    input_variables=["user_query", "chat_context"],
    template="""
You are a friendly and helpful real estate assistant. Respond naturally and conversationally.
Previous context: {chat_context}
User Query: {user_query}

Respond in a friendly, conversational manner while staying professional. Include follow-up questions when appropriate.
"""
)

extract_info_prompt = PromptTemplate(
    input_variables=["user_query"],
    template="""
Extract property search requirements from the user's query. Return a JSON object with the following fields:
- budget: (number or null)
- location: (string or null)
- property_type: (string or null)
- bedrooms: (number or null)
- furnished: (boolean or null)

User Query: {user_query}

Return only the JSON object, no explanations.
"""
)

# Add a new prompt for booking requests
booking_prompt = PromptTemplate(
    input_variables=["property_details"],
    template="""
You are helping a user book a property viewing. The user is interested in:
{property_details}

Respond naturally and ask for necessary booking details like:
- Preferred viewing date and time
- Contact number (if not already provided)
- Any specific requirements for the viewing

Keep the tone friendly and professional.
"""
)

class PropertyChatbot:
    def __init__(self):
        self.conversation_context = {}

    def _initialize_user_context(self, user_id: str):
        """Initialize or reset user context with all necessary fields."""
        self.conversation_context[user_id] = {
            'requirements': {},
            'last_query': None,
            'last_properties_shown': None,
            'current_property': None,
            'chat_history': [],
            'booking_state': None
        }

    def _update_chat_history(self, user_id: str, message: str, is_user: bool = True):
        """Maintain chat history for context."""
        if user_id not in self.conversation_context:
            self._initialize_user_context(user_id)
        
        self.conversation_context[user_id]['chat_history'].append({
            'role': 'user' if is_user else 'assistant',
            'message': message
        })

    def _extract_property_info(self, user_query: str) -> Dict:
        """Extract property requirements from user query."""
        try:
            response = llm.predict(extract_info_prompt.format(user_query=user_query))
            return json.loads(response)
        except Exception as e:
            print(f"Error extracting property info: {e}")
            return {}

    def _validate_requirements(self, requirements: Dict) -> Tuple[bool, List[str]]:
        """Check if all necessary requirements are present."""
        missing_fields = []
        required_fields = ['budget', 'location']
        
        for field in required_fields:
            if not requirements.get(field):
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields

    def _generate_missing_info_prompt(self, missing_fields: List[str]) -> str:
        """Generate a prompt to ask for missing information."""
        field_prompts = {
            'budget': "What's your budget for the property?",
            'location': "Which area or location are you interested in?",
            'property_type': "What type of property are you looking for (apartment, house, etc.)?",
            'bedrooms': "How many bedrooms do you need?",
            'furnished': "Do you prefer furnished or unfurnished properties?"
        }
        
        return field_prompts.get(missing_fields[0], "Could you provide more details about your requirements?")

    def _format_property_response(self, properties: List[Dict]) -> str:
        """Format property listings in a more natural way."""
        if not properties or isinstance(properties, dict) and 'error' in properties:
            return "I couldn't find any properties matching your criteria. Would you like to try with different requirements?"
        
        response = "I found some properties that might interest you:\n\n"
        for idx, prop in enumerate(properties[:3], 1):
            response += f"{idx}. "
            details = []
            
            # Property type and room type
            room_info = []
            if prop.get('roomtype'):
                room_info.append(prop['roomtype'])
            if prop.get('propertytype'):
                room_info.append(f"in a {prop['propertytype']}")
            if room_info:
                details.append(" ".join(room_info))
            
            # Location
            location_parts = []
            if prop.get('add1'):
                location_parts.append(prop['add1'])
            if prop.get('zone'):
                location_parts.append(f"({prop['zone']} Zone)")
            if location_parts:
                details.append("Located at " + ", ".join(location_parts))
            
            # Rent (using S$ for Singapore Dollar)
            if prop.get('rentmonth') and float(prop['rentmonth']) > 0:
                details.append(f"Rent: S${float(prop['rentmonth']):,.2f}/month")
            
            response += "\n".join(details) + "\n\n"
        
        response += "Would you like to know more about any of these properties or schedule a viewing?"
        return response

    def _format_detailed_property_response(self, property_data: Dict) -> str:
        """Format detailed information for a single property."""
        details = ["📍 Detailed Property Information:\n"]
        
        # Room Information
        if property_data.get('roomtype'):
            details.append(f"🏠 Room Type: {property_data['roomtype']}")
        if property_data.get('propertytype'):
            details.append(f"🏢 Property Type: {property_data['propertytype']}")
        
        # Location Details
        location_parts = []
        if property_data.get('add1'):
            location_parts.append(property_data['add1'])
        if property_data.get('zone'):
            location_parts.append(f"{property_data['zone']} Zone")
        if location_parts:
            details.append(f"📌 Address: {', '.join(location_parts)}")
        
        # Rental Information
        if property_data.get('rentmonth'):
            details.append(f"💰 Rent: S${float(property_data['rentmonth']):,.2f}/month")
        
        # Amenities
        amenities = []
        if property_data.get('airconditioned') == 'Y':
            amenities.append("Air Conditioning")
        if property_data.get('wifi') == 'Y':
            amenities.append("WiFi")
        if property_data.get('tv') == 'Y':
            amenities.append("TV")
        if property_data.get('fridge') == 'Y':
            amenities.append("Refrigerator")
        if property_data.get('washer') == 'Y':
            amenities.append("Washing Machine")
        if property_data.get('gym') == 'Y':
            amenities.append("Gym Access")
        if property_data.get('swimming') == 'Y':
            amenities.append("Swimming Pool Access")
        
        if amenities:
            details.append(f"✨ Amenities: {', '.join(amenities)}")
        
        # Additional Information
        if property_data.get('nearestmrt'):
            details.append(f"🚇 Nearest MRT: {property_data['nearestmrt']}")
        if property_data.get('nearestbusstop'):
            details.append(f"🚌 Nearest Bus Stop: {property_data['nearestbusstop']}")
        
        details.append("\nWould you like to schedule a viewing of this property?")
        return "\n".join(details)

    def _handle_booking_request(self, user_id: str, user_query: str) -> str:
        """Handle property booking requests."""
        context = self.conversation_context[user_id]
        
        if not context.get('last_properties_shown'):
            return "I don't see any specific property being discussed. Could you tell me which property you're interested in booking?"
        
        if not context.get('booking_state'):
            context['booking_state'] = 'initial'
            return "I'll help you schedule a viewing. What would be your preferred date and time to view the property?"
        
        # Handle different booking states
        if 'date' in user_query.lower() or 'time' in user_query.lower():
            context['booking_state'] = 'contact'
            return "Great! Could you please provide your contact number so we can confirm the viewing?"
        
        if context['booking_state'] == 'contact':
            context['booking_state'] = 'confirmed'
            return "Perfect! I've scheduled your viewing. Our agent will contact you shortly to confirm the details. Is there anything else you'd like to know?"

    def _handle_follow_up_question(self, user_query: str, current_property: Dict) -> str:
        """Handle follow-up questions about a specific property using LLM."""
        try:
            # Format property context for the classifier
            property_context = json.dumps(current_property, indent=2)
            
            # Classify the follow-up question
            classifier_response = llm.predict(
                follow_up_classifier_prompt.format(
                    user_query=user_query,
                    property_context=property_context
                )
            )
            
            classification = json.loads(classifier_response)
            
            if not classification['is_follow_up']:
                return None

            # Map common aspects to their corresponding database fields
            aspect_to_fields = {
                'amenities': ['wifi', 'airconditioned', 'tv', 'fridge', 'washer', 'gym', 'swimming'],
                'location': ['add1', 'add2', 'city', 'zone', 'nearestmrt', 'nearestbusstop'],
                'price': ['rentmonth'],
                'property_details': ['roomtype', 'propertytype'],
                'transportation': ['nearestmrt', 'nearestbusstop']
            }

            # Get relevant fields for the asked aspect
            relevant_fields = aspect_to_fields.get(classification['aspect'].lower(), [])
            
            # Check if we have the necessary data
            has_data = any(current_property.get(field) for field in relevant_fields)
            if not has_data:
                return f"I apologize, but I don't have information about {classification['aspect']} for this property. Would you like to know about other aspects such as amenities, location, or price?"

            # Create a focused property context with only relevant fields
            focused_data = {
                field: current_property.get(field)
                for field in relevant_fields
                if current_property.get(field) is not None
            }

            # Add basic property identification
            focused_data.update({
                'address': current_property.get('add1', 'the property'),
                'propertytype': current_property.get('propertytype', 'property'),
                'rentmonth': current_property.get('rentmonth')
            })

            # Generate response using only the available database information
            response = llm.predict(
                follow_up_response_prompt.format(
                    user_query=user_query,
                    property_data=json.dumps(focused_data, indent=2),
                    aspect=classification['aspect']
                )
            )
            
            return response.strip()
            
        except Exception as e:
            print(f"Error handling follow-up question: {e}")
            return None

    def process_message(self, user_id: str, user_query: str) -> str:
        """Enhanced message processing with LLM-based follow-up handling."""
        if user_id not in self.conversation_context:
            self._initialize_user_context(user_id)
        
        self._update_chat_history(user_id, user_query)
        
        # Check for booking-related queries
        if any(word in user_query.lower() for word in ['book', 'schedule', 'viewing', 'visit']):
            response = self._handle_booking_request(user_id, user_query)
            self._update_chat_history(user_id, response, is_user=False)
            return response

        # Handle queries about previously shown properties
        current_property = self.conversation_context[user_id].get('current_property')
        last_properties = self.conversation_context[user_id].get('last_properties_shown', [])

        if current_property:
            # Try to handle as a follow-up question about the current property
            follow_up_response = self._handle_follow_up_question(user_query, current_property)
            if follow_up_response:
                self._update_chat_history(user_id, follow_up_response, is_user=False)
                return follow_up_response

        if last_properties:
            # Check if user is asking about a specific property from the list
            property_indicators = [
                (r'(?:show|tell|give|share).*(?:details|information|more).*(?:about)?.*(?:first|1st|second|2nd|third|3rd|last).*property', 1),
                (r'(?:first|1st).*property', 0),
                (r'(?:second|2nd).*property', 1),
                (r'(?:third|3rd|last).*property', 2),
                (r'property.*(?:number|#)\s*(\d)', lambda m: int(m.group(1)) - 1),
                (r'most expensive', -1)
            ]
            
            for pattern, index_or_func in property_indicators:
                if re.search(pattern, user_query.lower()):
                    if callable(index_or_func):
                        match = re.search(pattern, user_query.lower())
                        index = index_or_func(match)
                    elif index_or_func == -1:
                        index = max(range(len(last_properties)), 
                                  key=lambda i: float(last_properties[i].get('rentmonth', 0)))
                    else:
                        index = index_or_func
                    
                    if 0 <= index < len(last_properties):
                        self.conversation_context[user_id]['current_property'] = last_properties[index]
                        return self._format_detailed_property_response(last_properties[index])

        # Regular intent classification and processing
        intent = classify_intent(user_query)
        
        if intent == "General Query":
            chat_context = "\n".join([f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['message']}" 
                                    for msg in self.conversation_context[user_id]['chat_history'][-3:]])
            
            response = llm.predict(general_response_prompt.format(
                user_query=user_query,
                chat_context=chat_context
            )).strip()
            
            self._update_chat_history(user_id, response, is_user=False)
            return response

        # Handle property search
        new_info = self._extract_property_info(user_query)
        self.conversation_context[user_id]['requirements'].update(
            {k: v for k, v in new_info.items() if v is not None}
        )
        
        requirements = self.conversation_context[user_id]['requirements']
        is_complete, missing_fields = self._validate_requirements(requirements)
        
        if not is_complete:
            response = self._generate_missing_info_prompt(missing_fields)
            self._update_chat_history(user_id, response, is_user=False)
            return response

        # Generate and execute query
        sql_query = generate_sql_query(user_query, requirements)
        if sql_query:
            print(f"Executing query: {sql_query}")  # Debug log
            results = execute_query(sql_query)
            print(f"Query results: {results}")  # Debug log
            
            if not results or (isinstance(results, list) and len(results) == 0):
                print("No exact matches, trying similarity search")  # Debug log
                results = find_similar_properties(sql_query, user_query)
            
            self.conversation_context[user_id]['last_properties_shown'] = results
            response = self._format_property_response(results)
        else:
            response = "I'm having trouble understanding your requirements. Could you please be more specific about what you're looking for?"

        self._update_chat_history(user_id, response, is_user=False)
        return response

    def reset_context(self, user_id: str):
        """Reset the conversation context for a user."""
        self.conversation_context[user_id] = {
            'requirements': {},
            'last_query': None,
            'last_properties_shown': None,
            'current_property': None,
            'chat_history': [],
            'booking_state': None
        }
