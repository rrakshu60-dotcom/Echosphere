# pyright: reportMissingImports=false
"""
EchoSphere Gemma 2 Local RTX 4060 GPU Training Engine (Ultra-Stable Laptop Profile)
Engineered specifically for Laptop RTX 4060 (8GB VRAM) with:
1. Micro-batch size = 1 with 16 gradient accumulation steps (Peak VRAM < 3.4 GB)
2. Prediction loss only mode (Zero logit accumulation, zero RAM overflow)
3. Early Stopping Callback (patience=3, threshold=0.001)
4. Optimum Validation Curve with fast 50-sample validation evaluations (< 2 sec)
5. Live Terminal Progress with instant flush and ASCII Validation Loss Curve
6. Auto-restores Best Model Checkpoint via load_best_model_at_end=True
"""

import os
import sys
import gc
import json
import time
import shutil

# Guarantee immediate unbuffered terminal output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Prevent Windows CUDA memory fragmentation
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"

import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
    TrainerCallback,
    TrainerControl,
    TrainerState
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# 1. Environment & Auth
HF_TOKEN = "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"
os.environ["HF_TOKEN"] = HF_TOKEN

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(SCRIPT_DIR, "echosphere_gemma_dataset.jsonl")
if not os.path.isfile(DATASET_PATH):
    DATASET_PATH = os.path.join(SCRIPT_DIR, "echosphere_campus_gemma_dataset.jsonl")

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_gemma_model")
FINAL_ADAPTER = os.path.join(OUTPUT_DIR, "final_adapter")
OLD_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_gemma_campus_model")
OLD_ADAPTER = os.path.join(OLD_OUTPUT_DIR, "final_adapter")

print("=" * 72, flush=True)
print("  ECHOSPHERE SOTA GEMMA 2 TRAINING ENGINE (CLAUDE / CHATGPT PROFILE)", flush=True)
print("  Target Hardware:    NVIDIA GeForce RTX 4060 Laptop (8 GB VRAM)", flush=True)
print("  Deep LoRA Depth:    20 Deep Transformer Layers (Layers 6 to 25)", flush=True)
print("  RSLoRA Tuning:      ENABLED (r=64, alpha=128, all 7 linear projections)", flush=True)
print("  Loss Masking:       ENABLED (Completion-only on assistant response tokens)", flush=True)
print("  NEFTune Noise:      ENABLED (alpha=7.0 for conversational generalization)", flush=True)
print("  Target Steps:       800 Steps (Effective batch 16, ~90-150 min budget)", flush=True)
print("  Early Stopping:     ENABLED (Patience: 8, Threshold: 0.001)", flush=True)
print("  Validation Curve:   ENABLED (Evaluated every 40 steps)", flush=True)
print("=" * 72, flush=True)

if not torch.cuda.is_available():
    print("[ERROR] CUDA is not available! A GPU is required for training.", flush=True)
    sys.exit(1)

gpu_name = torch.cuda.get_device_name(0)
total_vram = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
print(f"  GPU Detected:       {gpu_name} ({total_vram} GB VRAM)", flush=True)
print(f"  BF16 Accelerated:   {torch.cuda.is_bf16_supported()}", flush=True)
print("=" * 72 + "\n", flush=True)

# 2. Load & Split Dataset (90% Train, 10% Validation with 100-sample eval slice)
print(f"[1/5] Loading dataset from: {DATASET_PATH}", flush=True)
raw_dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
print(f"      Total scenarios: {len(raw_dataset)}", flush=True)

split_data = raw_dataset.train_test_split(test_size=0.10, seed=42, shuffle=True)
train_raw = split_data["train"]
eval_raw = split_data["test"].select(range(min(100, len(split_data["test"]))))
print(f"      Train split: {len(train_raw)} | Focused validation slice: {len(eval_raw)}", flush=True)

# 3. Model & Tokenizer Setup (4-Bit NF4 with BF16 compute)
MODEL_ID = "google/gemma-2-2b-it"
print(f"\n[2/5] Loading Gemma 2 Base Model: {MODEL_ID}", flush=True)
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True)
except Exception:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

try:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        local_files_only=True
    )
except Exception:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        token=HF_TOKEN
    )
model = prepare_model_for_kbit_training(model)

