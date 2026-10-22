import os
import re
import time
import wave
import asyncio
import logging
import hashlib
import queue
import threading
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
KOKORO_API_URL = os.getenv("KOKORO_API_URL", "https://rakshiroxy-echosphere-tts.hf.space").strip().rstrip("/")

# Never hardcode a token here: HF_TOKEN comes from the environment (Render dashboard / local .env).
DEFAULT_HF_TOKEN = None

_cached_gradio_client = None
_cached_gradio_url = None
_cached_gradio_token = None
_openai_endpoint_supported = False
_kokoro_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="KokoroZeroGPU")
_IN_FLIGHT_SYNTHESIS_LOCK = threading.Lock()
# Circuit breaker for the ZeroGPU speech worker: while its free GPU quota is exhausted (or its
# queue is timing out) skip it entirely, so a new notice never waits on a call that will fail.
_KOKORO_UNAVAILABLE_UNTIL = 0.0


def remote_kokoro_enabled() -> bool:
    """
    The free ZeroGPU worker needs ~6s just to get a GPU per call and its daily quota covers only a
    few calls, so it can't give new notices a near-zero gap. It is used only when KOKORO_PRIMARY=true
    (e.g. after moving to a paid GPU or an always-on CPU worker); otherwise the fast neural voice is primary.
    """
    return (os.getenv("KOKORO_PRIMARY", "false").lower() == "true"
            and os.getenv("ENABLE_REMOTE_KOKORO", "true").lower() == "true")
_IN_FLIGHT_SYNTHESIS: dict[str, threading.Event] = {}

_keepalive_thread: Optional[threading.Thread] = None
_keepalive_stop_event = threading.Event()
_last_keepalive_ping_time: Optional[float] = None
_last_keepalive_status: Optional[str] = None


def prewarm_gradio_client(force: bool = False):
    """Pre-initializes Gradio Client in the background to eliminate initial handshake latency."""
    global _cached_gradio_client, _cached_gradio_url, _cached_gradio_token
    api_url = os.getenv("KOKORO_API_URL", KOKORO_API_URL).strip().rstrip("/")
    if not api_url:
        return
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or DEFAULT_HF_TOKEN
    if not force and _cached_gradio_client is not None and _cached_gradio_url == api_url and _cached_gradio_token == hf_token:
        return
    try:
        from gradio_client import Client
        client_kwargs = {"token": hf_token} if hf_token else {}
        try:
            client = Client(api_url, **client_kwargs)
        except TypeError:
            legacy_kwargs = {"hf_token": hf_token} if hf_token else {}
            client = Client(api_url, **legacy_kwargs)
        _cached_gradio_client = client
        _cached_gradio_url = api_url
        _cached_gradio_token = hf_token
        logger.info(f"ZeroGPU Gradio client pre-warmed successfully: {api_url}")

        # No warm-up synthesis here: every ZeroGPU call reserves 60s of the small free daily
        # quota, and warming every 9 minutes used it all up before real notices arrived.
    except Exception as gc_e:
        logger.debug(f"ZeroGPU Gradio client pre-warm note: {gc_e}")


