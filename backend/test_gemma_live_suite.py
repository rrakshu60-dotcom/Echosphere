import json
import urllib.request
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

URL = "http://127.0.0.1:8008/generate"

test_cases = [
    {
        "name": "1. Student Academic Subject Tutoring (ML Coursework)",
        "prompt": "<start_of_turn>user\nExplain backpropagation in neural networks and why the chain rule of calculus is necessary.<end_of_turn>\n<start_of_turn>model\n"
    },
    {
        "name": "2. Student App Navigation Query",
        "prompt": "<start_of_turn>user\nHow do I bookmark important department circulars and filter by urgent notices in the app?<end_of_turn>\n<start_of_turn>model\n"
    },
    {
        "name": "3. Student Casual Chat Guardrail Refusal",
        "prompt": "<start_of_turn>user\nTell me a funny joke and recommend a good comedy movie for tonight.<end_of_turn>\n<start_of_turn>model\n"
    },
    {
        "name": "4. App Assistant Greeting & Persona (Clean Markdown, No Clutter)",
        "prompt": "<start_of_turn>user\nhello who are you<end_of_turn>\n<start_of_turn>model\n"
    }
]

print("=" * 70)
print("  ECHOSPHERE GEMMA 2 LIVE VERIFICATION SUITE")
print("=" * 70)

for tc in test_cases:
    print(f"\n[TEST CASE]: {tc['name']}")
    req_body = json.dumps({"prompt": tc["prompt"], "max_new_tokens": 220}).encode("utf-8")
    req = urllib.request.Request(URL, data=req_body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[LATENCY]: {data.get('duration_ms')} ms")
            print("[RESPONSE]:")
            print(data.get("text"))
            print("-" * 70)
    except Exception as e:
        print(f"[ERROR]: {e}")
