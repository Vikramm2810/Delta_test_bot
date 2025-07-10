import os
import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import hashlib
import hmac
import json

# Load keys from .env
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

SYMBOL = "BTCUSDT"
TIMEFRAME = "5m"
TRADE_SIZE = 0.001

def fetch_ohlcv():
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": SYMBOL,
        "interval": TIMEFRAME,
        "limit": 20
    }
    response = requests.get(url, params=params)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["time"] = pd.to_datetime(df["close_time"], unit='ms')
    df["close"] = df["close"].astype(float)

    return df[["time", "close"]]

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def generate_signal(df):
    df["ema_fast"] = df["close"].ewm(span=9).mean()
    df["ema_slow"] = df["close"].ewm(span=21).mean()
    df["rsi"] = compute_rsi(df["close"])

    last_ema_fast = df["ema_fast"].iloc[-1]
    last_ema_slow = df["ema_slow"].iloc[-1]
    last_rsi = df["rsi"].iloc[-1]

    if last_ema_fast > last_ema_slow and last_rsi < 60:
        return "BUY"
    elif last_ema_fast < last_ema_slow and last_rsi > 40:
        return "SELL"
    else:
        return None

def place_order(side):
    url = "https://demoapi.delta.exchange/v2/orders"  # Replit-compatible domain
    timestamp = str(int(time.time() * 1000))

    order = {
        "product_id": 2,
        "size": TRADE_SIZE,
        "side": side,
        "order_type": "market",
        "post_only": False,
        "client_order_id": f"testbot-{int(time.time())}"
    }

    body = json.dumps(order)
    message = timestamp + "POST" + "/v2/orders" + body
    signature = hmac.new(
        API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "api-key": API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=body)
    if response.status_code == 200:
        print(f"✅ Trade Executed: {side.upper()}")
    else:
        print(f"❌ Trade Error {response.status_code}: {response.text}")

def simulate_trade(signal):
    now = datetime.now().strftime("%H:%M:%S")
    if signal == "BUY":
        print(f"[{now}] 📈 Long Signal — Sending Order")
        place_order("buy")
    elif signal == "SELL":
        print(f"[{now}] 📉 Short Signal — Sending Order")
        place_order("sell")
    else:
        print(f"[{now}] ⏳ No Trade Signal")


def run_bot():
    print("🚀 Bot Started — Delta Testnet Live Trading Mode")
    last_signal = None
    while True:
        try:
            df = fetch_ohlcv()
            signal = generate_signal(df)
            if signal != last_signal and signal is not None:
                simulate_trade(signal)
                last_signal = signal
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔁 Holding")
        except Exception as e:
            print("❌ Error:", e)
        
        print("⏳ Still alive at", datetime.now().strftime('%H:%M:%S'))
        time.sleep(30)
