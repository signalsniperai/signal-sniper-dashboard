import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
from supabase import create_client, Client
from modular_scraper import run_all_scrapers

# === ENV SETUP ===
load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === INIT CLIENTS ===
alpaca = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === TELEGRAM FUNCTION ===
def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
        print("✅ Telegram alert sent!")
    except Exception as e:
        print(f"Telegram error: {e}")

# === MAIN LOOP ===
while True:
    try:
        signals = run_all_scrapers()
        for signal in signals:
            print("🟢 New signal:", signal)

            # Clean UTC timestamp
            signal["timestamp"] = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

            # Supabase log
            supabase.table("signals").insert(signal).execute()

            # Webhook push
            requests.post(N8N_WEBHOOK_URL, json=signal)

            # Telegram alert
            message = f"🚨 New Signal:\n{signal['ticker']} - {signal['strategy']}\n{signal.get('summary', '')}"
            send_telegram_message(message)

        time.sleep(60)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
