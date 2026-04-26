import os
import requests
import time
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

sent_cot = False

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

def fetch_cot():
    # CFTC API - Gold futures (code 088691)
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json?cftc_commodity_code=088691&$order=report_date_as_yyyy_mm_dd DESC&$limit=2"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        if len(data) < 2:
            return None
        
        latest = data[0]
        previous = data[1]
        
        # Non-Commercial (specs)
        nc_long = int(latest.get("noncomm_positions_long_all", 0))
        nc_short = int(latest.get("noncomm_positions_short_all", 0))
        nc_net = nc_long - nc_short
        
        nc_long_prev = int(previous.get("noncomm_positions_long_all", 0))
        nc_short_prev = int(previous.get("noncomm_positions_short_all", 0))
        nc_net_prev = nc_long_prev - nc_short_prev
        
        # Commercial (hedgers)
        comm_long = int(latest.get("comm_positions_long_all", 0))
        comm_short = int(latest.get("comm_positions_short_all", 0))
        comm_net = comm_long - comm_short
        
        nc_change = nc_net - nc_net_prev
        date = latest.get("report_date_as_yyyy_mm_dd", "")[:10]
        
        return {
            "date": date,
            "nc_net": nc_net,
            "nc_change": nc_change,
            "comm_net": comm_net
        }
    except Exception as e:
        print(f"COT fetch error: {e}", flush=True)
        return None

def get_cot_verdict(nc_net, nc_change, comm_net):
    lines = []
    
    # Specs positioning
    if nc_net > 150000:
        lines.append("🔴 Specs massivement LONG → risque de retournement baissier")
    elif nc_net > 80000:
        lines.append("🟡 Specs modérément LONG → biais haussier mais surveiller")
    elif nc_net < 0:
        lines.append("🟢 Specs NET SHORT → potentiel squeeze haussier")
    else:
        lines.append("🟡 Specs positioning neutre")
    
    # Weekly change
    if nc_change > 10000:
        lines.append(f"📈 Specs ont ajouté {nc_change:,} contrats LONG cette semaine → momentum haussier")
    elif nc_change < -10000:
        lines.append(f"📉 Specs ont liquidé {abs(nc_change):,} contrats cette semaine → momentum baissier")
    
    # Commercials (smart money — toujours à contre-courant)
    if comm_net < -200000:
        lines.append("⚠️ Commercials massivement SHORT → hedging institutionnel fort")
    
    # Verdict final
    if nc_net > 150000 or nc_change < -10000:
        verdict = "🔴 <b>COT GOLD BEARISH</b>"
    elif nc_net < 50000 or nc_change > 10000:
        verdict = "🟢 <b>COT GOLD BULLISH</b>"
    else:
        verdict = "🟡 <b>COT GOLD NEUTRE</b>"
    
    return "\n".join(lines), verdict

def send_cot_report():
    data = fetch_cot()
    if not data:
        print("COT data unavailable", flush=True)
        return
    
    details, verdict = get_cot_verdict(data["nc_net"], data["nc_change"], data["comm_net"])
    
    nc_change_str = f"+{data['nc_change']:,}" if data["nc_change"] > 0 else f"{data['nc_change']:,}"
    
    msg = (
        f"📊 <b>COT REPORT — GOLD Futures</b>\n"
        f"📅 Semaine du {data['date']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Specs (Non-Commercial)\n"
        f"Position nette: <b>{data['nc_net']:,}</b> ({nc_change_str} vs semaine dernière)\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{details}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{verdict}"
    )
    send_telegram(msg)
    print("COT report sent", flush=True)

print("COT report started", flush=True)

while True:
    now = datetime.now(timezone.utc)
    # Vendredi (weekday=4) à 20h30 UTC = samedi 3h30 Bangkok
    if now.weekday() == 4 and now.hour == 20 and now.minute == 30:
        if not sent_cot:
            send_cot_report()
            sent_cot = True
    else:
        if not (now.weekday() == 4 and now.hour == 20):
            sent_cot = False
    
    time.sleep(60)
