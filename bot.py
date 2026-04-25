import sys
print("STEP 1 - Python fonctionne", flush=True)
sys.stdout.flush()

import discord
print("STEP 2 - Discord importé", flush=True)

import os
token = os.environ.get("DISCORD_TOKEN")
print(f"STEP 3 - Token présent: {bool(token)}", flush=True)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"STEP 4 - Bot connecté: {client.user}", flush=True)

print("STEP 5 - Lancement du bot...", flush=True)
client.run(token)
