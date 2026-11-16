import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fallback to a default path if .env is missing the variable
DB_PATH = os.getenv("DB_PATH", "./data/compliance.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    # Ensure the 'data/' directory exists so SQLite doesn't crash
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    # Allows us to access columns by name later (e.g., row['device_id'])
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Initializes the database schema and indexes."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # The SQL you provided, formatted as Python strings
    schema_sql = """
    CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY,
        hostname TEXT NOT NULL,
        bitlocker_status TEXT CHECK(bitlocker_status IN ('256-bit', '128-bit', 'none')),
        last_seen TEXT NOT NULL,
        is_compliant INTEGER DEFAULT 0
    );
    """
    
    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_non_compliant 
    ON devices(device_id) 
    WHERE is_compliant = 0;
    """
    
    try:
        cursor.execute(schema_sql)
        cursor.execute(index_sql)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        raise
    finally:
        conn.close()

# Allows you to run `python db.py` to test it independently
if __name__ == "__main__":
    init_db()
    print(f"✅ Database successfully initialized at {DB_PATH}")