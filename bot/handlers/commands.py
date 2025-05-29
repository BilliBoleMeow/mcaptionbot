# bot/handlers/commands.py

import logging
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, ChannelPrivate

from bot.handlers.media_processing import process_single_file_and_edit_caption

logger = logging.getLogger(__name__)

async def start_command_handler(client: Client, message: Message):
    """Handles the /start command in private chat."""
    await message.reply_text(
        "Hi! I add MediaInfo to file captions in channels/groups where I am admin.\n\n"
        "**Commands:**\n"
        "`/processhistory <chat_id_or_username> [limit]` - Scans messages and updates captions.\n"
        "  * `<chat_id_or_username>`: e.g., `@mychannel` or `-1001234567890`\n"
        "  * `[limit]`: Optional. Number of recent messages (e.g., `100`). 0 or omit for all (use with caution!).\n\n"
        "**Example:** `/processhistory @mychannel 50`"
    )

async def process_history_command_handler(client: Client, message: Message):
    """Handles the /processhistory command to scan a chat."""
    command_parts = message.text.split(maxsplit=2)
    if len(command_parts) < 2:
        await message.reply_text(
            "**Usage:** `/processhistory <chat_id_or_username> [limit]`\n"
            "Example: `/processhistory @mychannel 100`"
        )
        return

    target_chat_input = command_parts[1]
    limit = 0
    if len(command_parts) > 2:
        try:
            limit = int(command_parts[2])
            if limit < 0:
                await message.reply_text("Limit cannot be negative. Use 0 or omit for all messages.")
                return
        except ValueError:
            await message.reply_text("Invalid limit. Must be a number.")
            return
    
    try:
        target_chat = await client.get_chat(target_chat_input)
        target_chat_id = target_chat.id
        chat_title = target_chat.title if hasattr(target_chat, 'title') else (target_chat.first_name if hasattr(target_chat, 'first_name') else str(target_chat_id))
        logger.info(f"Target chat resolved: {chat_title} (ID: {target_chat_id})")
    except Exception as e:
        logger.error(f"Could not resolve/access chat '{target_chat_input}': {e}")
        await message.reply_text(f"Could not access/find chat: `{target_chat_input}`. Error: {e}")
        return
    
    status_msg_text = (
        f"🚀 Starting history processing for: `{chat_title}` "
        f"(Limit: {'all' if limit == 0 else limit} msgs).\nThis may take time."
    )
    status_message = await message.reply_text(status_msg_text)
    
    processed_count = 0
    edited_count = 0
    failed_count = 0
    last_status_update = time.time()
    
    try:
        async for hist_msg in client.get_chat_history(target_chat_id, limit=limit):
            processed_count += 1
            
            if hist_msg.video or hist_msg.audio or \
               (hist_msg.document and hist_msg.document.mime_type and \
                ("video/" in hist_msg.document.mime_type or "audio/" in hist_msg.document.mime_type)):
                
                logger.info(f"Found media in msg ID {hist_msg.id} from chat {target_chat_id}")
                if await process_single_file_and_edit_caption(client, hist_msg, hist_msg):
                    edited_count += 1
                else:
                    failed_count += 1
                await asyncio.sleep(3) 

            current_time = time.time()
            if current_time - last_status_update >= 15: # Update every 15 seconds
                progress_text = (
                    f"⏳ Progress for: `{chat_title}`\n"
                    f"Scanned: {processed_count}\n"
                    f"Edited: {edited_count}\n"
                    f"Failed: {failed_count}"
                )
                try:
                    await status_message.edit_text(progress_text)
                    last_status_update = current_time
                except FloodWait as e_flood:
                    logger.warning(f"Flood wait on status update: {e_flood.value}s. Pausing updates.")
                    await asyncio.sleep(e_flood.value + 5)
                    last_status_update = time.time() 
                except Exception as e_stat:
                    logger.error(f"Error updating status: {e_stat}")
                    last_status_update = time.time()

        final_report_text = (
            f"✅ Finished for: `{chat_title}`.\n\n"
            f"Total Scanned: {processed_count}\n"
            f"Edited: {edited_count}\n"
            f"Failed: {failed_count}"
        )
        await status_message.edit_text(final_report_text)

    except (ChatAdminRequired, UserNotParticipant, ChannelPrivate) as e:
        logger.error(f"Permission error for chat {target_chat_id}: {e}")
        await status_message.edit_text(f"❌ Error: No permission for chat `{chat_title}`. Details: {e}")
    except FloodWait as e_main_flood:
        logger.error(f"Critical FloodWait ({e_main_flood.value}s) for {target_chat_id}. Aborting.")
        await status_message.edit_text(f"❌ Operation for `{chat_title}` paused (FloodWait {e_main_flood.value}s). Try later.")
    except Exception as e_main:
        logger.error(f"Unexpected error for chat {target_chat_id}: {e_main}", exc_info=True)
        await status_message.edit_text(f"❌ Unexpected error for `{chat_title}`: {e_main}")