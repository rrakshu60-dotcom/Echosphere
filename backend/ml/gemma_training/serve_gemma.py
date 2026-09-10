"""
EchoSphere Gemma 2 GPU Inference Microservice
Runs on NVIDIA RTX 4060 GPU with 4-bit NF4 quantization and BF16 compute.
Serves local sub-100ms inference to the FastAPI backend.
"""

import os
import sys
import time
import threading
from typing import Optional, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

app = FastAPI(title="EchoSphere Gemma 2 Local Inference Service")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from app.services.ai_text_sanitizer import sanitize_ai_markdown
except ImportError:
    def sanitize_ai_markdown(text):
        return text

new_adapter = os.path.join(SCRIPT_DIR, "output_gemma_model", "final_adapter")
old_adapter = os.path.join(SCRIPT_DIR, "output_gemma_campus_model", "final_adapter")
ADAPTER_PATH = new_adapter if os.path.isdir(new_adapter) else old_adapter
MODEL_ID = "google/gemma-2-2b-it"
HF_TOKEN = os.getenv("HF_TOKEN", "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")

tokenizer = None
model = None
inference_lock = threading.Lock()
is_ready = False
init_error = None


def load_gemma_model():
    global tokenizer, model, is_ready, init_error
    try:
        print(f"[Gemma Service] Initializing on GPU (CUDA: {torch.cuda.is_available()})...")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available for GPU inference.")

        print(f"[Gemma Service] Device: {torch.cuda.get_device_name(0)}")
        tokenizer = AutoTokenizer.from_pretrained(
            ADAPTER_PATH if os.path.isdir(ADAPTER_PATH) else MODEL_ID,
            token=HF_TOKEN
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

        print(f"[Gemma Service] Loading base model: {MODEL_ID}...")
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            token=HF_TOKEN,
        )

        if os.path.isdir(ADAPTER_PATH):
            print(f"[Gemma Service] Loading fine-tuned adapter from {ADAPTER_PATH}...")
            model = PeftModel.from_pretrained(base_model, ADAPTER_PATH, token=HF_TOKEN)
        else:
            print("[Gemma Service] Running base model without adapter.")
            model = base_model

        model.eval()
        is_ready = True
        print("[Gemma Service] Model loaded and ready for ultra-fast GPU inference!")
    except Exception as e:
        init_error = str(e)
        print(f"[Gemma Service] Model loading error: {e}")


class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.3


@app.get("/health")
def health() -> Dict[str, Any]:
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None"
    vram_used = (
        round(torch.cuda.memory_allocated(0) / (1024**2), 1)
        if torch.cuda.is_available()
        else 0
    )
    return {
        "status": "ready" if is_ready else "loading",
        "model": MODEL_ID,
        "adapter_loaded": os.path.isdir(ADAPTER_PATH),
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": gpu_name,
        "vram_used_mb": vram_used,
        "error": init_error,
    }


@app.post("/generate")
def generate(req: GenerateRequest) -> Dict[str, Any]:
    if not is_ready:
        if init_error:
            raise HTTPException(status_code=500, detail=f"Gemma failed to load: {init_error}")
        raise HTTPException(status_code=503, detail="Gemma model is still loading...")

    start_time = time.time()
    prompt = req.prompt.strip()

    # Wrap into Gemma 2 instruction turn format if not already wrapped
    if "<start_of_turn>" not in prompt:
        chat_prompt = f"<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n"
    else:
        chat_prompt = prompt

    with inference_lock:
        inputs = tokenizer(chat_prompt, return_tensors="pt").to("cuda")
        temp = req.temperature if (req.temperature is not None and req.temperature > 0) else 0.7
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=req.max_new_tokens or 256,
                do_sample=True,
                temperature=temp,
                top_p=0.9,
                repetition_penalty=1.12
            )
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        raw_reply = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        reply = sanitize_ai_markdown(raw_reply)

    duration_ms = round((time.time() - start_time) * 1000.0, 1)
    return {
        "text": reply,
        "duration_ms": duration_ms,
        "model": "Fine-Tuned Gemma 2 2B (Local GPU)"
    }


@app.on_event("startup")
def startup_event():
    # Load model in a separate thread so server starts immediately and health returns status
    threading.Thread(target=load_gemma_model, daemon=True).start()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8008, log_level="info")
