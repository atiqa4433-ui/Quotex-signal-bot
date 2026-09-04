import os
import time
import json
import threading
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import websocket
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from supabase import create_client, Client

# Dummy HTTP Server (Render Port Scan Bypass)
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Live Market Strategy Engine Running")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

candle_data = []

def analyze_and_generate():
    global candle_data
    if len(candle_data) < 15:
        return

    df = pd.DataFrame(candle_data)
    
    # Clean Light Technical Indicators Calculation
    rsi_series = RSIIndicator(close=df['close'], window=14).rsi()
    ema_fast_series = EMAIndicator(close=df['close'], window=5).ema_indicator()
    ema_slow_series = EMAIndicator(close=df['close'], window=13).ema_indicator()
    
    rsi_val = round(rsi_series.iloc[-1], 1)
    close_price = round(df['close'].iloc[-1], 5)
    ema_fast = ema_fast_series.iloc[-1]
    ema_slow = ema_slow_series.iloc[-1]
    
    direction = None
    confidence = 0
    
    if rsi_val < 35 and ema_fast > ema_slow:
        direction = "CALL"
        confidence = min(98, int(80 + (35 - rsi_val) * 1.2))
        ema_cross = "BULLISH"
        bb_state = "OVERSOLD"
    elif rsi_val > 65 and ema_fast < ema_slow:
        direction = "PUT"
        confidence = min(98, int(80 + (rsi_val - 65) * 1.2))
        ema_cross = "BEARISH"
        bb_state = "OVERBOUGHT"

    if direction:
        now = datetime.utcnow()
        expiry = now + timedelta(minutes=1)
        
        payload = {
            "asset": "EUR/USD (OTC)",
            "direction": direction,
            "timeframe": "1 MIN",
            "confidence": confidence,
            "entry_price": close_price,
            "status": "PENDING",
            "rsi": rsi_val,
            "ema_cross": ema_cross,
            "bb_state": bb_state,
            "pattern": "Live Technical Reversal",
            "created_at": now.isoformat(),
            "entry_time": now.isoformat(),
            "expiry_time": expiry.isoformat()
        }
        
        try:
            supabase.table("live_signals").insert(payload).execute()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] LIVE SIGNAL: {direction} | RSI: {rsi_val} | Price: {close_price}")
        except Exception as e:
            print(f"Database Error: {e}")

def on_message(ws, message):
    global candle_data
    try:
        data = json.loads(message)
        if 'price' in data:
            candle_data.append({'close': float(data['price']), 'time': time.time()})
            if len(candle_data) > 100:
                candle_data.pop(0)
    except Exception:
        pass

def start_market_stream():
    ws_url = "wss://stream.binaryoptionsapi.com/quotes"
    ws = websocket.WebSocketApp(ws_url, on_message=on_message)
    ws.run_forever()

threading.Thread(target=start_market_stream, daemon=True).start()

if __name__ == "__main__":
    print("Real-Time OTC Market Engine Started...")
    while True:
        analyze_and_generate()
        time.sleep(60)
        
