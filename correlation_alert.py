import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

last_alert = None

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

def get_candles(symbol, interval="30m"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range=1d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) < 2:
            return None, None
        return closes[-2], closes[-1]
    except Exception as e:
        print(f"Candles error {symbol}: {e}", flush=True)
        return None, None

def is_active_session():
    now = datetime.now(timezone.utc)
    h = now.hour
    wd = now.weekday()
    if wd >= 5:
        return False
    return 7 <= h < 17

def check_correlation():
    global last_alert

    gold_prev, gold_curr = get_candles("GC=F")
    dxy_prev, dxy_curr = get_candles("DX-Y.NYB")

    if not all([gold_prev, gold_curr, dxy_prev, dxy_curr]):
        return

    gold_move = gold_curr - gold_prev
    dxy_move = dxy_curr - dxy_prev

    gold_pct = round((gold_move / gold_prev) * 100, 3)
    dxy_pct = round((dxy_move / dxy_prev) * 100, 3)

    alert_key = f"{round(gold_curr)}-{round(dxy_curr)}"

    # Correlation anormale : DXY et Gold montent ensemble ou baissent ensemble
    if gold_move > 0 and dxy_move > 0 and abs(gold_pct) > 0.1 and abs(dxy_pct) > 0.05:
        if last_alert != alert_key:
            msg = (
                f"CORRELATION ANORMALE - ALERTE\n"
                f"Gold ET DXY montent ensemble\n"
                f"Gold: {round(gold_curr, 2)} ({gold_pct}%)\n"
                f"DXY: {round(dxy_curr, 3)} ({dxy_pct}%)\n"
                f"Signal: move institutionnel possible\n"
                f"Surveiller liquidity sweep imminent"
            )
            send_telegram(msg)
            last_alert = alert_key
            print("Correlation alert sent - both up", flush=True)

    elif gold_move < 0 and dxy_move < 0 and abs(gold_pct) > 0.1 and abs(dxy_pct) > 0.05:
        if last_alert != alert_key:
            msg = (
                f"CORRELATION ANORMALE - ALERTE\n"
                f"Gold ET DXY baissent ensemble\n"
                f"Gold: {round(gold_curr, 2)} ({gold_pct}%)\n"
                f"DXY: {round(dxy_curr, 3)} ({dxy_pct}%)\n"
                f"Signal: move institutionnel possible\n"
                f"Surveiller liquidity sweep imminent"
            )
            send_telegram(msg)
            last_alert = alert_key
            print("Correlation alert sent - both down", flush=True)

print("Correlation alert started", flush=True)

while True:
    now = datetime.now(timezone.utc)
    if is_active_session():
        check_correlation()
    time.sleep(1800)
