import spaces
from kokoro import KPipeline
import gradio as gr
import soundfile as sf
import torch
import numpy as np

# 1. Pipeline caching
pipelines = {}

def get_pipeline(lang_code="a"):
    if lang_code not in pipelines:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading KPipeline(lang_code='{lang_code}', device='{device}')...")
        pipelines[lang_code] = KPipeline(lang_code=lang_code, device=device)
    return pipelines[lang_code]

# 2. ZeroGPU Accelerated Function
@spaces.GPU(duration=60)
def generate_audio(text: str, voice: str = "af_heart", speed: float = 1.0):
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

    return (24000, samples)

VOICE_CHOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "af_alloy",
    "am_adam", "am_michael", "am_echo", "am_eric", "am_fenrir", "am_puck",
    "bf_emma", "bf_isabella", "bf_alice", "bm_george", "bm_fable"
]

demo = gr.Interface(
    fn=generate_audio,
    inputs=[
        gr.Textbox(
            label="Announcement Text",
            value="Attention all students and faculty. The campus symposium will commence at 10 AM in the main auditorium.",
            lines=3,
        ),
        gr.Dropdown(choices=VOICE_CHOICES, value="af_heart", label="Speaker Voice"),
        gr.Slider(minimum=0.5, maximum=2.0, value=1.0, step=0.1, label="Speed"),
    ],
    outputs=gr.Audio(label="Synthesized Kokoro Audio (24kHz Studio Quality)"),
    title="🎙️ EchoSphere Kokoro-82M AI Worker (ZeroGPU)",
    description="100% Free ZeroGPU AI Speech Microservice for EchoSphere PA & Smart Speakers.",
    api_name="synthesize",
)

if __name__ == "__main__":
    demo.queue().launch()
