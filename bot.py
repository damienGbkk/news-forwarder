import sys
print("STEP 1", flush=True)
import discord
print("STEP 2", flush=True)
import os
print(f"STEP 3 token={bool(os.environ.get('DISCORD_TOKEN'))}", flush=True)
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
@client.event
async def on_ready():
    print(f"STEP 4 {client.user}", flush=True)
print("STEP 5", flush=True)
client.run(os.environ.get("DISCORD_TOKEN"))
