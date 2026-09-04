import os
import time
import json
import threading
import pandas as pd
import pandas_ta as ta
import websocket
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from supabase import create_client, Client

# Dummy HTTP Server (Render Port Binding Bypass)
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Live Market Analysis Engine Running")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# Supabase Client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

candle_data = []

def analyze_and_generate():
    global candle_data
    if len(candle_data) < 15:
        return  # Live candles accumulate hone ka wait karega

    df = pd.DataFrame(candle_data)
    
    # Technical Indicators Calculation
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema_fast'] = ta.ema(df['close'], length=5)
    df['ema_slow'] = ta.ema(df['close'], length=13)
    
    latest = df.iloc[-1]
    rsi_val = round(latest['rsi'], 1)
    close_price = round(latest['close'], 5)
    
    direction = None
    confidence = 0
    
    if rsi_val < 35 and latest['ema_fast'] > latest['ema_slow']:
        direction = "CALL"
        confidence = min(98, int(80 + (35 - rsi_val) * 1.2))
        ema_cross = "BULLISH"
        bb_state = "OVERSOLD"
    elif rsi_val > 65 and latest['ema_fast'] < latest['ema_slow']:
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
            print(f"[{datetime.now().strftime('%H:%M:%S')}] LIVE ANALYSIS SIGNAL: {direction} | RSI: {rsi_val} | Price: {close_price}")
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
    print("Real-Time Engine Started...")
    while True:
        analyze_and_generate()
        time.sleep(60)
               
