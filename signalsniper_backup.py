import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
from supabase import create_client, Client
from modular_scraper import run_all_scrapers  # 🎯 Pull in your enhanced scrapers

# === ENV SETUP ===
load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

# === SUPABASE SETUP ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === BOT CONFIG ===
test_mode = True
real_threshold = 75  # Trade only if score exceeds this (when not testing)
min_score_threshold = 50  # Minimum score to consider

# === INIT CLIENT ===
alpaca = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

# === ENHANCED SECTOR ANALYSIS ===
def analyze_sector_trends(df):
    """Analyze which sectors are showing strength"""
    if df.empty:
        return {}
    
    sector_analysis = df.groupby('sector').agg({
        'signal_score': ['mean', 'count', 'max'],
        'ticker': 'count'
    }).round(2)
    
    print("\n📈 Sector Analysis:")
    print(sector_analysis)
    
    return sector_analysis

# === EXECUTE TRADE WITH ENHANCED LOGIC ===
def execute_enhanced_trade(row):
    """Execute trade with sector-specific position sizing"""
    ticker = row['ticker']
    score = row['signal_score']
    sector = row['sector']
    signal_type = row['signal_type']
    
    # Dynamic position sizing based on signal strength and type
    if signal_type == 'fda_catalyst':
        base_qty = 50  # Smaller positions for binary biotech events
    elif signal_type == 'insider_trading':
        base_qty = 100  # Medium positions for insider activity
    elif signal_type == 'unusual_options':
        base_qty = 75  # Medium positions for options flow
    else:
        base_qty = 100
    
    # Scale quantity by score
    qty = int(base_qty * (score / 100))
    qty = max(1, min(qty, 200))  # Keep between 1-200 shares
    
    trade_data = {
        'ticker': ticker,
        'quantity': qty,
        'signal_score': score,
        'signal_type': signal_type,
        'sector': sector,
        'source': row['source'],
        'timestamp': datetime.utcnow().isoformat(),
        'action': 'BUY',
        'reasoning': f"Score: {score}, Type: {signal_type}, Sector: {sector}"
    }
    
    if test_mode:
        print(f"🧪 TEST MODE - Would buy {qty} shares of {ticker} (Score: {score})")
        log_to_supabase(trade_data)
        send_to_webhook(trade_data)
        return trade_data
    else:
        if score >= real_threshold:
            order = place_equity_order(ticker, qty)
            if order:
                trade_data['alpaca_order_id'] = order.id
                log_to_supabase(trade_data)
                send_to_webhook(trade_data)
                return trade_data
        else:
            print(f"⏸️ Signal {ticker} below threshold (Score: {score} < {real_threshold})")
    
    return None

# === EXECUTE EQUITY ORDER ===
def place_equity_order(symbol, qty=1):
    try:
        order = alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side='buy',
            type='market',
            time_in_force='gtc'
        )
        print(f"🟢 Alpaca Order Placed: {symbol} x{qty}")
        return order
    except Exception as e:
        print("🔴 Alpaca Order Failed:", e)
        return None

# === SEND TO N8N ===
def send_to_webhook(trade):
    if not N8N_WEBHOOK_URL:
        print("⚠️ No webhook URL configured")
        return
    
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=trade, timeout=10)
        print("📡 Webhook:", response.status_code)
    except Exception as e:
        print("🔴 Webhook Failed:", e)

# === LOG TO SUPABASE ===
def log_to_supabase(trade_data: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Supabase not configured")
        return
    
    try:
        data, count = supabase.table("signal_sniper_v2").insert(trade_data).execute()
        print("📊 Trade logged to Supabase")
    except Exception as e:
        print("🔴 Supabase Logging Error:", e)

# === MAIN EXECUTION LOOP ===
def run_signal_sniper():
    """Main execution function"""
    print("🎯 Signal Sniper v2.0 Starting...")
    print(f"🧪 Test Mode: {test_mode}")
    print(f"🎚️ Threshold: {real_threshold}")
    
    # Run all scrapers
    df = run_all_scrapers()
    
    if df.empty:
        print("❌ No signals found")
        return
    
    # Filter by minimum score
    df_filtered = df[df['signal_score'] >= min_score_threshold]
    print(f"🔍 Signals above threshold ({min_score_threshold}): {len(df_filtered)}")
    
    if df_filtered.empty:
        print("❌ No signals meet minimum threshold")
        return
    
    # Analyze sector trends
    analyze_sector_trends(df_filtered)
    
    # Display top signals
    print(f"\n🏆 Top 10 Signals:")
    top_signals = df_filtered.head(10)
    for idx, row in top_signals.iterrows():
        print(f"  {row['ticker']} | Score: {row['signal_score']} | {row['signal_type']} | {row['sector']}")
    
    # Execute trades for top signals
    executed_trades = []
    for idx, row in top_signals.head(5).iterrows():  # Execute top 5 only
        trade = execute_enhanced_trade(row)
        if trade:
            executed_trades.append(trade)
    
    print(f"\n✅ Executed {len(executed_trades)} trades")
    
    return executed_trades

# === CLI ENTRY POINT ===
if __name__ == "__main__":
    try:
        trades = run_signal_sniper()
        print("🎯 Signal Sniper execution complete")
    except KeyboardInterrupt:
        print("\n⏹️ Signal Sniper stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()