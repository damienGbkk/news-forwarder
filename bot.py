import discord
import aiohttp
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DISCORD_CHANNEL_NAME = "general"

async def send_to_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()

class NewsForwarder(discord.Client):
    async def on_ready(self):
        print(f"Bot connecté : {self.user}")

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.name != DISCORD_CHANNEL_NAME:
            return

        text = f"📰 <b>{message.author.display_name}</b>\n{message.content}"
        await send_to_telegram(text)

intents = discord.Intents.default()
intents.message_content = True

client = NewsForwarder(intents=intents)
client.run(os.environ.get("DISCORD_TOKEN"))
