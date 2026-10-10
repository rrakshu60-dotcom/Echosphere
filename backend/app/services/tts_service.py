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
KOKORO_API_URL = os.getenv("KOKORO_API_URL", "").strip().rstrip("/")


def synthesize_remote_kokoro_api(
    text: str,
    voice: str = "af_heart",
    output_path: str = "",
    response_format: str = "mp3",
    timeout: float = 25.0,
) -> bool:
    """
    Synthesizes speech using a dedicated remote Kokoro-82M neural worker (e.g. Hugging Face Spaces
    running Kokoro-FastAPI) via the OpenAI-compatible /v1/audio/speech endpoint.
    Saves high-fidelity audio stream to output_path.
    """
    api_url = os.getenv("KOKORO_API_URL", "").strip().rstrip("/")
    if not api_url:
        return False
    try:
        import requests
        clean = clean_text_for_speech(text)
        if not clean:
            clean = "Attention. Official campus announcement broadcast."

        target_url = f"{api_url}/v1/audio/speech"
        payload = {
            "input": clean,
            "voice": voice or "af_heart",
            "model": "kokoro",
            "response_format": response_format,
        }
        headers = {"Content-Type": "application/json"}
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        resp = requests.post(target_url, json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 200 and len(resp.content) > 1024:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"Kokoro-82M audio generated via remote worker: {output_path} ({len(resp.content)} bytes)")
            return True
        else:
            logger.warning(f"Remote Kokoro worker returned status {resp.status_code}: {resp.text[:150]}")
            return False
    except Exception as e:
        logger.warning(f"Remote Kokoro worker connection error: {e}")
        return False


