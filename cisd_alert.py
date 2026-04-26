import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

last_cisd = None

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

def get_candles():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=5m&range=1d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]
        candles = []
        for i in range(len(quotes["high"])):
            h = quotes["high"][i]
            l = quotes["low"][i]
            o = quotes["open"][i]
            c = quotes["close"][i]
            if h and l and o and c:
                candles.append({
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "open": round(o, 2),
                    "close": round(c, 2),
                    "bullish": c > o
                })
        return candles
    except Exception as e:
        print(f"CISD candles error: {e}", flush=True)
        return []

def is_active_session():
    now = datetime.now(timezone.utc)
    h = now.hour
    wd = now.weekday()
    if wd >= 5:
        return False
    return 7 <= h < 17

def check_cisd():
    global last_cisd

    candles = get_candles()
    if len(candles) < 4:
        return

    # CISD = apres une serie de bougies bearish, une bougie bullish casse le high de la precedente
    # ou apres une serie bullish, une bearish casse le low de la precedente

    c1 = candles[-4]
    c2 = candles[-3]
    c3 = candles[-2]
    c4 = candles[-1]

    cisd_key = f"{c4['open']}-{c4['close']}"
    if cisd_key == last_cisd:
        return

    # Bullish CISD: 3 bougies bearish puis bougie bullish qui casse le high de c3
    if (not c1["bullish"] and not c2["bullish"] and not c3["bullish"]
            and c4["bullish"] and c4["high"] > c3["high"]):
        size = round(c4["close"] - c4["open"], 2)
        if size > 1:
            msg = (
                f"CISD BULLISH - 5min\n"
                f"------------------------\n"
                f"Changement de structure bullish detecte\n"
                f"3 bougies bearish -> bougie bullish\n"
                f"Breakout: {c3['high']} -> {c4['high']}\n"
                f"Prix actuel: {c4['close']}\n"
                f"------------------------\n"
                f"Confluence avec FVG bullish -> setup LONG\n"
                f"Attendre retest si possible"
            )
            send_telegram(msg)
            last_cisd = cisd_key
            print(f"Bullish CISD detected at {c4['close']}", flush=True)

    # Bearish CISD: 3 bougies bullish puis bougie bearish qui casse le low de c3
    elif (c1["bullish"] and c2["bullish"] and c3["bullish"]
            and not c4["bullish"] and c4["low"] < c3["low"]):
        size = round(c4["open"] - c4["close"], 2)
        if size > 1:
            msg = (
                f"CISD BEARISH - 5min\n"
                f"------------------------\n"
                f"Changement de structure bearish detecte\n"
                f"3 bougies bullish -> bougie bearish\n"
                f"Breakout: {c3['low']} -> {c4['low']}\n"
                f"Prix actuel: {c4['close']}\n"
                f"------------------------\n"
                f"Confluence avec FVG bearish -> setup SHORT\n"
                f"Attendre retest si possible"
            )
            send_telegram(msg)
            last_cisd = cisd_key
            print(f"Bearish CISD detected at {c4['close']}", flush=True)

print("CISD alert started", flush=True)

while True:
    if is_active_session():
        check_cisd()
    time.sleep(300)
