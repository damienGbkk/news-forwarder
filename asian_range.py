import os
import requests
import time
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

sent_asian_range = False

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

def get_asian_range():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1h&range=2d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        timestamps = data["chart"]["result"][0]["timestamp"]
        highs = data["chart"]["result"][0]["indicators"]["quote"][0]["high"]
        lows = data["chart"]["result"][0]["indicators"]["quote"][0]["low"]
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]

        now = datetime.now(timezone.utc)
        asian_start = now.replace(hour=23, minute=0, second=0, microsecond=0) - timedelta(days=1)
        asian_end = now.replace(hour=6, minute=0, second=0, microsecond=0)

        asian_highs = []
        asian_lows = []

        for i, ts in enumerate(timestamps):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            if asian_start <= dt <= asian_end:
                if highs[i] is not None:
                    asian_highs.append(highs[i])
                if lows[i] is not None:
                    asian_lows.append(lows[i])

        if not asian_highs or not asian_lows:
            return None

        asian_high = round(max(asian_highs), 2)
        asian_low = round(min(asian_lows), 2)
        asian_range_size = round(asian_high - asian_low, 2)
        current_price = closes[-1]

        return {
            "high": asian_high,
            "low": asian_low,
            "range": asian_range_size,
            "current": round(current_price, 2) if current_price else None
        }
    except Exception as e:
        print(f"Asian range error: {e}", flush=True)
        return None

def send_asian_range():
    data = get_asian_range()
    if not data:
        print("Asian range data unavailable", flush=True)
        return

    current = data["current"]
    h = data["high"]
    l = data["low"]
    rng = data["range"]

    if current:
        if current > h:
            position = "Prix AU-DESSUS du range -> sweep du high possible"
        elif current < l:
            position = "Prix EN-DESSOUS du range -> sweep du low possible"
        elif current > (h + l) / 2:
            position = "Prix dans le range -> upper half"
        else:
            position = "Prix dans le range -> lower half"
    else:
        position = "Prix indisponible"

    msg = (
        f"ASIAN RANGE - GOLD\n"
        f"High: {h}\n"
        f"Low: {l}\n"
        f"Range: {rng} pts\n"
        f"Prix actuel: {current}\n"
        f"{position}\n"
        f"Niveaux London open:\n"
        f"Resistance: {h}\n"
        f"Support: {l}"
    )
    send_telegram(msg)
    print("Asian range sent", flush=True)

print("Asian range started", flush=True)

while True:
    now = datetime.now(timezone.utc)
    if now.hour == 6 and now.minute == 30:
        if not sent_asian_range:
            send_asian_range()
            sent_asian_range = True
    else:
        if not (now.hour == 6 and now.minute >= 30):
            sent_asian_range = False
    time.sleep(60)
