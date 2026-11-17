import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Returns a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "auditor"),
        password=os.getenv("DB_PASSWORD", "securepassword123"),
        dbname=os.getenv("DB_NAME", "compliance_db"),
        cursor_factory=RealDictCursor
    )

def init_db():
    """Initializes the database schema, indexes, and outbox table."""
    conn = get_connection()
    # Autocommit is required for DDL (CREATE TABLE) in psycopg2
    conn.autocommit = True 
    cursor = conn.cursor()
    
    # 1. Devices Table (Note: Postgres uses native BOOLEAN)
    schema_sql = """
    CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY,
        hostname TEXT NOT NULL,
        bitlocker_status TEXT CHECK(bitlocker_status IN ('256-bit', '128-bit', 'none')),
        last_seen TEXT NOT NULL,
        is_compliant BOOLEAN DEFAULT FALSE
    );
    """
    
    # 2. Partial Index (Postgres syntax)
    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_non_compliant 
    ON devices(device_id) 
    WHERE is_compliant = FALSE;
    """

    # 3. Outbox Table (For the Transactional Outbox Pattern)
    outbox_sql = """
    CREATE TABLE IF NOT EXISTS outbox (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        payload JSONB NOT NULL,
        processed BOOLEAN DEFAULT FALSE
    );
    """
    
    try:
        cursor.execute(schema_sql)
        cursor.execute(index_sql)
        cursor.execute(outbox_sql)
        print("✅ Database schema, indexes, and outbox initialized successfully.")
    except psycopg2.Error as e:
        print(f"❌ Database initialization error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()