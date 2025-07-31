import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd

def safe_get(url, headers=None):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None

def scrape_quiver_senate():
    url = "https://www.quiverquant.com/sources/senatetrading"
    html = safe_get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")[1:] if table else []
    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 5:
            data.append({
                "source": "QuiverQuant Senate",
                "ticker": cols[0].text.strip(),
                "name": cols[1].text.strip(),
                "date": cols[2].text.strip(),
                "type": cols[3].text.strip(),
                "amount": cols[4].text.strip()
            })
    return data

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
            data.append({
                "source": "HighShortInterest",
                "ticker": cols[1].text.strip(),
                "short_float": cols[3].text.strip()
            })
    return data

def scrape_finviz_gainers():
    url = "https://finviz.com/screener.ashx?v=111&s=ta_topgainers"
    html = safe_get(url, headers={"User-Agent": "Mozilla/5.0"})
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="table-light")
    rows = table.find_all("tr")[1:] if table else []
    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            data.append({
                "source": "Finviz Gainers",
                "ticker": cols[1].text.strip(),
                "company": cols[2].text.strip()
            })
    return data

def run_all_scrapers():
    all_data = []
    all_data.extend(scrape_quiver_senate())
    all_data.extend(scrape_highshortinterest())
    all_data.extend(scrape_finviz_gainers())
    df = pd.DataFrame(all_data)
    df["scraped_at"] = datetime.utcnow().isoformat()
    return df

if __name__ == "__main__":
    df = run_all_scrapers()
    print(df.head())
