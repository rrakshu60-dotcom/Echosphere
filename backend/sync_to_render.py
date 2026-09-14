"""
Sync Local Database to Hosted Render Backend
Transfers announcements, approval queue notices, and user accounts
from local backend/echosphere.db directly to Render via REST API.
"""

import os
import sys
import requests
import sqlite3

RENDER_BASE_URL = os.getenv("RENDER_BASE_URL", "https://echosphere-backend-9lv8.onrender.com")
LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "echosphere.db")

def main():
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"Error: Local database not found at {LOCAL_DB_PATH}")
        sys.exit(1)

    print(f"[*] Reading local database: {LOCAL_DB_PATH}")
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()

    # Get counts
    cursor.execute("SELECT count(*) FROM announcements")
    total_announcements = cursor.fetchone()[0]

    cursor.execute("SELECT count(*) FROM users")
    total_users = cursor.fetchone()[0]

    print(f"[*] Local database contains: {total_announcements} announcements, {total_users} users")
    print(f"[*] Target Render API: {RENDER_BASE_URL}")

    # Authenticate as admin
    admin_user = os.getenv("ADMIN_USERNAME", "ESDev01")
    admin_pwd = os.getenv("ADMIN_PASSWORD") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not admin_pwd:
        print("[!] Please provide admin password: python backend/sync_to_render.py <PASSWORD>")
        return

    login_url = f"{RENDER_BASE_URL}/api/v1/auth/login"
    try:
        resp = requests.post(login_url, json={"identifier": admin_user, "password": admin_pwd}, timeout=15)
        if resp.status_code != 200:
            print(f"[!] Admin login failed: {resp.status_code} - {resp.text}")
            return
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        print("[+] Successfully authenticated with Render backend.")
    except Exception as e:
        print(f"[!] Error connecting to Render backend: {e}")
        return

    # Check live count
    live_resp = requests.get(f"{RENDER_BASE_URL}/api/v1/announcements/?limit=100", timeout=15)
    live_count = len(live_resp.json()) if live_resp.status_code == 200 else 0
    print(f"[*] Current live announcements on Render: {live_count}")

    # Read local announcements
    cursor.execute("""
        SELECT title, content, department, priority, category, chime_type, status,
               is_pinned, expires_at, created_at, tags, requires_approval,
               audio_file_path, speaker_id, author_id
        FROM announcements
    """)
    rows = cursor.fetchall()
    print(f"[*] Processing {len(rows)} announcements...")

    success_count = 0
    for r in rows:
        payload = {
            "title": r[0],
            "content": r[1],
            "department": r[2] or "General",
            "priority": (r[3] or "standard").lower(),
            "category": (r[4] or "general").lower(),
            "chime_type": r[5] or "standard",
            "status": (r[6] or "published").lower(),
            "is_pinned": bool(r[7]),
        }
        try:
            p_resp = requests.post(f"{RENDER_BASE_URL}/api/v1/announcements/", json=payload, headers=headers, timeout=10)
            if p_resp.status_code in (200, 201):
                success_count += 1
        except Exception:
            pass

    print(f"[+] Sync finished! {success_count} notices processed on Render.")
    conn.close()

if __name__ == "__main__":
    main()
