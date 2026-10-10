import os
import sys
import requests

def test_kokoro_endpoint(api_url: str):
    clean_url = api_url.strip().rstrip("/")
    print(f"=== Testing Kokoro-82M AI Worker: {clean_url} ===")
    
    # 1. Health / Web UI check
    try:
        r = requests.get(f"{clean_url}/web", timeout=10)
        print(f"[*] Web UI status: {r.status_code}")
    except Exception as e:
        print(f"[-] Web UI note: {e}")

    # 2. Test speech synthesis endpoint
    target = f"{clean_url}/v1/audio/speech"
    payload = {
        "input": "Attention. Official EchoSphere campus announcement test broadcast.",
        "voice": "af_heart",
        "model": "kokoro",
        "response_format": "mp3",
    }
    headers = {"Content-Type": "application/json"}
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    print(f"[*] Sending synthesis request to {target}...")
    try:
        res = requests.post(target, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            out_file = "test_kokoro_output.mp3"
            with open(out_file, "wb") as f:
                f.write(res.content)
            print(f"[SUCCESS] Received {len(res.content)} bytes from Kokoro-82M! Saved to {out_file}")
            return True
        else:
            print(f"[ERROR] Kokoro endpoint returned status {res.status_code}: {res.text[:200]}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to connect to Kokoro worker: {e}")
        return False

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("KOKORO_API_URL", "")
    if not url:
        print("Usage: python test_hf_kokoro.py <https://your-space.hf.space>")
        sys.exit(1)
    test_kokoro_endpoint(url)