def ping_zerogpu_worker() -> bool:
    """
    Sends a fast, lightweight HTTP GET probe to Hugging Face ZeroGPU Spaces (TTS & Gemma LLM).
    Prevents ZeroGPU containers from spinning down after 15 minutes of inactivity.
    """
    global _last_keepalive_ping_time, _last_keepalive_status
    tts_url = os.getenv("KOKORO_API_URL", KOKORO_API_URL).strip().rstrip("/")
    llm_url = (os.getenv("GEMMA_API_URL") or os.getenv("CAMPUS_LLM_API_URL") or "").strip().rstrip("/")
    if llm_url.endswith("/generate"):
        llm_url = llm_url.rsplit("/generate", 1)[0].rstrip("/")

    target_urls = set(filter(None, [tts_url, llm_url]))
    if not target_urls:
        return False

    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or DEFAULT_HF_TOKEN
    headers = {"User-Agent": "EchoSphere-ZeroGPU-KeepAlive/2.2"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    any_success = False
    status_notes = []

    try:
        import requests
        for api_url in target_urls:
            space_success = False
            for endpoint in ["/health", "/config", "/info", ""]:
                probe_url = f"{api_url}{endpoint}"
                try:
                    resp = requests.get(probe_url, headers=headers, timeout=4.0)
                    if resp.status_code in (200, 302, 307):
                        _last_keepalive_ping_time = time.time()
                        status_notes.append(f"{api_url}: HTTP {resp.status_code}")
                        logger.info(f"ZeroGPU keep-alive ping successful: {probe_url} (HTTP {resp.status_code})")
                        space_success = True
                        any_success = True
                        break
                except Exception:
                    continue
            if not space_success:
                status_notes.append(f"{api_url}: unreachable")
        if status_notes:
            _last_keepalive_status = " | ".join(status_notes)
    except Exception as e:
        logger.debug(f"ZeroGPU keep-alive ping note: {e}")
        _last_keepalive_status = f"Error: {e}"

    # Also pre-warm Gradio client in background
    if any_success:
        try:
            threading.Thread(target=prewarm_gradio_client, daemon=True).start()
        except Exception:
            pass

    return any_success


def _zerogpu_keepalive_loop():
    """
    Background daemon loop that executes every 9 minutes (540s)
    to keep Hugging Face ZeroGPU Spaces perpetually awake and eliminate cold starts.
    """
    logger.info("EchoSphere ZeroGPU Keep-Alive Daemon started (9-minute interval).")
    time.sleep(2)
    ping_zerogpu_worker()
    prewarm_gradio_client()

    while not _keepalive_stop_event.is_set():
        for _ in range(108):
            if _keepalive_stop_event.is_set():
                return
            time.sleep(5)
        ping_zerogpu_worker()


def start_zerogpu_keepalive_daemon():
    """Starts the background ZeroGPU warm-up daemon if not already running."""
    global _keepalive_thread
    if _keepalive_thread is None or not _keepalive_thread.is_alive():
        _keepalive_thread = threading.Thread(
            target=_zerogpu_keepalive_loop,
            daemon=True,
            name="ZeroGPUKeepAliveDaemon",
        )
        _keepalive_thread.start()


def get_zerogpu_health_status() -> dict:
    """Returns diagnostics for the ZeroGPU keep-alive daemon and Kokoro worker."""
    api_url = os.getenv("KOKORO_API_URL", KOKORO_API_URL).strip().rstrip("/")
    return {
        "kokoro_api_url": api_url or None,
        "gradio_client_cached": bool(_cached_gradio_client is not None),
        "keepalive_daemon_active": bool(_keepalive_thread and _keepalive_thread.is_alive()),
        "last_ping_time": _last_keepalive_ping_time,
        "last_ping_status": _last_keepalive_status,
        "fast_fallback_timeout_sec": float(os.getenv("KOKORO_TIMEOUT_SEC", "10.0")),
    }


def synthesize_remote_kokoro_api(
    text: str,
    voice: str = "af_heart",
    output_path: str = "",
    response_format: str = "wav",
    timeout: float = 10.0,
) -> bool:
    """
    Synthesizes speech using a dedicated remote Kokoro-82M neural worker (e.g. Hugging Face Spaces)
    via OpenAI-compatible /v1/audio/speech endpoint or native Gradio ZeroGPU space with client caching.
    Guarantees companion WAV and MP3 files exist on disk for instant ESP32 I2S and web streaming.
    """
    global _cached_gradio_client, _cached_gradio_url, _openai_endpoint_supported

    global _KOKORO_UNAVAILABLE_UNTIL
    api_url = os.getenv("KOKORO_API_URL", KOKORO_API_URL).strip().rstrip("/")
    if not api_url:
        return False
    if time.time() < _KOKORO_UNAVAILABLE_UNTIL:
        return False  # worker known unavailable (quota exhausted / queue timing out): fall back at once

    clean = clean_text_for_speech(text)
    if not clean:
        clean = "Attention. Official campus announcement broadcast."

    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or DEFAULT_HF_TOKEN

    # Fast Probe: Only try OpenAI endpoint if NOT a Gradio/HuggingFace space
    is_hf_space = ("hf.space" in api_url) or ("huggingface.co" in api_url)
    if not is_hf_space and (_openai_endpoint_supported is None or _openai_endpoint_supported):
        try:
            import requests
            target_url = f"{api_url}/v1/audio/speech"
            payload = {
                "input": clean,
                "voice": voice or "af_heart",
                "model": "kokoro",
                "response_format": response_format,
            }
            headers = {"Content-Type": "application/json"}
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"

            resp = requests.post(target_url, json=payload, headers=headers, timeout=min(2.0, timeout))
            if resp.status_code == 200 and len(resp.content) > 1024:
                _openai_endpoint_supported = True
                is_wav = resp.content[:4] == b"RIFF"
                with open(output_path, "wb") as f:
                    f.write(resp.content)

                if is_wav and output_path.endswith(".mp3"):
                    companion_wav = output_path[:-4] + ".wav"
                    with open(companion_wav, "wb") as f:
                        f.write(resp.content)
                    convert_wav_to_mp3(companion_wav, output_path)
                elif not is_wav and output_path.endswith(".wav"):
                    companion_mp3 = output_path[:-4] + ".mp3"
                    with open(companion_mp3, "wb") as f:
                        f.write(resp.content)
                logger.info(f"Kokoro-82M audio generated via remote worker: {output_path} ({len(resp.content)} bytes)")
                return True
            else:
                _openai_endpoint_supported = False
        except Exception as http_err:
            _openai_endpoint_supported = False
            logger.debug(f"OpenAI endpoint call note: {http_err}")

    # Fallback 2: Connect via Gradio Client (native Hugging Face ZeroGPU Gradio Space with persistent client cache)
    # Strict 4.0s timeout ensures zero blocking during ZeroGPU cold-starts, immediately falling back to Edge-TTS.
    try:
        from gradio_client import Client
        import shutil

        # Patch gradio_client schema parsing for Gradio 5 boolean schemas if needed
        try:
            from gradio_client import utils as client_utils
            orig_schema_type = getattr(client_utils, "_json_schema_to_python_type", None)
            if orig_schema_type and not getattr(client_utils, "_echosphere_patched", False):
                def _safe_schema_type(schema):
                    if schema is True or schema is False or not isinstance(schema, dict):
                        return Any
                    return orig_schema_type(schema)
                client_utils._json_schema_to_python_type = _safe_schema_type
                client_utils._echosphere_patched = True
        except Exception:
            pass

        def _execute_gradio_inference():
            global _cached_gradio_client, _cached_gradio_url, _cached_gradio_token
            if _cached_gradio_client is None or _cached_gradio_url != api_url or _cached_gradio_token != hf_token:
                client_kwargs = {"token": hf_token} if hf_token else {}
                try:
                    _cached_gradio_client = Client(api_url, **client_kwargs)
                except TypeError:
                    legacy_kwargs = {"hf_token": hf_token} if hf_token else {}
                    _cached_gradio_client = Client(api_url, **legacy_kwargs)
                _cached_gradio_url = api_url
                _cached_gradio_token = hf_token

            return _cached_gradio_client.predict(
                clean,
                voice or "af_heart",
                1.0,
                api_name="/synthesize",
            )

        future = _kokoro_executor.submit(_execute_gradio_inference)
        audio_path = future.result(timeout=timeout)
        if isinstance(audio_path, dict):
            audio_path = audio_path.get("path")

        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1024:
            with open(audio_path, "rb") as f:
                sample_bytes = f.read(4)
            is_wav = sample_bytes == b"RIFF"

            if output_path.endswith(".wav"):
                if is_wav:
                    shutil.copy(audio_path, output_path)
                    companion_mp3 = output_path[:-4] + ".mp3"
                    convert_wav_to_mp3(output_path, companion_mp3)
                else:
                    companion_mp3 = output_path[:-4] + ".mp3"
                    shutil.copy(audio_path, companion_mp3)
                    try:
                        import miniaudio
                        decoded = miniaudio.mp3_read_file_s16(companion_mp3)
                        miniaudio.wav_write_file(output_path, decoded)
                    except Exception:
                        pass
            else:
                if is_wav:
                    companion_wav = output_path[:-4] + ".wav"
                    shutil.copy(audio_path, companion_wav)
                    convert_wav_to_mp3(companion_wav, output_path)
                else:
                    shutil.copy(audio_path, output_path)
                    companion_wav = output_path[:-4] + ".wav"
                    try:
                        import miniaudio
                        decoded = miniaudio.mp3_read_file_s16(output_path)
                        miniaudio.wav_write_file(companion_wav, decoded)
                    except Exception:
                        pass

            logger.info(f"Kokoro-82M audio generated via Gradio ZeroGPU worker: {output_path}")
            return True
    except concurrent.futures.TimeoutError:
        _KOKORO_UNAVAILABLE_UNTIL = time.time() + 120
        logger.warning(
            f"Kokoro ZeroGPU remote worker latency exceeded {timeout}s cutoff (Space cold-starting or queuing). "
            f"Using the fallback voice for the next 2 minutes."
        )
        return False
    except Exception as g_err:
        msg = str(g_err)
        if "ZeroGPU quota" in msg or "exceeded your" in msg:
            import re as _re
            m = _re.search(r"Try again in (\d+):(\d+):(\d+)", msg)
            wait_s = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))) if m else 3600
            _KOKORO_UNAVAILABLE_UNTIL = time.time() + min(wait_s, 24 * 3600)
            logger.warning(f"ZeroGPU quota exhausted; using the fallback voice for {wait_s // 60} min.")
        else:
            logger.debug(f"Gradio Space client error: {g_err}")
        _cached_gradio_client = None

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


