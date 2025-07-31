import os
from dotenv import load_dotenv
import httpx

# === Load Environment Variables ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        with httpx.Client(transport=httpx.HTTPTransport(local_address="0.0.0.0")) as client:
            response = client.post(url, data=payload)
            response.raise_for_status()
            print("✅ Message sent successfully:", response.json())
    except Exception as e:
        print("❌ Telegram send failed:", e)

if __name__ == "__main__":
    test_message = "🚨 Signal Sniper Test: Telegram alerts are working! 🧠📡"
    send_telegram_message(test_message)
