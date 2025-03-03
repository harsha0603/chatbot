from mysql.connector import Error, connect
from app.config.db_config import get_db_connection
import re

def validate_read_query(query: str) -> bool:
    """Ensures only safe SELECT queries are executed."""
    query = query.strip().lower()
    
    # Basic validation
    if not query.startswith("select"):
        print("❌ Query must start with SELECT")
        return False
        
    # Prevent any modifications
    dangerous_keywords = ["insert", "update", "delete", "drop", "truncate", "alter"]
    if any(keyword in query for keyword in dangerous_keywords):
        print("❌ Query contains dangerous keywords")
        return False
        
    # Update valid tables to match your actual schema
    valid_tables = {"properties", "rooms"}
    
    # Update table validation to handle JOINs
    table_matches = re.findall(r'from\s+(\w+)|join\s+(\w+)', query.lower())
    tables_in_query = {match[0] or match[1] for match in table_matches}
    
    if not all(table in valid_tables for table in tables_in_query):
        print(f"❌ Invalid tables in query. Valid tables are: {valid_tables}")
        print(f"Tables found in query: {tables_in_query}")
        return False
        
    return True

def execute_query(query: str):
    """Executes a safe read-only SQL query and returns results as a list of dictionaries."""
    print(f"🔍 Executing query: {query}")  # Debug log
    
    if not validate_read_query(query):
        print("❌ Query validation failed")  # Debug log
        return {"error": "Only safe SELECT queries are allowed."}

    connection = get_db_connection()
    if not connection:
        print("❌ Database connection failed")  # Debug log
        return {"error": "Database connection failed."}

    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        print(f"✅ Query executed successfully. Found {len(results)} results")  # Debug count
        
        if len(results) == 0:
            # Debug query to check data availability
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM rooms) as room_count,
                    (SELECT COUNT(*) FROM rooms WHERE status NOT IN ('i', 'I', 'inactive', 'INACTIVE')) as active_rooms,
                    (SELECT COUNT(*) FROM rooms WHERE rentmonth > 0) as priced_rooms,
                    (SELECT COUNT(*) FROM properties) as property_count
            """)
            counts = cursor.fetchone()
            print("📊 Database Statistics:")
            print(f"Total rooms: {counts['room_count']}")
            print(f"Active rooms: {counts['active_rooms']}")
            print(f"Rooms with prices: {counts['priced_rooms']}")
            print(f"Total properties: {counts['property_count']}")
            
        return results
    except Error as e:
        print(f"❌ Database error: {e}")  # Debug log
        return {"error": str(e)}
    finally:
        cursor.close()
        connection.close()

def check_database_content():
    """Debug function to check database content."""
    connection = get_db_connection()
    if not connection:
        return "❌ Database connection failed"

    cursor = connection.cursor(dictionary=True)
    debug_info = ["📊 Database Check Results:", "=" * 50]

    try:
        # Check rooms table
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status NOT IN ('i', 'I', 'inactive', 'INACTIVE') THEN 1 END) as active,
                COUNT(CASE WHEN rentmonth > 0 THEN 1 END) as with_price,
                COUNT(DISTINCT propertytype) as property_types,
                COUNT(DISTINCT roomtype) as room_types
            FROM rooms
        """)
        room_stats = cursor.fetchone()
        debug_info.extend([
            f"Rooms Statistics:",
            f"- Total rooms: {room_stats['total']}",
            f"- Active rooms: {room_stats['active']}",
            f"- Rooms with price: {room_stats['with_price']}",
            f"- Unique property types: {room_stats['property_types']}",
            f"- Unique room types: {room_stats['room_types']}\n"
        ])

        # Sample room data
        cursor.execute("""
            SELECT rentmonth, status, roomtype, propertytype, nearestbusstop 
            FROM rooms 
            WHERE status NOT IN ('i', 'I', 'inactive', 'INACTIVE')
            AND rentmonth > 0
            LIMIT 3
        """)
        sample_rooms = cursor.fetchall()
        debug_info.append("Sample Active Rooms:")
        debug_info.extend([str(room) for room in sample_rooms])
        debug_info.append("")

        # Check properties table
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT zone) as zones,
                COUNT(DISTINCT city) as cities
            FROM properties
        """)
        prop_stats = cursor.fetchone()
        debug_info.extend([
            f"Properties Statistics:",
            f"- Total properties: {prop_stats['total']}",
            f"- Unique zones: {prop_stats['zones']}",
            f"- Unique cities: {prop_stats['cities']}\n"
        ])

        # Sample property data
        cursor.execute("""
            SELECT propertyid, add1, city, zone 
            FROM properties 
            LIMIT 3
        """)
        sample_props = cursor.fetchall()
        debug_info.append("Sample Properties:")
        debug_info.extend([str(prop) for prop in sample_props])

        return "\n".join(debug_info)

    except Error as e:
        return f"❌ Error checking database: {e}"
    finally:
        cursor.close()
        connection.close()
