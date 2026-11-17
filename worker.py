import time
import signal
import sys
from services.alert import process_outbox

# Flag to handle graceful shutdown (Ctrl+C)
running = True

def signal_handler(sig, frame):
    global running
    print("\n🛑 Shutting down worker gracefully...")
    running = False

# Register the signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    print("🚀 Starting Compliance Outbox Worker...")
    print("Press Ctrl+C to stop.")
    
    poll_interval = 30 # seconds
    
    while running:
        try:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Polling outbox...")
            result = process_outbox()
            
            if result["alerts_sent"] > 0:
                print(f"✅ Sent {result['alerts_sent']} alert(s).")
            elif result["failed_alerts"] > 0:
                print(f"⚠️  {result['failed_alerts']} alert(s) failed. Will retry next cycle.")
            else:
                print("ℹ️  No pending alerts.")
                
        except Exception as e:
            print(f"❌ Worker error: {e}")
            
        # Sleep in small increments to allow for responsive Ctrl+C
        for _ in range(poll_interval):
            if not running:
                break
            time.sleep(1)
            
    print("👋 Worker stopped.")

if __name__ == "__main__":
    main()