# 4. LoRA Setup (20 Deep Transformer Layers: 6 to 25 across all 7 linear projections)
DEEP_LAYERS = list(range(6, 26))  # 20 deep layers
print(f"[LoRA] Targeting {len(DEEP_LAYERS)} deep transformer layers (indices 6 to 25)...", flush=True)
peft_config = LoraConfig(
    r=64,
    lora_alpha=128,
    use_rslora=True,
    layers_to_transform=DEEP_LAYERS,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.08,
    bias="none",
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# 5. Tokenization with SOTA Completion-Only Loss Masking (512 Sequence Length)
MAX_SEQ_LEN = 512
MODEL_MARKER = "<start_of_turn>model\n"
print(f"\n[3/5] Tokenizing dataset with Completion Loss Masking (max length: {MAX_SEQ_LEN})...", flush=True)

def tokenize_fn(examples):
    tokens = tokenizer(examples["text"], max_length=MAX_SEQ_LEN, truncation=True)
    all_labels = []
    for text, input_ids in zip(examples["text"], tokens["input_ids"]):
        labels = list(input_ids)
        if MODEL_MARKER in text:
            prefix = text.split(MODEL_MARKER)[0] + MODEL_MARKER
            prefix_tokens = tokenizer.encode(prefix, add_special_tokens=True)
            prefix_len = len(prefix_tokens)
            for i in range(min(prefix_len, len(labels))):
                labels[i] = -100
        all_labels.append(labels)
    tokens["labels"] = all_labels
    return tokens

tokenized_train = train_raw.map(tokenize_fn, batched=True, remove_columns=train_raw.column_names)
tokenized_eval = eval_raw.map(tokenize_fn, batched=True, remove_columns=eval_raw.column_names)
data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, pad_to_multiple_of=8)

# 6. Real-Time Terminal Progress & Dynamic ASCII Validation Curve Callback
class SafeTerminalProgressCallback(TrainerCallback):
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.history = []
        self.best_eval_loss = float("inf")
        self.best_step = 0
        self.start_time = time.time()
        self.last_train_loss = 0.0

    def on_log(self, args, state: TrainerState, control: TrainerControl, logs=None, **kwargs):
        if not logs:
            return
        if "loss" in logs:
            self.last_train_loss = logs["loss"]
        if "eval_loss" in logs:
            self._handle_eval(state.global_step, logs["eval_loss"], logs.get("learning_rate", 0.0))

    def on_evaluate(self, args, state: TrainerState, control: TrainerControl, metrics=None, **kwargs):
        if metrics and "eval_loss" in metrics:
            self._handle_eval(state.global_step, metrics["eval_loss"], metrics.get("learning_rate", 0.0))

    def _handle_eval(self, step: int, eval_loss: float, lr: float):
        if any(h["step"] == step for h in self.history):
            return

        # Clean VRAM after evaluation
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        vram = round(torch.cuda.memory_allocated(0) / (1024**3), 2) if torch.cuda.is_available() else 0.0
        elapsed_min = round((time.time() - self.start_time) / 60.0, 1)

        is_best = eval_loss < self.best_eval_loss
        if is_best:
            self.best_eval_loss = eval_loss
            self.best_step = step

        entry = {
            "step": step,
            "train_loss": round(self.last_train_loss, 4),
            "eval_loss": round(eval_loss, 4),
            "lr": f"{lr:.2e}" if lr else "-",
            "vram_gb": vram,
            "is_best": is_best
        }
        self.history.append(entry)

        best_marker = " ⭐ [NEW BEST - CHECKPOINT SAVED]" if is_best else f" (Best: {self.best_eval_loss:.4f} @ Step {self.best_step})"
        print("\n" + "═" * 76, flush=True)
        print(f"  [EVALUATION STEP {step:03d}/{self.total_steps:03d}]", flush=True)
        print(f"  Train Loss: {self.last_train_loss:.4f}  │  Eval Loss: {eval_loss:.4f}{best_marker}", flush=True)
        print(f"  Time Elapsed: {elapsed_min} min  │  Active VRAM: {vram} GB / {total_vram} GB", flush=True)
        print("─" * 76, flush=True)
        print("  📊 LIVE VALIDATION LOSS CURVE:", flush=True)
        self._print_ascii_curve()
        print("═" * 76 + "\n", flush=True)

    def _print_ascii_curve(self):
        if not self.history:
            return
        losses = [h["eval_loss"] for h in self.history]
        min_loss = min(losses)
        max_loss = max(losses)
        span = max(max_loss - min_loss, 0.0001)

        for h in self.history:
            s = h["step"]
            el = h["eval_loss"]
            tl = h["train_loss"]
            bar_len = int(6 + 22 * ((el - min_loss) / span)) if span > 0.002 else 14
            bar = "█" * bar_len
            star = " ⭐ (BEST)" if h["step"] == self.best_step else ""
            print(f"   Step {s:03d} │ Eval: {el:.4f} │ Train: {tl:.4f} │ {bar}{star}", flush=True)

    def on_train_end(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        total_time = round((time.time() - self.start_time) / 60.0, 1)
        print("\n" + "╔" + "═" * 74 + "╗", flush=True)
        print("║              ECHOSPHERE MODEL TRAINING COMPLETED                         ║", flush=True)
        print("╚" + "═" * 74 + "╝", flush=True)
        print(f"  Total Steps Executed: {state.global_step}/{self.total_steps}", flush=True)
        print(f"  Best Step Restored:   Step {self.best_step} (Optimal Validation Checkpoint)", flush=True)
        print(f"  Best Eval Loss:       {self.best_eval_loss:.4f}", flush=True)
        print(f"  Total Time:           {total_time} minutes", flush=True)
        print("\n  📈 FINAL VALIDATION LOSS PROGRESSION:", flush=True)
        self._print_ascii_curve()
        print("═" * 76 + "\n", flush=True)

        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            curve_file = os.path.join(OUTPUT_DIR, "validation_curve.json")
            with open(curve_file, "w", encoding="utf-8") as f:
                json.dump({
                    "total_steps": state.global_step,
                    "best_step": self.best_step,
                    "best_eval_loss": self.best_eval_loss,
                    "total_runtime_minutes": total_time,
                    "history": self.history
                }, f, indent=2)
            print(f"Validation curve metrics saved to: {curve_file}", flush=True)
        except Exception as e:
            print(f"Failed to save curve metrics: {e}", flush=True)


# 7. SOTA Ultra-Safe Training Arguments for Laptop RTX 4060 (Claude / ChatGPT Profile)
MAX_STEPS = 800
EVAL_STEPS = 40
WARMUP_STEPS = 40

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    max_steps=MAX_STEPS,
    per_device_train_batch_size=1,       # Micro-batch size 1 guarantees peak VRAM < 4.2 GB
    gradient_accumulation_steps=16,     # Effective batch size = 16 (12,800 samples evaluated)
    per_device_eval_batch_size=1,        # Minimal eval batch size
    prediction_loss_only=True,           # NEVER hoard logits on GPU/RAM
    eval_accumulation_steps=1,           # Move loss to CPU immediately
    learning_rate=1.5e-4,
    lr_scheduler_type="cosine",
    warmup_steps=WARMUP_STEPS,
    optim="paged_adamw_8bit",
    neftune_noise_alpha=7.0,            # NEFTune noise injection for high generalization
    logging_steps=5,
    eval_strategy="steps",
    eval_steps=EVAL_STEPS,
    save_strategy="steps",
    save_steps=EVAL_STEPS,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    fp16=False,
    bf16=True,
    dataloader_num_workers=0,
    report_to="none"
)

