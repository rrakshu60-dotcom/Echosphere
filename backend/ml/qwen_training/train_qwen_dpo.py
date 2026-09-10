# pyright: reportMissingImports=false
"""
EchoSphere Qwen 2.5 3B Stage 2 DPO (Direct Preference Optimization) Alignment Engine
Reinforces:
1. Zero false refusal on conversational greetings ("hi", "hello")
2. Strict non-compliance with prompt injection and privilege escalation attacks
3. Deep academic rigor for engineering coursework explanations
"""

import os
import sys
import gc
import json
import time
import shutil

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"

import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainerCallback,
)
from peft import PeftModel
from trl import DPOTrainer, DPOConfig

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DPO_DATASET_PATH = os.path.join(SCRIPT_DIR, "qwen_dpo_dataset.jsonl")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_qwen_model")
FINAL_ADAPTER = os.path.join(OUTPUT_DIR, "final_adapter")
DPO_ADAPTER = os.path.join(OUTPUT_DIR, "dpo_adapter")
PROGRESS_JSON = os.path.join(OUTPUT_DIR, "training_progress.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "training.log")
MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"

os.makedirs(OUTPUT_DIR, exist_ok=True)


class DualLogger:
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.logfile = open(filepath, "a", encoding="utf-8", buffering=1)

    def write(self, message):
        try:
            self.terminal.write(message)
            self.terminal.flush()
        except Exception:
            pass
        try:
            self.logfile.write(message)
            self.logfile.flush()
        except Exception:
            pass

    def flush(self):
        try:
            self.terminal.flush()
        except Exception:
            pass
        try:
            self.logfile.flush()
        except Exception:
            pass


sys.stdout = DualLogger(LOG_FILE)


class DPOProgressCallback(TrainerCallback):
    def __init__(self, total_steps: int, gpu_name: str):
        self.total_steps = total_steps
        self.gpu_name = gpu_name
        self.start_time = time.time()
        self.step = 0

    def on_step_end(self, args, state, control, **kwargs):
        self.step = state.global_step
        elapsed = max(time.time() - self.start_time, 0.001)
        sps = self.step / elapsed
        eta_sec = ((self.total_steps - self.step) / sps) if sps > 0 else 0.0
        vram = round(torch.cuda.memory_allocated(0) / (1024**3), 2) if torch.cuda.is_available() else 0.0
        percent = round((self.step / self.total_steps) * 100, 1)

        prog_data = {
            "status": "dpo_training",
            "model": "Qwen/Qwen2.5-3B-Instruct (DPO)",
            "gpu": self.gpu_name,
            "step": self.step,
            "total_steps": self.total_steps,
            "percent": percent,
            "elapsed_sec": round(elapsed, 1),
            "eta_sec": round(eta_sec, 1),
            "vram_gb": vram,
            "speed_steps_per_sec": round(sps, 3),
        }
        try:
            with open(PROGRESS_JSON, "w", encoding="utf-8") as f:
                json.dump(prog_data, f, indent=2)
        except Exception:
            pass


def load_curated_dpo_dataset(path: str, max_samples: int = 1500) -> Dataset:
    print(f"Loading DPO triplets from {path} (max: {max_samples})...", flush=True)
    prompts, chosens, rejecteds = [], [], []
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            data = json.loads(line)
            prompts.append(data["prompt"])
            chosens.append(data["chosen"])
            rejecteds.append(data["rejected"])
            if len(prompts) >= max_samples:
                break
    print(f"Loaded {len(prompts)} preference pairs for DPO alignment.", flush=True)
    return Dataset.from_dict({
        "prompt": prompts,
        "chosen": chosens,
        "rejected": rejecteds
    })


def run_dpo_training():
    print("\n" + "=" * 76)
    print("  ECHOSPHERE QWEN 2.5 3B :: STAGE 2 DPO ALIGNMENT ENGINE")
    print("=" * 76)

    if not torch.cuda.is_available():
        print("[ERROR] CUDA is required for DPO training.")
        return

    gpu_name = torch.cuda.get_device_name(0)
    total_vram = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    print(f"  Target GPU:      {gpu_name} ({total_vram} GB VRAM)")
    print(f"  SFT Adapter:     {FINAL_ADAPTER}")
    print(f"  DPO Dataset:     {DPO_DATASET_PATH}")
    print("=" * 76 + "\n")

    # 1. Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(FINAL_ADAPTER, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 2. Base Model (NF4 4-bit)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True
    )

    print("Loading base model in 4-bit NF4 precision...", flush=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        trust_remote_code=True
    )

    # 3. Attach trained SFT adapter as trainable PEFT policy
    print(f"Attaching SFT DoRA adapter from {FINAL_ADAPTER}...", flush=True)
    model = PeftModel.from_pretrained(base_model, FINAL_ADAPTER, is_trainable=True)

    # 4. Load Dataset
    dpo_dataset = load_curated_dpo_dataset(DPO_DATASET_PATH, max_samples=1200)

    # 5. DPO Hyperparameters
    TOTAL_STEPS = 150
    dpo_config = DPOConfig(
        output_dir=DPO_ADAPTER,
        max_steps=TOTAL_STEPS,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=5e-6,
        lr_scheduler_type="cosine",
        warmup_steps=15,
        bf16=True,
        gradient_checkpointing=True,
        max_length=512,
        beta=0.1,
        logging_steps=10,
        save_strategy="steps",
        save_steps=75,
        report_to="none"
    )

    callback = DPOProgressCallback(total_steps=TOTAL_STEPS, gpu_name=gpu_name)

    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # Handled automatically via adapter disable without extra VRAM
        args=dpo_config,
        train_dataset=dpo_dataset,
        processing_class=tokenizer,
        callbacks=[callback]
    )

    print("\nStarting DPO Preference Alignment Training (150 steps)...")
    print(f"Effective batch size: 4 | Beta: 0.1 | LR: 5e-6 | Cosine schedule\n", flush=True)

    t0 = time.time()
    train_result = trainer.train()
    total_time = round(time.time() - t0, 1)

    print("\n" + "=" * 76)
    print(f"  DPO ALIGNMENT COMPLETED IN {total_time}s ({round(total_time/60, 2)} min)!")
    print(f"  Final Training Loss: {train_result.training_loss:.4f}")
    print("=" * 76 + "\n")

    # Save aligned adapter
    print(f"Saving aligned DPO adapter to {DPO_ADAPTER}...", flush=True)
    trainer.save_model(DPO_ADAPTER)
    tokenizer.save_pretrained(DPO_ADAPTER)

    # Update final_adapter with DPO weights
    print(f"Updating production final_adapter at {FINAL_ADAPTER}...", flush=True)
    for fname in os.listdir(DPO_ADAPTER):
        src = os.path.join(DPO_ADAPTER, fname)
        dst = os.path.join(FINAL_ADAPTER, fname)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

    # Free memory
    del trainer, model, base_model
    gc.collect()
    torch.cuda.empty_cache()

    # Automatically trigger merge into standalone model
    print("\nTriggering merge_qwen_model.py to fuse DPO adapter into merged_model...", flush=True)
    merge_script = os.path.join(SCRIPT_DIR, "merge_qwen_model.py")
    if os.path.isfile(merge_script):
        import subprocess
        subprocess.run([sys.executable, merge_script], check=True)
        print("Standalone fused model updated with DPO alignment!", flush=True)


if __name__ == "__main__":
    run_dpo_training()
