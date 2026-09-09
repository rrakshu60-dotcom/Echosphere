"""
EchoSphere Campus Gemma 2 QLoRA Fine-Tuning Pipeline
Fine-tunes Google Gemma 2 (2B-IT or 9B-IT) to institutional ChatGPT-Plus level performance:
- Parameter-Efficient Fine-Tuning (PEFT) via QLoRA (4-bit NF4 quantization)
- High rank LoRA (r=32, alpha=64) on attention and MLP projections
- Supervised Fine-Tuning Trainer (SFTTrainer) on Gemma chat template
- Target models: google/gemma-2-2b-it (recommended for on-device/edge), google/gemma-2-9b-it
"""

import os
import torch
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("EchoSphere.GemmaTraining")
logging.basicConfig(level=logging.INFO)

DATASET_PATH = os.path.join(os.path.dirname(__file__), "echosphere_campus_gemma_dataset.jsonl")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_gemma_campus_model")


def run_training(
    model_id: str = "google/gemma-2-2b-it",
    epochs: int = 3,
    batch_size: int = 4,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 1024,
    output_dir: str = OUTPUT_DIR
):
    try:
        from datasets import load_dataset
        from transformers import (
            AutoTokenizer,
            AutoModelForCausalLM,
            BitsAndBytesConfig,
            TrainingArguments
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer
    except ImportError as e:
        logger.error(
            f"Training dependencies not installed: {e}\n"
            "To train Gemma on a GPU machine, run:\n"
            "pip install torch transformers peft trl bitsandbytes datasets accelerate"
        )
        return False

    logger.info(f"Loading dataset from: {DATASET_PATH}")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    logger.info(f"Configuring 4-bit NormalFloat Quantization for {model_id}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    logger.info(f"Downloading tokenizer & base model weights: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        trust_remote_code=True
    )
    model = prepare_model_for_kbit_training(model)

    # LoRA target modules for Gemma 2
    peft_config = LoraConfig(
        r=32,
        lora_alpha=64,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        optim="paged_adamw_8bit",
        logging_steps=25,
        save_strategy="epoch",
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        report_to="none"
    )

    logger.info("Starting Supervised Fine-Tuning (SFTTrainer)...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        tokenizer=tokenizer,
        args=training_args,
    )

    trainer.train()
    trainer.model.save_pretrained(os.path.join(output_dir, "final_adapter"))
    tokenizer.save_pretrained(os.path.join(output_dir, "final_adapter"))
    logger.info(f"Training complete! Adapter weights saved to: {os.path.join(output_dir, 'final_adapter')}")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EchoSphere Gemma 2 Fine-Tuning Pipeline")
    parser.add_argument("--model", type=str, default="google/gemma-2-2b-it", help="Base Gemma model ID")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Per device batch size")
    args = parser.parse_args()

    run_training(model_id=args.model, epochs=args.epochs, batch_size=args.batch_size)
