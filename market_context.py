import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FRED_API_KEY = os.environ.get("FRED_API_KEY")

sent_london = False
sent_ny = False

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}", flush=True)

def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        return round(data["chart"]["result"][0]["meta"]["regularMarketPrice"], 2)
    except:
        return None

def get_tips():
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DFII10&api_key={FRED_API_KEY}&sort_order=desc&limit=1&file_type=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return round(float(data["observations"][0]["value"]), 2)
    except:
        return None

def get_verdict(tips, dxy, vix):
    bull = 0
    bear = 0
    details = []

    if tips is not None:
        if tips < 0:
            bull += 2
            details.append("🟢 Taux réels négatifs → favorable Gold")
        elif tips < 1.5:
            bull += 1
            details.append("🟡 Taux réels bas → neutre/bullish Gold")
        else:
            bear += 2
            details.append("🔴 Taux réels élevés → défavorable Gold")

    if dxy is not None:
        if dxy < 99:
            bull += 2
            details.append("🟢 DXY faible → favorable Gold")
        elif dxy > 101:
            bear += 2
            details.append("🔴 DXY fort → défavorable Gold")
        else:
            bull += 1
            details.append("🟡 DXY neutre")

    if vix is not None:
        if vix > 25:
            details.append("⚠️ VIX élevé → volatilité forte, prudence")
        else:
            bull += 1
            details.append("🟢 VIX bas → risk-on")

    if bull > bear + 1:
        verdict = "🟢 <b>GOLD BULLISH</b>"
    elif bear > bull + 1:
        verdict = "🔴 <b>GOLD BEARISH</b>"
    else:
        verdict = "🟡 <b>GOLD NEUTRE</b> — pas de biais clair"

    return verdict, "\n".join(details)

def send_context(session_name):
    gold = get_price("GC=F")
    dxy = get_price("DX-Y.NYB")
    vix =
