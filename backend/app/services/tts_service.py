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


def clean_text_for_speech(text: str) -> str:
    """
    Strips raw markdown syntax, action tags, asterisks, and symbols
    so the speech engine outputs clear, natural human speech.
    """
    import re
    cleaned = text
    # Strip [[ACTION:...]] tags
    cleaned = re.sub(r'\[\[ACTION:[^\]]+\]\]', '', cleaned)
    # Strip markdown headers (###)
    cleaned = re.sub(r'#{1,6}\s*', '', cleaned)
    # Strip bold/italic asterisks (**)
    cleaned = re.sub(r'\*+', '', cleaned)
    # Strip bullet indicators (- or •)
    cleaned = re.sub(r'^[ \t]*[-•*][ \t]+', '', cleaned, flags=re.MULTILINE)
    # Strip URLs
    cleaned = re.sub(r'https?://\S+', '', cleaned)
    # Clean multiple spaces/newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


TTS_ENGINE = os.getenv("TTS_ENGINE", "kokoro").lower()
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_heart")
KOKORO_LANG = os.getenv("KOKORO_LANG", "a")

_kokoro_pipeline = None
_kokoro_lock = None


def get_kokoro_pipeline():
    """Returns a thread-safe cached Kokoro-82M pipeline instance for ultra-fast offline synthesis."""
    global _kokoro_pipeline, _kokoro_lock
    if _kokoro_lock is None:
        import threading
        _kokoro_lock = threading.Lock()
    with _kokoro_lock:
        if _kokoro_pipeline is None:
            try:
                from kokoro import KPipeline
                _kokoro_pipeline = KPipeline(lang_code=KOKORO_LANG, repo_id="hexgrad/Kokoro-82M")
                logger.info("Initialized and cached Kokoro-82M offline neural TTS pipeline.")
            except Exception as e:
                logger.debug(f"Kokoro initialization error: {e}")
                return None
        return _kokoro_pipeline


def is_kokoro_available() -> bool:
    """Check whether Kokoro-82M offline neural TTS is installed and operational."""
    try:
        pipeline = get_kokoro_pipeline()
        return pipeline is not None
    except Exception:
        return False


def generate_announcement_audio_sync(announcement_id: int, text: str) -> dict:
    """
    Synchronously generates text-to-speech audio stream for a given announcement ID.
    Cleans markdown formatting and attempts Kokoro-82M (100% offline neural), Edge-TTS, and gTTS with robust fallback.
    """
    ensure_audio_dir_exists()
    mp3_filename = f"announcement_{announcement_id}.mp3"
    wav_filename = f"announcement_{announcement_id}.wav"
    mp3_filepath = os.path.join(STATIC_AUDIO_DIR, mp3_filename)
    wav_filepath = os.path.join(STATIC_AUDIO_DIR, wav_filename)

    speech_text = clean_text_for_speech(text)
    if not speech_text:
        speech_text = "Attention. Official campus announcement broadcast."

    # 1. Try Kokoro-82M (100% Offline Neural Speech Synthesis)
    if TTS_ENGINE in ["kokoro", "auto", "offline"]:
        try:
            pipeline = get_kokoro_pipeline()
            if pipeline is not None:
                import soundfile as sf
                import numpy as np

                generator = pipeline(speech_text, voice=KOKORO_VOICE, speed=1.0)
                audio_segments = [audio for gs, ps, audio in generator]
                if audio_segments:
                    combined = np.concatenate(audio_segments)
                    sf.write(wav_filepath, combined, 24000)
                    duration = round(len(combined) / 24000.0, 2)
                    logger.info(f"Kokoro-82M offline neural audio generated successfully ({duration}s): {wav_filepath}")
                    return {
                        "file_name": wav_filename,
                        "file_path": wav_filepath,
                        "url_path": f"/static/audio_streams/{wav_filename}",
                        "type": "wav",
                        "engine": "Kokoro-82M (100% Offline Neural)",
                        "duration_sec": duration
                    }
        except Exception as k_err:
            logger.debug(f"Kokoro-82M attempt skipped/failed: {k_err}. Falling back to Edge-TTS.")

    # 2. Try modern high-fidelity neural TTS (Microsoft Edge-TTS)
    try:
        import asyncio
        import edge_tts

        async def _run_edge():
            comm = edge_tts.Communicate(speech_text, "en-IN-NeerjaNeural")
            await comm.save(mp3_filepath)

        asyncio.run(_run_edge())
        logger.info(f"Edge-TTS neural audio stream generated successfully: {mp3_filepath}")
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
        }
    except Exception as edge_err:
        logger.debug(f"Edge-TTS attempt skipped/failed: {edge_err}. Trying gTTS fallback...")
        try:
            from gtts import gTTS
            tts = gTTS(text=speech_text, lang="en", slow=False)
            tts.save(mp3_filepath)
            logger.info(f"gTTS audio stream generated successfully: {mp3_filepath}")
            return {
                "file_name": mp3_filename,
                "file_path": mp3_filepath,
                "url_path": f"/static/audio_streams/{mp3_filename}",
                "type": "mp3",
            }
        except Exception as e:
            logger.warning(f"Network TTS generation failed: {e}. Generating offline WAV fallback.")
            generate_synthesized_wav_fallback(wav_filepath, speech_text)
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

