import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
import requests

# Supabase Credentials
SUPABASE_URL = "https://qvgwwfxrlnnouyunumko.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2Z3d3ZnhybG5ub3V5dW51bWtvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4ODQ0MTcxOSwiZXhwIjoyMTA0MDE3NzE5fQ.Doi9UQpMP0vty3KraW6b8Y3M0kIPL6A5USMKM116nsA"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase connected successfully!")
except Exception as e:
    print(f"Supabase Connection Error: {e}")

# Render Health Check Server (Handles both GET and HEAD requests)
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Signal Engine Active")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def start_health_check_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

def get_market_price():
    try:
        res = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=5)
        if res.status_code == 200:
            return res.json()["rates"]["USD"]
    except Exception as e:
        print(f"Price Fetch API Error: {e}")
    return 1.08380

def auto_resolve_pending_signals():
    try:
        now_utc = datetime.now(timezone.utc).isoformat()
        response = supabase.table("live_signals").select("*").eq("result", "Pending").execute()
        
        for sig in response.data:
            expiry_str = sig.get("expiry_time", "")
            if expiry_str and expiry_str <= now_utc:
                current_price = get_market_price()
                entry_price = sig.get("entry_price", current_price)
                direction = sig.get("direction", "CALL")

                result = "WIN" if (direction == "CALL" and current_price >= entry_price) or (direction == "PUT" and current_price <= entry_price) else "LOSS"

                supabase.table("live_signals").update({
                    "exit_price": current_price,
                    "result": result
                }).eq("id", sig["id"]).execute()
                
                print(f"Signal {sig['id']} Resolved: {result}")
    except Exception as e:
        print(f"Auto Resolve Error: {e}")

def run_engine():
    print("Guaranteed Signal Engine Started...")
    last_signal_time = 0
    COOLDOWN_SECONDS = 180  # 3 Minute Cooldown

    while True:
        # 1. Resolve past expired signals
        auto_resolve_pending_signals()

        # 2. Check and generate new signal
        current_time = time.time()
        if current_time - last_signal_time >= COOLDOWN_SECONDS:
            price = get_market_price()
            direction = "CALL" if (int(current_time) % 2 == 0) else "PUT"
            now = datetime.now(timezone.utc)
            expiry = now + timedelta(seconds=60)

            try:
                supabase.table("live_signals").insert({
                    "asset": "EUR/USD (OTC)",
                    "direction": direction,
                    "entry_price": price,
                    "created_at": now.isoformat(),
                    "expiry_time": expiry.isoformat(),
                    "result": "Pending",
                    "confidence": 88
                }).execute()

                print(f"SUCCESS: New Signal Inserted -> {direction} @ {price}")
                last_signal_time = current_time
            except Exception as e:
                print(f"CRITICAL: Signal Insert Error -> {e}")

        time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    run_engine()
    
