import mysql.connector
from mysql.connector import Error
from app.config.db_config import get_db_connection

def validate_read_query(query: str) -> bool:
    """Ensures only SELECT queries are executed."""
    query = query.strip().lower()
    return query.startswith("select")

def execute_query(query: str):
    """Executes a safe read-only SQL query and returns results as a list of dictionaries."""
    if not validate_read_query(query):
        return {"error": "Only SELECT queries are allowed."}

    connection = get_db_connection()
    if not connection:
        return {"error": "Database connection failed."}

    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        connection.close()
