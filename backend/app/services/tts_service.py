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

VOICE_PROFILES = {
    # key: (kokoro_voice, kokoro_lang, edge_voice, display_name)
    "indian_female": ("af_heart", "a", "en-IN-NeerjaNeural", "Indian Female (Neerja / Heart)"),
    "indian_male": ("am_adam", "a", "en-IN-PrabhatNeural", "Indian Male (Prabhat / Adam)"),
    "american_female": ("af_bella", "a", "en-US-JennyNeural", "American Female (Bella / Jenny)"),
    "american_male": ("am_michael", "a", "en-US-GuyNeural", "American Male (Guy / Michael)"),
    "british_female": ("bf_emma", "b", "en-GB-SoniaNeural", "British Female (Emma / Sonia)"),
    "british_male": ("bm_george", "b", "en-GB-RyanNeural", "British Male (George / Ryan)"),
}


def resolve_voice_profile(gender: str = "female", accent: str = "indian", voice_preset: str = None) -> tuple:
    if voice_preset and voice_preset.lower() in VOICE_PROFILES:
        return VOICE_PROFILES[voice_preset.lower()]
    g = "male" if "male" in gender.lower() and "female" not in gender.lower() else "female"
    acc = "indian"
    a_lower = accent.lower()
    if "americ" in a_lower or "us" in a_lower:
        acc = "american"
    elif "brit" in a_lower or "uk" in a_lower or "gb" in a_lower:
        acc = "british"
    key = f"{acc}_{g}"
    return VOICE_PROFILES.get(key, VOICE_PROFILES["indian_female"])


_kokoro_pipelines = {}
_kokoro_lock = None


def get_kokoro_pipeline(lang_code: str = "a"):
    """Returns a thread-safe cached Kokoro-82M pipeline instance for ultra-fast offline synthesis."""
    global _kokoro_pipelines, _kokoro_lock
    if _kokoro_lock is None:
        import threading
        _kokoro_lock = threading.Lock()
    with _kokoro_lock:
        if lang_code not in _kokoro_pipelines:
            try:
                from kokoro import KPipeline
                _kokoro_pipelines[lang_code] = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M")
                logger.info(f"Initialized Kokoro-82M offline neural TTS pipeline (lang='{lang_code}').")
            except Exception as e:
                logger.debug(f"Kokoro initialization error (lang='{lang_code}'): {e}")
                return None
        return _kokoro_pipelines.get(lang_code)


def is_kokoro_available() -> bool:
    """Check whether Kokoro-82M offline neural TTS is installed and operational."""
    try:
        pipeline = get_kokoro_pipeline("a")
        return pipeline is not None
    except Exception:
        return False


def generate_announcement_audio_sync(
    announcement_id: int,
    text: str,
    gender: str = "female",
    accent: str = "indian",
    voice_preset: str = None,
    is_summary: bool = False,
) -> dict:
    """
    Synchronously generates text-to-speech audio stream for a given announcement ID.
    Supports male/female voices across Indian, American, and British accents.
    """
    ensure_audio_dir_exists()
    kok_voice, kok_lang, edge_voice, voice_name = resolve_voice_profile(gender, accent, voice_preset)
    
    tag = f"{accent.lower()}_{gender.lower()}"
    if is_summary:
        tag += "_summary"

    mp3_filename = f"announcement_{announcement_id}_{tag}.mp3"
    wav_filename = f"announcement_{announcement_id}_{tag}.wav"
    mp3_filepath = os.path.join(STATIC_AUDIO_DIR, mp3_filename)
    wav_filepath = os.path.join(STATIC_AUDIO_DIR, wav_filename)

    # Check cache
    if os.path.exists(wav_filepath) and os.path.getsize(wav_filepath) > 1024:
        return {
            "file_name": wav_filename,
            "file_path": wav_filepath,
            "url_path": f"/static/audio_streams/{wav_filename}",
            "type": "wav",
            "engine": f"Kokoro-82M ({voice_name} - Cached)",
            "voice": voice_name,
        }
    if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
            "engine": f"Neural TTS ({voice_name} - Cached)",
            "voice": voice_name,
        }

    speech_text = clean_text_for_speech(text)
    if not speech_text:
        speech_text = "Attention. Official campus announcement broadcast."

    # 1. Try Kokoro-82M (100% Offline Neural Speech Synthesis)
    if TTS_ENGINE in ["kokoro", "auto", "offline"]:
        try:
            pipeline = get_kokoro_pipeline(kok_lang)
            if pipeline is not None:
                import soundfile as sf
                import numpy as np

                generator = pipeline(speech_text, voice=kok_voice, speed=1.0)
                audio_segments = [audio for gs, ps, audio in generator]
                if audio_segments:
                    combined = np.concatenate(audio_segments)
                    sf.write(wav_filepath, combined, 24000)
                    duration = round(len(combined) / 24000.0, 2)
                    logger.info(f"Kokoro-82M offline neural audio ({voice_name}, {duration}s): {wav_filepath}")
                    return {
                        "file_name": wav_filename,
                        "file_path": wav_filepath,
                        "url_path": f"/static/audio_streams/{wav_filename}",
                        "type": "wav",
                        "engine": f"Kokoro-82M ({voice_name})",
                        "voice": voice_name,
                        "duration_sec": duration,
                    }
        except Exception as k_err:
            logger.debug(f"Kokoro-82M attempt skipped/failed: {k_err}. Falling back to Edge-TTS.")

    # 2. Try modern high-fidelity neural TTS (Microsoft Edge-TTS)
    try:
        import asyncio
        import edge_tts

        async def _run_edge():
            comm = edge_tts.Communicate(speech_text, edge_voice)
            await comm.save(mp3_filepath)

        asyncio.run(_run_edge())
        logger.info(f"Edge-TTS neural audio stream generated successfully ({voice_name}): {mp3_filepath}")
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
            "engine": f"Neural Cloud ({voice_name})",
            "voice": voice_name,
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
                "engine": "gTTS (Cloud)",
                "voice": "Standard English",
            }
        except Exception as e:
            logger.warning(f"Network TTS generation failed: {e}. Generating offline WAV fallback.")
            generate_synthesized_wav_fallback(wav_filepath, speech_text)
            return {
                "file_name": wav_filename,
                "file_path": wav_filepath,
                "url_path": f"/static/audio_streams/{wav_filename}",
                "type": "wav",
                "engine": "Offline Synthetic WAV",
                "voice": "Synthetic",
            }


