# bot/main.py

import asyncio
import logging
import os # For os.path.exists and os.makedirs
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler

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
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


async def run_bot():
    """Initializes and runs the Pyrogram bot."""
    
    if not os.path.exists(TEMP_DOWNLOAD_DIR):
        try:
            os.makedirs(TEMP_DOWNLOAD_DIR)
            logger.info(f"Created temporary download directory from main: {TEMP_DOWNLOAD_DIR}")
        except OSError as e:
            logger.critical(f"Could not create TEMP_DOWNLOAD_DIR from main: {e}. Exiting.")
            return

    app = Client(
        SESSION_NAME, 
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    # Register command handlers CORRECTLY
    app.add_handler(MessageHandler(start_command_handler, filters.command("start") & filters.private))
    app.add_handler(MessageHandler(process_history_command_handler, filters.command("processhistory") & filters.private))
    
    # Register message handler for direct files CORRECTLY
    # This handles private messages that are media and NOT commands handled above.
    app.add_handler(MessageHandler(
        handle_direct_file_private_message,
        filters.private & 
        (filters.video | filters.audio | filters.document) # Removed the problematic ~filters.command()
    ))
    
    try:
        logger.info("Starting bot...")
        await app.start()
        me = await app.get_me()
        logger.info(f"Bot @{me.username} (ID: {me.id}) is now online!")
        await asyncio.Event().wait()
    except Exception as e:
        logger.critical(f"Critical error during bot startup or runtime: {e}", exc_info=True)
    finally:
        if app.is_initialized: 
            logger.info("Stopping bot...")
            await app.stop()
            logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Failed to run bot from __main__: {e}", exc_info=True)