_BACKUP_QUEUE: "queue.Queue[Tuple[str, str, float]]" = queue.Queue()
_BACKUP_WORKER_STARTED = False
_BACKUP_WORKER_LOCK = threading.Lock()
# Wait this long after synthesis before backing up, so a notice that is about to play gets the CPU
_BACKUP_DELAY_SECONDS = 10.0


def _backup_upload_worker() -> None:
    from app.services.cloud_storage_service import CloudStorageService
    from app.services.speaker_playback import any_stream_busy
    while True:
        file_path, file_name, queued_at = _BACKUP_QUEUE.get()
        try:
            time.sleep(max(0.0, queued_at + _BACKUP_DELAY_SECONDS - time.monotonic()))
            while any_stream_busy():
                time.sleep(1.0)
            if not _should_back_up(file_name):
                continue
            CloudStorageService.upload_file(file_path, folder="audio_streams", custom_filename=file_name)
        except Exception as e:
            logger.debug(f"Background cloud backup note: {e}")


def _should_back_up(file_name: str) -> bool:
    """Never back up audio of a notice that has been deleted."""
    match = re.match(r"^announcement_(\d+)(_|\.)", file_name)
    if not match:
        return True
    from app.services.notice_record_service import notice_was_deleted

    return not notice_was_deleted(int(match.group(1)))


