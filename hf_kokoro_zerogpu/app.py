import spaces
import os
import io
import time
import soundfile as sf
import torch
import numpy as np
import gradio as gr

# Compatibility patch for Gradio 5 / Pydantic boolean schemas in get_type
try:
    import gradio_client.utils
    _orig_get_type = gradio_client.utils.get_type
    def _patched_get_type(schema):
        if not isinstance(schema, dict):
            return "bool" if isinstance(schema, bool) else "any"
        return _orig_get_type(schema)
    gradio_client.utils.get_type = _patched_get_type

    _orig_schema_to_type = gradio_client.utils._json_schema_to_python_type
    def _patched_schema_to_type(schema, defs):
        if not isinstance(schema, dict):
            return "any"
        return _orig_schema_to_type(schema, defs)
    gradio_client.utils._json_schema_to_python_type = _patched_schema_to_type
except Exception:
    pass

from kokoro import KPipeline
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

HF_TOKEN = os.getenv("HF_TOKEN", "")
BASE_MODEL_ID = "google/gemma-2-2b-it"
ADAPTER_ID = "RakshiRoxy/echosphere-campus-gemma-2b"

# Lazy-loaded globals
_tts_pipeline = None
_llm_model = None
_llm_tokenizer = None

def get_tts_pipeline():
    global _tts_pipeline
    if _tts_pipeline is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[EchoSphere TTS] Initializing KPipeline with device={device}...")
        _tts_pipeline = KPipeline(lang_code="a", device=device)
    return _tts_pipeline

def get_llm():
    global _llm_model, _llm_tokenizer
    if _llm_model is None or _llm_tokenizer is None:
        print(f"[EchoSphere LLM] Loading tokenizer from {BASE_MODEL_ID}...")
        _llm_tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, token=HF_TOKEN)
        if _llm_tokenizer.pad_token is None:
            _llm_tokenizer.pad_token = _llm_tokenizer.eos_token

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[EchoSphere LLM] Loading base model on {device}...")
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            token=HF_TOKEN,
        )
        if torch.cuda.is_available():
            base_model = base_model.to("cuda")

        print(f"[EchoSphere LLM] Loading adapter {ADAPTER_ID}...")
        _llm_model = PeftModel.from_pretrained(base_model, ADAPTER_ID, token=HF_TOKEN)
        _llm_model.eval()
        print("[EchoSphere LLM] Model loaded and ready!")
    return _llm_model, _llm_tokenizer

@spaces.GPU(duration=60)
def generate_audio(text: str, voice: str = "af_heart", speed: float = 1.0):
    try:
        pipeline = get_tts_pipeline()
        clean_text = text.strip() if text else "Attention. Official campus announcement broadcast."
        clean_voice = (voice or "af_heart").strip().lower()
        generator = pipeline(clean_text, voice=clean_voice, speed=float(speed or 1.0))
        audio_chunks = []
        for _, _, audio in generator:
            if isinstance(audio, torch.Tensor):
                audio_chunks.append(audio.detach().cpu().numpy())
            elif isinstance(audio, np.ndarray):
                audio_chunks.append(audio)
        samples = np.concatenate(audio_chunks) if audio_chunks else np.zeros(24000, dtype=np.float32)
        return (24000, samples)
    except Exception as e:
        print(f"[EchoSphere TTS error]: {e}")
        return (24000, np.zeros(24000, dtype=np.float32))

@spaces.GPU(duration=60)
def generate_campus_text(prompt: str, max_new_tokens: int = 256, temperature: float = 0.3) -> str:
    try:
        model, tokenizer = get_llm()
        clean = (prompt or "").strip()
        if not clean:
            return ""

        if "<start_of_turn>" not in clean:
            chat_prompt = f"<start_of_turn>user\n{clean}<end_of_turn>\n<start_of_turn>model\n"
        else:
            chat_prompt = clean

        target_device = next(model.parameters()).device
        inputs = tokenizer(chat_prompt, return_tensors="pt").to(target_device)
        temp = float(temperature or 0.3)
        do_sample = temp > 0.05

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=int(max_new_tokens or 256),
                do_sample=do_sample,
                temperature=temp if do_sample else None,
                top_p=0.9 if do_sample else None,
                repetition_penalty=1.12,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    except Exception as e:
        import traceback
        return f"Error: {e}\n{traceback.format_exc()}"

VOICE_CHOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "af_alloy",
    "am_adam", "am_michael", "am_echo", "am_eric", "am_fenrir", "am_puck",
    "bf_emma", "bf_isabella", "bf_alice", "bm_george", "bm_fable"
]

tts_interface = gr.Interface(
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
    api_name="synthesize",
)

llm_interface = gr.Interface(
    fn=generate_campus_text,
    inputs=[
        gr.Textbox(
            label="Campus Query / Draft Memo",
            placeholder="e.g. Expand this note: Final semester practical lab examination begins next Monday in Turing Lab",
            lines=4
        ),
        gr.Slider(minimum=32, maximum=512, value=256, step=16, label="Max New Tokens"),
        gr.Slider(minimum=0.0, maximum=1.0, value=0.3, step=0.05, label="Temperature"),
    ],
    outputs=gr.Textbox(label="Fine-Tuned Gemma 2B Output", lines=8),
    api_name="generate",
)

demo = gr.TabbedInterface(
    interface_list=[tts_interface, llm_interface],
    tab_names=["🎙️ Kokoro-82M Voice Synthesis", "🧠 Campus Gemma 2B Neural Brain"],
    title="🎙️ EchoSphere Unified ZeroGPU AI & Voice Worker",
)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_api=True
    )
