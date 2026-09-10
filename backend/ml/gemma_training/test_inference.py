import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
new_adapter = os.path.join(SCRIPT_DIR, "output_gemma_model", "final_adapter")
old_adapter = os.path.join(SCRIPT_DIR, "output_gemma_campus_model", "final_adapter")
adapter_path = new_adapter if os.path.isdir(new_adapter) else old_adapter
model_id = "google/gemma-2-2b-it"
hf_token = "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"

print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"Adapter exists: {os.path.isdir(adapter_path)} ({adapter_path})")

tokenizer = AutoTokenizer.from_pretrained(adapter_path if os.path.isdir(adapter_path) else model_id, token=hf_token)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

print("Loading base model...")
base_model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    token=hf_token,
)

print("Loading adapter...")
model = PeftModel.from_pretrained(base_model, adapter_path, token=hf_token)
model.eval()

queries = [
    "hello who are you",
    "How does backpropagation work in neural networks?",
    "How do I bookmark circulars in the app?",
    "Tell me a funny joke"
]

for q in queries:
    prompt = f"<start_of_turn>user\n{q}<end_of_turn>\n<start_of_turn>model\n"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=150, do_sample=False)
    reply = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    print(f"\n[QUERY]: {q}")
    print(f"[REPLY]:\n{reply}\n{'-'*40}")
