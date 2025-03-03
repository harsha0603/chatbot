from twilio.rest import Client
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

def send_whatsapp_message(to_number: str, body: str, media_url: str = None) -> str:
    """
    Sends a WhatsApp message via Twilio API.
    
    Args:
        to_number (str): Recipient's WhatsApp number (e.g., "whatsapp:+1234567890").
        body (str): The text message.
        media_url (str, optional): URL of an image/video to send.

    Returns:
        str: Message SID if sent successfully, or error message if failed.
    """
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

        client = Client(account_sid, auth_token)

        message_data = {
            "from_": twilio_whatsapp_number,
            "body": body,
            "to": to_number
        }

        if media_url:
            message_data["media_url"] = [media_url]

        message = client.messages.create(**message_data)
        
        logging.info(f"✅ Message sent successfully! SID: {message.sid}")
        return message.sid

    except Exception as e:
        logging.error(f"❌ Failed to send WhatsApp message: {e}")
        return f"Error: {str(e)}"
