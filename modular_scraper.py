
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import re
import yfinance as yf
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

def safe_get(url, headers=None, timeout=15):
    try:
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://google.com"
        }
        headers = headers or default_headers
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        import time
        time.sleep(0.5)
        return response.content
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout fetching {url}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Request error for {url}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error fetching {url}: {e}")
    return None

def validate_ticker(ticker: str) -> bool:
    if not ticker or len(ticker) > 5 or not ticker.isupper() or not ticker.isalpha():
        return False
    false_positives = {
        'AI', 'CEO', 'IPO', 'USA', 'SEC', 'FDA', 'LLC', 'INC', 'NYSE', 'NASDAQ',
        'ETF', 'API', 'URL', 'HTTP', 'HTML', 'JSON', 'XML', 'PDF', 'WSB', 'DD',
        'YOLO', 'FD', 'PUT', 'CALL', 'BUY', 'SELL', 'HOLD', 'NEW', 'OLD'
    }
    return ticker not in false_positives

def verify_ticker_exists(ticker: str) -> Optional[dict]:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if info and 'symbol' in info and info.get('regularMarketPrice'):
            return {
                'symbol': info.get('symbol'),
                'name': info.get('longName', info.get('shortName', '')),
                'sector': info.get('sector', ''),
                'price': info.get('regularMarketPrice'),
                'market_cap': info.get('marketCap'),
                'volume': info.get('regularMarketVolume')
            }
    except:
        pass
    return None

def scrape_highshortinterest():
    url = "https://highshortinterest.com/"
    html = safe_get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")[1:] if table else []
    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            ticker = cols[1].text.strip().upper()
            if validate_ticker(ticker):
                data.append({
                    "source": "HighShortInterest",
                    "ticker": ticker,
                    "short_float": cols[3].text.strip(),
                    "signal_type": "short_squeeze",
                    "sector": "squeeze_candidate"
                })
    return data

def scrape_reddit_wsb():
    url = "https://www.reddit.com/r/wallstreetbets/hot.json"
    try:
        response = requests.get(url, headers={"User-Agent": "SignalSniper/1.0"})
        if response.status_code == 200:
            data_json = response.json()
            posts = data_json.get('data', {}).get('children', [])
            data = []
            for post in posts[:20]:
                text = post.get('data', {}).get('title', '') + " " + post.get('data', {}).get('selftext', '')
                tickers = re.findall(r'\$([A-Z]{1,5})', text) or re.findall(r'([A-Z]{2,5})', text)
                for ticker in tickers:
                    if validate_ticker(ticker):
                        data.append({
                            "source": "Reddit WSB",
                            "ticker": ticker,
                            "description": text[:150],
                            "signal_type": "social_sentiment",
                            "sector": "reddit_hype"
                        })
                        break
            return data
    except:
        pass
    return []

def calculate_enhanced_score(row):
    score = 0
    source = row.get('source', '').lower()
    signal_type = row.get('signal_type', '').lower()
    sector = row.get('sector', '').lower()
    description = str(row.get('description', '')).lower()
    if 'sec' in source or 'quiver' in source:
        score += 30
    elif 'unusual' in source or 'biotech' in source:
        score += 25
    elif 'reddit' in source:
        score += 15
    if signal_type == 'insider_trading':
        score += 25
    elif signal_type == 'unusual_options':
        score += 20
    elif signal_type == 'fda_catalyst':
        score += 30
    elif signal_type == 'short_squeeze':
        score += 25
    elif signal_type == 'ai_catalyst':
        score += 20
    elif signal_type == 'energy_catalyst':
        score += 20
    elif signal_type == 'social_sentiment':
        score += 20
    if sector in ['biotech', 'technology', 'energy']:
        score += 15
    for keyword in ['breakthrough', 'approval', 'partnership', 'acquisition', 'patent']:
        if keyword in description:
            score += 10
    return min(score, 100)

def filter_valid_tickers(df):
    if df.empty:
        return df
    top = df.head(20)
    valid = set()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(verify_ticker_exists, ticker): ticker
            for ticker in top['ticker'].unique()
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                if future.result():
                    valid.add(ticker)
            except:
                pass
    print(f"🔍 Validated {len(valid)} tickers.")
    return df[df['ticker'].isin(valid)].copy()

def run_all_scrapers():
    all_data = []
    scrapers = [scrape_highshortinterest, scrape_reddit_wsb]
    for scraper in scrapers:
        try:
            print(f"🔍 Running {scraper.__name__}...")
            data = scraper()
            all_data.extend(data)
            print(f"✅ {scraper.__name__}: {len(data)} signals")
        except Exception as e:
            print(f"❌ {scraper.__name__} failed: {e}")
    if not all_data:
        print("⚠️ No data collected from any scraper")
        return pd.DataFrame()
    df = pd.DataFrame(all_data)
    df["scraped_at"] = datetime.now().isoformat()
    df['signal_score'] = df.apply(calculate_enhanced_score, axis=1)
    df = df.sort_values('signal_score', ascending=False)
    df = df.drop_duplicates(subset=['ticker'], keep='first')
    df = filter_valid_tickers(df)
    print(f"🎯 Total unique signals: {len(df)}")
    if len(df) > 0:
        print(f"🏆 Top signal: {df.iloc[0]['ticker']} (Score: {df.iloc[0]['signal_score']})")
    return df

if __name__ == "__main__":
    df = run_all_scrapers()
    if len(df) > 0:
        print("\n📊 Top 10 Signals:")
        print(df[['ticker', 'source', 'signal_type', 'sector', 'signal_score']].head(10))
    else:
        print("No signals found")
