import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import GroupCallFactory
from pytgcalls.types.input_stream import InputStream
from pytgcalls.types.input_stream.input_url import AudioPiped
from yt_dlp import YoutubeDL
from pyrogram.idle import idle

# ==== CONFIG ====
API_ID = 25178048  # Replace with your API ID
API_HASH = "d2d5ccf4592270fd54ad9e2014c960e7"  # Replace with your API HASH
BOT_TOKEN = "8053754984:AAHZekNdgufuppnYhrc8Mdftfz9e0xbXDrA"  # Replace with your bot token

# ==== INIT ====
app = Client("vcplayer", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = GroupCallFactory(app).get_group_call()

# ==== UTILS ====
def get_audio_stream(query):
    ydl_opts = {
        'format': 'bestaudio[ext=webm][acodec=opus]/bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch1',
        'noplaylist': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info['url'], info['title']

# ==== COMMANDS ====
@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply("Hey! Use /play <song name or YouTube URL> in a group VC to start music!")

@app.on_message(filters.command("play") & filters.group)
async def play(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/play <song name or URL>`", quote=True)

    query = message.text.split(maxsplit=1)[1]
    msg = await message.reply("🔍 Searching for the song...", quote=True)

    try:
        url, title = get_audio_stream(query)
    except Exception as e:
        return await msg.edit(f"❌ Failed to fetch audio:\n`{e}`")

    try:
        await pytgcalls.join_group_call(
            message.chat.id,
            InputStream(AudioPiped(url)),
        )
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸ Pause", callback_data="pause"),
             InlineKeyboardButton("▶️ Resume", callback_data="resume")],
            [InlineKeyboardButton("⏭ Skip", callback_data="skip"),
             InlineKeyboardButton("⏹ Stop", callback_data="stop")]
        ])
        await msg.edit(f"▶️ Now Playing: **{title}**", reply_markup=buttons)
    except Exception as e:
        await msg.edit(f"❌ Error joining VC:\n`{e}`")

@app.on_message(filters.command("pause") & filters.group)
async def pause(_, message: Message):
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("⏸ Paused")
    except Exception as e:
        await message.reply(f"❌ Error:\n`{e}`")

@app.on_message(filters.command("resume") & filters.group)
async def resume(_, message: Message):
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("▶️ Resumed")
    except Exception as e:
        await message.reply(f"❌ Error:\n`{e}`")

@app.on_message(filters.command("stop") & filters.group)
async def stop(_, message: Message):
    try:
        await pytgcalls.leave_group_call(message.chat.id)
        await message.reply("⏹ Stopped and left VC.")
    except Exception as e:
        await message.reply(f"❌ Error:\n`{e}`")

@app.on_message(filters.command("skip") & filters.group)
async def skip(_, message: Message):
    try:
        await pytgcalls.leave_group_call(message.chat.id)
        await message.reply("⏭ Skipped the song.")
    except Exception as e:
        await message.reply(f"❌ Error:\n`{e}`")

@app.on_message(filters.command("help"))
async def help(_, message: Message):
    await message.reply("""**🎵 VC Music Bot Commands:**

/play <song name or YouTube link> - Play music  
/pause - Pause the music  
/resume - Resume the music  
/stop - Stop the stream  
/skip - Skip current song  
/help - Show help
""")

# ==== BUTTON HANDLERS ====
@app.on_callback_query()
async def callback(_, query):
    data = query.data
    chat_id = query.message.chat.id

    try:
        if data == "pause":
            await pytgcalls.pause_stream(chat_id)
            await query.answer("⏸ Paused")
        elif data == "resume":
            await pytgcalls.resume_stream(chat_id)
            await query.answer("▶️ Resumed")
        elif data == "stop":
            await pytgcalls.leave_group_call(chat_id)
            await query.answer("⏹ Stopped")
            await query.message.edit("⏹ Stopped.")
        elif data == "skip":
            await pytgcalls.leave_group_call(chat_id)
            await query.answer("⏭ Skipped")
            await query.message.edit("⏭ Skipped.")
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)

# ==== RUN ====
async def main():
    await app.start()
    await pytgcalls.start()
    print(">> VC Music Bot Started.")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
