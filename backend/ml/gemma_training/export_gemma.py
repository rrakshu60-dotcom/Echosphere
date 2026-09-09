"""
EchoSphere Gemma Model Export & Quantization Utility
Merges LoRA adapter weights into base Gemma 2 and exports to:
1. Merged full precision / fp16 HuggingFace model.
2. GGUF format (q4_k_m) for on-device mobile execution (MediaPipe / llama.cpp / local edge).
"""

import os
import logging

logger = logging.getLogger("EchoSphere.GemmaExport")
logging.basicConfig(level=logging.INFO)


def export_merged_model(
    base_model_id: str = "google/gemma-2-2b-it",
    adapter_path: str = "./output_gemma_campus_model/final_adapter",
    output_merged_path: str = "./output_gemma_campus_model/merged_fp16"
):
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError as e:
        logger.error(f"Dependencies missing: {e}. Run: pip install torch transformers peft")
        return False

    logger.info(f"Loading base model: {base_model_id}")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(adapter_path)

    logger.info(f"Loading and merging LoRA adapter from: {adapter_path}")
    model = PeftModel.from_pretrained(base_model, adapter_path)
    merged_model = model.merge_and_unload()

    logger.info(f"Saving merged standalone model to: {output_merged_path}")
    merged_model.save_pretrained(output_merged_path)
    tokenizer.save_pretrained(output_merged_path)

    logger.info("Merged model ready!")
    print("\nTo convert to GGUF for on-device/mobile execution:")
    print(f"python llama.cpp/convert_hf_to_gguf.py {output_merged_path} --outtype q8_0")
    print(f"./llama.cpp/llama-quantize {output_merged_path}/ggml-model-q8_0.gguf ./gemma-campus-q4_k_m.gguf q4_k_m")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EchoSphere Gemma Export")
    parser.add_argument("--base_model", type=str, default="google/gemma-2-2b-it")
    parser.add_argument("--adapter", type=str, default="./output_gemma_campus_model/final_adapter")
    parser.add_argument("--output", type=str, default="./output_gemma_campus_model/merged_fp16")
    args = parser.parse_args()

    export_merged_model(args.base_model, args.adapter, args.output)
