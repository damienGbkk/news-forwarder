import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

last_fvg = None

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
        highs = quotes["high"]
        lows = quotes["low"]
        closes = quotes["close"]

        candles = []
        for i in range(len(highs)):
            if highs[i] and lows[i] and closes[i]:
                candles.append({
                    "high": round(highs[i], 2),
                    "low": round(lows[i], 2),
                    "close": round(closes[i], 2)
                })
        return candles
    except Exception as e:
        print(f"FVG candles error: {e}", flush=True)
        return []

def is_active_session():
    now = datetime.now(timezone.utc)
    h = now.hour
    wd = now.weekday()
    if wd >= 5:
        return False
    return 7 <= h < 17

def check_fvg():
    global last_fvg

    candles = get_candles()
    if len(candles) < 3:
        return

    c1 = candles[-3]
    c2 = candles[-2]
    c3 = candles[-1]

    fvg_key = f"{c2['high']}-{c2['low']}"
    if fvg_key == last_fvg:
        return

    # Bullish FVG: low de c3 > high de c1
    if c3["low"] > c1["high"]:
        gap_size = round(c3["low"] - c1["high"], 2)
        if gap_size > 1:
            msg = (
                f"FVG BULLISH DETECTE - 5min\n"
                f"------------------------\n"
                f"Zone: {c1['high']} - {c3['low']}\n"
                f"Taille: {gap_size} pts\n"
                f"Prix actuel: {c3['close']}\n"
                f"------------------------\n"
                f"Si prix revient dans la zone -> chercher long\n"
                f"Valide apres liquidity sweep"
            )
            send_telegram(msg)
            last_fvg = fvg_key
            print(f"Bullish FVG detected: {c1['high']} - {c3['low']}", flush=True)

    # Bearish FVG: high de c3 < low de c1
    elif c3["high"] < c1["low"]:
        gap_size = round(c1["low"] - c3["high"], 2)
        if gap_size > 1:
            msg = (
                f"FVG BEARISH DETECTE - 5min\n"
                f"------------------------\n"
                f"Zone: {c3['high']} - {c1['low']}\n"
                f"Taille: {gap_size} pts\n"
                f"Prix actuel: {c3['close']}\n"
                f"------------------------\n"
                f"Si prix revient dans la zone -> chercher short\n"
                f"Valide apres liquidity sweep"
            )
            send_telegram(msg)
            last_fvg = fvg_key
            print(f"Bearish FVG detected: {c3['high']} - {c1['low']}", flush=True)

print("FVG alert started", flush=True)

while True:
    if is_active_session():
        check_fvg()
    time.sleep(300)
