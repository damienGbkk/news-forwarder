import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

sent_weekly = False

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

def get_weekly_data(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1wk&range=1mo"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]
        closes = quotes["close"]
        highs = quotes["high"]
        lows = quotes["low"]
        prev_close = closes[-2]
        prev_high = highs[-2]
        prev_low = lows[-2]
        curr_open = quotes["open"][-1]
        return {
            "prev_close": round(prev_close, 2) if prev_close else None,
            "prev_high": round(prev_high, 2) if prev_high else None,
            "prev_low": round(prev_low, 2) if prev_low else None,
            "curr_open": round(curr_open, 2) if curr_open else None
        }
    except Exception as e:
        print(f"Weekly data error {symbol}: {e}", flush=True)
        return None

def get_macro_events():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        events = r.json()
        high_impact = []
        for e in events:
            if e.get("currency") == "USD" and e.get("impact") == "High":
                title = e.get("title", "")
                date = e.get("date", "")
                time_str = e.get("time", "")
                high_impact.append(f"- {title} ({date} {time_str} UTC)")
        return high_impact[:5]
    except:
        return []

def send_weekly_bias():
    gold = get_weekly_data("GC=F")
    dxy = get_weekly_data("DX-Y.NYB")
    events = get_macro_events()

    bias_lines = []
    verdict = "NEUTRE"

    if gold:
        gap = None
        if gold["curr_open"] and gold["prev_close"]:
            gap = round(gold["curr_open"] - gold["prev_close"], 2)
            if gap > 5:
                bias_lines.append(f"Gold gap UP +{gap} -> bullish momentum")
                verdict = "BULLISH"
            elif gap < -5:
                bias_lines.append(f"Gold gap DOWN {gap} -> bearish momentum")
                verdict = "BEARISH"
            else:
                bias_lines.append(f"Gold gap neutre {gap}")

        if gold["prev_high"] and gold["prev_low"]:
            bias_lines.append(f"Weekly High precedent: {gold['prev_high']}")
            bias_lines.append(f"Weekly Low precedent: {gold['prev_low']}")

    if dxy:
        if dxy["prev_close"] and dxy["curr_open"]:
            dxy_gap = round(dxy["curr_open"] - dxy["prev_close"], 2)
            if dxy_gap > 0.2:
                bias_lines.append(f"DXY gap UP +{dxy_gap} -> pression sur Gold")
                if verdict == "BULLISH":
                    verdict = "NEUTRE"
            elif dxy_gap < -0.2:
                bias_lines.append(f"DXY gap DOWN {dxy_gap} -> favorable Gold")
                if verdict == "NEUTRE":
                    verdict = "BULLISH"

    events_str = "\n".join(events) if events else "Aucun event majeur"

    msg = (
        f"WEEKLY BIAS - GOLD\n"
        f"Semaine du {datetime.now(timezone.utc).strftime('%d/%m/%Y')}\n"
        f"------------------------\n"
        f"ANALYSE:\n"
        f"{chr(10).join(bias_lines)}\n"
        f"------------------------\n"
        f"EVENTS HIGH IMPACT cette semaine:\n"
        f"{events_str}\n"
        f"------------------------\n"
        f"VERDICT: {verdict}"
    )
    send_telegram(msg)
    print("Weekly bias sent", flush=True)

print("Weekly bias started", flush=True)

while True:
    now = datetime.now(timezone.utc)
    # Lundi 06h00 UTC = 13h00 Bangkok
    if now.weekday() == 0 and now.hour == 6 and now.minute == 0:
        if not sent_weekly:
            send_weekly_bias()
            sent_weekly = True
    else:
        if not (now.weekday() == 0 and now.hour == 6):
            sent_weekly = False
    time.sleep(30)
