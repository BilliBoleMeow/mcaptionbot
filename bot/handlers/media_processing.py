# bot/handlers/media_processing.py

import logging
import os
import asyncio
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, ChannelPrivate, BadRequest
from pyrogram import Client, filters 

from bot.helpers.mediainfo_utils import run_mediainfo, extract_relevant_info
from bot.config import TEMP_DOWNLOAD_DIR

logger = logging.getLogger(__name__)

async def process_single_file_and_edit_caption(client: Client, source_message: Message, original_message_to_edit: Message):
    """
    Downloads file from source_message, gets MediaInfo, edits original_message_to_edit's caption.
    """
    file_to_process = source_message.video or source_message.audio or source_message.document
    if not file_to_process:
        logger.warning(f"No file in source_message ID {source_message.id}")
        return False

    original_caption = original_message_to_edit.caption.markdown if original_message_to_edit.caption else ""
    
    is_video = bool(source_message.video)
    is_audio = bool(source_message.audio)
    is_doc_media = bool(source_message.document and source_message.document.mime_type and \
                        ("video/" in source_message.document.mime_type or "audio/" in source_message.document.mime_type))

    if not (is_video or is_audio or is_doc_media):
        logger.info(f"Skipping non-media msg ID {original_message_to_edit.id} (Type: {file_to_process.mime_type if hasattr(file_to_process, 'mime_type') else 'N/A'})")
        return False

    temp_file_path = None
    success = False
    try:
        file_name_attr = getattr(file_to_process, 'file_name', None)
        unique_id = file_to_process.file_unique_id
        base_name = f"{unique_id}_{file_name_attr if file_name_attr else 'unknown_file'}"
        base_name = "".join(c if c.isalnum() or c in ['.', '_', '-'] else '_' for c in base_name)
        temp_file_path = os.path.join(TEMP_DOWNLOAD_DIR, base_name)
        
        logger.info(f"Downloading media from msg ID {source_message.id} (orig ID {original_message_to_edit.id}) to {temp_file_path}")
        downloaded_path = await client.download_media(source_message, file_name=temp_file_path)

        if not downloaded_path or not os.path.exists(str(downloaded_path)):
            logger.error(f"Download failed for msg ID {source_message.id}. Path: {downloaded_path}")
            # Ensure temp_file_path (if partially created or named) is cleaned up if it exists
            if temp_file_path and os.path.exists(temp_file_path) and (not downloaded_path or str(downloaded_path) != temp_file_path):
                 try: os.remove(temp_file_path) # cleanup if download_media created a different name or failed mid-way
                 except OSError: pass
            return False
        temp_file_path = str(downloaded_path) # Use actual downloaded path
        logger.info(f"File for msg ID {original_message_to_edit.id} downloaded to: {temp_file_path}")

        media_info_data = run_mediainfo(temp_file_path)
        if media_info_data:
            extracted_info_str = extract_relevant_info(media_info_data)
            new_caption_parts = []
            current_original_caption = original_caption
            if current_original_caption:
                if "\n--- MediaInfo ---" in current_original_caption:
                    current_original_caption = current_original_caption.split("\n--- MediaInfo ---")[0].strip()
                if current_original_caption:
                    new_caption_parts.append(current_original_caption)
            
            new_caption_parts.append("\n--- MediaInfo ---")
            new_caption_parts.append(extracted_info_str)
            final_caption = "\n".join(new_caption_parts).strip()

            if len(final_caption.encode('utf-8')) > 1024:
                while len(final_caption.encode('utf-8')) > 1019:
                    final_caption = final_caption[:-1]
                final_caption += "..."
            
            if final_caption == (original_message_to_edit.caption.markdown if original_message_to_edit.caption else ""):
                 logger.info(f"Caption for msg ID {original_message_to_edit.id} is already up-to-date.")
                 success = True
            else:
                await client.edit_message_caption(
                    chat_id=original_message_to_edit.chat.id,
                    message_id=original_message_to_edit.id,
                    caption=final_caption
                )
                logger.info(f"Caption edited for msg ID {original_message_to_edit.id} in chat {original_message_to_edit.chat.id}")
                success = True
        else:
            logger.warning(f"Could not retrieve MediaInfo for file from msg ID {original_message_to_edit.id}")
    except FloodWait as e:
        logger.warning(f"Flood wait of {e.value}s for msg {original_message_to_edit.id}. Pausing...")
        await asyncio.sleep(e.value + 5)
    except (ChatAdminRequired, UserNotParticipant, ChannelPrivate) as e:
        logger.error(f"Permission error for chat {original_message_to_edit.chat.id}: {e}.")
        raise
    except BadRequest as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            logger.info(f"Caption for msg ID {original_message_to_edit.id} not modified.")
            success = True
        else:
            logger.error(f"Bad request for msg ID {original_message_to_edit.id}: {e}.")
    except Exception as e:
        logger.error(f"Unexpected error processing file from msg ID {original_message_to_edit.id}: {e}", exc_info=True)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Temp file {temp_file_path} deleted.")
            except OSError as e_del:
                logger.error(f"Error deleting temp file {temp_file_path}: {e_del}")
    return success

async def handle_direct_file_private_message(client: Client, message: Message):
    """Handles direct file uploads to the bot in a private chat."""
    if message.document and not (message.document.mime_type and \
                                  ("video/" in message.document.mime_type or "audio/" in message.document.mime_type)):
        logger.info(f"Skipping direct document (type: {message.document.mime_type}) from user {message.from_user.id}")
        return

    status_msg = await message.reply_text("Processing your file...")
    if await process_single_file_and_edit_caption(client, message, message):
        await status_msg.edit_text("MediaInfo added to caption!")
    else:
        await status_msg.edit_text("Failed to process your file or add MediaInfo.")