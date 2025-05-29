# bot/config.py

import os

# Telegram API Credentials
API_ID = 12345678  # Replace with your API ID from my.telegram.org
API_HASH = "YOUR_API_HASH"  # Replace with your API Hash
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Replace with your BotFather token

# Bot Session Name
SESSION_NAME = "mediainfo_bot_session" # Pyrogram session file will be named this

# Paths
# This assumes the script or entry point (main.py) is run from within the 'bot' directory,
# or that the current working directory is 'mediainfo_telegram_bot' when main.py is run.
# A more robust way if running main.py from the 'bot' directory:
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This should be 'mediainfo_telegram_bot'
TEMP_DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "temp_downloads")

# Ensure temp directory exists
if not os.path.exists(TEMP_DOWNLOAD_DIR):
    try:
        os.makedirs(TEMP_DOWNLOAD_DIR)
        print(f"Created temporary download directory: {TEMP_DOWNLOAD_DIR}")
    except OSError as e:
        print(f"Error creating temporary download directory {TEMP_DOWNLOAD_DIR}: {e}")
        # exit(1) # Decide if fatal

# Logging Configuration
LOG_LEVEL = "INFO" # e.g., DEBUG, INFO, WARNING, ERROR