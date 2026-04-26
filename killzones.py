import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

sent = {
    "asian_open": False,
    "london_open": False,
    "london_close": False,
    "ny_open": False,
    "ny_close": False
}

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

def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        return round(data["chart"]["result"][0]["meta"]["regularMarketPrice"], 2)
    except:
        return None

def send_killzone(name, emoji, description, tip):
    gold = get_price("GC=F")
    price_str = f"GOLD: {gold}" if gold else "GOLD: N/A"
    msg = (
        f"{emoji} {name}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{price_str}\n"
        f"{description}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"ICT: {tip}"
    )
    send_telegram(msg)
    print(f"{name} sent", flush=True)

print("Killzones started", flush=True)

while True:
    now = datetime.now(timezone.utc)
    h = now.hour
    m = now.minute
    wd = now.weekday()  # 0=lundi, 6=dimanche

    # Pas le weekend
    if wd >= 5:
        time.sleep(60)
        continue

    # Asian Open — 00h00 UTC = 07h00 Bangkok
    if h == 0 and m == 0:
        if not sent["asian_open"]:
            send_killzone(
                "ASIAN SESSION OPEN",
                "🌏",
                "Session 00h00-06h00 UTC (07h-13h Bangkok)\nVolume faible — range en formation",
                "Identifier le High et Low asiatique. Ce sont les niveaux de liquidite pour London."
            )
            sent["asian_open"] = True
    else:
        if h != 0:
            sent["asian_open"] = False

    # London Killzone — 07h00 UTC = 14h00 Bangkok
    if h == 7 and m == 0:
        if not sent["london_open"]:
            send_killzone(
                "LONDON KILLZONE OPEN",
                "🇬🇧",
                "Killzone 07h00-09h00 UTC (14h-16h Bangkok)\nVolume fort — setups prioritaires",
                "Chercher sweep du High ou Low asiatique + CISD + FVG. C'est ici que les institutionnels positionnent."
            )
            sent["london_open"] = True
    else:
        if h != 7:
            sent["london_open"] = False

    # London Close — 12h00 UTC = 19h00 Bangkok
    if h == 12 and m == 0:
        if not sent["london_close"]:
            send_killzone(
                "LONDON CLOSE / NY OPEN",
                "🇺🇸",
                "Killzone 12h00-14h00 UTC (19h-21h Bangkok)\nOverlap London-NY — volume maximum",
                "Setup le plus puissant de la journee. Liquidity sweep possible sur les highs/lows London."
            )
            sent["london_close"] = True
    else:
        if h != 12:
            sent["london_close"] = False

    # NY Close — 17h00 UTC = 00h00 Bangkok
    if h == 17 and m == 0:
        if not sent["ny_close"]:
            send_killzone(
                "NY SESSION CLOSE",
                "🔔",
                "Fermeture NY 17h00 UTC (00h Bangkok)\nFin de la session active",
                "Eviter les nouvelles positions. Marche peu liquide jusqu'a Asian open."
            )
            sent["ny_close"] = True
    else:
        if h != 17:
            sent["ny_close"] = False

    time.sleep(30)
