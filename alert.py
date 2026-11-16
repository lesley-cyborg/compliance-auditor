import json
import os
import requests
from datetime import datetime, timezone
from contextlib import closing
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

from db import get_connection, init_db

# Load environment variables
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
FAILED_ALERTS_PATH = "./data/failed_alerts.json"

# Ensure data directory exists
os.makedirs('./data', exist_ok=True)

def get_non_compliant_devices():
    """
    Queries non-compliant devices.
    NOTE: This query leverages the partial index idx_non_compliant for O(log N) performance.
    """
    # init_db() ensures the table exists even if this is run before ingest.py
    init_db() 
    
    # contextlib.closing guarantees the connection closes even if the query fails
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT device_id, hostname, bitlocker_status 
            FROM devices 
            WHERE is_compliant = 0
        """)
        return [dict(row) for row in cursor.fetchall()]

def build_discord_payload(devices):
    """Builds a rich Discord embed payload."""
    if not devices:
        return None

    violations = []
    for d in devices:
        violations.append(f"• **{d['hostname']}** (`{d['device_id']}`) — {d['bitlocker_status']}")

    payload = {
        "embeds": [{
            "title": "🚨 Endpoint Compliance Failure",
            "description": "\n".join(violations),
            "color": 15158332,  # Red
            "fields": [
                {"name": "Total Violations", "value": str(len(devices)), "inline": True},
                {"name": "Policy", "value": os.getenv("POLICY_MIN_BITLOCKER", "256-bit"), "inline": True},
                {"name": "Timestamp", "value": datetime.now(timezone.utc).isoformat(), "inline": False}
            ],
            "footer": {"text": "Compliance Auditor Bot"}
        }]
    }
    return payload

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.HTTPError),
    reraise=True
)
def send_to_discord(payload):
    """Sends payload to Discord webhook with automatic retry on HTTP errors."""
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    response.raise_for_status()
    return response

def save_to_dead_letter(payload):
    """Appends failed alert payload to failed_alerts.json for manual review."""
    failed_alerts = []
    if os.path.exists(FAILED_ALERTS_PATH):
        try:
            with open(FAILED_ALERTS_PATH, 'r') as f:
                failed_alerts = json.load(f)
        except json.JSONDecodeError:
            failed_alerts = []

    failed_alerts.append({
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload
    })

    with open(FAILED_ALERTS_PATH, 'w') as f:
        json.dump(failed_alerts, f, indent=2)

def alert():
    """Main alert function. Queries non-compliant devices and sends to Discord."""
    if not DISCORD_WEBHOOK_URL or "your-webhook-url-here" in DISCORD_WEBHOOK_URL:
        print("⚠️  DISCORD_WEBHOOK_URL not configured. Skipping alert.")
        return 0

    devices = get_non_compliant_devices()
    
    if not devices:
        print("✅ No compliance violations. No alerts to send.")
        return 0

    payload = build_discord_payload(devices)

    try:
        send_to_discord(payload)
        print(f"📤 Successfully sent alert for {len(devices)} violation(s) to Discord.")
        return len(devices)
    except RetryError:
        print(f"❌ Discord webhook failed after 3 attempts. Saving to {FAILED_ALERTS_PATH}")
        save_to_dead_letter(payload)
        return 0
    except requests.exceptions.RequestException as e:
        # Catch connection errors (e.g., DNS failure) that aren't HTTP errors
        print(f"❌ Network error: {e}")
        save_to_dead_letter(payload)
        return 0

if __name__ == "__main__":
    alert()