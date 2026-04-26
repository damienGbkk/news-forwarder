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
        value = float(data["observations"][0]["value"])
        return round(value, 2)
    except:
        return None

def get_bias(tips, dxy, vix):
    bias = []
    if tips is not None:
        if tips < 0:
            bias.append("🟢 Real rate negative → Gold bullish")
        elif tips < 1.5:
            bias.append("🟡 Real rate low → Gold neutral/bullish")
        else:
            bias.append("🔴 Real rate high → Gold bearish")
    if dxy is not None:
        if dxy < 99:
            bias.append("🟢 DXY weak → Gold bullish")
        elif dxy > 101:
            bias.append("🔴 DXY strong → Gold bearish")
        else:
            bias.append("🟡 DXY neutral")
    if vix is not None:
        if vix > 25:
            bias.append("⚠️ VIX elevated → Risk-off, Gold volatile")
        else:
            bias.append("🟢 VIX low → Risk-on")
    return "\n".join(bias)

def send_context(session_name):
    gold = get_price("GC=F")
    dxy = get_price("DX-Y.NYB")
    vix = get_price("^VIX")
    tips = get_tips()
    bias = get_bias(tips, dxy, vix)

    msg = (
        f"🌍 <b>{session_name} OPEN — Market Context</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"GOLD: <b>{gold}</b>\n"
        f"DXY: <b>{dxy}</b>\n"
        f"VIX: <b>{vix}</b>\n"
        f"TIPS 10Y (real rate): <b>{tips}%</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{bias}"
    )
    send_telegram(msg)
    print(f"{session_name} context sent", flush=True)

print("Market context started", flush=True)

while True:
    now = datetime.now(timezone.utc)
    hour = now.hour
    minute = now.minute

    if hour == 7 and minute == 0:
        if not sent_london:
            send_context("LONDON")
            sent_london = True
    else:
        if hour != 7:
            sent_london = False

    if hour == 12 and minute == 0:
        if not sent_ny:
            send_context("NEW YORK")
            sent_ny = True
    else:
        if hour != 12:
            sent_ny = False

    time.sleep(30)
