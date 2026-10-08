import urllib.request
import json

try:
    req = urllib.request.Request("https://echosphere-backend-9lv8.onrender.com/openapi.json", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as res:
        schema = json.loads(res.read().decode())
        paths = schema.get("paths", {})
        print("Paths on Render:")
        for path, methods in paths.items():
            print(f"  {path}: {list(methods.keys())}")
except Exception as e:
    print("Error:", e)
