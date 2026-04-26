import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FRED_API_KEY = os.environ.get("FRED_API_KEY")

sent_london = False
sent_ny = False

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
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        return round(data["chart"]["result"][0]["meta"]["regularMarketPrice"], 2)
    except:
        return None

def get_tips():
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DFII10&api_key={FRED_API_KEY}&sort_order=desc&limit=1&file_type=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return round(float(data["observations"][0]["value"]), 2)
    except:
        return None

def get_verdict(tips, dxy, vix, gsr):
    bull = 0
    bear = 0
    details = []

    if tips is not None:
        if tips < 0:
            bull += 2
            details.append("🟢 Taux reels negatifs -> favorable Gold")
        elif tips < 1.5:
            bull += 1
            details.append("🟡 Taux reels bas -> neutre/bullish Gold")
        else:
            bear += 2
            details.append("🔴 Taux reels eleves -> defavorable Gold")

    if dxy is not None:
        if dxy < 99:
            bull += 2
            details.append("🟢 DXY faible -> favorable Gold")
        elif dxy > 101:
            bear += 2
            details.append("🔴 DXY fort -> defavorable Gold")
        else:
            bull += 1
            details.append("🟡 DXY neutre")

    if vix is not None:
        if vix > 25:
            details.append("⚠️ VIX eleve -> volatilite forte, prudence")
        else:
            bull += 1
            details.append("🟢 VIX bas -> risk-on")

    if gsr is not None:
        if gsr < 80:
            bull += 1
            details.append("🟢 Gold/Silver ratio bas -> Silver surperforme -> risk-on confirme")
        elif gsr > 90:
            bear += 1
            details.append("🔴 Gold/Silver ratio eleve -> Silver sous-performe -> risk-off")
        else:
            details.append("🟡 Gold/Silver ratio neutre")

    if bull > bear + 1:
        verdict = "🟢 GOLD BULLISH"
    elif bear > bull + 1:
        verdict = "🔴 GOLD BEARISH"
    else:
        verdict = "🟡 GOLD NEUTRE - pas de biais clair"

    return verdict, "\n".join(details)

def send_context(session_name):
    gold = get_price("GC=F")
    silver = get_price("SI=F")
    dxy = get_price("DX-Y.NYB")
    vix = get_price("^VIX")
    tips = get_tips()

    gsr = None
    if gold and silver and silver > 0:
        gsr = round(gold / silver, 2)

    verdict, details = get_verdict(tips, dxy, vix, gsr)

    msg = (
        f"🌍 {session_name} OPEN - Market Context\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"GOLD: {gold} | SILVER: {silver}\n"
        f"DXY: {dxy} | VIX: {vix}\n"
        f"TIPS 10Y: {tips}% | Gold/Silver: {gsr}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{details}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{verdict}"
    )
    send_telegram(msg)
    print(f"{session_name} context sent", flush=True)

print("Market context started", flush=True)

while True:
    now = datetime.now(timezone.utc)
    hour = now.hour
    minute = now.minute

    if hour == 7 and minute == 0:
        if not sent_london:
            send_context("LONDON")
            sent_london = True
    else:
        if hour != 7:
            sent_london = False

    if hour == 12 and minute == 0:
        if not sent_ny:
            send_context("NEW YORK")
            sent_ny = True
    else:
        if hour != 12:
            sent_ny = False

    time.sleep(30)
