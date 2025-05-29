# bot/main.py

import asyncio
import logging
from pyrogram import Client, filters # Import Client and filters

# Import configurations from bot.config
from bot.config import API_ID, API_HASH, BOT_TOKEN, SESSION_NAME, LOG_LEVEL, TEMP_DOWNLOAD_DIR

# Import handlers from bot.handlers
from bot.handlers.commands import start_command_handler, process_history_command_handler
from bot.handlers.media_processing import handle_direct_file_private_message

# Setup basic logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(), # Output to console
        # You can add logging.FileHandler("bot.log") here if you want file logging
    ]
)
logger = logging.getLogger(__name__)


async def run_bot():
    """Initializes and runs the Pyrogram bot."""
    
    # Ensure TEMP_DOWNLOAD_DIR exists (config.py should also do this, but good to be sure)
    import os
    if not os.path.exists(TEMP_DOWNLOAD_DIR):
        try:
            os.makedirs(TEMP_DOWNLOAD_DIR)
            logger.info(f"Created temporary download directory from main: {TEMP_DOWNLOAD_DIR}")
        except OSError as e:
            logger.critical(f"Could not create TEMP_DOWNLOAD_DIR from main: {e}. Exiting.")
            return


    # Create the Pyrogram Client instance
    # The session name is used to store session data (e.g., mediainfo_bot_session.session)
    # It will be created in the directory where you run this script.
    # If running "python -m bot.main" from project root, session file will be in project root.
    app = Client(
        SESSION_NAME, 
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        # workdir="." # Or specify a workdir if session file needs to be elsewhere
    )

    # Register command handlers
    # Using app.on_message decorator style for Pyrogram
    app.add_handler(filters.command("start") & filters.private)(start_command_handler)
    app.add_handler(filters.command("processhistory") & filters.private)(process_history_command_handler)
    
    # Register message handler for direct files in private chat
    # Ensure it doesn't clash with commands by using ~filters.command
    app.add_handler(
        filters.private & 
        ~filters.command & 
        (filters.video | filters.audio | filters.document)
    )(handle_direct_file_private_message)
    
    try:
        logger.info("Starting bot...")
        await app.start()
        me = await app.get_me()
        logger.info(f"Bot @{me.username} (ID: {me.id}) is now online!")
        await asyncio.Event().wait()  # Keep the bot running indefinitely
    except Exception as e:
        logger.critical(f"Critical error during bot startup or runtime: {e}", exc_info=True)
    finally:
        if app.is_initialized and app.is_connected:
            logger.info("Stopping bot...")
            await app.stop()
            logger.info("Bot stopped.")
        elif app.is_initialized: # If started but not connected (e.g. auth error)
             logger.info("Bot was initialized but not fully connected. Attempting to stop.")
             await app.stop() # Stop to clean up resources
             logger.info("Bot stopped.")


if __name__ == "__main__":
    # This structure is designed to be run as a module from the project root:
    # python -m bot.main
    # Or, if you're in the 'mediainfo_telegram_bot' directory, that command works.
    # If you're inside the 'bot' directory: python main.py
    # (but imports might need adjustment if not using -m)
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Failed to run bot from __main__: {e}", exc_info=True)