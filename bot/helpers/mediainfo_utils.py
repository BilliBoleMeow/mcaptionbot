# bot/helpers/mediainfo_utils.py

import subprocess
import json
import logging
import os

logger = logging.getLogger(__name__)

def run_mediainfo(file_path: str) -> dict | None:
    """
    Runs the 'mediainfo' command-line tool on the specified file.
    """
    try:
        command = ["mediainfo", "--Output=JSON", file_path]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"MediaInfo execution error for {file_path}: {e.stderr}")
        return None
    except FileNotFoundError:
        logger.error("'mediainfo' command not found. Ensure it's installed and in PATH.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MediaInfo JSON output for {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in run_mediainfo for {file_path}: {e}")
        return None

def extract_relevant_info(media_info_data: dict) -> str:
    """
    Extracts specific details (video format, audio stream count, audio languages)
    from parsed MediaInfo JSON data.
    """
    if not media_info_data or 'media' not in media_info_data or 'track' not in media_info_data['media']:
        return "Could not extract MediaInfo (no media/track data)."

    tracks = media_info_data['media']['track']
    info_parts = []

    video_track = next((t for t in tracks if t.get('@type') == 'Video'), None)
    if video_track:
        video_format = video_track.get('Format')
        if video_format:
            info_parts.append(f"Video Format: {video_format}")
        else:
            info_parts.append("Video Format: N/A")
    else:
        info_parts.append("Video Track: Not found")

    audio_tracks = [t for t in tracks if t.get('@type') == 'Audio']
    num_audio_streams = len(audio_tracks)
    info_parts.append(f"Audio Streams: {num_audio_streams}")

    if num_audio_streams > 0:
        audio_languages_details = []
        for i, audio_track in enumerate(audio_tracks):
            lang = audio_track.get('Language_String') or audio_track.get('Language')
            if lang:
                lang_simple = lang.split('/')[0].strip()
                audio_languages_details.append(f"Track {i+1}: {lang_simple if lang_simple else 'Unknown'}")
            else:
                audio_languages_details.append(f"Track {i+1}: Unknown")
        if audio_languages_details:
            info_parts.append("Audio Languages:\n  " + "\n  ".join(audio_languages_details))
    
    if not info_parts or (len(info_parts) == 1 and "Not found" in info_parts[0]):
        return "No specific MediaInfo details found."

    formatted_info = []
    for part in info_parts:
        if part.startswith("Audio Languages:"):
            formatted_info.append(part)
        else:
            formatted_info.append(f"- {part}")
    return "\n".join(formatted_info)