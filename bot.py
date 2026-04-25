import discord
import aiohttp
import os
import traceback

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DISCORD_CHANNEL_NAME = "general"

async def send_to_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message[:4000]
    }
    print(f"[TELEGRAM] Envoi vers {TELEGRAM_CHAT_ID}...")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()
            print(f"[TELEGRAM] Réponse : {result}")
            return result

class NewsForwarder(discord.Client):
    async def on_ready(self):
        print(f"Bot connecté : {self.user}")

    async def on_message(self, message):
        print(f"[DISCORD] Message reçu de {message.author} dans #{message.channel.name}")

        if message.author.bot:
            print("[DISCORD] Ignoré : c'est un bot")
            return

        if message.channel.name != DISCORD_CHANNEL_NAME:
            print(f"[DISCORD] Ignoré : canal '{message.channel.name}' != '{DISCORD_CHANNEL_NAME}'")
            return

        text = f"{message.author.display_name}:\n{message.content}"
        print(f"[DISCORD] Forward vers Telegram : {text[:100]}")
        await send_to_telegram(text)

intents = discord.Intents.default()
intents.message_content = True

client = NewsForwarder(intents=intents)

print(f"[STARTUP] Token Discord présent : {bool(os.environ.get('DISCORD_TOKEN'))}")
print(f"[STARTUP] Telegram token présent : {bool(os.environ.get('TELEGRAM_TOKEN'))}")
print(f"[STARTUP] Chat ID : {os.environ.get('TELEGRAM_CHAT_ID')}")

try:
    client.run(os.environ.get("DISCORD_TOKEN"))
except Exception as e:
    print(f"[ERREUR FATALE] {e}")
    traceback.print_exc()
