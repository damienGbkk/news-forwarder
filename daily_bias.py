import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

sent_daily = False

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

def get_daily_data():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=5d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]
        closes = quotes["close"]
        highs = quotes["high"]
        lows = quotes["low"]
        opens = quotes["open"]

        prev_close = closes[-2]
        prev_high = highs[-2]
        prev_low = lows[-2]
        prev_open = opens[-2]
        curr_open = opens[-1]

        return {
            "prev_close": round(prev_close, 2) if prev_close else None,
            "prev_high": round(prev_high, 2) if prev_high else None,
            "prev_low": round(prev_low, 2) if prev_low else None,
            "prev_open": round(prev_open, 2) if prev_open else None,
            "curr_open": round(curr_open, 2) if curr_open else None
        }
    except Exception as e:
        print(f"Daily data error: {e}", flush=True)
        return None

def send_daily_bias():
    data = get_daily_data()
    if not data:
        print("Daily data unavailable", flush=True)
        return

    bias_lines = []
    verdict = "NEUTRE"

    prev_close = data["prev_close"]
    prev_high = data["prev_high"]
    prev_low = data["prev_low"]
    prev_open = data["prev_open"]
    curr_open = data["curr_open"]

    if prev_close and prev_open:
        prev_candle = "BULLISH" if prev_close > prev_open else "BEARISH"
        bias_lines.append(f"Bougie precedente: {prev_candle} (O:{prev_open} C:{prev_close})")

    if prev_high:
        bias_lines.append(f"ODH (Old Day High): {prev_high} -> liquidite au-dessus")
    if prev_low:
        bias_lines.append(f"ODL (Old Day Low): {prev_low} -> liquidite en-dessous")

    if curr_open and prev_close:
        gap = round(curr_open - prev_close, 2)
        if gap > 3:
            bias_lines.append(f"Gap UP +{gap} -> bullish momentum")
            verdict = "BULLISH"
        elif gap < -3:
            bias_lines.append(f"Gap DOWN {gap} -> bearish momentum")
            verdict = "BEARISH"
        else:
            bias_lines.append(f"Ouverture proche cloture ({gap}) -> pas de biais gap")

    if prev_close and prev_high and prev_low:
        midpoint = round((prev_high + prev_low) / 2, 2)
        if curr_open and curr_open > midpoint:
            bias_lines.append(f"Prix au-dessus du midpoint ({midpoint}) -> biais haussier")
            if verdict == "NEUTRE":
                verdict = "BULLISH"
        elif curr_open and curr_open < midpoint:
            bias_lines.append(f"Prix en-dessous du midpoint ({midpoint}) -> biais baissier")
            if verdict == "NEUTRE":
                verdict = "BEARISH"

    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    msg = (
        f"DAILY BIAS - GOLD\n"
        f"{today}\n"
        f"------------------------\n"
        f"{chr(10).join(bias_lines)}\n"
        f"------------------------\n"
        f"VERDICT: {verdict}\n"
        f"------------------------\n"
        f"Niveaux cles du jour:\n"
        f"Resistance: {prev_high}\n"
        f"Support: {prev_low}"
    )
    send_telegram(msg)
    print("Daily bias sent", flush=True)

print("Daily bias started", flush=True)

while True:
    now = datetime.now(timezone.utc)
    # 06h00 UTC = 13h00 Bangkok, avant Asian range
    if now.hour == 6 and now.minute == 0:
        if not sent_daily:
            send_daily_bias()
            sent_daily = True
    else:
        if now.hour != 6:
            sent_daily = False
    time.sleep(30)
