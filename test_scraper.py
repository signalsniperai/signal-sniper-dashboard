import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import re
import json

def safe_get(url, headers=None):
    try:
        default_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        headers = headers or default_headers
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
        return None

# === CORE SCRAPERS ===
def scrape_finviz_gainers():
    """Scrape Finviz top gainers - reliable and fast"""
    print("🔍 Scraping Finviz Gainers...")
    url = "https://finviz.com/screener.ashx?v=111&s=ta_topgainers"
    html = safe_get(url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    data = []
    
    # Look for the screener table
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:20]:  # Skip header, take top 20
            cols = row.find_all("td")
            if len(cols) >= 12:  # Finviz has many columns
                ticker = cols[1].get_text().strip()
                company = cols[2].get_text().strip()
                sector = cols[3].get_text().strip()
                price = cols[8].get_text().strip()
                change = cols[9].get_text().strip()
                volume = cols[10].get_text().strip()
                
                if ticker and len(ticker) <= 5:
                    data.append({
                        "source": "Finviz Gainers", 
                        "ticker": ticker,
                        "company": company[:50],
                        "sector": sector,
                        "price": price,
                        "change": change,
                        "volume": volume,
                        "signal_type": "momentum",
                        "description": f"{company} - {change} gain"
                    })
    
    print(f"✅ Finviz: Found {len(data)} gainers")
    return data

