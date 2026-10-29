"""
Print the device key to flash into a speaker (hardware/ESp32/wifi_secrets.h).

The key is derived from the speaker's MAC and SPEAKER_KEY_SECRET (or JWT_SECRET_KEY when that is
unset), so run this with the same secret the backend uses, e.g. from backend/.env:

    python backend/scripts/speaker_device_key.py D4:F3:2D:22:2A:CB 8C:AA:B5:37:30:B4

A platform admin can also read it from GET /api/v1/hardware/speakers/{id}/device-key.
"""
import os
import sys

from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
sys.path.insert(0, BACKEND_DIR)

if not (os.getenv("SPEAKER_KEY_SECRET") or os.getenv("JWT_SECRET_KEY")):
    sys.exit("Set SPEAKER_KEY_SECRET or JWT_SECRET_KEY (as on the backend) first.")

from app.core.speaker_auth import device_key_for  # noqa: E402

if len(sys.argv) < 2:
    sys.exit(__doc__)
for mac in sys.argv[1:]:
    print(f"{mac.upper()}  {device_key_for(mac)}")
