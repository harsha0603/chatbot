import os

# Define the project structure
PROJECT_STRUCTURE = {
    "real_estate_chatbot": [
        "app/core",
        "app/routes",
        "app/models",
        "app/utils",
        "tests"
    ]
}

# Define the files to be created
FILES = {
    "app/core/intent_classifier.py": "# Handles user intent classification",
    "app/core/llm_processor.py": "# Processes GPT-based SQL and NL responses",
    "app/core/db_connector.py": "# Manages MySQL connections & query execution",
    "app/core/followup_manager.py": "# Handles follow-up questions for missing info",
    "app/core/twilio_handler.py": "# Manages Twilio interactions for WhatsApp",

    "app/routes/chat_routes.py": "# FastAPI routes for chatbot interaction",
    "app/models/db_models.py": "# Defines SQLAlchemy models for structured DB handling",
    "app/utils/config.py": "# Loads environment variables and API keys",
    "app/main.py": "# Entry point for FastAPI",

    "tests/test_core.py": "# Unit tests for core logic",
    ".env": "# Store API keys, DB credentials, etc.",
    "requirements.txt": "fastapi\nlangchain\nopenai\nmysql-connector-python\nsqlalchemy\ntwilio\ndotenv",
    "README.md": "# Real Estate Chatbot - Project Overview"
}

def create_structure():
    """Creates the directory structure and files for the project."""
    for base, folders in PROJECT_STRUCTURE.items():
        for folder in folders:
            os.makedirs(folder, exist_ok=True)

    for filepath, content in FILES.items():
        with open(filepath, "w") as f:
            f.write(content)

    print("\n✅ Project structure created successfully!")

if __name__ == "__main__":
    create_structure()
