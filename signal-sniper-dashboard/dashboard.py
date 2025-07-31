import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Signal Sniper Dashboard", layout="wide")

st.title("📡 Signal Sniper - Live Feed")

# Example dummy data — we’ll later connect this to Supabase or your scraper
sample_signals = [
    {"ticker": "CELH", "confidence": 0.81, "strategy": "Volume Spike", "timestamp": "2025-07-31T15:22:00Z"},
    {"ticker": "FUBO", "confidence": 0.76, "strategy": "Options Sweep", "timestamp": "2025-07-31T15:21:00Z"},
]

df = pd.DataFrame(sample_signals)
df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize("UTC").dt.tz_convert("US/Eastern")

st.dataframe(df.sort_values("confidence", ascending=False), use_container_width=True)

st.markdown("✅ This dashboard will soon show real-time trades and signals from your AI system.")
