"""
EchoSphere Campus Gemma 2 Local RTX 4060 GPU Training Engine
Accelerated with Ada Lovelace 4th-gen Tensor Cores, Native BF16, and SDPA Flash-Attention.
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# 1. Environment & Auth
HF_TOKEN = "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"
os.environ["HF_TOKEN"] = HF_TOKEN

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(SCRIPT_DIR, "echosphere_campus_gemma_dataset.jsonl")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_gemma_campus_model")
FINAL_ADAPTER = os.path.join(OUTPUT_DIR, "final_adapter")

print("=" * 65)
print("ECHOSPHERE LOCAL GPU TRAINING ENGINE (ASUS ROG STRIX RTX 4060)")
print("=" * 65)
print(f"CUDA Available:     {torch.cuda.is_available()}")
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    print(f"Active GPU:         {gpu_name} ({vram_gb} GB VRAM)")
    print(f"Architecture:       Ada Lovelace (Compute 8.9, 4th-Gen Tensor Cores)")
    print(f"BF16 Supported:     {torch.cuda.is_bf16_supported()}")
print("=" * 65)

# 2. Load Dataset
print(f"\n[1/5] Loading campus dataset from: {DATASET_PATH}")
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
print(f"      Loaded {len(dataset)} campus scenarios.")

# 3. Model & Tokenizer Setup (4-Bit NF4 with BF16 compute)
MODEL_ID = "google/gemma-2-2b-it"
print(f"\n[2/5] Loading Gemma 2 Base Model: {MODEL_ID}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    attn_implementation="sdpa",  # PyTorch 2.x Scaled Dot-Product Attention (FlashAttention)
    token=HF_TOKEN
)
model = prepare_model_for_kbit_training(model)

# 4. LoRA Setup
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# 5. Tokenization (Optimized 256 sequence length)
print("\n[3/5] Tokenizing campus scenarios with 256 max length...")
def tokenize_fn(examples):
    tokens = tokenizer(examples["text"], max_length=256, truncation=True)
    tokens["labels"] = [ids.copy() for ids in tokens["input_ids"]]
    return tokens

tokenized_dataset = dataset.map(tokenize_fn, batched=True, remove_columns=dataset.column_names)
data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, pad_to_multiple_of=8)

# 6. Optimized Fast Training Configuration for RTX 4060
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=2,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=20,
    optim="paged_adamw_8bit",
    logging_steps=25,
    save_strategy="epoch",
    fp16=False,
    bf16=True,  # Native hardware acceleration on RTX 4060
    dataloader_num_workers=0,
    report_to="none"
)

trainer = Trainer(
    model=model,
    train_dataset=tokenized_dataset,
    args=training_args,
    data_collator=data_collator,
)

print("\n[4/5] [START] Starting Local GPU Training on NVIDIA RTX 4060...")
trainer.train()

# 7. Save Final Adapter Weights
print(f"\n[5/5] Saving fine-tuned adapter weights to: {FINAL_ADAPTER}")
trainer.model.save_pretrained(FINAL_ADAPTER)
tokenizer.save_pretrained(FINAL_ADAPTER)

print("\n" + "=" * 65)
print(f"[SUCCESS] LOCAL GPU TRAINING COMPLETE! Adapter saved to:\n  {FINAL_ADAPTER}")
print("=" * 65)
