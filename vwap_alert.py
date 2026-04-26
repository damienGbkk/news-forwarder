import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

last_vwap_alert = None
last_weekly_vwap = None

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

def get_vwap_data():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]
        timestamps = result["timestamp"]

        highs = quotes["high"]
        lows = quotes["low"]
        closes = quotes["close"]
        volumes = quotes["volume"]

        # Calcul VWAP daily
        cum_vol = 0
        cum_tp_vol = 0
        vwap_values = []

        for i in range(len(closes)):
            if closes[i] and highs[i] and lows[i] and volumes[i]:
                tp = (highs[i] + lows[i] + closes[i]) / 3
                cum_tp_vol += tp * volumes[i]
                cum_vol += volumes[i]
                if cum_vol > 0:
                    vwap_values.append(cum_tp_vol / cum_vol)
                else:
                    vwap_values.append(closes[i])

        if not vwap_values or not closes:
            return None

        current_vwap = round(vwap_values[-1], 2)
        current_price = round(closes[-1], 2)

        # Biais VWAP daily
        daily_bias = "BULLISH" if current_price > current_vwap else "BEARISH"

        return {
            "vwap": current_vwap,
            "price": current_price,
            "daily_bias": daily_bias,
            "distance": round(abs(current_price - current_vwap), 2)
        }
    except Exception as e:
        print(f"VWAP data error: {e}", flush=True)
        return None

def get_weekly_vwap():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1h&range=5d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]
        timestamps = result["timestamp"]

        highs = quotes["high"]
        lows = quotes["low"]
        closes = quotes["close"]
        volumes = quotes["volume"]

        now = datetime.now(timezone.utc)
        # Debut de semaine = lundi 00h UTC
        days_since_monday = now.weekday()
        week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = week_start.replace(day=now.day - days_since_monday)

        cum_vol = 0
        cum_tp_vol = 0

        for i in range(len(closes)):
            if not timestamps[i] or not closes[i] or not volumes[i]:
                continue
            dt = datetime.fromtimestamp(timestamps[i], tz=timezone.utc)
            if dt >= week_start:
                if highs[i] and lows[i] and volumes[i]:
                    tp = (highs[i] + lows[i] + closes[i]) / 3
                    cum_tp_vol += tp * volumes[i]
                    cum_vol += volumes[i]

        if cum_vol == 0:
            return None

        weekly_vwap = round(cum_tp_vol / cum_vol, 2)
        return weekly_vwap

    except Exception as e:
        print(f"Weekly VWAP error: {e}", flush=True)
        return None

def is_killzone():
    now = datetime.now(timezone.utc)
    h = now.hour
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

def is_monday():
    return datetime.now(timezone.utc).weekday() == 0

def check_vwap_touch():
    global last_vwap_alert, last_weekly_vwap

    data = get_vwap_data()
    if not data:
        return

    weekly_vwap = get_weekly_vwap()
    price = data["price"]
    daily_vwap = data["vwap"]
    distance = data["distance"]
    daily_bias = data["daily_bias"]

    # Prix proche du Daily VWAP = dans les 2 points
    if distance > 2:
        return

    alert_key = f"{round(daily_vwap)}-{round(price)}"
    if alert_key == last_vwap_alert:
        return

    # Biais Weekly vs Daily
    if weekly_vwap:
        weekly_bias = "BULLISH" if price > weekly_vwap else "BEARISH"
        bias_aligned = weekly_bias == daily_bias
        weekly_str = f"Weekly VWAP: {weekly_vwap} -> biais {weekly_bias}"
    else:
        bias_aligned = None
        weekly_str = "Weekly VWAP: indisponible"

    # Lundi warning
    monday_warning = ""
    if is_monday():
        monday_warning = "ATTENTION: Lundi - biais potentiellement fausse par gap weekend. Observation uniquement."

    # Alignement des biais
    if bias_aligned is False:
        alignment_str = "BIAIS NON ALIGNES - Weekly et Daily en opposition -> PAS DE TRADE"
    elif bias_aligned is True:
        alignment_str = f"Biais alignes - Weekly et Daily tous deux {daily_bias} -> conviction forte"
    else:
        alignment_str = "Verifier biais manuellement"

    # Direction du setup
    if daily_bias == "BULLISH":
        setup_str = "Setup potentiel: LONG\nChercher absorption rouge dans wick inferieure + CVD vert"
    else:
        setup_str = "Setup potentiel: SHORT\nChercher absorption verte dans wick superieure + CVD rouge"

    msg = (
        f"SETUP ROBIN - VWAP TOUCH\n"
        f"========================\n"
        f"Prix: {price} | Daily VWAP: {daily_vwap}\n"
        f"Distance: {distance} pts\n"
        f"{weekly_str}\n"
        f"------------------------\n"
        f"{alignment_str}\n"
        f"------------------------\n"
        f"{setup_str}\n"
        f"------------------------\n"
        f"Checklist:\n"
        f"[ ] CVD signal confirme (HH + LH CVD)\n"
        f"[ ] Absorption forte sur footprint M3/M2\n"
        f"[ ] CVD roule apres absorption\n"
        f"[ ] RR 1:4 atteignable\n"
        f"[ ] Pas de news dans les 30min\n"
        f"------------------------\n"
        f"{monday_warning if monday_warning else 'Bonne chance. Quatre criteres ou rien.'}"
    )

    send_telegram(msg)
    last_vwap_alert = alert_key
    print(f"VWAP touch alert sent: price {price} near VWAP {daily_vwap}", flush=True)

print("VWAP alert started", flush=True)

while True:
    if is_killzone():
        check_vwap_touch()
    time.sleep(60)
