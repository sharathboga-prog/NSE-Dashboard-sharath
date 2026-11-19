"""Read-only public data adapters. Missing feeds are reported, never fabricated."""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import quote
import requests
import pandas as pd

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"


def fetch_yahoo(ticker: str, period="18mo", interval="1d"):
    import yfinance as yf
    symbol = ticker.upper().strip()
    data = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True, actions=False)
    if data is None or data.empty:
        raise RuntimeError(f"No historical data returned for {symbol}")
    return data[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])


def fetch_fundamentals(symbol: str):
    import yfinance as yf
    info = yf.Ticker(symbol).info or {}
    keys = {"trailingPE": "PE", "pegRatio": "PEG", "returnOnEquity": "ROE",
            "debtToEquity": "Debt/Equity", "marketCap": "Market cap", "sector": "Sector",
            "earningsGrowth": "Earnings growth", "revenueGrowth": "Revenue growth"}
    return {display: info.get(key) for key, display in keys.items()}


def fetch_nse_fii_dii():
    """Official NSE provisional cash-market flow; may be blocked by NSE's anti-bot layer."""
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    sess = requests.Session()
    headers = {"User-Agent": UA, "Accept": "application/json,text/plain,*/*",
               "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.nseindia.com/reports/fii-dii"}
    sess.get("https://www.nseindia.com/", headers=headers, timeout=8)
    res = sess.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    payload = res.json()
    if not isinstance(payload, list) or not payload:
        raise ValueError("NSE returned empty or changed FII/DII schema")
    records = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        records.append({"Category": row.get("category"), "Date": row.get("date"),
                        "Buy ₹Cr": row.get("buyValue"), "Sell ₹Cr": row.get("sellValue"),
                        "Net ₹Cr": row.get("netValue")})
    if not records:
        raise ValueError("No parseable NSE FII/DII records")
    return pd.DataFrame(records), url


def fetch_moneycontrol_headlines(limit=8):
    """Google News RSS headlines linking to original reporting; not an official Moneycontrol API."""
    from xml.etree import ElementTree as ET
    query = quote('site:moneycontrol.com/news/business/markets/ India stocks when:3d')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=10)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    rows=[]
    for item in root.findall("./channel/item")[:limit]:
        rows.append({"Headline": item.findtext("title"), "Published": item.findtext("pubDate"),
                     "Link": item.findtext("link"), "Source": "Google News RSS / Moneycontrol"})
    return pd.DataFrame(rows), url


def market_link(symbol):
    return f"https://www.moneycontrol.com/india/stockpricequote/"  # category-specific paths vary


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
