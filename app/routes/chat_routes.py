from fastapi import FastAPI, HTTPException, Request
from app.core.twilio_handler import send_whatsapp_message
from app.core.llm_processor import PropertyChatbot
import logging
import uvicorn

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize the chatbot
chatbot = PropertyChatbot()

@app.post("/webhook/")
async def whatsapp_webhook(request: Request):
    try:
        form_data = await request.form()
        user_input = form_data.get("Body")
        user_number = form_data.get("From")
        
        if not user_input or not user_number:
            logger.error("Invalid request: Missing user input or phone number")
            raise HTTPException(status_code=400, detail="Invalid request data")
        
        logger.info(f"Received message from {user_number}: {user_input}")
        
        # Process the message using PropertyChatbot
        response_message = chatbot.process_message(user_number, user_input)
        
        logger.info(f"Generated response: {response_message}")
        
        message_sid = send_whatsapp_message(user_number, response_message)
        
        return {"message": "Response sent successfully", "message_sid": message_sid}
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