def _queue_backup_upload(file_path: str, file_name: str) -> None:
    global _BACKUP_WORKER_STARTED
    with _BACKUP_WORKER_LOCK:
        if not _BACKUP_WORKER_STARTED:
            threading.Thread(target=_backup_upload_worker, daemon=True, name="CloudBackupUploader").start()
            _BACKUP_WORKER_STARTED = True
    _BACKUP_QUEUE.put((file_path, file_name, time.monotonic()))


def _format_audio_result(
    file_name: str,
    file_path: str,
    audio_type: str,
    engine: str,
    voice: str,
    chime: Optional[str] = None,
    duration_sec: Optional[float] = None,
) -> dict:
    """
    Persists synthesized audio to Hugging Face Datasets Git LFS CDN and returns
    both permanent Cloudflare raw CDN URL and local static fallback path.
    """
    public_url = f"/static/audio_streams/{file_name}"
    cdn_url = None
    # Back up to Hugging Face later, one file at a time, while no speaker is streaming
    _queue_backup_upload(file_path, file_name)

    res = {
        "file_name": file_name,
        "file_path": file_path,
        "url_path": f"/static/audio_streams/{file_name}",
        "public_url": public_url,
        "cdn_url": cdn_url,
        "type": audio_type,
        "engine": engine,
        "voice": voice,
    }
    if chime is not None:
        res["chime"] = chime
    if duration_sec is not None:
        res["duration_sec"] = duration_sec
    return res


