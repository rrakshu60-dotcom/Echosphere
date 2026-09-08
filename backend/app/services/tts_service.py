import os
import struct
import wave
import logging

logger = logging.getLogger("echosphere.tts")

STATIC_AUDIO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static",
    "audio_streams",
)


def ensure_audio_dir_exists():
    try:
        os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)
    except Exception:
        pass


def generate_synthesized_wav_fallback(file_path: str, text: str):
    """
    Generates a lightweight standard WAV file with tone bursts representing speech,
    ensuring a valid playable audio file exists even if internet connectivity is offline.
    """
    sample_rate = 16000
    duration_per_word = 0.35
    words = text.split()
    total_duration = max(1.5, len(words) * duration_per_word)
    num_samples = int(sample_rate * total_duration)

    with wave.open(file_path, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Generate audio tone pulses
        freq = 440.0  # A4 tone pitch
        samples = []
        import math
        for i in range(num_samples):
            # Pulsing amplitude per word
            word_idx = int((i / sample_rate) / duration_per_word)
            in_word = (i % int(sample_rate * duration_per_word)) < int(sample_rate * 0.25)
            amp = 12000 if (in_word and word_idx < len(words)) else 0
            val = int(amp * math.sin(2 * math.pi * freq * (i / sample_rate)))
            samples.append(struct.pack("<h", val))

        wav_file.writeframes(b"".join(samples))


def generate_announcement_audio_sync(announcement_id: int, text: str) -> dict:
    """
    Synchronously generates text-to-speech audio stream for a given announcement ID.
    Attempts Google TTS (gTTS) first, falling back to clean WAV tone stream if offline.
    """
    ensure_audio_dir_exists()
    mp3_filename = f"announcement_{announcement_id}.mp3"
    wav_filename = f"announcement_{announcement_id}.wav"
    mp3_filepath = os.path.join(STATIC_AUDIO_DIR, mp3_filename)
    wav_filepath = os.path.join(STATIC_AUDIO_DIR, wav_filename)

    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(mp3_filepath)
        logger.info(f"gTTS audio stream generated successfully: {mp3_filepath}")
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
        }
    except Exception as e:
        logger.warning(f"gTTS network generation failed: {e}. Generating offline WAV fallback.")
        generate_synthesized_wav_fallback(wav_filepath, text)
        return {
            "file_name": wav_filename,
            "file_path": wav_filepath,
            "url_path": f"/static/audio_streams/{wav_filename}",
            "type": "wav",
        }


async def generate_announcement_audio(announcement_id: int, text: str) -> dict:
    """
    Async wrapper for announcement audio generation.
    """
    return generate_announcement_audio_sync(announcement_id, text)

