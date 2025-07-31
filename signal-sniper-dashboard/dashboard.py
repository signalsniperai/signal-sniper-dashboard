import pandas as pd
import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Signal Sniper - Live Feed", layout="wide")

st.title("🧠 Signal Sniper - Live Feed")

# Replace this URL with your actual endpoint
API_URL = "https://your-n8n-webhook/render-feed"

try:
    response = requests.get(API_URL)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Fix: if already tz-aware, just convert to Eastern; otherwise localize to UTC then convert
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC").dt.tz_convert("US/Eastern")
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert("US/Eastern")

        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %I:%M:%S %p")

    st.dataframe(df[::-1], use_container_width=True)

except Exception as e:
    st.error(f"Error fetching or processing data: {e}")
