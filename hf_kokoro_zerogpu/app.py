import io
import os
import re
import numpy as np
import soundfile as sf
import torch
from typing import Tuple, Optional
from fastapi import FastAPI, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import gradio as gr

# 1. ZeroGPU Safe Import & Decorator Wrapper
try:
    import spaces
    has_spaces = True
except ImportError:
    has_spaces = False

print(f"ZeroGPU Environment Detected: {has_spaces}")

# 2. Kokoro Pipelines Cache
_pipelines = {}

def get_pipeline(lang_code: str = "a"):
    """
    Lazy-loads and caches KPipeline for English American ('a') or British ('b').
    Automatically uses CUDA if available inside @spaces.GPU or falls back to CPU.
    """
    global _pipelines
    if lang_code not in _pipelines:
        from kokoro import KPipeline
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading KPipeline(lang_code='{lang_code}', device='{device}')...")
        _pipelines[lang_code] = KPipeline(lang_code=lang_code, device=device)
        print(f"KPipeline(lang_code='{lang_code}') loaded successfully.")
    return _pipelines[lang_code]


def _core_synthesize(text: str, voice: str = "af_heart", speed: float = 1.0) -> Tuple[int, np.ndarray]:
    """
    Synthesizes speech using Kokoro-82M neural model.
    Yields 24kHz single-channel float32 audio.
    """
    clean_voice = (voice or "af_heart").strip().lower()
    lang_code = "b" if clean_voice.startswith("b") else "a"
    pipeline = get_pipeline(lang_code)

    clean_text = text.strip() if text else "Attention. Official campus announcement broadcast."
    generator = pipeline(clean_text, voice=clean_voice, speed=speed)

    audio_chunks = []
    for _, _, audio in generator:
        if isinstance(audio, torch.Tensor):
            audio_chunks.append(audio.detach().cpu().numpy())
        elif isinstance(audio, np.ndarray):
            audio_chunks.append(audio)

    if audio_chunks:
        samples = np.concatenate(audio_chunks)
    else:
        samples = np.zeros(24000, dtype=np.float32)

    return 24000, samples


# Wrap core inference with @spaces.GPU when deployed on ZeroGPU
if has_spaces:
    @spaces.GPU(duration=60)
    def synthesize_with_gpu(text: str, voice: str = "af_heart", speed: float = 1.0) -> Tuple[int, np.ndarray]:
        return _core_synthesize(text, voice, speed)
else:
    synthesize_with_gpu = None


def synthesize(text: str, voice: str = "af_heart", speed: float = 1.0) -> Tuple[int, np.ndarray]:
    """
    Robust dispatch: Attempts ZeroGPU acceleration first; seamlessly falls back
    to CPU (16 GB RAM) if ZeroGPU queue is temporarily unavailable.
    """
    if synthesize_with_gpu is not None:
        try:
            return synthesize_with_gpu(text, voice, speed)
        except Exception as e:
            print(f"ZeroGPU execution notice: {e}. Falling back to CPU...")
            return _core_synthesize(text, voice, speed)
    return _core_synthesize(text, voice, speed)


def pcm_to_mp3(samples: np.ndarray, sample_rate: int = 24000, bitrate: int = 128) -> bytes:
    """Encodes float32 PCM samples into standard MP3 using lameenc."""
    try:
        import lameenc
        int16_samples = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bitrate)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(1)
        encoder.set_quality(5)
        mp3_bytes = encoder.encode(int16_samples.tobytes()) + encoder.flush()
        return mp3_bytes
    except Exception:
        buf = io.BytesIO()
        sf.write(buf, samples, sample_rate, format="WAV")
        return buf.getvalue()


