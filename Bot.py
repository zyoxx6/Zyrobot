import discord
import os
import asyncio
from dotenv import load_dotenv
from discord import File, app_commands
from google import generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from flask import Flask, render_template, request
from threading import Thread
import base64, io
import webserver

# 🔐 Load env
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_BOT_TOKEN  = os.getenv("GEMINI_BOT_TOKEN")

# 🌐 Globals
PUBLIC_URL = "https://your-app-name.onrender.com"  # ← set this manually after deploying!
last_request_ch = None

# 🛡️ Gemini
safety_settings = [
    {"category": c, "threshold": HarmBlockThreshold.BLOCK_NONE}
    for c in HarmCategory
    if c != HarmCategory.HARM_CATEGORY_UNSPECIFIED
]
genai.configure(api_key=GEMINI_BOT_TOKEN)
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction="You're a helpful assistant",
    safety_settings=safety_settings
)
chat = model.start_chat(history=[])

# 📡 Discord
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree   = app_commands.CommandTree(client)

# 🌐 Flask
app = Flask(__name__, template_folder="templates")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload_snap", methods=["POST"])
def upload_snap():
    global last_request_ch
    if not last_request_ch:
        return ("No channel set", 400)
    data = request.json
    b64 = data.get("image", "").split(",", 1)[1]
    img = base64.b64decode(b64)
    f = File(fp=io.BytesIO(img), filename="snap.png")
    asyncio.run_coroutine_threadsafe(
        last_request_ch.send("📸 Snap time!", file=f),
        client.loop
    )
    return ("", 204)

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# 🤖 Bot Ready
@client.event
async def on_ready():
    Thread(target=run_flask, daemon=True).start()
    await tree.sync()
    print(f"✅ Logged in as {client.user}")

# 💬 Message Handler
@client.event
async def on_message(msg):
    global last_request_ch
    if msg.author.bot:
        return

    if msg.content.startswith("!ask"):
        q = msg.content[4:].strip()
        if not q:
            return await msg.channel.send("❌ Say somethin', bro.")
        await msg.channel.send("🤖 Thinking...")
        r = await asyncio.get_event_loop().run_in_executor(None, chat.send_message, q)
        return await msg.channel.send(r.text)

    if msg.content.strip().lower() == "!generate":
        last_request_ch = msg.channel
        return await msg.channel.send(f"🔗 Snap & upload here:\n{PUBLIC_URL}/")

# 🛡️ Keep alive for uptime sites
webserver.keep_alive()
client.run(DISCORD_BOT_TOKEN)
