"""
Speaker device keys.

Every speaker proves who it is with a per-device key sent in the X-Speaker-Key header (the MAC
address alone is printed on the board and visible on the network, so it is not a secret). The key
is derived from the speaker's MAC and a server secret, so nothing extra is stored in the database:

    key = HMAC-SHA256(SPEAKER_KEY_SECRET, "speaker-device:" + MAC upper-case), first 32 hex chars

SPEAKER_KEY_SECRET falls back to JWT_SECRET_KEY. Changing either secret changes every key, so the
speakers must be re-flashed with their new keys afterwards (see hardware/ESp32/README.md).
A platform admin can read a speaker's key from GET /api/v1/hardware/speakers/{id}/device-key,
or run backend/scripts/speaker_device_key.py with the same secret.
"""

import hashlib
import hmac
import os
import re
from typing import Optional

from fastapi import HTTPException, status

from app.core.security import SECRET_KEY

SPEAKER_KEY_HEADER = "X-Speaker-Key"
_MAC_RE = re.compile(r"([0-9A-F]{2}:){5}[0-9A-F]{2}")


def _secret() -> str:
    return os.getenv("SPEAKER_KEY_SECRET", "").strip() or SECRET_KEY


def normalize_mac(mac: Optional[str]) -> Optional[str]:
    value = (mac or "").strip().upper()
    return value if _MAC_RE.fullmatch(value) else None


def device_key_for(mac: str) -> str:
    normalized = normalize_mac(mac)
    if not normalized:
        raise ValueError("Invalid MAC address.")
    return hmac.new(_secret().encode(), f"speaker-device:{normalized}".encode(), hashlib.sha256).hexdigest()[:32]


def is_valid_device_key(mac: Optional[str], key: Optional[str]) -> bool:
    normalized = normalize_mac(mac)
    if not normalized or not key:
        return False
    return hmac.compare_digest(device_key_for(normalized), key.strip().lower())


def require_device_key(mac: Optional[str], key: Optional[str]) -> str:
    """The normalized MAC when the key matches it; 401 otherwise (same answer for every failure)."""
    if not is_valid_device_key(mac, key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Speaker authentication failed.")
    return normalize_mac(mac) or ""
