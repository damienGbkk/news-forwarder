import os
import requests
import time
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

last_setup = None
sweep_detected = None
cisd_detected = None
fvg_detected = None
sweep_time = None
cisd_time = None
fvg_time = None

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

def get_candles_5m():
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
        print(f"Candles 5m error: {e}", flush=True)
        return []

def get_daily_levels():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=5d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]
        highs = [h for h in quotes["high"] if h]
        lows = [l for l in quotes["low"] if l]
        return {
            "odh": round(highs[-2], 2),
            "odl": round(lows[-2], 2),
            "weekly_high": round(max(highs[-6:]), 2),
            "weekly_low": round(min(lows[-6:]), 2)
        }
    except Exception as e:
        print(f"Daily levels error: {e}", flush=True)
        return None

def is_killzone():
    now = datetime.now(timezone.utc)
    h = now.hour
    m = now.minute
    wd = now.weekday()
    if wd >= 5:
        return False
    # London killzone 07h-09h UTC
    if 7 <= h < 9:
        return True
    # NY killzone 12h-14h UTC
    if 12 <= h < 14:
        return True
    return False

def within_15min(t1, t2):
    if t1 is None or t2 is None:
        return False
    return abs((t1 - t2).total_seconds()) <= 900

def check_setup():
    global last_setup, sweep_detected, cisd_detected, fvg_detected
    global sweep_time, cisd_time, fvg_time

    candles = get_candles_5m()
    levels = get_daily_levels()

    if len(candles) < 4 or not levels:
        return

    now = datetime.now(timezone.utc)
    c1 = candles[-4]
    c2 = candles[-3]
    c3 = candles[-2]
    c4 = candles[-1]

    current_price = c4["close"]

    # SWEEP detection
    sweep_dir = None
    sweep_level = None

    if c4["high"] > levels["odh"] and c4["close"] < levels["odh"]:
        sweep_dir = "BEARISH"
        sweep_level = levels["odh"]
        sweep_detected = "BEARISH"
        sweep_time = now
    elif c4["low"] < levels["odl"] and c4["close"] > levels["odl"]:
        sweep_dir = "BULLISH"
        sweep_level = levels["odl"]
        sweep_detected = "BULLISH"
        sweep_time = now
    elif c4["high"] > levels["weekly_high"] and c4["close"] < levels["weekly_high"]:
        sweep_dir = "BEARISH"
        sweep_level = levels["weekly_high"]
        sweep_detected = "BEARISH"
        sweep_time = now
    elif c4["low"] < levels["weekly_low"] and c4["close"] > levels["weekly_low"]:
        sweep_dir = "BULLISH"
        sweep_level = levels["weekly_low"]
        sweep_detected = "BULLISH"
        sweep_time = now

    # CISD detection
    if (not c1["bullish"] and not c2["bullish"] and not c3["bullish"]
            and c4["bullish"] and c4["high"] > c3["high"]
            and round(c4["close"] - c4["open"], 2) > 1):
        cisd_detected = "BULLISH"
        cisd_time = now

    elif (c1["bullish"] and c2["bullish"] and c3["bullish"]
            and not c4["bullish"] and c4["low"] < c3["low"]
            and round(c4["open"] - c4["close"], 2) > 1):
        cisd_detected = "BEARISH"
        cisd_time = now

    # FVG detection
    if c3["low"] > c1["high"] and round(c3["low"] - c1["high"], 2) > 1:
        fvg_detected = "BULLISH"
        fvg_time = now
        fvg_zone = f"{c1['high']} - {c3['low']}"
    elif c3["high"] < c1["low"] and round(c1["low"] - c3["high"], 2) > 1:
        fvg_detected = "BEARISH"
        fvg_time = now
        fvg_zone = f"{c3['high']} - {c1['low']}"
    else:
        fvg_zone = None

    # CONFLUENCE check - les 3 dans la meme direction dans les 15 dernieres minutes
    setup_key = f"{current_price}-{sweep_detected}-{cisd_detected}-{fvg_detected}"

    if (sweep_detected and cisd_detected and fvg_detected
            and sweep_detected == cisd_detected == fvg_detected
            and within_15min(sweep_time, cisd_time)
            and within_15min(cisd_time, fvg_time)
            and setup_key != last_setup):

        direction = sweep_detected
        action = "LONG" if direction == "BULLISH" else "SHORT"

        msg = (
            f"SETUP COMPLET - {direction}\n"
            f"========================\n"
            f"Sweep + CISD + FVG confirmes\n"
            f"Direction: {action}\n"
            f"Prix actuel: {current_price}\n"
            f"FVG zone: {fvg_zone}\n"
            f"------------------------\n"
            f"ODH: {levels['odh']} | ODL: {levels['odl']}\n"
            f"------------------------\n"
            f"Chercher entree sur retest FVG\n"
            f"SL sous le sweep | TP prochain niveau"
        )
        send_telegram(msg)
        last_setup = setup_key
        sweep_detected = None
        cisd_detected = None
        fvg_detected = None
        print(f"Full setup sent: {direction} at {current_price}", flush=True)

print("Setup detector started", flush=True)

while True:
    if is_killzone():
        check_setup()
    time.sleep(300)