def scrape_yahoo_trending():
    """Scrape Yahoo Finance trending tickers"""
    print("🔍 Scraping Yahoo Trending...")
    url = "https://finance.yahoo.com/trending-tickers"
    html = safe_get(url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    data = []
    
    # Look for trending ticker data
    rows = soup.find_all("tr")
    for row in rows[:15]:
        cols = row.find_all("td")
        if len(cols) >= 3:
            ticker_cell = cols[0].find("a")
            if ticker_cell:
                ticker = ticker_cell.get_text().strip()
                if ticker and len(ticker) <= 5:
                    company = cols[1].get_text().strip()
                    price = cols[2].get_text().strip()
                    change = cols[3].get_text().strip() if len(cols) > 3 else ""
                    
                    data.append({
                        "source": "Yahoo Trending",
                        "ticker": ticker,
                        "company": company[:50],
                        "price": price,
                        "change": change,
                        "signal_type": "trending",
                        "sector": "trending",
                        "description": f"{company} trending on Yahoo"
                    })
    
    print(f"✅ Yahoo: Found {len(data)} trending stocks")
    return data

def scrape_marketwatch_movers():
    """Scrape MarketWatch movers"""
    print("🔍 Scraping MarketWatch Movers...")
    url = "https://www.marketwatch.com/tools/screener/premarket"
    html = safe_get(url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    data = []
    
    # Look for stock data in tables
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:15]:  # Top 15
            cols = row.find_all("td")
            if len(cols) >= 4:
                ticker_cell = cols[0].find("a")
                if ticker_cell:
                    ticker = ticker_cell.get_text().strip()
                    if ticker and len(ticker) <= 5:
                        company = cols[1].get_text().strip() if len(cols) > 1 else ""
                        price = cols[2].get_text().strip() if len(cols) > 2 else ""
                        change = cols[3].get_text().strip() if len(cols) > 3 else ""
                        
                        data.append({
                            "source": "MarketWatch Movers",
                            "ticker": ticker,
                            "company": company[:50],
                            "price": price,
                            "change": change,
                            "signal_type": "premarket_mover",
                            "sector": "movers",
                            "description": f"{company} premarket activity"
                        })
    
    print(f"✅ MarketWatch: Found {len(data)} movers")
    return data

def find_ai_biotech_energy_tickers(data):
    """Classify tickers into our target sectors based on company names"""
    ai_keywords = ['artificial', 'ai', 'intelligence', 'machine', 'neural', 'robotics', 'autonomous', 'semiconductor', 'chip', 'nvidia', 'software', 'cloud', 'data']
    biotech_keywords = ['bio', 'pharma', 'therapeutic', 'medical', 'drug', 'clinical', 'health', 'gene', 'cell', 'vaccine']
    energy_keywords = ['solar', 'renewable', 'energy', 'battery', 'electric', 'power', 'grid', 'oil', 'gas', 'nuclear', 'wind']
    
    for item in data:
        company_lower = item.get('company', '').lower()
        ticker_context = f"{company_lower} {item.get('description', '').lower()}"
        
        # Check for AI/Tech
        if any(keyword in ticker_context for keyword in ai_keywords):
            item['target_sector'] = 'AI/Tech'
            item['sector_score'] = 20
        # Check for Biotech
        elif any(keyword in ticker_context for keyword in biotech_keywords):
            item['target_sector'] = 'Biotech'
            item['sector_score'] = 25
        # Check for Energy
        elif any(keyword in ticker_context for keyword in energy_keywords):
            item['target_sector'] = 'Energy'
            item['sector_score'] = 20
        else:
            item['target_sector'] = 'Other'
            item['sector_score'] = 5
    
    return data

def calculate_signal_score(row):
    """Calculate signal score for each opportunity"""
    score = 0
    
    # Base score by signal type
    signal_type = row.get('signal_type', '').lower()
    if signal_type == 'momentum':
        score += 25
    elif signal_type == 'trending':
        score += 20
    elif signal_type == 'premarket_mover':
        score += 30
    
    # Sector bonus (our target sectors)
    sector_score = row.get('sector_score', 0)
    score += sector_score
    
    # Volume/change bonuses
    change = str(row.get('change', ''))
    if '+' in change:
        try:
            change_num = float(change.replace('+', '').replace('%', ''))
            if change_num > 10:
                score += 15
            elif change_num > 5:
                score += 10
        except:
            pass
    
    return min(score, 100)

def run_simple_scraper():
    """Run simplified version focusing on reliable sources"""
    print("🎯 Signal Sniper - Simple Test Version")
    print("=" * 50)
    
    all_data = []
    
    # Run scrapers
    scrapers = [
        scrape_finviz_gainers,
        scrape_yahoo_trending,
        scrape_marketwatch_movers
    ]
    
    for scraper in scrapers:
        try:
            data = scraper()
            all_data.extend(data)
        except Exception as e:
            print(f"❌ {scraper.__name__} failed: {e}")
    
    if not all_data:
        print("❌ No data found")
        return pd.DataFrame()
    
    # Classify into target sectors
    all_data = find_ai_biotech_energy_tickers(all_data)
    
    # Create DataFrame
    df = pd.DataFrame(all_data)
    df['scraped_at'] = datetime.utcnow().isoformat()
    
    # Calculate scores
    df['signal_score'] = df.apply(calculate_signal_score, axis=1)
    
    # Sort by score
    df = df.sort_values('signal_score', ascending=False)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['ticker'], keep='first')
    
    print(f"\n📊 RESULTS:")
    print(f"Total signals: {len(df)}")
    
    # Show target sector breakdown
    target_sectors = df[df['target_sector'].isin(['AI/Tech', 'Biotech', 'Energy'])]
    print(f"Target sector opportunities: {len(target_sectors)}")
    
    if len(target_sectors) > 0:
        print(f"\n🎯 TARGET SECTOR OPPORTUNITIES:")
        for idx, row in target_sectors.head(10).iterrows():
            print(f"  {row['ticker']:>6} | {row['target_sector']:>8} | Score: {row['signal_score']:>3} | {row['company'][:40]}")
    
    # Show all top signals
    print(f"\n🏆 TOP 15 SIGNALS (All Sectors):")
    for idx, row in df.head(15).iterrows():
        sector_flag = "🎯" if row['target_sector'] in ['AI/Tech', 'Biotech', 'Energy'] else "  "
        print(f"{sector_flag} {row['ticker']:>6} | Score: {row['signal_score']:>3} | {row['signal_type']:>15} | {row['company'][:35]}")
    
    return df

if __name__ == "__main__":
    try:
        df = run_simple_scraper()
        print(f"\n✅ Scraping complete. Found {len(df)} total opportunities.")
        
        # Save to CSV for analysis
        if len(df) > 0:
            filename = f"signals_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            df.to_csv(filename, index=False)
            print(f"💾 Results saved to {filename}")
            
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()