async def generate_announcement_audio(
    announcement_id: int,
    text: str,
    gender: str = "female",
    accent: str = "indian",
    voice_preset: str = None,
    is_summary: bool = False,
) -> dict:
    """
    Async wrapper for announcement audio generation.
    """
    return generate_announcement_audio_sync(
        announcement_id=announcement_id,
        text=text,
        gender=gender,
        accent=accent,
        voice_preset=voice_preset,
        is_summary=is_summary,
    )


def synthesize_text_audio(
    text: str,
    gender: str = "female",
    accent: str = "indian",
    voice_preset: str = None,
    filename_prefix: str = "ai_speech",
) -> dict:
    """
    Synthesizes arbitrary text into speech using Kokoro-82M (with Edge-TTS / gTTS fallbacks).
    Supports male/female and Indian, American, and British accents.
    """
    import hashlib
    ensure_audio_dir_exists()
    
    clean_text = clean_text_for_speech(text)
    if not clean_text:
        clean_text = "EchoSphere Intelligent Campus Notification."

    kok_voice, kok_lang, edge_voice, voice_name = resolve_voice_profile(gender, accent, voice_preset)
    tag = f"{accent.lower()}_{gender.lower()}"
    text_hash = hashlib.md5(f"{clean_text}_{tag}".encode("utf-8")).hexdigest()[:12]
    wav_filename = f"{filename_prefix}_{tag}_{text_hash}.wav"
    mp3_filename = f"{filename_prefix}_{tag}_{text_hash}.mp3"
    wav_filepath = os.path.join(STATIC_AUDIO_DIR, wav_filename)
    mp3_filepath = os.path.join(STATIC_AUDIO_DIR, mp3_filename)

    # Check cache first
    if os.path.exists(wav_filepath) and os.path.getsize(wav_filepath) > 1024:
        return {
            "file_name": wav_filename,
            "file_path": wav_filepath,
            "url_path": f"/static/audio_streams/{wav_filename}",
            "type": "wav",
            "engine": f"Kokoro-82M ({voice_name} - Cached)",
            "voice": voice_name,
        }
    if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
            "engine": f"Neural TTS ({voice_name} - Cached)",
            "voice": voice_name,
        }

    # 1. Kokoro-82M
    if TTS_ENGINE in ["kokoro", "auto", "offline"]:
        try:
            pipeline = get_kokoro_pipeline(kok_lang)
            if pipeline is not None:
                import soundfile as sf
                import numpy as np

                generator = pipeline(clean_text, voice=kok_voice, speed=1.0)
                audio_segments = [audio for gs, ps, audio in generator]
                if audio_segments:
                    combined = np.concatenate(audio_segments)
                    sf.write(wav_filepath, combined, 24000)
                    duration = round(len(combined) / 24000.0, 2)
                    logger.info(f"Kokoro-82M synthesized ({voice_name}, {duration}s): {wav_filepath}")
                    return {
                        "file_name": wav_filename,
                        "file_path": wav_filepath,
                        "url_path": f"/static/audio_streams/{wav_filename}",
                        "type": "wav",
                        "engine": f"Kokoro-82M ({voice_name})",
                        "voice": voice_name,
                        "duration_sec": duration,
                    }
        except Exception as k_err:
            logger.debug(f"Kokoro text synthesis fallback: {k_err}")

    # 2. Edge-TTS fallback
    try:
        import asyncio
        import edge_tts

        async def _run_edge():
            comm = edge_tts.Communicate(clean_text, edge_voice)
            await comm.save(mp3_filepath)

        asyncio.run(_run_edge())
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
            "engine": f"Edge-TTS ({voice_name})",
            "voice": voice_name,
        }
    except Exception:
        pass

    # 3. gTTS fallback
    try:
        from gtts import gTTS
        tts = gTTS(text=clean_text, lang="en", slow=False)
        tts.save(mp3_filepath)
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
            "engine": "gTTS (Cloud)",
            "voice": "Standard English",
        }
    except Exception:
        generate_synthesized_wav_fallback(wav_filepath, clean_text)
        return {
            "file_name": wav_filename,
            "file_path": wav_filepath,
            "url_path": f"/static/audio_streams/{wav_filename}",
            "type": "wav",
            "engine": "Offline Synthetic WAV",
            "voice": "Synthetic",
        }



