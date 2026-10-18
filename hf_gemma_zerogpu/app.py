import os
import sys
import time
import torch
import gradio as gr
from typing import Optional, Dict, Any
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
import spaces

HF_TOKEN = os.getenv("HF_TOKEN", "")
BASE_MODEL_ID = "google/gemma-2-2b-it"
ADAPTER_ID = "RakshiRoxy/echosphere-campus-gemma-2b"

print(f"[EchoSphere AI Space] Loading tokenizer from {ADAPTER_ID}...")
tokenizer = AutoTokenizer.from_pretrained(
    ADAPTER_ID,
    token=HF_TOKEN
)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print(f"[EchoSphere AI Space] Loading base model {BASE_MODEL_ID} in 4-bit NF4...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    token=HF_TOKEN,
)

print(f"[EchoSphere AI Space] Loading fine-tuned adapter: {ADAPTER_ID}...")
model = PeftModel.from_pretrained(base_model, ADAPTER_ID, token=HF_TOKEN)
model.eval()
print("[EchoSphere AI Space] Model ready for ZeroGPU cloud inference!")


@spaces.GPU(duration=60)
def generate_announcement_or_answer(prompt: str, max_new_tokens: int = 256, temperature: float = 0.3) -> str:
    clean = (prompt or "").strip()
    if not clean:
        return ""

    if "<start_of_turn>" not in clean:
        chat_prompt = f"<start_of_turn>user\n{clean}<end_of_turn>\n<start_of_turn>model\n"
    else:
        chat_prompt = clean

    inputs = tokenizer(chat_prompt, return_tensors="pt").to(model.device)
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


demo = gr.Interface(
    fn=generate_announcement_or_answer,
    inputs=[
        gr.Textbox(
            label="Input Prompt / Topic / Memo",
            placeholder="e.g. Draft an announcement for practical lab exam starting next Monday",
            lines=4
        ),
        gr.Slider(minimum=32, maximum=512, value=256, step=16, label="Max Tokens"),
        gr.Slider(minimum=0.0, maximum=1.0, value=0.3, step=0.05, label="Temperature"),
    ],
    outputs=gr.Textbox(label="Generated Output (Fine-Tuned Gemma 2B)", lines=8),
    title="🧠 EchoSphere Campus Gemma 2B AI Brain (ZeroGPU)",
    description="Dedicated 100% Free Cloud Neural Microservice for EchoSphere. Running on NVIDIA A10G/A100 ZeroGPU.",
    api_name="generate"
)

demo.queue()

if hasattr(demo, "app") and demo.app is not None:
    class GenRequest(BaseModel):
        prompt: str
        max_new_tokens: Optional[int] = 256
        temperature: Optional[float] = 0.3

    @demo.app.post("/generate")
    def api_generate(req: GenRequest):
        t0 = time.time()
        res = generate_announcement_or_answer(req.prompt, req.max_new_tokens or 256, req.temperature or 0.3)
        return {
            "text": res,
            "duration_ms": round((time.time() - t0) * 1000.0, 1),
            "model": ADAPTER_ID
        }

    @demo.app.get("/health")
    def health_check():
        return {
            "status": "ready",
            "model": ADAPTER_ID,
            "base_model": BASE_MODEL_ID,
            "engine": "ZeroGPU Cloud"
        }

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
