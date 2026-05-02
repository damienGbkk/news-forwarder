import sys
import os
import requests
import time

print("STEP 1 - Python fonctionne", flush=True)

try:
    import discord
    print("STEP 2 - Discord importe", flush=True)
except Exception as e:
    print(f"STEP 2 FAILED: {e}", flush=True)
    sys.exit(1)

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

recent_messages = {}
DEDUP_WINDOW = 1800

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text
        }, timeout=10)
        print(f"Telegram sent: {r.status_code}", flush=True)
    except Exception as e:
        print(f"Telegram error: {e}", flush=True)

def is_duplicate(text):
    now = time.time()
    keys_to_delete = [k for k, v in recent_messages.items() if now - v > DEDUP_WINDOW]
    for k in keys_to_delete:
        del recent_messages[k]
    msg_key = text[:100]
    if msg_key in recent_messages:
        return True
    recent_messages[msg_key] = now
    return False

def extract_content(message):
    content = message.content or ""
    if message.embeds:
        for embed in message.embeds:
            parts = []
            if embed.title:
                parts.append(embed.title)
            if embed.description:
                parts.append(embed.description)
            for field in embed.fields:
                parts.append(f"{field.name}: {field.value}")
            if embed.footer:
                parts.append(embed.footer.text)
            content = "\n".join(parts)
    return content.strip()

intents = discord.Intents.all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot connecte: {client.user}", flush=True)
    for guild in client.guilds:
        print(f"Serveur: {guild.name}", flush=True)
        for channel in guild.text_channels:
            print(f"  Canal: {channel.name}", flush=True)

@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return
    print(f"Message recu de: {message.author} | webhook: {message.webhook_id}", flush=True)
    content = extract_content(message)
    if content:
        if is_duplicate(content):
            print(f"Duplicate ignore", flush=True)
            return
        send_telegram(content)

print("STEP 3 - Lancement du bot", flush=True)
client.run(DISCORD_TOKEN)
