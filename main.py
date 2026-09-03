import os
import time
import random
from datetime import datetime, timedelta
from supabase import create_client, Client

# Supabase Credentials (Render Environment Variables se aayenge)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase credentials missing in Environment Variables!")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ASSETS = ['EUR/USD (OTC)', 'GBP/USD (OTC)', 'USD/JPY (OTC)', 'AUD/USD (OTC)']

def generate_and_push_signal():
    asset = random.choice(ASSETS)
    direction = random.choice(['CALL', 'PUT'])
    confidence = random.randint(85, 98)
    entry_price = round(random.uniform(1.05000, 1.10000), 5)
    
    if direction == 'CALL':
        rsi = round(random.uniform(20.0, 32.0), 1)
        ema_cross = 'BULLISH'
        bb_state = 'OVERSOLD'
        pattern = 'Bullish Reversal'
    else:
        rsi = round(random.uniform(68.0, 80.0), 1)
        ema_cross = 'BEARISH'
        bb_state = 'OVERBOUGHT'
        pattern = 'Bearish Reversal'

    now = datetime.utcnow()
    expiry = now + timedelta(minutes=1)

    signal_payload = {
        "asset": asset,
        "direction": direction,
        "timeframe": "1 MIN",
        "confidence": confidence,
        "entry_price": entry_price,
        "status": "PENDING",
        "rsi": rsi,
        "ema_cross": ema_cross,
        "bb_state": bb_state,
        "pattern": pattern,
        "created_at": now.isoformat(),
        "entry_time": now.isoformat(),
        "expiry_time": expiry.isoformat()
    }

    try:
        data, count = supabase.table("live_signals").insert(signal_payload).execute()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Signal Pushed: {asset} - {direction} ({confidence}%)")
    except Exception as e:
        print(f"Error pushing signal: {e}")

if __name__ == "__main__":
    print("Starting Binary Options Strategy Bot Engine...")
    while True:
        generate_and_push_signal()
        # Har 1 minute (60 seconds) mein naya signal push hoga
        time.sleep(60)
      
