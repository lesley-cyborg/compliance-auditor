import csv
import sqlite3
import logging
import os
from db import get_connection, init_db

# --- Configuration & Logging Setup ---
# Ensure the data directory exists for the log file
os.makedirs('./data', exist_ok=True)

# Configure logging to write to audit.log
logging.basicConfig(
    filename='./data/audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Allowed values for the bitlocker_status column
VALID_STATUSES = {'256-bit', '128-bit', 'none'}
REQUIRED_COLUMNS = {'device_id', 'hostname', 'bitlocker_status', 'last_seen'}

def ingest_csv(file_path):
    """
    Reads a CSV file, validates the schema, and upserts records into SQLite.
    """
    init_db()

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        print(f"❌ Error: File not found at {file_path}")
        return

    processed_count = 0
    skipped_count = 0

    print(f"📥 Starting ingestion from {file_path}...")
    
    # Open with encoding='utf-8' to prevent crashes on weird enterprise exports
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        # Validate that the CSV has the expected headers
        if not REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            msg = f"CSV is missing required columns: {missing}"
            logging.error(msg)
            print(f"❌ {msg}")
            return

        conn = get_connection()
        cursor = conn.cursor()

        for row_num, row in enumerate(reader, start=2): # start=2 because row 1 is headers
            try:
                # 1. Basic Data Validation
                device_id = row.get('device_id', '').strip()
                if not device_id:
                    raise ValueError("Missing or empty 'device_id'")

                status = row.get('bitlocker_status', '').strip()
                if status not in VALID_STATUSES:
                    raise ValueError(f"Invalid bitlocker_status: '{status}'. Must be one of {VALID_STATUSES}")

                # 2. Database Upsert (Idempotency)
                # INSERT OR REPLACE will update the row if device_id (PK) already exists
                sql = """
                    INSERT OR REPLACE INTO devices 
                    (device_id, hostname, bitlocker_status, last_seen)
                    VALUES (?, ?, ?, ?)
                """
                cursor.execute(sql, (
                    device_id,
                    row.get('hostname', '').strip(),
                    status,
                    row.get('last_seen', '').strip()
                ))
                processed_count += 1

            except Exception as e:
                # 3. Graceful Failure: Log the error and the raw row, then continue
                skipped_count += 1
                error_msg = f"Row {row_num} failed: {str(e)} | Raw data: {dict(row)}"
                logging.error(error_msg)
                # Optional: print to console so you see it happening in real-time
                print(f"⚠️  {error_msg}")

        conn.commit()
        conn.close()

    print(f"✅ Ingestion complete. Processed: {processed_count} | Skipped: {skipped_count}")
    return processed_count, skipped_count

# Allow running this file directly for quick testing
if __name__ == "__main__":
    ingest_csv('mock_inventory.csv')