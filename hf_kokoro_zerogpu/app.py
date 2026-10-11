import spaces
from kokoro import KPipeline
import gradio as gr
import soundfile as sf
import torch
import numpy as np
import os

# 1. Compatibility patch for Starlette TemplateResponse (fixes Jinja2 TypeError: unhashable type: 'dict' on localhost)
try:
    from starlette.templating import Jinja2Templates
    from starlette.requests import Request
    _orig_template_response = Jinja2Templates.TemplateResponse

    def _safe_template_response(self, *args, **kwargs):
        name = None
        context = kwargs.get("context", {})
        request = kwargs.get("request")

        for arg in args:
            if isinstance(arg, str):
                name = arg
            elif isinstance(arg, dict):
                context = arg
            elif isinstance(arg, Request):
                request = arg

        if not request and isinstance(context, dict):
            request = context.get("request")

        if not name:
            name = kwargs.get("name", "index.html")

        if isinstance(context, dict) and request:
            context.setdefault("request", request)

        try:
            return _orig_template_response(self, request=request, name=name, context=context)
        except TypeError:
            return _orig_template_response(self, name, context)

    Jinja2Templates.TemplateResponse = _safe_template_response
except Exception:
    pass

# 2. Compatibility patch for Pydantic boolean schemas in Gradio Client
try:
    import gradio_client.utils
    _orig_get_type = gradio_client.utils.get_type
    def _patched_get_type(schema):
        if not isinstance(schema, dict):
            return "bool" if isinstance(schema, bool) else "any"
        return _orig_get_type(schema)
    gradio_client.utils.get_type = _patched_get_type

    _orig_json_schema = getattr(gradio_client.utils, "_json_schema_to_python_type", None)
    if _orig_json_schema is not None:
        def _patched_json_schema(schema, defs=None):
            if not isinstance(schema, dict):
                return "bool" if isinstance(schema, bool) else "any"
            return _orig_json_schema(schema, defs)
        gradio_client.utils._json_schema_to_python_type = _patched_json_schema
except Exception:
    pass

# 3. Compatibility patch for HfFolder
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

# 4. Pipeline caching
pipelines = {}

def get_pipeline(lang_code="a"):
    if lang_code not in pipelines:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading KPipeline(lang_code='{lang_code}', device='{device}')...")
        pipelines[lang_code] = KPipeline(lang_code=lang_code, device=device)
    return pipelines[lang_code]

# 5. ZeroGPU Accelerated Function
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
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
