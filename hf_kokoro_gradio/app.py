import io
import os
import urllib.request
import soundfile as sf
from fastapi import FastAPI, Response
from pydantic import BaseModel
import gradio as gr
from kokoro_onnx import Kokoro

os.makedirs("models", exist_ok=True)
model_path = "models/kokoro-v1.0.int8.onnx"
voices_path = "models/voices-v1.0.bin"
base_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

if not os.path.exists(model_path) or os.path.getsize(model_path) < 50_000_000:
    print("Downloading Kokoro-82M INT8 neural weights (88MB)...")
    urllib.request.urlretrieve(f"{base_url}/kokoro-v1.0.int8.onnx", model_path)

if not os.path.exists(voices_path) or os.path.getsize(voices_path) < 15_000_000:
    print("Downloading Kokoro voice embeddings (28MB)...")
    urllib.request.urlretrieve(f"{base_url}/voices-v1.0.bin", voices_path)

kokoro = Kokoro(model_path, voices_path)
print("Kokoro-82M AI Worker is ready on 16 GB RAM!")

app = FastAPI(title="EchoSphere Kokoro-82M Dedicated Worker")

class SpeechRequest(BaseModel):
    input: str
    voice: str = "af_heart"
    model: str = "kokoro"
    response_format: str = "wav"

@app.post("/v1/audio/speech")
def speech(req: SpeechRequest):
    clean_voice = req.voice or "af_heart"
    text = req.input or "Attention. Official campus announcement broadcast."
    samples, sample_rate = kokoro.create(text, voice=clean_voice, speed=1.0, lang="en-us")
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    audio_bytes = buf.getvalue()
    return Response(content=audio_bytes, media_type="audio/wav")

def web_demo(text, voice):
    clean_voice = voice or "af_heart"
    samples, sample_rate = kokoro.create(text, voice=clean_voice, speed=1.0, lang="en-us")
    return (sample_rate, samples)

demo = gr.Interface(
    fn=web_demo,
    inputs=[
        gr.Textbox(label="Notice Text", value="Attention. Official campus announcement broadcast.", lines=3),
        gr.Dropdown(choices=["af_heart", "am_adam", "af_bella", "af_nicole", "bf_emma", "bm_george"], value="af_heart", label="Speaker Voice"),
    ],
    outputs=gr.Audio(label="Synthesized Kokoro Audio"),
    title="🎙️ EchoSphere Kokoro-82M AI Worker",
    description="100% Free 16 GB RAM neural audio worker serving OpenAI-compatible /v1/audio/speech for EchoSphere.",
)

demo.queue()
app = gr.mount_gradio_app(app, demo, path="/")
