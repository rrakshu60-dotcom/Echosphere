import urllib.request
import json

url = "https://echosphere-backend-9lv8.onrender.com/api/v1/announcements?limit=100"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.loads(res.read().decode())
        print(f"Render DB returned {len(data)} announcements!")
        for item in data[:20]:
            print(f"  ID: {item.get('id')}, Title: {item.get('title')}")
except Exception as e:
    print("Error querying Render:", e)
