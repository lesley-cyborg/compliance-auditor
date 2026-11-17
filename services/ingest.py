import csv
import logging
import os
from db import get_connection, init_db

os.makedirs('./data', exist_ok=True)
logging.basicConfig(filename='./data/audit.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VALID_STATUSES = {'256-bit', '128-bit', 'none'}
REQUIRED_COLUMNS = {'device_id', 'hostname', 'bitlocker_status', 'last_seen'}

def ingest_csv(file_path: str):
    init_db()
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return {"message": "File not found", "processed_count": 0, "skipped_count": 0}

    processed_count = 0
    skipped_count = 0

    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        if not REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
            return {"message": "Invalid CSV headers", "processed_count": 0, "skipped_count": 0}

        conn = get_connection()
        cursor = conn.cursor()

        for row_num, row in enumerate(reader, start=2):
            try:
                device_id = row.get('device_id', '').strip()
                if not device_id: raise ValueError("Missing device_id")
                status = row.get('bitlocker_status', '').strip()
                if status not in VALID_STATUSES: raise ValueError(f"Invalid status: {status}")

                sql = """
                    INSERT INTO devices (device_id, hostname, bitlocker_status, last_seen)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (device_id) DO UPDATE SET
                        hostname = EXCLUDED.hostname,
                        bitlocker_status = EXCLUDED.bitlocker_status,
                        last_seen = EXCLUDED.last_seen;
                """
                cursor.execute(sql, (device_id, row.get('hostname', '').strip(), status, row.get('last_seen', '').strip()))
                processed_count += 1
            except Exception as e:
                skipped_count += 1
                logging.error(f"Row {row_num} failed: {e} | Raw: {dict(row)}")

        conn.commit()
        cursor.close()
        conn.close()

    return {"message": "Ingestion complete", "processed_count": processed_count, "skipped_count": skipped_count}