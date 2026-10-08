"""
Emergency utility module for EchoSphere.
Provides universal detection of emergency notices, critical alerts,
and evacuation broadcasts across all layers of the application.
"""
from typing import Any


def is_emergency_announcement(ann: Any) -> bool:
    """
    Universally detects whether an announcement represents an emergency,
    disaster, or critical campus alert across all possible representations:
    1. emergency_level in [EMERGENCY, CRITICAL]
    2. priority in [EMERGENCY, CRITICAL]
    3. Category name containing 'Emergency'
    4. Title or description containing emergency / evacuation / danger keywords
    """
    if not ann:
        return False

    # 1. Emergency Level check
    em_level = getattr(ann, "emergency_level", None)
    em_str = (getattr(em_level, "value", em_level) or "").upper()
    if "EMERG" in em_str or em_str == "CRITICAL":
        return True

    # 2. Priority check
    prio = getattr(ann, "priority", None)
    prio_str = (getattr(prio, "value", prio) or "").upper()
    if "EMERG" in prio_str or prio_str == "CRITICAL":
        return True

    # 3. Category relation check
    cat = getattr(ann, "category", None)
    cat_name = getattr(cat, "name", "") if cat else ""
    if "EMERG" in str(cat_name).upper():
        return True

    cat_id_name = str(getattr(ann, "category_name", "") or "")
    if "EMERG" in cat_id_name.upper():
        return True

    # 4. Title & Description keyword analysis
    title = str(getattr(ann, "title", "") or "").lower()
    desc = str(getattr(ann, "description", "") or "").lower()
    title_desc = f"{title} {desc}"

    emergency_keywords = (
        "emergency",
        "earthquake",
        "evacuat",
        "fire alert",
        "fire alarm",
        "immediate evacuation",
        "siren",
        "lockdown",
        "hazard",
        "gas leak",
        "chemical spill",
        "flood",
        "tsunami",
        "active threat",
        "disaster alert",
        "drill",
        "danger",
        "tremor",
        "cyclone",
        "explosion",
    )
    if any(k in title_desc for k in emergency_keywords):
        return True

    return False
