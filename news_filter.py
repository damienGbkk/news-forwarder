import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HIGH_IMPACT_KEYWORDS = [
    "Non-Farm", "NFP", "CPI", "Core CPI", "FOMC", "Fed", "Powell",
    "PPI", "GDP", "Retail Sales", "ISM", "ADP", "Jobless Claims",
    "PCE", "Unemployment", "Interest Rate", "Monetary Policy",
    "Press Conference", "Trump", "sanctions", "tariff"
]

alerted_1h = set()
alerted_15m = set()
alerted_result = set()

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

def is_high_impact(title):
    for keyword in HIGH_IMPACT_KEYWORDS:
        if keyword.lower() in title.lower():
            return True
    return False

def fetch_forex_factory():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        return r.json()
    except Exception as e:
        print(f"ForexFactory fetch error: {e}", flush=True)
        return []

def interpret_result(title, actual, forecast, previous):
    try:
        actual_f = float(actual.replace("%", "").replace("K", "").replace("M", "").replace("B", "").strip())
        forecast_f = float(forecast.replace("%", "").replace("K", "").replace("M", "").replace("B", "").strip())
    except:
        return "🟡 <b>Impact neutre</b> — données insuffisantes pour interpréter"

    title_lower = title.lower()
    diff = actual_f - forecast_f

    # CPI / PPI / PCE / inflation → haut = bearish Gold
    if any(k in title_lower for k in ["cpi", "ppi", "pce", "inflation"]):
        if diff > 0:
            return "🔴 <b>GOLD BEARISH</b>\nInflation au-dessus du forecast → Dollar fort → pression sur Gold"
        elif diff < 0:
            return "🟢 <b>GOLD BULLISH</b>\nInflation sous le forecast → Dollar faible → Gold favorisé"
        else:
            return "🟡 <b>Impact neutre</b>\nInflation conforme au forecast"

    # NFP / ADP / Employment → fort = bearish Gold
    elif any(k in title_lower for k in ["non-farm", "nfp", "adp", "employment", "jobless", "unemployment"]):
        if diff > 0:
            return "🔴 <b>GOLD BEARISH</b>\nEmploi au-dessus du forecast → Fed hawkish → Gold sous pression"
        elif diff < 0:
            return "🟢 <b>GOLD BULLISH</b>\nEmploi sous le forecast → Fed dovish → Gold favorisé"
        else:
            return "🟡 <b>Impact neutre</b>\nEmploi conforme au forecast"

    # GDP → fort = bearish Gold
    elif "gdp" in title_lower:
        if diff > 0:
            return "🔴 <b>GOLD BEARISH</b>\nCroissance forte → Dollar fort → pression sur Gold"
        elif diff < 0:
            return "🟢 <b>GOLD BULLISH</b>\nCroissance faible → risque récession → Gold favorisé"
        else:
            return "🟡 <b>Impact neutre</b>\nGDP conforme au forecast"

    # ISM / Retail Sales → fort = bearish Gold
    elif any(k in title_lower for k in ["ism", "retail"]):
        if diff > 0:
            return "🔴 <b>GOLD BEARISH</b>\nDonnées économiques fortes → Dollar fort"
        elif diff < 0:
            return "🟢 <b>GOLD BULLISH</b>\nDonnées économiques faibles → Dollar sous pression"
        else:
            return "🟡 <b>Impact neutre</b>"

    # FOMC / Interest Rate
    elif any(k in title_lower for k in ["fomc", "interest rate", "fed"]):
        return "⚠️ <b>FOMC/FED</b> — Attendre la conférence de presse avant de trader"

    else:
        if diff > 0:
            return "🔴 <b>Données au-dessus du forecast</b> → tendance Dollar haussière → surveiller Gold"
        elif diff < 0:
            return "🟢 <b>Données sous le forecast</b> → tendance Dollar baissière → surveiller Gold"
        else:
            return "🟡 <b>Impact neutre</b> — conforme au forecast"

def check_events():
    events = fetch_forex_factory()
    now = datetime.now(timezone.utc)

    for event in events:
        if event.get("currency") != "USD":
            continue
        if event.get("impact") != "High":
            continue

        title = event.get("title", "")
        date_str = event.get("date", "")
        time_str = event.get("time", "")

        if not time_str or time_str == "":
            continue

        try:
            event_dt = datetime.strptime(f"{date_str} {time_str}", "%m-%d-%Y %I:%M%p")
            event_dt = event_dt.replace(tzinfo=timezone.utc)
        except:
            continue

        event_id = f"{title}_{date_str}_{time_str}"
        diff = (event_dt - now).total_seconds() / 60

        forecast = event.get("forecast", "N/A")
        previous = event.get("previous", "N/A")

        # Alerte 1h avant
        if 55 <= diff <= 65 and event_id not in alerted_1h:
            msg = (
                f"⚠️ <b>1H WARNING — {title}</b>\n"
                f"🕐 {time_str} UTC\n"
                f"Forecast: {forecast} | Previous: {previous}\n"
                f"🔴 High impact — envisager de fermer les positions"
            )
            send_telegram(msg)
            alerted_1h.add(event_id)
            print(f"1H alert sent: {title}", flush=True)

        # Alerte 15min avant
        if 10 <= diff <= 20 and event_id not in alerted_15m:
            msg = (
                f"🔴 <b>15MIN WARNING — {title}</b>\n"
                f"🕐 {time_str} UTC\n"
                f"Forecast: {forecast} | Previous: {previous}\n"
                f"🚨 Ne pas être en position"
            )
            send_telegram(msg)
            alerted_15m.add(event_id)
            print(f"15M alert sent: {title}", flush=True)

        # Résultat + interprétation
        actual = event.get("actual", "")
        if actual and actual != "" and event_id not in alerted_result and diff < -2:
            interpretation = interpret_result(title, actual, forecast, previous)
            msg = (
                f"✅ <b>RESULT — {title}</b>\n"
                f"Actual: <b>{actual}</b> | Forecast: {forecast} | Previous: {previous}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"{interpretation}"
            )
            send_telegram(msg)
            alerted_result.add(event_id)
            print(f"Result sent: {title}", flush=True)

print("News filter started", flush=True)
while True:
    check_events()
    time.sleep(900)