VOICE_PROFILES = {
    # English Neural Voices
    "american_female": ("af_heart", "a", "en-US-AriaNeural", "American Female"),
    "american_male": ("am_adam", "a", "en-US-ChristopherNeural", "American Male"),
    "indian_female": ("af_heart", "a", "en-IN-NeerjaNeural", "Indian Female"),
    "indian_male": ("am_adam", "a", "en-IN-PrabhatNeural", "Indian Male"),
    "british_female": ("bf_emma", "b", "en-GB-SoniaNeural", "British Female"),
    "british_male": ("bm_george", "b", "en-GB-RyanNeural", "British Male"),
    # Regional Indian Neural Voices
    "kannada_female": ("af_heart", "a", "kn-IN-SapnaNeural", "Kannada Female"),
    "kannada_male": ("am_adam", "a", "kn-IN-GaganNeural", "Kannada Male"),
    "hindi_female": ("af_heart", "a", "hi-IN-SwaraNeural", "Hindi Female"),
    "hindi_male": ("am_adam", "a", "hi-IN-MadhurNeural", "Hindi Male"),
    "telugu_female": ("af_heart", "a", "te-IN-ShrutiNeural", "Telugu Female"),
    "telugu_male": ("am_adam", "a", "te-IN-MohanNeural", "Telugu Male"),
    "tamil_female": ("af_heart", "a", "ta-IN-PallaviNeural", "Tamil Female"),
    "tamil_male": ("am_adam", "a", "ta-IN-ValluvarNeural", "Tamil Male"),
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
_kokoro_onnx_instance = None
_kokoro_onnx_lock = None


def download_kokoro_int8_weights(target_dir: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads lightweight INT8 Kokoro-82M model (~88MB) and voice binaries (~28MB)
    from GitHub Releases into target_dir if not already cached.
    Uses atomic temp files so corrupted downloads never persist.
    """
    try:
        import urllib.request
        os.makedirs(target_dir, exist_ok=True)
        model_path = os.path.join(target_dir, "kokoro-v1.0.int8.onnx")
        voices_path = os.path.join(target_dir, "voices-v1.0.bin")

        base_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
        
        # 1. Download Model if missing or incomplete (< 50MB)
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 50_000_000:
            tmp_m = model_path + ".tmp"
            logger.info("Downloading Kokoro-82M INT8 ONNX neural model (88MB)...")
            urllib.request.urlretrieve(f"{base_url}/kokoro-v1.0.int8.onnx", tmp_m)
            if os.path.exists(tmp_m) and os.path.getsize(tmp_m) > 50_000_000:
                os.replace(tmp_m, model_path)
                logger.info(f"Kokoro-82M INT8 model cached successfully: {model_path}")

        # 2. Download Voices if missing or incomplete (< 15MB)
        if not os.path.exists(voices_path) or os.path.getsize(voices_path) < 15_000_000:
            tmp_v = voices_path + ".tmp"
            logger.info("Downloading Kokoro voice embeddings (28MB)...")
            urllib.request.urlretrieve(f"{base_url}/voices-v1.0.bin", tmp_v)
            if os.path.exists(tmp_v) and os.path.getsize(tmp_v) > 15_000_000:
                os.replace(tmp_v, voices_path)
                logger.info(f"Kokoro voices cached successfully: {voices_path}")

        if os.path.exists(model_path) and os.path.exists(voices_path):
            return model_path, voices_path
    except Exception as dl_err:
        logger.warning(f"Kokoro INT8 weights download error: {dl_err}")
    return None, None


def convert_wav_to_mp3(wav_path: str, mp3_path: str, bitrate: int = 128) -> bool:
    """
    Converts a WAV file to MP3 using lameenc and soundfile/wave.
    Handles IEEE float and standard int16 PCM seamlessly.
    """
    if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
        return False
    try:
        import lameenc
        try:
            import soundfile as sf
            data, sample_rate = sf.read(wav_path, dtype="int16")
            n_channels = 1 if len(data.shape) == 1 else data.shape[1]
            pcm_bytes = data.tobytes()
        except Exception:
            with wave.open(wav_path, "rb") as wf:
                n_channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                pcm_bytes = wf.readframes(wf.getnframes())

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bitrate)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(n_channels)
        encoder.set_quality(5)
        mp3_bytes = encoder.encode(pcm_bytes) + encoder.flush()

        with open(mp3_path, "wb") as f:
            f.write(mp3_bytes)
        return os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 500
    except Exception as e:
        logger.debug(f"convert_wav_to_mp3 note: {e}")
        return False


def get_kokoro_onnx():
    """Returns a thread-safe cached Kokoro-ONNX instance if installed and weights are found or auto-downloaded."""
    is_on_render = bool(os.getenv("RENDER") or os.getenv("IS_RENDER"))
    allow_local_on_render = os.getenv("ENABLE_LOCAL_KOKORO_ON_RENDER", "false").lower() == "true"
    if is_on_render and not allow_local_on_render:
        logger.info(
            "Render 512MB cloud environment detected. Local Kokoro-ONNX disabled to enforce strict 512MB memory boundary. "
            "Set KOKORO_API_URL to route to dedicated 16GB Kokoro worker."
        )
        return None

    global _kokoro_onnx_instance, _kokoro_onnx_lock
    if _kokoro_onnx_lock is None:
        import threading
        _kokoro_onnx_lock = threading.Lock()
    with _kokoro_onnx_lock:
        if _kokoro_onnx_instance is not None:
            return _kokoro_onnx_instance
        try:
            from kokoro_onnx import Kokoro
            import tempfile
            cache_tmp_dir = os.path.join(tempfile.gettempdir(), "kokoro")
            candidate_dirs = [
                cache_tmp_dir,
                os.path.abspath("models/kokoro"),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "models", "kokoro")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models_data", "kokoro")),
                os.path.expanduser("~/.cache/kokoro"),
                "/tmp/kokoro",
            ]
            model_path = None
            voices_path = None
            for d in candidate_dirs:
                m_int8 = os.path.join(d, "kokoro-v1.0.int8.onnx")
                m1 = os.path.join(d, "kokoro-v1.0.onnx")
                m2 = os.path.join(d, "kokoro-v0_19.onnx")
                v1 = os.path.join(d, "voices-v1.0.bin")
                v2 = os.path.join(d, "voices.bin")
                m_chosen = m_int8 if os.path.exists(m_int8) else (m1 if os.path.exists(m1) else (m2 if os.path.exists(m2) else None))
                v_chosen = v1 if os.path.exists(v1) else (v2 if os.path.exists(v2) else None)
                if m_chosen and v_chosen:
                    model_path = m_chosen
                    voices_path = v_chosen
                    break

            # If not found in any candidate directory, auto-download INT8 weights (88MB)
            if not model_path or not voices_path:
                dl_m, dl_v = download_kokoro_int8_weights(cache_tmp_dir)
                if dl_m and dl_v:
                    model_path = dl_m
                    voices_path = dl_v

            if model_path and voices_path:
                try:
                    import onnxruntime as rt
                    sess_options = rt.SessionOptions()
                    sess_options.intra_op_num_threads = 1
                    sess_options.inter_op_num_threads = 1
                    sess_options.execution_mode = rt.ExecutionMode.ORT_SEQUENTIAL
                    sess_options.enable_cpu_mem_arena = False
                    sess_options.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_BASIC
                    session = rt.InferenceSession(model_path, sess_options=sess_options, providers=["CPUExecutionProvider"])
                    _kokoro_onnx_instance = Kokoro.from_session(session, voices_path)
                    logger.info(f"Initialized ultra-low-memory Kokoro-ONNX pipeline from '{model_path}'.")
                except Exception as opt_err:
                    logger.debug(f"from_session note: {opt_err}. Fallback to standard Kokoro...")
                    _kokoro_onnx_instance = Kokoro(model_path, voices_path)
                    logger.info(f"Initialized Kokoro-ONNX pipeline from '{model_path}'.")
                return _kokoro_onnx_instance
        except Exception as e:
            logger.debug(f"Kokoro-ONNX initialization note: {e}")
            return None
    return None


def get_kokoro_pipeline(lang_code: str = "a"):
    """Returns a thread-safe cached Kokoro-82M pipeline instance if installed."""
    is_on_render = bool(os.getenv("RENDER") or os.getenv("IS_RENDER"))
    if is_on_render:
        return None

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
    """Check whether Kokoro neural TTS (Remote Worker, ONNX, or PyTorch) is installed and operational."""
    if bool(os.getenv("KOKORO_API_URL")):
        return True
    if get_kokoro_onnx() is not None:
        return True
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

    # Tier 1: Try Kokoro Neural Engine (Remote AI Worker, ONNX, or PyTorch pipeline)
    if TTS_ENGINE not in ["edge_only", "gtts_only"]:
        # 1A. Dedicated Remote Kokoro-82M Worker (Hugging Face Spaces with 16GB RAM)
        if KOKORO_API_URL:
            # Generate high-fidelity MP3 for streaming to ESP32 and web clients
            if synthesize_remote_kokoro_api(speech_text, voice=kok_voice, output_path=mp3_filepath, response_format="mp3"):
                return {
                    "file_name": mp3_filename,
                    "file_path": mp3_filepath,
                    "url_path": f"/static/audio_streams/{mp3_filename}",
                    "type": "mp3",
                    "engine": f"Kokoro-82M Neural ({voice_name})",
                    "voice": voice_name,
                    "chime": selected_chime if include_chime else "none",
                }

        # 1B. Local Kokoro-ONNX / PyTorch Pipeline
        kok_onnx = get_kokoro_onnx()
        if kok_onnx is not None:
            try:
                import soundfile as sf
                import numpy as np

                v = kok_voice or "af_heart"
                samples, sample_rate = kok_onnx.create(speech_text, voice=v, speed=1.0, lang="en-us")
                if samples is not None and len(samples) > 0:
                    if include_chime:
                        chime_bytes = generate_chime_pcm(selected_chime, sample_rate=sample_rate)
                        chime_float = np.frombuffer(chime_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                        combined = np.concatenate([chime_float, samples])
                    else:
                        combined = samples

                    sf.write(wav_filepath, combined, sample_rate)
                    duration = round(len(combined) / float(sample_rate), 2)
                    logger.info(f"Kokoro-ONNX neural audio generated: {wav_filepath}")

                    # Automatically encode MP3 for low-bandwidth streaming to ESP32 / web
                    has_mp3 = convert_wav_to_mp3(wav_filepath, mp3_filepath)
                    import gc
                    gc.collect()

                    return {
                        "file_name": mp3_filename if has_mp3 else wav_filename,
                        "file_path": mp3_filepath if has_mp3 else wav_filepath,
                        "url_path": f"/static/audio_streams/{mp3_filename if has_mp3 else wav_filename}",
                        "type": "mp3" if has_mp3 else "wav",
                        "engine": f"Kokoro-82M INT8 ({voice_name})",
                        "voice": voice_name,
                        "duration_sec": duration,
                        "chime": selected_chime if include_chime else "none",
                    }
            except Exception as k_err:
                logger.debug(f"Kokoro-ONNX synthesis note: {k_err}. Trying PyTorch pipeline...")

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

    # Tier 5: Contextual institutional chime fallback — guarantees valid audio and zero HTTP 500
    try:
        from app.services.chime_service import get_or_create_chime_wav
        fallback_wav = get_or_create_chime_wav(selected_chime)
        if os.path.exists(fallback_wav) and os.path.getsize(fallback_wav) > 1024:
            has_mp3 = convert_wav_to_mp3(fallback_wav, mp3_filepath)
            return {
                "file_name": mp3_filename if has_mp3 else os.path.basename(fallback_wav),
                "file_path": mp3_filepath if has_mp3 else fallback_wav,
                "url_path": f"/static/audio_streams/{mp3_filename if has_mp3 else os.path.basename(fallback_wav)}",
                "type": "mp3" if has_mp3 else "wav",
                "engine": f"Campus Notice Chime ({selected_chime})",
                "voice": "Institutional Chime",
                "chime": selected_chime,
            }
    except Exception as chime_fallback_err:
        logger.error(f"Chime fallback error: {chime_fallback_err}")

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

    # Tier 1: Kokoro Neural Engine (Remote AI Worker, ONNX, or PyTorch pipeline)
    if TTS_ENGINE not in ["edge_only", "gtts_only"]:
        # 1A. Dedicated Remote Kokoro-82M Worker
        if KOKORO_API_URL:
            if synthesize_remote_kokoro_api(clean_text, voice=kok_voice, output_path=mp3_filepath, response_format="mp3"):
                return {
                    "file_name": mp3_filename,
                    "file_path": mp3_filepath,
                    "url_path": f"/static/audio_streams/{mp3_filename}",
                    "type": "mp3",
                    "engine": f"Kokoro-82M Neural ({voice_name})",
                    "voice": voice_name,
                }

        # 1B. Local Kokoro-ONNX / PyTorch Pipeline
        kok_onnx = get_kokoro_onnx()
        if kok_onnx is not None:
            try:
                import soundfile as sf
                v = kok_voice or "af_heart"
                samples, sample_rate = kok_onnx.create(clean_text, voice=v, speed=1.0, lang="en-us")
                if samples is not None and len(samples) > 0:
                    sf.write(wav_filepath, samples, sample_rate)
                    duration = round(len(samples) / float(sample_rate), 2)
                    has_mp3 = convert_wav_to_mp3(wav_filepath, mp3_filepath)
                    return {
                        "file_name": mp3_filename if has_mp3 else wav_filename,
                        "file_path": mp3_filepath if has_mp3 else wav_filepath,
                        "url_path": f"/static/audio_streams/{mp3_filename if has_mp3 else wav_filename}",
                        "type": "mp3" if has_mp3 else "wav",
                        "engine": f"Kokoro-82M INT8 ({voice_name})",
                        "voice": voice_name,
                        "duration_sec": duration,
                    }
            except Exception as k_err:
                logger.debug(f"Kokoro-ONNX text synthesis note: {k_err}")

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
