import io
import os
import re
import numpy as np
import soundfile as sf
import torch
from typing import Tuple, Optional
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. Compatibility patch for Gradio 4.x / huggingface_hub
try:
    import huggingface_hub
    if not hasattr(huggingface_hub, "HfFolder"):
        class MockHfFolder:
            @staticmethod
            def get_token():
                return os.getenv("HF_TOKEN", "")
            @staticmethod
            def save_token(token):
                pass
            @staticmethod
            def delete_token():
                pass
        huggingface_hub.HfFolder = MockHfFolder
except Exception:
    pass

# 2. Safe ZeroGPU Import (Works seamlessly on CPU Basic and ZeroGPU)
try:
    import spaces
    gpu_decorator = spaces.GPU(duration=60)
except Exception:
    gpu_decorator = lambda f: f

import gradio as gr

# 3. Kokoro Pipeline Caching (16 GB RAM)
_pipelines = {}

def get_pipeline(lang_code: str = "a"):
    """
    Loads and caches KPipeline for English American ('a') or British ('b').
    Runs ultra-fast on 16 GB RAM.
    """
    global _pipelines
    if lang_code not in _pipelines:
        from kokoro import KPipeline
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading KPipeline(lang_code='{lang_code}', device='{device}')...")
        _pipelines[lang_code] = KPipeline(lang_code=lang_code, device=device)
    return _pipelines[lang_code]


# 4. Core Speech Synthesis
@gpu_decorator
def synthesize(text: str, voice: str = "af_heart", speed: float = 1.0) -> Tuple[int, np.ndarray]:
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


def pcm_to_mp3(samples: np.ndarray, sample_rate: int = 24000, bitrate: int = 128) -> bytes:
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


# 5. FastAPI Endpoints for EchoSphere Render Backend
app = FastAPI(title="EchoSphere Kokoro Dedicated Worker", version="2.0.0")

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
        "service": "EchoSphere Kokoro-82M Dedicated Worker",
        "memory_ram": "16 GB High Memory",
        "cuda_available": torch.cuda.is_available(),
    }

@app.get("/v1/models")
def list_models():
    return {"object": "list", "data": [{"id": "kokoro", "object": "model"}]}

@app.post("/v1/audio/speech")
def openai_speech(req: SpeechRequest):
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
        return Response(content=buf.getvalue(), media_type="audio/wav")


# 6. Interactive Gradio UI
VOICE_CHOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "af_alloy",
    "am_adam", "am_michael", "am_echo", "am_eric", "am_fenrir", "am_puck",
    "bf_emma", "bf_isabella", "bf_alice", "bm_george", "bm_fable"
]

demo = gr.Interface(
    fn=synthesize,
    inputs=[
        gr.Textbox(
            label="Announcement Text",
            value="Attention all students and faculty. The campus symposium will commence at 10 AM.",
            lines=3,
        ),
        gr.Dropdown(choices=VOICE_CHOICES, value="af_heart", label="Speaker Voice"),
        gr.Slider(minimum=0.5, maximum=2.0, value=1.0, step=0.1, label="Speed"),
    ],
    outputs=gr.Audio(label="Synthesized Kokoro Audio (24kHz Studio Quality)"),
    title="🎙️ EchoSphere Kokoro-82M AI Worker",
    description="100% Free 16 GB RAM Neural Audio Worker for EchoSphere PA & Smart Speakers.",
)

demo.queue()
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