def generate_announcement_audio_sync(announcement_id: int, text: str, **kwargs) -> dict:
    """Synthesize a notice's audio. If the notice was deleted while this ran, its audio is discarded."""
    result = _generate_announcement_audio(announcement_id, text, **kwargs)
    from app.services.notice_record_service import discard_audio_if_notice_deleted

    discard_audio_if_notice_deleted(announcement_id)
    return result


def _generate_announcement_audio(
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

    # 1. Restore from Hugging Face Git LFS CDN if container local disk was wiped
    try:
        from app.services.cloud_storage_service import CloudStorageService
        if not os.path.exists(wav_filepath) and not os.path.exists(mp3_filepath):
            CloudStorageService.restore_file_from_cdn_if_missing(mp3_filename, folder="audio_streams")
            CloudStorageService.restore_file_from_cdn_if_missing(wav_filename, folder="audio_streams")
    except Exception:
        pass

    # Check WAV cache (and purge legacy beep files if encountered)
    if os.path.exists(wav_filepath):
        if is_legacy_beep_file(wav_filepath):
            logger.info(f"Purging legacy 16kHz beep file: {wav_filepath}")
            try:
                os.remove(wav_filepath)
            except Exception:
                pass
        elif os.path.getsize(wav_filepath) > 1024:
            return _format_audio_result(
                file_name=wav_filename,
                file_path=wav_filepath,
                audio_type="wav",
                engine=f"Kokoro-82M Neural ({voice_name} - Cached)",
                voice=voice_name,
                chime=selected_chime if include_chime else "none",
            )

    # Check MP3 cache
    if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
        return _format_audio_result(
            file_name=mp3_filename,
            file_path=mp3_filepath,
            audio_type="mp3",
            engine=f"Kokoro-82M Neural ({voice_name} - Cached)",
            voice=voice_name,
            chime=selected_chime if include_chime else "none",
        )

    # 1B. Re-use existing speech audio for this notice across all repeat rounds (0ms synthesis!)
    # Only the same voice and only the full notice: a summary is different speech.
    base_nochime_name = f"announcement_{announcement_id}_{accent.lower()}_{gender.lower()}_nochime.wav"
    base_nochime_path = os.path.join(STATIC_AUDIO_DIR, base_nochime_name)
    base_reusable = (not is_summary) and os.path.exists(base_nochime_path) and os.path.getsize(base_nochime_path) > 1024

    if not include_chime and base_reusable:
        return _format_audio_result(
            file_name=base_nochime_name,
            file_path=base_nochime_path,
            audio_type="wav",
            engine=f"Kokoro-82M Neural ({voice_name} - Cached)",
            voice=voice_name,
            chime="none",
        )

    if include_chime and base_reusable:
        if prepend_chime_to_wav_file(base_nochime_path, wav_filepath, chime_type=selected_chime):
            convert_wav_to_mp3(wav_filepath, mp3_filepath)
            return _format_audio_result(
                file_name=wav_filename,
                file_path=wav_filepath,
                audio_type="wav",
                engine=f"Kokoro-82M Neural ({voice_name} - Cached)",
                voice=voice_name,
                chime=selected_chime,
            )

    # Any other cached speech for this exact voice and variant (e.g. a WAV kept under its plain
    # name). Never borrow another voice, the summary, or a file with a chime baked in: that
    # played the wrong voice or a double chime, and copying it in cached the mistake for good.
    try:
        voice_prefix = f"announcement_{announcement_id}_{accent.lower()}_{gender.lower()}"
        if os.path.exists(STATIC_AUDIO_DIR) and not is_summary:
            for f in os.listdir(STATIC_AUDIO_DIR):
                if not (f.startswith(voice_prefix) and f.endswith(".wav")) or "_summary" in f:
                    continue
                if include_chime or "_nochime" not in f:
                    continue
                fp = os.path.join(STATIC_AUDIO_DIR, f)
                if os.path.getsize(fp) > 2048 and not is_legacy_beep_file(fp):
                    return _format_audio_result(
                        file_name=f,
                        file_path=fp,
                        audio_type="wav",
                        engine=f"Kokoro-82M Neural ({voice_name} - Cached)",
                        voice=voice_name,
                        chime="none",
                    )
    except Exception:
        pass

    # In-Flight Synthesis De-duplication: Prevent multiple concurrent requests from hammering ZeroGPU for the same announcement
    synth_key = f"{announcement_id}_{tag}"
    is_waiter = False
    with _IN_FLIGHT_SYNTHESIS_LOCK:
        if synth_key in _IN_FLIGHT_SYNTHESIS:
            event = _IN_FLIGHT_SYNTHESIS[synth_key]
            is_waiter = True
        else:
            event = threading.Event()
            _IN_FLIGHT_SYNTHESIS[synth_key] = event

    if is_waiter:
        event.wait(timeout=5.0)
        if os.path.exists(wav_filepath) and os.path.getsize(wav_filepath) > 1024:
            return _format_audio_result(
                file_name=wav_filename,
                file_path=wav_filepath,
                audio_type="wav",
                engine=f"Kokoro-82M Neural ({voice_name} - Cached)",
                voice=voice_name,
                chime=selected_chime if include_chime else "none",
            )
        elif os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
            return _format_audio_result(
                file_name=mp3_filename,
                file_path=mp3_filepath,
                audio_type="mp3",
                engine=f"Kokoro-82M Neural ({voice_name} - Cached)",
                voice=voice_name,
                chime=selected_chime if include_chime else "none",
            )
    def _release_lock():
        if not is_waiter:
            with _IN_FLIGHT_SYNTHESIS_LOCK:
                event.set()
                _IN_FLIGHT_SYNTHESIS.pop(synth_key, None)

    speech_text = clean_text_for_speech(text)
    if not speech_text:
        speech_text = "Attention. Official campus announcement broadcast."

    # Tier 1: Try Kokoro Neural Engine (Local ONNX first for zero-network instantaneous synthesis)
    if TTS_ENGINE not in ["edge_only", "gtts_only"]:
        # 1A. Local Kokoro-ONNX Pipeline (Sub-second local inference, 100% offline & reliable)
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
                    logger.info(f"Kokoro-ONNX neural audio generated: {wav_filepath} ({duration}s)")

                    # Automatically encode MP3 for low-bandwidth streaming to ESP32 / web
                    has_mp3 = convert_wav_to_mp3(wav_filepath, mp3_filepath)
                    import gc
                    gc.collect()

                    chosen_fn = mp3_filename if has_mp3 else wav_filename
                    chosen_fp = mp3_filepath if has_mp3 else wav_filepath
                    _release_lock()
                    return _format_audio_result(
                        file_name=chosen_fn,
                        file_path=chosen_fp,
                        audio_type="mp3" if has_mp3 else "wav",
                        engine=f"Kokoro-82M INT8 ({voice_name})",
                        voice=voice_name,
                        duration_sec=duration,
                        chime=selected_chime if include_chime else "none",
                    )
            except Exception as k_err:
                logger.debug(f"Kokoro-ONNX synthesis note: {k_err}. Trying remote worker...")

        # 1B. Dedicated Remote Kokoro-82M Worker (Hugging Face ZeroGPU / Space)
        enable_remote = remote_kokoro_enabled()
        remote_timeout = float(os.getenv("KOKORO_TIMEOUT_SEC", "8.0"))
        if KOKORO_API_URL and enable_remote:
            if synthesize_remote_kokoro_api(speech_text, voice=kok_voice, output_path=wav_filepath, response_format="wav", timeout=remote_timeout):
                if include_chime and selected_chime != "none":
                    temp_wav = wav_filepath + ".chime_tmp.wav"
                    if prepend_chime_to_wav_file(wav_filepath, temp_wav, chime_type=selected_chime):
                        os.replace(temp_wav, wav_filepath)
                if not os.path.exists(mp3_filepath) or os.path.getsize(mp3_filepath) < 500:
                    convert_wav_to_mp3(wav_filepath, mp3_filepath)
                chosen_fn = mp3_filename if os.path.exists(mp3_filepath) else wav_filename
                chosen_fp = mp3_filepath if os.path.exists(mp3_filepath) else wav_filepath
                _release_lock()
                return _format_audio_result(
                    file_name=chosen_fn,
                    file_path=chosen_fp,
                    audio_type="mp3" if os.path.exists(mp3_filepath) else "wav",
                    engine=f"Kokoro-82M Neural ({voice_name})",
                    voice=voice_name,
                    chime=selected_chime if include_chime else "none",
                )

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
                    return _format_audio_result(
                        file_name=wav_filename,
                        file_path=wav_filepath,
                        audio_type="wav",
                        engine=f"Kokoro-82M ({voice_name})",
                        voice=voice_name,
                        duration_sec=duration,
                        chime=selected_chime if include_chime else "none",
                    )
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
            # Also decode/write wav_filepath immediately in the pre-generation phase so hardware I2S gets instant WAV!
            try:
                import miniaudio
                decoded = miniaudio.mp3_read_file_s16(mp3_filepath)
                miniaudio.wav_write_file(wav_filepath, decoded)
            except Exception:
                pass
            logger.info(f"Edge-TTS neural audio generated ({voice_name}): {mp3_filepath}")
            _release_lock()
            return _format_audio_result(
                file_name=mp3_filename,
                file_path=mp3_filepath,
                audio_type="mp3",
                engine=f"Neural Cloud ({voice_name})",
                voice=voice_name,
                chime=selected_chime if include_chime else "none",
            )
    except Exception as edge_err:
        logger.debug(f"Edge-TTS attempt failed: {edge_err}. Trying gTTS fallback...")

    # Tier 3: Try Google gTTS (Cloud Fallback)
    try:
        from gtts import gTTS
        tts = gTTS(text=speech_text, lang="en", slow=False)
        tts.save(mp3_filepath)
        if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
            logger.info(f"gTTS audio stream generated: {mp3_filepath}")
            _release_lock()
            return _format_audio_result(
                file_name=mp3_filename,
                file_path=mp3_filepath,
                audio_type="mp3",
                engine="gTTS (Cloud)",
                voice="Standard English",
                chime=selected_chime if include_chime else "none",
            )
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
            _release_lock()
            return _format_audio_result(
                file_name=wav_filename,
                file_path=wav_filepath,
                audio_type="wav",
                engine="Offline Speech (pyttsx3)",
                voice=f"{gender.capitalize()} Offline",
                chime=selected_chime if include_chime else "none",
            )
    except Exception as p_err:
        logger.error(f"pyttsx3 offline synthesis error: {p_err}")

    # Tier 5: Contextual institutional chime fallback — guarantees valid audio and zero HTTP 500
    try:
        from app.services.chime_service import get_or_create_chime_wav
        fallback_wav = get_or_create_chime_wav(selected_chime)
        if os.path.exists(fallback_wav) and os.path.getsize(fallback_wav) > 1024:
            has_mp3 = convert_wav_to_mp3(fallback_wav, mp3_filepath)
            chosen_fn = mp3_filename if has_mp3 else os.path.basename(fallback_wav)
            chosen_fp = mp3_filepath if has_mp3 else fallback_wav
            _release_lock()
            return _format_audio_result(
                file_name=chosen_fn,
                file_path=chosen_fp,
                audio_type="mp3" if has_mp3 else "wav",
                engine=f"Campus Notice Chime ({selected_chime})",
                voice="Institutional Chime",
                chime=selected_chime,
            )
    except Exception as chime_fallback_err:
        logger.error(f"Chime fallback error: {chime_fallback_err}")

    _release_lock()
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

    # 1. Restore from Hugging Face Git LFS CDN if container local disk was wiped
    try:
        from app.services.cloud_storage_service import CloudStorageService
        if not os.path.exists(wav_filepath) and not os.path.exists(mp3_filepath):
            CloudStorageService.restore_file_from_cdn_if_missing(mp3_filename, folder="audio_streams")
            CloudStorageService.restore_file_from_cdn_if_missing(wav_filename, folder="audio_streams")
    except Exception:
        pass

    # 1. Check WAV cache
    if os.path.exists(wav_filepath):
        if is_legacy_beep_file(wav_filepath):
            try:
                os.remove(wav_filepath)
            except Exception:
                pass
        elif os.path.getsize(wav_filepath) > 1024:
            return _format_audio_result(
                file_name=wav_filename,
                file_path=wav_filepath,
                audio_type="wav",
                engine=f"Neural Speech ({voice_name} - Cached)",
                voice=voice_name,
            )

    # 2. Check MP3 cache
    if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
        return _format_audio_result(
            file_name=mp3_filename,
            file_path=mp3_filepath,
            audio_type="mp3",
            engine=f"Neural Speech ({voice_name} - Cached)",
            voice=voice_name,
        )

    # Tier 1: Kokoro Neural Engine (Remote AI Worker, ONNX, or PyTorch pipeline)
    if TTS_ENGINE not in ["edge_only", "gtts_only"]:
        # 1A. Dedicated Remote Kokoro-82M Worker
        if KOKORO_API_URL and remote_kokoro_enabled():
            remote_timeout = float(os.getenv("KOKORO_TIMEOUT_SEC", "8.0"))
            if synthesize_remote_kokoro_api(clean_text, voice=kok_voice, output_path=mp3_filepath, response_format="mp3", timeout=remote_timeout):
                return _format_audio_result(
                    file_name=mp3_filename,
                    file_path=mp3_filepath,
                    audio_type="mp3",
                    engine=f"Kokoro-82M Neural ({voice_name})",
                    voice=voice_name,
                )

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
                    chosen_fn = mp3_filename if has_mp3 else wav_filename
                    chosen_fp = mp3_filepath if has_mp3 else wav_filepath
                    return _format_audio_result(
                        file_name=chosen_fn,
                        file_path=chosen_fp,
                        audio_type="mp3" if has_mp3 else "wav",
                        engine=f"Kokoro-82M INT8 ({voice_name})",
                        voice=voice_name,
                        duration_sec=duration,
                    )
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
                    return _format_audio_result(
                        file_name=wav_filename,
                        file_path=wav_filepath,
                        audio_type="wav",
                        engine=f"Kokoro-82M ({voice_name})",
                        voice=voice_name,
                        duration_sec=duration,
                    )
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
            return _format_audio_result(
                file_name=mp3_filename,
                file_path=mp3_filepath,
                audio_type="mp3",
                engine=f"Edge-TTS ({voice_name})",
                voice=voice_name,
            )
    except Exception as e_err:
        logger.debug(f"Edge-TTS text synthesis failed: {e_err}")

    # Tier 3: gTTS (Google Cloud)
    try:
        from gtts import gTTS
        tts = gTTS(text=clean_text, lang="en", slow=False)
        tts.save(mp3_filepath)
        if os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 1024:
            return _format_audio_result(
                file_name=mp3_filename,
                file_path=mp3_filepath,
                audio_type="mp3",
                engine="gTTS (Cloud)",
                voice="Standard English",
            )
    except Exception as g_err:
        logger.debug(f"gTTS text synthesis failed: {g_err}")

    # Tier 4: pyttsx3 (100% Offline Local Speech)
    try:
        ok = generate_offline_speech_pyttsx3(wav_filepath, clean_text, gender=gender)
        if ok:
            return _format_audio_result(
                file_name=wav_filename,
                file_path=wav_filepath,
                audio_type="wav",
                engine="Offline Speech (pyttsx3)",
                voice=f"{gender.capitalize()} Offline",
            )
    except Exception as p_err:
        logger.error(f"pyttsx3 arbitrary text synthesis failed: {p_err}")

    raise RuntimeError("Speech synthesis failed across all engines.")
