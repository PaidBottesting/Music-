import os
import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types.input_stream import AudioPiped
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")  # User account for voice chat
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Bot account for commands
CHAT_ID = int(os.getenv("CHAT_ID"))

# Initialize Pyrogram clients
user_app = Client("user_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)  # For voice chat
bot_app = Client("bot_account", bot_token=BOT_TOKEN)  # For commands
call_handler = PyTgCalls(user_app)  # PyTgCalls uses user account

# Store current stream
current_stream = None

# Helper: Download audio from YouTube
async def get_audio_url(query):
    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': True,
        'quiet': True,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return info['url'], info['title']
        except Exception as e:
            return None, str(e)

# Start PyTgCalls
async def start_call_handler():
    await call_handler.start()

# /play command handler (bot processes command)
@bot_app.on_message(filters.command("play") & filters.group)
async def play_song(client, message):
    global current_stream
    if message.chat.id != CHAT_ID:
        return  # Ignore commands from other groups

    query = " ".join(message.command[1:])
    if not query:
        await message.reply("Please provide a song name or URL!")
        return

    # Check if voice chat is active
    try:
        chat = await user_app.get_chat(CHAT_ID)
        if not chat.is_voice_chat:
            await message.reply("Start a voice chat in the group first!")
            return
    except Exception as e:
        await message.reply(f"Error checking voice chat: {str(e)}")
        return

    # Download audio
    audio_url, title = await get_audio_url(query)
    if not audio_url:
        await message.reply(f"Could not find '{query}': {title}")
        return

    try:
        # Join voice chat with user account
        if not call_handler.is_running:
            await call_handler.join_group_call(
                CHAT_ID,
                AudioPiped(audio_url, stream_type=StreamType.LIVE_STREAM),
            )
            current_stream = title
            await message.reply(f"🎵 Playing: **{title}**")
        else:
            # Update stream
            await call_handler.change_stream(
                CHAT_ID,
                AudioPiped(audio_url, stream_type=StreamType.LIVE_STREAM),
            )
            current_stream = title
            await message.reply(f"🎵 Switched to: **{title}**")
    except Exception as e:
        await message.reply(f"Error playing song: {str(e)}")

# /stop command handler
@bot_app.on_message(filters.command("stop") & filters.group)
async def stop_song(client, message):
    global current_stream
    if message.chat.id != CHAT_ID:
        return

    try:
        await call_handler.leave_group_call(CHAT_ID)
        current_stream = None
        await message.reply("🛑 Stopped and left voice chat.")
    except Exception as e:
        await message.reply(f"Error stopping: {str(e)}")

# Run both clients
async def main():
    await bot_app.start()
    await user_app.start()
    await start_call_handler()
    print("Bot and user account are running...")
    await asyncio.Event().wait()  # Keep running

if __name__ == "__main__":
    asyncio.run(main())