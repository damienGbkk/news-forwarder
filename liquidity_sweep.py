import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

last_sweep = None

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

def get_current_candle():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=5m&range=1d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]
        highs = quotes["high"]
        lows = quotes["low"]
        closes = quotes["close"]
        highs = [h for h in highs if h]
        lows = [l for l in lows if l]
        closes = [c for c in closes if c]
        if not highs:
            return None
        return {
            "high": round(highs[-1], 2),
            "low": round(lows[-1], 2),
            "close": round(closes[-1], 2)
        }
    except Exception as e:
        print(f"Current candle error: {e}", flush=True)
        return None

def is_active_session():
    now = datetime.now(timezone.utc)
    h = now.hour
    wd = now.weekday()
    if wd >= 5:
        return False
    return 7 <= h < 17

def check_sweep():
    global last_sweep

    levels = get_daily_levels()
    candle = get_current_candle()

    if not levels or not candle:
        return

    sweep_key = f"{candle['high']}-{candle['low']}"
    if sweep_key == last_sweep:
        return

    sweeps = []

    # Sweep du ODH
    if candle["high"] > levels["odh"] and candle["close"] < levels["odh"]:
        sweeps.append(f"SWEEP ODH {levels['odh']} -> close sous le niveau")

    # Sweep du ODL
    if candle["low"] < levels["odl"] and candle["close"] > levels["odl"]:
        sweeps.append(f"SWEEP ODL {levels['odl']} -> close au-dessus du niveau")

    # Sweep du Weekly High
    if candle["high"] > levels["weekly_high"] and candle["close"] < levels["weekly_high"]:
        sweeps.append(f"SWEEP WEEKLY HIGH {levels['weekly_high']} -> close sous le niveau")

    # Sweep du Weekly Low
    if candle["low"] < levels["weekly_low"] and candle["close"] > levels["weekly_low"]:
        sweeps.append(f"SWEEP WEEKLY LOW {levels['weekly_low']} -> close au-dessus du niveau")

    if sweeps:
        msg = (
            f"LIQUIDITY SWEEP DETECTE\n"
            f"------------------------\n"
            f"{chr(10).join(sweeps)}\n"
            f"------------------------\n"
            f"Prix actuel: {candle['close']}\n"
            f"Chercher CISD + FVG pour entree"
        )
        send_telegram(msg)
        last_sweep = sweep_key
        print(f"Sweep alert sent: {sweeps}", flush=True)

print("Liquidity sweep started", flush=True)

while True:
    if is_active_session():
        check_sweep()
    time.sleep(300)