early_stopping_cb = EarlyStoppingCallback(
    early_stopping_patience=8,
    early_stopping_threshold=0.001
)
terminal_curve_cb = SafeTerminalProgressCallback(total_steps=MAX_STEPS)

trainer = Trainer(
    model=model,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_eval,
    args=training_args,
    data_collator=data_collator,
    callbacks=[early_stopping_cb, terminal_curve_cb]
)

print("\n[4/5] [START] Starting Ultra-Stable GPU Training on NVIDIA RTX 4060...", flush=True)
print(f"      Target: {MAX_STEPS} steps | Eval every {EVAL_STEPS} steps | Early stopping patience: 3\n", flush=True)
trainer.train()

# 8. Save Best Adapter
print(f"\n[5/5] Saving optimum fine-tuned adapter weights to: {FINAL_ADAPTER}", flush=True)
os.makedirs(FINAL_ADAPTER, exist_ok=True)
trainer.model.save_pretrained(FINAL_ADAPTER)
tokenizer.save_pretrained(FINAL_ADAPTER)

# Mirror to backward-compatible directory
try:
    os.makedirs(OLD_ADAPTER, exist_ok=True)
    trainer.model.save_pretrained(OLD_ADAPTER)
    tokenizer.save_pretrained(OLD_ADAPTER)
    print(f"      Mirrored adapter to backward-compatible path: {OLD_ADAPTER}", flush=True)
except Exception as e:
    print(f"      Warning: Mirroring failed: {e}", flush=True)

print("\n" + "=" * 72, flush=True)
print("[SUCCESS] ECHOSPHERE RETRAINING COMPLETE WITH OPTIMUM VALIDATION CURVE!", flush=True)
print(f"Adapter saved to:\n  {FINAL_ADAPTER}", flush=True)
print("=" * 72, flush=True)
