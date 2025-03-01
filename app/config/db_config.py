import mysql.connector
import os
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Parse DB credentials from DATABASE_URL
DB_URL = os.getenv("DATABASE_URL")  # Example: mysql://user:password@localhost/dbname
parsed_db_url = urllib.parse.urlparse(DB_URL)
DB_NAME = parsed_db_url.path[1:]

db_config = {
    "host": parsed_db_url.hostname,
    "user": parsed_db_url.username,
    "password": urllib.parse.unquote(parsed_db_url.password),
    "database": DB_NAME
}

def get_db_connection():
    """Establishes a database connection and returns the connection object."""
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as err:
        print(f"❌ Database connection failed: {err}")
        return None

def get_db_schema():
    """Fetches the table structure dynamically from the database."""
    connection = get_db_connection()
    if not connection:
        return None  # Return None if connection fails

    cursor = connection.cursor()
    schema_info = {}

    try:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = [column[0] for column in cursor.fetchall()]
            schema_info[table_name] = columns

        for table, columns in schema_info.items():
            print(f"📌 {table}: {', '.join(columns)}")

    except mysql.connector.Error as e:
        print(f"❌ Error fetching schema: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

    return schema_info  # Return schema as a dictionary


# 🔹 TEST: Fetch Schema and Print
schema = get_db_schema()

import json

def format_schema_for_llm(schema):
    """
    Converts the schema dictionary into a structured text format for LLM.
    """
    if not schema:
        return "No schema available."

    formatted_schema = []
    for table, columns in schema.items():
        formatted_schema.append(f"Table: {table}\nColumns: {', '.join(columns)}")

    return "\n\n".join(formatted_schema)

# 🔹 TEST: Convert Schema into LLM-friendly Format
schema = get_db_schema()
formatted_schema_text = format_schema_for_llm(schema)