# 3. FastAPI Application Initialization
app = FastAPI(
    title="EchoSphere Kokoro-82M Dedicated Worker",
    description="100% Free ZeroGPU AI Speech Microservice for EchoSphere Smart PA System",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpeechRequest(BaseModel):
    input: str
    voice: Optional[str] = "af_heart"
    model: Optional[str] = "kokoro"
    response_format: Optional[str] = "wav"
    speed: Optional[float] = 1.0


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "EchoSphere Kokoro-82M AI Worker",
        "zerogpu_available": has_spaces,
        "cuda_active": torch.cuda.is_available(),
    }


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "kokoro",
                "object": "model",
                "created": 1700000000,
                "owned_by": "hexgrad",
            }
        ],
    }


@app.post("/v1/audio/speech")
def openai_speech(req: SpeechRequest):
    """
    OpenAI-compatible speech generation endpoint called by EchoSphere backend.
    Returns 24kHz 16-bit PCM WAV (ideal for ESP32 MAX98357A I2S streaming)
    or MP3 (for web/mobile client playback).
    """
    target_format = (req.response_format or "wav").lower()
    clean_voice = req.voice or "af_heart"
    clean_speed = req.speed or 1.0

    sample_rate, samples = synthesize(req.input, voice=clean_voice, speed=clean_speed)

    if target_format == "mp3":
        mp3_bytes = pcm_to_mp3(samples, sample_rate=sample_rate)
        return Response(content=mp3_bytes, media_type="audio/mpeg")
    else:
        buf = io.BytesIO()
        sf.write(buf, samples, sample_rate, format="WAV")
        wav_bytes = buf.getvalue()
        return Response(content=wav_bytes, media_type="audio/wav")


# 4. Interactive Gradio Web Demo
VOICE_CHOICES = [
    # American Female
    "af_heart",
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky",
    "af_alloy",
    "af_jessica",
    "af_river",
    # American Male
    "am_adam",
    "am_michael",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_onyx",
    "am_puck",
    "am_santa",
    # British Female
    "bf_emma",
    "bf_isabella",
    "bf_alice",
    "bf_lily",
    # British Male
    "bm_george",
    "bm_fable",
    "bm_lewis",
    "bm_daniel",
]

def gradio_synthesize(text: str, voice: str, speed: float):
    sample_rate, samples = synthesize(text, voice=voice, speed=speed)
    return (sample_rate, samples)

demo = gr.Interface(
    fn=gradio_synthesize,
    inputs=[
        gr.Textbox(
            label="Announcement Text",
            value="Attention all students and faculty. The campus tech symposium will commence at 10 AM in the main auditorium.",
            lines=4,
        ),
        gr.Dropdown(
            choices=VOICE_CHOICES,
            value="af_heart",
            label="Speaker Voice",
            info="Select American or British male/female neural voices.",
        ),
        gr.Slider(
            minimum=0.5,
            maximum=2.0,
            value=1.0,
            step=0.1,
            label="Speaking Speed",
        ),
    ],
    outputs=gr.Audio(label="Synthesized Neural Audio (24kHz Studio Quality)"),
    title="🎙️ EchoSphere Kokoro-82M AI Worker (ZeroGPU)",
    description=(
        "**100% Free Dedicated Neural Audio Microservice** for EchoSphere Smart PA System.\n\n"
        "• Provides OpenAI-compatible `/v1/audio/speech` for Render backend.\n"
        "• Outputs clean 24kHz 16-bit PCM WAV for ESP32 MAX98357A I2S streaming.\n"
        "• Powered by dynamic ZeroGPU (NVIDIA A100) or high-memory CPU on Hugging Face Spaces."
    ),
    examples=[
        ["Attention all students and faculty. The campus library will close early today at 5:00 PM for scheduled maintenance.", "af_heart", 1.0],
        ["Emergency drill alert. Please proceed to the nearest designated assembly zone in an orderly manner.", "am_adam", 1.0],
        ["Good morning students. Classes for Department of Computer Science are relocated to Hall B for today's morning session.", "bf_emma", 1.0],
    ],
)

demo.queue()
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
