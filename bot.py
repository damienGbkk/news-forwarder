import sys
import os
import requests

print("STEP 1 - Python fonctionne", flush=True)
print("STEP 2 - os et requests importés", flush=True)

try:
    import discord
    print("STEP 3 - Discord importé", flush=True)
except Exception as e:
    print(f"STEP 3 FAILED: {e}", flush=True)
    sys.exit(1)

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram response: {r.status_code}", flush=True)
    except Exception as e:
        print(f"Telegram error: {e}", flush=True)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"STEP 4 - Bot connecté: {client.user}", flush=True)

@client.event
async def on_message(message):
    if message.author.bot and message.author.id != client.user.id:
        content = message.content
        if message.embeds:
            for embed in message.embeds:
                parts = []
                if embed.title:
                    parts.append(f"<b>{embed.title}</b>")
                if embed.description:
                    parts.append(embed.description)
                for field in embed.fields:
                    parts.append(f"{field.name}: {field.value}")
                if embed.footer:
                    parts.append(f"<i>{embed.footer.text}</i>")
                content = "\n".join(parts)
        if content:
            print(f"Message reçu: {content[:100]}", flush=True)
            send_telegram(content)

print("STEP 5 - Lancement du bot", flush=True)
client.run(DISCORD_TOKEN)
