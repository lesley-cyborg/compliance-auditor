import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from db import get_connection, init_db

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def build_embed(devices_data):
    # devices_data is now a list of dictionaries directly from Postgres
    violations = "\n".join([f"• **{d['hostname']}** (`{d['device_id']}`) — {d['bitlocker_status']}" for d in devices_data])
    return {
        "embeds": [{
            "title": "🚨 Endpoint Compliance Failure",
            "description": violations,
            "color": 15158332,
            "footer": {"text": "Compliance Auditor Bot V2"}
        }]
    }

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(requests.exceptions.HTTPError), reraise=True)
def send_to_discord(payload):
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()

def process_outbox():
    init_db()
    if not DISCORD_WEBHOOK_URL: 
        return {"message": "Webhook not configured", "alerts_sent": 0, "failed_alerts": 0}

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch unprocessed outbox items
        cursor.execute("SELECT id, payload FROM outbox WHERE processed = FALSE")
        items = cursor.fetchall()
        
        if not items: 
            return {"message": "No pending alerts", "alerts_sent": 0, "failed_alerts": 0}

        # THE FIX: psycopg2 + JSONB already returns a Python dict. No json.loads() needed!
        devices_data = [item['payload'] for item in items]
        
        payload = build_embed(devices_data)
        send_to_discord(payload)

        # Mark as processed
        item_ids = [(item['id'],) for item in items]
        cursor.executemany("UPDATE outbox SET processed = TRUE WHERE id = %s", item_ids)
        conn.commit()
        
        return {"message": "Alerts sent successfully", "alerts_sent": len(items), "failed_alerts": 0}

    except RetryError:
        conn.rollback()
        return {"message": "Discord failed after retries. Items remain in outbox.", "alerts_sent": 0, "failed_alerts": len(items)}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()