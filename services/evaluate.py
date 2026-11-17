import os
import json
from db import get_connection, init_db

BITLOCKER_RANK = {"none": 0, "128-bit": 1, "256-bit": 2}

def evaluate_devices():
    required_status = os.getenv("POLICY_MIN_BITLOCKER", "256-bit").strip()
    required_rank = BITLOCKER_RANK.get(required_status, 2)
    
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Fetch all devices
        cursor.execute("SELECT device_id, hostname, bitlocker_status FROM devices")
        devices = cursor.fetchall()

        updates = []
        outbox_payloads = []
        compliant_count = 0

        for d in devices:
            current_rank = BITLOCKER_RANK.get(d['bitlocker_status'], -1)
            is_compliant = current_rank >= required_rank
            
            if is_compliant: compliant_count += 1
            updates.append((is_compliant, d['device_id']))

            # TRANSACTIONAL OUTBOX: If non-compliant, queue it for alerting
            if not is_compliant:
                payload = json.dumps({
                    "device_id": d['device_id'],
                    "hostname": d['hostname'],
                    "bitlocker_status": d['bitlocker_status']
                })
                outbox_payloads.append((payload,))

        # 2. Execute Updates and Outbox Inserts in ONE transaction
        for u in updates:
            cursor.execute("UPDATE devices SET is_compliant = %s WHERE device_id = %s", u)
        
        for p in outbox_payloads:
            cursor.execute("INSERT INTO outbox (payload) VALUES (%s)", p)

        conn.commit()
        
        return {
            "message": "Evaluation complete",
            "total_devices": len(devices),
            "compliant_count": compliant_count,
            "non_compliant_count": len(devices) - compliant_count,
            "queued_for_alert": len(outbox_payloads)
        }
    except Exception as e:
        conn.rollback() # Rollback both updates and outbox if anything fails
        raise e
    finally:
        cursor.close()
        conn.close()