import requests
import time
import os
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    })

def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return price
    except:
        return None

def is_trading_session():
    now = datetime.now(timezone.utc)
    hour = now.hour
    # London 07:00-12:00 UTC / NY 12:00-17:00 UTC
    return 7 <= hour < 17

last_signal = None

while True:
    if is_trading_session():
        gold = get_price("GC=F")
        dxy = get_price("DX-Y.NYB")
        vix = get_price("^VIX")

        if gold and dxy and vix:
            print(f"GOLD: {gold} | DXY: {dxy} | VIX: {vix}")

            if dxy < 98.50 and gold > 4700 and vix < 25:
                signal = "BULL"
                msg = f"BULL GOLD\nDXY: {dxy:.2f} | GOLD: {gold:.0f} | VIX: {vix:.2f}\nChercher LONG sur liquidity sweep / FVG 5min"
            elif dxy > 99 and gold < 4750 and vix > 20:
                signal = "BEAR"
                msg = f"BEAR GOLD\nDXY: {dxy:.2f} | GOLD: {gold:.0f} | VIX: {vix:.2f}\nChercher SHORT sur liquidity sweep / FVG 5min"
            else:
                signal = "NEUTRAL"
                msg = None

            if signal != last_signal and msg:
                send_telegram(msg)
                last_signal = signal

    time.sleep(300)  # toutes les 5 minutes
