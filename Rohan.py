import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from pytube import YouTube
from youtube_search import YoutubeSearch
from pyrogram import Client
from pytgcalls import GroupCallFactory
from lyricsgenius import Genius
import os
import logging

# Configuration
TOKEN = "8053754984:AAHZekNdgufuppnYhrc8Mdftfz9e0xbXDrA"
API_ID = "6435225"
API_HASH = "d2d5ccf4592270fd54ad9e2014c960e7"
GENIUS_TOKEN = "3rob4MPYEzYsAajFAA1L9hhmtYgb_nKfdaAnBC1N"
DOWNLOAD_PATH = "downloads"

queue = []
current_song = None
playlists = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Client("my_account", api_id=API_ID, api_hash=API_HASH)
call_handler = GroupCallFactory(app).get_file_group_call()
genius = Genius(GENIUS_TOKEN)

def start(update, context):
    update.message.reply_text(
        "Welcome to AdvancedMusicBot! 🎵\n"
        "Use /play <song name> to play a song, /queue to see the queue, or /help for more commands."
    )

def help_command(update, context):
    help_text = (
        "🎵 AdvancedMusicBot Commands:\n"
        "/play <song name or URL> - Play a song in voice chat\n"
        "/queue - Show the current queue\n"
        "/skip - Skip the current song\n"
        "/pause - Pause voice chat playback\n"
        "/resume - Resume voice chat playback\n"
        "/stop - Stop playback and clear queue\n"
        "/lyrics <song name> - Get song lyrics\n"
        "/add <song name> - Add a song to your playlist\n"
        "/playlist - View your playlist\n"
        "/help - Show this help message"
    )
    update.message.reply_text(help_text)

def play(update, context):
    global current_song, queue
    query = " ".join(context.args)
    if not query:
        update.message.reply_text("Please provide a song name or URL, e.g., /play Happy")
        return
    
    chat_id = update.message.chat_id
    try:
        video_id = search_youtube(query)
        url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(url)
        
        song = {"title": yt.title, "url": url, "chat_id": chat_id}
        queue.append(song)
        
        if not current_song:
            context.job_queue.run_once(play_next, 0, context=context, chat_id=chat_id)
            update.message.reply_text(f"Now playing: {yt.title}")
        else:
            update.message.reply_text(f"Added '{yt.title}' to the queue. Position: {len(queue)}")
            
    except Exception as e:
        logger.error(f"Error in /play: {e}")
        update.message.reply_text("Sorry, I couldn't find that song. Try again!")

def play_next(context, chat_id):
    global current_song, queue
    if not queue:
        current_song = None
        context.bot.send_message(chat_id=chat_id, text="Queue is empty! Use /play to add songs.")
        return
    
    current_song = queue.pop(0)
    try:
        yt = YouTube(current_song["url"])
        audio = yt.streams.filter(only_audio=True).first()
        audio.download(output_path=DOWNLOAD_PATH, filename="song.mp3")
        
        call_handler.join_group_call(
            current_song["chat_id"],
            f"{DOWNLOAD_PATH}/song.mp3"
        )
        
        os.remove(f"{DOWNLOAD_PATH}/song.mp3")
        
    except Exception as e:
        logger.error(f"Error streaming song: {e}")
        context.bot.send_message(chat_id=chat_id, text="Error streaming song. Skipping...")
        current_song = None
        context.job_queue.run_once(play_next, 0, context=context, chat_id=chat_id)

def queue_command(update, context):
    if not queue and not current_song:
        update.message.reply_text("The queue is empty!")
        return
    
    queue_text = "🎵 Current Queue:\n"
    if current_song:
        queue_text += f"Now Playing: {current_song['title']}\n"
    for i, song in enumerate(queue, 1):
        queue_text += f"{i}. {song['title']}\n"
    update.message.reply_text(queue_text)

def skip(update, context):
    global current_song
    if not current_song:
        update.message.reply_text("Nothing is playing!")
        return
    chat_id = update.message.chat_id
    update.message.reply_text(f"Skipping {current_song['title']}...")
    current_song = None
    call_handler.leave_group_call(chat_id)
    context.job_queue.run_once(play_next, 0, context=context, chat_id=chat_id)

def pause(update, context):
    chat_id = update.message.chat_id
    try:
        call_handler.pause_stream(chat_id)
        update.message.reply_text("Playback paused.")
    except Exception as e:
        logger.error(f"Error pausing: {e}")
        update.message.reply_text("Nothing is playing or pause failed.")

def resume(update, context):
    chat_id = update.message.chat_id
    try:
        call_handler.resume_stream(chat_id)
        update.message.reply_text("Playback resumed.")
    except Exception as e:
        logger.error(f"Error resuming: {e}")
        update.message.reply_text("Nothing is paused or resume failed.")

def stop(update, context):
    global current_song, queue
    chat_id = update.message.chat_id
    current_song = None
    queue = []
    try:
        call_handler.leave_group_call(chat_id)
        update.message.reply_text("Stopped playback and cleared queue.")
    except Exception as e:
        logger.error(f"Error stopping: {e}")
        update.message.reply_text("Nothing is playing.")

def lyrics(update, context):
    query = " ".join(context.args)
    if not query:
        update.message.reply_text("Please provide a song name, e.g., /lyrics Happy")
        return
    
    try:
        song = genius.search_song(query)
        if song:
            lyrics = song.lyrics[:2000]
            update.message.reply_text(lyrics)
        else:
            update.message.reply_text("Lyrics not found.")
    except Exception as e:
        logger.error(f"Error fetching lyrics: {e}")
        update.message.reply_text("Error fetching lyrics. Try again!")

def add_to_playlist(update, context):
    user_id = update.message.from_user.id
    song = " ".join(context.args)
    if not song:
        update.message.reply_text("Please provide a song name, e.g., /add Happy")
        return
    if user_id not in playlists:
        playlists[user_id] = []
    playlists[user_id].append(song)
    update.message.reply_text(f"Added '{song}' to your playlist.")

def show_playlist(update, context):
    user_id = update.message.from_user.id
    if user_id in playlists and playlists[user_id]:
        playlist_text = "Your Playlist:\n" + "\n".join(f"{i+1}. {song}" for i, song in enumerate(playlists[user_id]))
        update.message.reply_text(playlist_text)
    else:
        update.message.reply_text("Your playlist is empty! Use /add to add songs.")

def search_youtube(query):
    search = YoutubeSearch(query, max_results=1).to_dict()
    if search:
        return search[0]['id']
    else:
        raise Exception("No search results found")

def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        update.message.reply_text("Something went wrong. Please try again.")

def main():
    # Build the application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("skip", skip))
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("lyrics", lyrics))
    application.add_handler(CommandHandler("add", add_to_playlist))
    application.add_handler(CommandHandler("playlist", show_playlist))
    
    application.add_error_handler(error_handler)
    
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    
    app.start()
    application.run_polling()
    app.stop()

if __name__ == "__main__":
    main()