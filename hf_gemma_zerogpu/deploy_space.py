import os
import sys
from huggingface_hub import HfApi, create_repo

HF_TOKEN = os.getenv("HF_TOKEN", "")
SPACE_ID = "RakshiRoxy/echosphere-campus-ai"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

print(f"Connecting to Hugging Face with user token...")
api = HfApi(token=HF_TOKEN)

try:
    print(f"Creating Hugging Face Space if not exists: {SPACE_ID}")
    create_repo(
        repo_id=SPACE_ID,
        token=HF_TOKEN,
        repo_type="space",
        space_sdk="gradio",
        exist_ok=True,
        private=False
    )
    print(f"[OK] Space repository verified: https://huggingface.co/spaces/{SPACE_ID}")
except Exception as e:
    print(f"Space create note: {e}")

print(f"Uploading Space files from {LOCAL_DIR}...")
api.upload_folder(
    folder_path=LOCAL_DIR,
    repo_id=SPACE_ID,
    repo_type="space",
    token=HF_TOKEN,
    ignore_patterns=["deploy_space.py", "__pycache__/*", "*.pyc"]
)

# Set the HF_TOKEN secret on the space so it can download the gated google/gemma-2-2b-it base model
try:
    print("Setting HF_TOKEN secret on the space for gated Gemma access...")
    api.add_space_secret(
        repo_id=SPACE_ID,
        key="HF_TOKEN",
        value=HF_TOKEN
    )
    print("[OK] HF_TOKEN secret configured.")
except Exception as se:
    print(f"Secret configuration note: {se}")

# Request ZeroGPU hardware
try:
    print("Requesting ZeroGPU hardware (zero-a10g)...")
    api.request_space_hardware(
        repo_id=SPACE_ID,
        hardware="zero-a10g"
    )
    print("[OK] ZeroGPU hardware requested successfully!")
except Exception as he:
    print(f"Hardware request note: {he}")

print("\n" + "="*60)
print(f"[SUCCESS] EchoSphere Campus Gemma Space deployed successfully!")
print(f"Space URL: https://huggingface.co/spaces/{SPACE_ID}")
print(f"Public API Endpoint: https://rakshiroxy-echosphere-campus-ai.hf.space/generate")
print("="*60 + "\n")
