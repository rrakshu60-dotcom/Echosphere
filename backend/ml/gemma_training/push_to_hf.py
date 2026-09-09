import os
from huggingface_hub import HfApi, create_repo

HF_TOKEN = "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"
REPO_ID = "RakshiRoxy/echosphere-campus-gemma-2b"
LOCAL_DIR = os.path.join(os.path.dirname(__file__), "output_gemma_campus_model", "final_adapter")

print(f"Connecting to Hugging Face with token...")
api = HfApi(token=HF_TOKEN)

try:
    print(f"Creating repository if not exists: {REPO_ID}")
    create_repo(repo_id=REPO_ID, token=HF_TOKEN, repo_type="model", exist_ok=True, private=False)
except Exception as e:
    print(f"Repo create info: {e}")

print(f"Uploading files from {LOCAL_DIR} to {REPO_ID}...")
api.upload_folder(
    folder_path=LOCAL_DIR,
    repo_id=REPO_ID,
    repo_type="model",
    token=HF_TOKEN
)

print(f"\n[SUCCESS] Model successfully pushed to Hugging Face:")
print(f"  https://huggingface.co/{REPO_ID}")
