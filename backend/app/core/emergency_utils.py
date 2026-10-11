"""
Emergency utility module for EchoSphere.
Provides universal detection of emergency notices, critical alerts,
and evacuation broadcasts across all layers of the application.
"""
from typing import Any


def is_emergency_announcement(ann: Any) -> bool:
    """
    Detects whether an announcement represents an active emergency, disaster,
    or critical campus alert.
    Requires explicit emergency designation (emergency_level or priority)
    to prevent false emergency sirens and queue lockouts on standard notices.
    """
    if not ann:
        return False

    # 1. Emergency Level check (Primary authority)
    em_level = getattr(ann, "emergency_level", None)
    em_str = (getattr(em_level, "value", em_level) or "").upper().strip()
    if "EMERG" in em_str or em_str == "CRITICAL":
        return True

    # 2. Priority check
    prio = getattr(ann, "priority", None)
    prio_str = (getattr(prio, "value", prio) or "").upper().strip()
    if "EMERG" in prio_str or prio_str == "CRITICAL":
        return True

    # If emergency_level is explicitly NORMAL or LOW, strictly enforce non-emergency
    if em_str in ("NORMAL", "LOW") and prio_str not in ("EMERGENCY", "CRITICAL"):
        return False

    # 3. Explicit emergency tag in title (e.g. manual [EMERGENCY REPEAT] or [EMERGENCY OVERRIDE])
    title = str(getattr(ann, "title", "") or "").upper()
    if "[EMERGENCY" in title or "EMERGENCY OVERRIDE" in title or "! EMERGENCY" in title:
        return True

    return False

