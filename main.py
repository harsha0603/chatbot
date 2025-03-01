from app.config.db_config import get_db_connection

conn = get_db_connection()
if conn:
    conn.close()
