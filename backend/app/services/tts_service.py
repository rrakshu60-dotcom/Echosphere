import os
import re
import wave
import asyncio
import logging
import hashlib
import concurrent.futures
from typing import Tuple, Dict, Any, Optional

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


def run_coroutine_sync(coro, timeout: float = 30.0):
    """
    Safely executes an async coroutine from synchronous code,
    handling nested event loops (e.g. inside FastAPI / Uvicorn worker threads)
    without raising 'RuntimeError: asyncio.run() cannot be called from a running event loop'.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result(timeout=timeout)
    else:
        return asyncio.run(coro)


def is_legacy_beep_file(file_path: str) -> bool:
    """
    Identifies legacy dummy tone-burst beep files (strictly 1-channel, 16000Hz).
    These files must be purged and replaced with real human spoken words.
    """
    if not file_path or not os.path.exists(file_path) or not file_path.endswith(".wav"):
        return False
    try:
        with wave.open(file_path, "rb") as wf:
            if wf.getnchannels() == 1 and wf.getframerate() == 16000:
                return True
    except Exception:
        pass
    return False


def generate_offline_speech_pyttsx3(file_path: str, text: str, gender: str = "female") -> bool:
    """
    Synthesizes natural spoken words offline using pyttsx3 (SAPI5 on Windows / eSpeak on Linux).
    Outputs a valid WAV file containing actual human spoken words (NEVER beeps).
    """
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        if isinstance(voices, (list, tuple)):
            target_gender = "female" if "female" in gender.lower() else "male"
            selected_v = None
            for v in voices:
                v_name = (getattr(v, "name", "") or "").lower()
                v_id = (getattr(v, "id", "") or "").lower()
                if target_gender == "female" and any(k in v_name or k in v_id for k in ["zira", "female", "eva", "hazel", "heera"]):
                    selected_v = v.id
                    break
                elif target_gender == "male" and any(k in v_name or k in v_id for k in ["david", "male", "mark", "george", "ravi"]):
                    selected_v = v.id
                    break
            if selected_v:
                engine.setProperty("voice", selected_v)
        engine.setProperty("rate", 160)
        engine.save_to_file(text, file_path)
        engine.runAndWait()
        return os.path.exists(file_path) and os.path.getsize(file_path) > 1024
    except Exception as e:
        logger.warning(f"pyttsx3 offline speech synthesis error: {e}")
        return False


def clean_text_for_speech(text: str) -> str:
    """
    Strips raw markdown syntax, action tags, asterisks, and symbols
    so the speech engine outputs clear, natural human speech.
    """
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
    # English Neural Voices
    "american_female": ("af_bella", "a", "en-US-JennyNeural", "American Female (Jenny)"),
    "american_male": ("am_michael", "a", "en-US-GuyNeural", "American Male (Guy)"),
    "indian_female": ("af_heart", "a", "en-IN-NeerjaNeural", "Indian Female (Neerja)"),
    "indian_male": ("am_adam", "a", "en-IN-PrabhatNeural", "Indian Male (Prabhat)"),
    "british_female": ("bf_emma", "b", "en-GB-SoniaNeural", "British Female (Sonia)"),
    "british_male": ("bm_george", "b", "en-GB-RyanNeural", "British Male (Ryan)"),
    # Regional Indian Neural Voices
    "kannada_female": ("af_heart", "a", "kn-IN-SapnaNeural", "Kannada Female (Sapna)"),
    "kannada_male": ("am_adam", "a", "kn-IN-GaganNeural", "Kannada Male (Gagan)"),
    "hindi_female": ("af_heart", "a", "hi-IN-SwaraNeural", "Hindi Female (Swara)"),
    "hindi_male": ("am_adam", "a", "hi-IN-MadhurNeural", "Hindi Male (Madhur)"),
    "telugu_female": ("af_heart", "a", "te-IN-ShrutiNeural", "Telugu Female (Shruti)"),
    "telugu_male": ("am_adam", "a", "te-IN-MohanNeural", "Telugu Male (Mohan)"),
    "tamil_female": ("af_heart", "a", "ta-IN-PallaviNeural", "Tamil Female (Pallavi)"),
    "tamil_male": ("am_adam", "a", "ta-IN-ValluvarNeural", "Tamil Male (Valluvar)"),
}


def resolve_voice_profile(gender: str = "female", accent: str = "american", voice_preset: Optional[str] = None) -> tuple:
    if voice_preset and voice_preset.lower() in VOICE_PROFILES:
        return VOICE_PROFILES[voice_preset.lower()]
    g = "male" if "male" in gender.lower() and "female" not in gender.lower() else "female"
    a_lower = accent.lower()
    acc = "american"
    if "kannada" in a_lower or a_lower == "kn":
        acc = "kannada"
    elif "hindi" in a_lower or a_lower == "hi":
        acc = "hindi"
    elif "telugu" in a_lower or a_lower == "te":
        acc = "telugu"
    elif "tamil" in a_lower or a_lower == "ta":
        acc = "tamil"
    elif "indian" in a_lower or a_lower == "in":
        acc = "indian"
    elif "brit" in a_lower or "uk" in a_lower or "gb" in a_lower:
        acc = "british"
    key = f"{acc}_{g}"
    return VOICE_PROFILES.get(key, VOICE_PROFILES["american_female"])


_kokoro_pipelines = {}
_kokoro_lock = None


def get_kokoro_pipeline(lang_code: str = "a"):
    """Returns a thread-safe cached Kokoro-82M pipeline instance if installed."""
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
    accent: str = "american",
    voice_preset: Optional[str] = None,
    is_summary: bool = False,
    include_chime: bool = True,
    chime_type: Optional[str] = None,
    priority: str = "NORMAL",
    category: str = "General",
    emergency_level: str = "NORMAL",
) -> dict:
    """
    Synchronously generates text-to-speech audio for a given announcement ID.
    Supports multi-tier speech generation:
    1. Kokoro-82M (if installed)
    2. Microsoft Edge-TTS (ultra-high fidelity neural cloud)
    3. Google gTTS (cloud fallback)
    4. pyttsx3 (100% offline local spoken speech)
    NEVER emits beep tones or dummy sinusoidal wav pulses.
    """
    ensure_audio_dir_exists()
    from app.services.chime_service import resolve_contextual_chime, generate_chime_pcm, prepend_chime_to_wav_file

    selected_chime = chime_type or resolve_contextual_chime(
        priority=priority,
        category=category,
        emergency_level=emergency_level,
        content=text,
    )

    kok_voice, kok_lang, edge_voice, voice_name = resolve_voice_profile(gender, accent, voice_preset)
    
    tag = f"{accent.lower()}_{gender.lower()}"
    if is_summary:
        tag += "_summary"
    if include_chime:
        tag += f"_{selected_chime}"
    else:
        tag += "_nochime"

    mp3_filename = f"announcement_{announcement_id}_{tag}.mp3"
    wav_filename = f"announcement_{announcement_id}_{tag}.wav"
    mp3_filepath = os.path.join(STATIC_AUDIO_DIR, mp3_filename)
    wav_filepath = os.path.join(STATIC_AUDIO_DIR, wav_filename)

    # 1. Check WAV cache (and purge legacy beep files if encountered)
    if os.path.exists(wav_filepath):
        if is_legacy_beep_file(wav_filepath):
            logger.info(f"Purging legacy 16kHz beep file: {wav_filepath}")
            try:
                os.remove(wav_filepath)
            except Exception:
                pass
        elif os.path.getsize(wav_filepath) > 1024:
            return {
                "file_name": wav_filename,
                "file_path": wav_filepath,
                "url_path": f"/static/audio_streams/{wav_filename}",
                "type": "wav",
                "engine": f"Neural Speech ({voice_name} - Cached)",
                "voice": voice_name,
                "chime": selected_chime if include_chime else "none",
            }

    # 2. Check MP3 cache
    if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
            "engine": f"Neural Speech ({voice_name} - Cached)",
            "voice": voice_name,
            "chime": selected_chime if include_chime else "none",
        }
    if os.path.exists(wav_filepath) and os.path.getsize(wav_filepath) > 4096:
        return {
            "file_name": wav_filename,
            "file_path": wav_filepath,
            "url_path": f"/static/audio_streams/{wav_filename}",
            "type": "wav",
            "engine": f"Kokoro-82M ({voice_name} - Cached)",
            "voice": voice_name,
            "chime": selected_chime if include_chime else "none",
        }

    speech_text = clean_text_for_speech(text)
    if not speech_text:
        speech_text = "Attention. Official campus announcement broadcast."

    # Tier 1: Try Kokoro-82M (if available)
    if TTS_ENGINE not in ["edge_only", "gtts_only"] and is_kokoro_available():
        try:
            pipeline = get_kokoro_pipeline(kok_lang)
            if pipeline is not None:
                import soundfile as sf
                import numpy as np

                generator = pipeline(speech_text, voice=kok_voice, speed=1.0)
                audio_segments = [audio for gs, ps, audio in generator]
                if audio_segments:
                    speech_audio = np.concatenate(audio_segments)
                    if include_chime:
                        chime_bytes = generate_chime_pcm(selected_chime, sample_rate=24000)
                        chime_float = np.frombuffer(chime_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                        combined = np.concatenate([chime_float, speech_audio])
                    else:
                        combined = speech_audio

                    sf.write(wav_filepath, combined, 24000)
                    duration = round(len(combined) / 24000.0, 2)
                    logger.info(f"Kokoro-82M offline audio generated: {wav_filepath}")
                    return {
                        "file_name": wav_filename,
                        "file_path": wav_filepath,
                        "url_path": f"/static/audio_streams/{wav_filename}",
                        "type": "wav",
                        "engine": f"Kokoro-82M ({voice_name})",
                        "voice": voice_name,
                        "duration_sec": duration,
                        "chime": selected_chime if include_chime else "none",
                    }
        except Exception as k_err:
            logger.debug(f"Kokoro-82M attempt failed: {k_err}. Falling back to Edge-TTS.")

    # Tier 2: Try Microsoft Edge-TTS (Ultra-high quality Neural voices)
    try:
        import edge_tts

        async def _run_edge():
            comm = edge_tts.Communicate(speech_text, edge_voice)
            await comm.save(mp3_filepath)

        run_coroutine_sync(_run_edge(), timeout=25.0)

        if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
            logger.info(f"Edge-TTS neural audio generated ({voice_name}): {mp3_filepath}")
            return {
                "file_name": mp3_filename,
                "file_path": mp3_filepath,
                "url_path": f"/static/audio_streams/{mp3_filename}",
                "type": "mp3",
                "engine": f"Neural Cloud ({voice_name})",
                "voice": voice_name,
                "chime": selected_chime if include_chime else "none",
            }
    except Exception as edge_err:
        logger.debug(f"Edge-TTS attempt failed: {edge_err}. Trying gTTS fallback...")

    # Tier 3: Try Google gTTS (Cloud Fallback)
    try:
        from gtts import gTTS
        tts = gTTS(text=speech_text, lang="en", slow=False)
        tts.save(mp3_filepath)
        if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
            logger.info(f"gTTS audio stream generated: {mp3_filepath}")
            return {
                "file_name": mp3_filename,
                "file_path": mp3_filepath,
                "url_path": f"/static/audio_streams/{mp3_filename}",
                "type": "mp3",
                "engine": "gTTS (Cloud)",
                "voice": "Standard English",
                "chime": selected_chime if include_chime else "none",
            }
    except Exception as g_err:
        logger.debug(f"gTTS attempt failed: {g_err}. Trying offline pyttsx3 speech...")

    # Tier 4: Try pyttsx3 (100% Offline Local Speech Synthesizer)
    try:
        ok = generate_offline_speech_pyttsx3(wav_filepath, speech_text, gender=gender)
        if ok:
            if include_chime:
                temp_wav = wav_filepath + ".chime_tmp.wav"
                if prepend_chime_to_wav_file(wav_filepath, temp_wav, chime_type=selected_chime):
                    os.replace(temp_wav, wav_filepath)
            logger.info(f"pyttsx3 offline speech audio generated: {wav_filepath}")
            return {
                "file_name": wav_filename,
                "file_path": wav_filepath,
                "url_path": f"/static/audio_streams/{wav_filename}",
                "type": "wav",
                "engine": "Offline Speech (pyttsx3)",
                "voice": f"{gender.capitalize()} Offline",
                "chime": selected_chime if include_chime else "none",
            }
    except Exception as p_err:
        logger.error(f"pyttsx3 offline synthesis error: {p_err}")

    # If all tiers fail, raise descriptive error — NEVER write dummy beep pulses
    raise RuntimeError("All speech synthesis engines (Edge-TTS, gTTS, pyttsx3) are currently unavailable.")


async def generate_announcement_audio(
    announcement_id: int,
    text: str,
    gender: str = "female",
    accent: str = "american",
    voice_preset: Optional[str] = None,
    is_summary: bool = False,
) -> dict:
    """Async wrapper for announcement audio generation."""
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
    accent: str = "american",
    voice_preset: Optional[str] = None,
    filename_prefix: str = "ai_speech",
) -> dict:
    """
    Synthesizes arbitrary text into speech using Edge-TTS neural voices,
    with gTTS and pyttsx3 offline fallbacks.
    """
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

    # 1. Check WAV cache
    if os.path.exists(wav_filepath):
        if is_legacy_beep_file(wav_filepath):
            try:
                os.remove(wav_filepath)
            except Exception:
                pass
        elif os.path.getsize(wav_filepath) > 1024:
            return {
                "file_name": wav_filename,
                "file_path": wav_filepath,
                "url_path": f"/static/audio_streams/{wav_filename}",
                "type": "wav",
                "engine": f"Neural Speech ({voice_name} - Cached)",
                "voice": voice_name,
            }

    # 2. Check MP3 cache
    if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
        return {
            "file_name": mp3_filename,
            "file_path": mp3_filepath,
            "url_path": f"/static/audio_streams/{mp3_filename}",
            "type": "mp3",
            "engine": f"Neural Speech ({voice_name} - Cached)",
            "voice": voice_name,
        }

    # Tier 1: Kokoro-82M (if available)
    if TTS_ENGINE not in ["edge_only", "gtts_only"] and is_kokoro_available():
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

    # Tier 2: Edge-TTS (Microsoft Neural Cloud)
    try:
        import edge_tts

        async def _run_edge():
            comm = edge_tts.Communicate(clean_text, edge_voice)
            await comm.save(mp3_filepath)

        run_coroutine_sync(_run_edge(), timeout=25.0)

        if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
            return {
                "file_name": mp3_filename,
                "file_path": mp3_filepath,
                "url_path": f"/static/audio_streams/{mp3_filename}",
                "type": "mp3",
                "engine": f"Edge-TTS ({voice_name})",
                "voice": voice_name,
            }
    except Exception as e_err:
        logger.debug(f"Edge-TTS text synthesis failed: {e_err}")

    # Tier 3: gTTS (Google Cloud)
    try:
        from gtts import gTTS
        tts = gTTS(text=clean_text, lang="en", slow=False)
        tts.save(mp3_filepath)
        if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
            return {
                "file_name": mp3_filename,
                "file_path": mp3_filepath,
                "url_path": f"/static/audio_streams/{mp3_filename}",
                "type": "mp3",
                "engine": "gTTS (Cloud)",
                "voice": "Standard English",
            }
    except Exception as g_err:
        logger.debug(f"gTTS text synthesis failed: {g_err}")

    # Tier 4: pyttsx3 (100% Offline Local Speech)
    try:
        ok = generate_offline_speech_pyttsx3(wav_filepath, clean_text, gender=gender)
        if ok:
            return {
                "file_name": wav_filename,
                "file_path": wav_filepath,
                "url_path": f"/static/audio_streams/{wav_filename}",
                "type": "wav",
                "engine": "Offline Speech (pyttsx3)",
                "voice": f"{gender.capitalize()} Offline",
            }
    except Exception as p_err:
        logger.error(f"pyttsx3 arbitrary text synthesis failed: {p_err}")

    raise RuntimeError("Speech synthesis failed across all engines.")
