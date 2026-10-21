import os
import urllib.request
import json
import sys

RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "")
SERVICE_ID = "srv-dabdp2rtqb8s73fjp000"

def get_deploys():
    req = urllib.request.Request(
        f"https://api.render.com/v1/services/{SERVICE_ID}/deploys?limit=5",
        headers={"Authorization": f"Bearer {RENDER_API_KEY}", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        for item in data:
            d = item.get("deploy", {})
            commit_id = d.get("commit", {}).get("id", "none")[:7] if d.get("commit") else "none"
            commit_msg = d.get("commit", {}).get("message", "").strip().split("\n")[0] if d.get("commit") else ""
            print(f"Deploy ID: {d.get('id')}, Status: {d.get('status')}, Commit: {commit_id} ({commit_msg}), CreatedAt: {d.get('createdAt')}")

def trigger_deploy():
    req = urllib.request.Request(
        f"https://api.render.com/v1/services/{SERVICE_ID}/deploys",
        headers={"Authorization": f"Bearer {RENDER_API_KEY}", "Accept": "application/json", "Content-Type": "application/json"},
        data=json.dumps({"clearCache": "do_not_clear"}).encode("utf-8"),
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("Triggered deploy:", data.get("id"), "Status:", data.get("status"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "trigger":
        trigger_deploy()
    else:
        get_deploys()
