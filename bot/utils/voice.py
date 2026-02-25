"""
Voice / Text-to-Speech utility for the ADM Platform Telegram Bot.
Uses gTTS (Google Text-to-Speech) for Hindi + English voice notes.

Usage:
    from utils.voice import send_voice_response, is_voice_enabled, toggle_voice

ADMs can toggle voice on/off with /voice command.
When enabled, every bot response is also sent as a voice note.
"""

import asyncio
import io
import re
import logging
import html as html_lib
from typing import Optional, Dict

from telegram import Update, Message
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# In-memory voice preference per user (telegram_id -> bool)
# Default: OFF (user enables with /voice)
_voice_prefs: Dict[int, bool] = {}


def is_voice_enabled(user_id: int) -> bool:
    """Check if voice is enabled for a user."""
    return _voice_prefs.get(user_id, False)


def toggle_voice(user_id: int) -> bool:
    """Toggle voice on/off for a user. Returns the new state."""
    current = _voice_prefs.get(user_id, False)
    _voice_prefs[user_id] = not current
    return not current


def set_voice(user_id: int, enabled: bool) -> None:
    """Explicitly set voice preference."""
    _voice_prefs[user_id] = enabled


def _strip_html_and_emojis(text: str) -> str:
    """Strip HTML tags and emojis from text for clean TTS."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = html_lib.unescape(text)
    # Remove emoji characters (Unicode ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed chars
        "\U0001f926-\U0001f937"  # additional
        "\U00010000-\U0010ffff"  # supplementary
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "\u2500-\u259F"  # box drawing / block elements
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub(' ', text)
    # Clean up multiple spaces / newlines
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    # Remove sequences of dots
    text = re.sub(r'\.[\s.]+', '. ', text)
    text = text.strip()
    return text


def _detect_language(text: str) -> str:
    """Simple detection: if text has Devanagari chars, use Hindi.
    For mixed Hindi-English (transliterated), use Hindi too since
    gTTS Hindi handles romanized Hindi reasonably well."""
    devanagari = re.compile(r'[\u0900-\u097F]')
    if devanagari.search(text):
        return 'hi'
    # Check for common Hindi words written in English
    hindi_indicators = [
        'aap', 'hai', 'hain', 'kya', 'nahi', 'mein', 'ke liye',
        'ka ', 'ki ', 'ko ', 'se ', 'aur', 'yeh', 'woh', 'karo',
        'kaise', 'kitna', 'sabse', 'bahut', 'achha', 'pehle',
        'baad', 'abhi', 'bhi', 'toh', 'chahiye', 'karein',
        'premium', 'cover', 'plan',
    ]
    text_lower = text.lower()
    hindi_count = sum(1 for word in hindi_indicators if word in text_lower)
    if hindi_count >= 3:
        return 'hi'
    return 'en'


def _generate_tts_audio_sync(text: str, lang: str = 'hi') -> Optional[io.BytesIO]:
    """Generate TTS audio bytes using gTTS (synchronous - run in thread).
    Returns BytesIO or None on error."""
    try:
        from gtts import gTTS

        # Keep text short for fast generation (max ~40 seconds of audio)
        if len(text) > 800:
            text = text[:800] + '. Baaki details text message mein padh sakte hain.'

        tts = gTTS(text=text, lang=lang, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer
    except Exception as e:
        logger.error("TTS generation failed: %s", e, exc_info=True)
        return None


async def send_voice_response(
    message: Message,
    text: str,
    context: Optional[ContextTypes.DEFAULT_TYPE] = None,
) -> None:
    """
    Send a voice note version of the text message if voice is enabled for the user.

    Args:
        message: The Telegram message object (to get chat_id and reply)
        text: The HTML-formatted text that was sent as the text response
        context: Optional context (not used currently but available for future)
    """
    try:
        user_id = message.chat.id
        logger.info("Voice check for user %s: enabled=%s", user_id, is_voice_enabled(user_id))

        if not is_voice_enabled(user_id):
            return

        # Clean text for TTS
        clean_text = _strip_html_and_emojis(text)
        logger.info("Voice TTS clean text length: %d chars", len(clean_text))

        if not clean_text or len(clean_text) < 5:
            logger.info("Voice skipped: text too short after cleaning")
            return

        # Detect language
        lang = _detect_language(clean_text)
        logger.info("Voice TTS lang=%s, generating audio...", lang)

        # Generate audio in a thread to avoid blocking the event loop
        audio = await asyncio.to_thread(_generate_tts_audio_sync, clean_text, lang)

        if not audio:
            logger.warning("Voice TTS: audio generation returned None")
            return

        audio_size = audio.getbuffer().nbytes
        logger.info("Voice TTS: audio generated, %d bytes, sending...", audio_size)

        await message.reply_voice(
            voice=audio,
            caption="\U0001F50A Voice Note",
        )
        logger.info("Voice TTS: sent successfully!")

    except Exception as e:
        logger.error("Voice response failed: %s", e, exc_info=True)


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /voice command - toggle voice on/off."""
    user_id = update.effective_user.id
    logger.info("/voice command from user %s", user_id)

    # Check if args specify on/off
    if context.args:
        arg = context.args[0].lower()
        if arg in ('on', 'enable', 'yes', 'haan'):
            set_voice(user_id, True)
            await update.message.reply_text(
                "\U0001F50A <b>Voice Mode: ON</b>\n\n"
                "Ab har response ke saath voice note bhi milega!\n"
                "Every response will also come as a voice note.\n\n"
                "<i>To turn off: /voice off</i>",
                parse_mode="HTML",
            )
            return
        elif arg in ('off', 'disable', 'no', 'nahi'):
            set_voice(user_id, False)
            await update.message.reply_text(
                "\U0001F507 <b>Voice Mode: OFF</b>\n\n"
                "Voice notes band kar diye.\n"
                "Voice notes disabled.\n\n"
                "<i>To turn on: /voice on</i>",
                parse_mode="HTML",
            )
            return

    # Toggle
    new_state = toggle_voice(user_id)
    if new_state:
        await update.message.reply_text(
            "\U0001F50A <b>Voice Mode: ON</b>\n\n"
            "Ab har response ke saath voice note bhi milega!\n"
            "Every response will also come as a voice note.\n\n"
            "<i>Toggle: /voice</i>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "\U0001F507 <b>Voice Mode: OFF</b>\n\n"
            "Voice notes band kar diye.\n"
            "Voice notes disabled.\n\n"
            "<i>Toggle: /voice</i>",
            parse_mode="HTML",
        )
