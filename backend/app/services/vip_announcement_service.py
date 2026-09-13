import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums.announcement import AnnouncementPriority
from app.models.announcement import Announcement
from app.models.announcement_vip_protocol import AnnouncementVipProtocol
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.models.user import User
from app.schemas.vip_protocol import VipProtocolUpdateRequest
from app.services.ai_service import call_modern_gemini
from app.services.conflict_service import EXAM_KEYWORDS
from app.services.hardware_speaker_service import (
    enqueue_and_broadcast_announcement,
    publish_mqtt_command,
    queue_command_for_nodes,
)
from app.services.tts_service import generate_announcement_audio_sync

logger = logging.getLogger("echosphere.vip_protocol")

# Dignitary detection keywords
VIP_KEYWORDS = [
    "chief guest",
    "dignitary",
    "keynote speaker",
    "guest of honour",
    "guest of honor",
    "distinguished guest",
    "honorable minister",
    "hon'ble",
    "inauguration by",
    "inaugurated by",
    "presided by",
    "special guest",
]

# Words that indicate false alarms
FALSE_ALARM_PHRASES = [
    "guest pass",
    "guest room",
    "guest coupon",
    "guest house",
    "guest lecturer from 1st sem",
    "guest pass fee",
]


def is_potential_vip_notice(text: str) -> bool:
    """Fast rule-based pre-filter to detect whether a notice describes a VIP / Chief Guest."""
    lower_text = text.lower()
    for phrase in FALSE_ALARM_PHRASES:
        if phrase in lower_text:
            return False
    return any(kw in lower_text for kw in VIP_KEYWORDS)


def extract_vip_details_heuristic(text: str, event_dt: datetime) -> Dict[str, any]:
    """
    Robust rule-based entity extractor fallback when cloud LLM is unreachable or offline.
    """
    lower = text.lower()
    guest_name = "Distinguished Dignitary"
    guest_title = "Chief Guest"
    event_name = "Campus Special Event"
    venue = "Central Auditorium"

    # Name pattern matching:
    # 1. Check for honorific titles first (Dr., Prof., Shri, Smt., Mr.)
    honorific_match = re.search(r"\b(Dr\.|Prof\.|Shri|Smt\.|Mr\.)\s+([A-Z][a-zA-Z\.\s]{1,30}?)(?=[,\n\r]|\s+will|\s+is|\s+former|\s+has|\s+to|\s+and\b)", text)
    if honorific_match:
        guest_name = f"{honorific_match.group(1)} {honorific_match.group(2).strip()}"
    else:
        # 2. Check "Name will be the Chief Guest"
        before_vip = re.search(r"([A-Z][a-zA-Z\.\s]{2,25}?)\s+(?:will be|is|as)\s+(?:the\s+)?(?:chief guest|guest of honour|keynote speaker)", text, re.IGNORECASE)
        if before_vip and len(before_vip.group(1).strip().split()) <= 4:
            guest_name = before_vip.group(1).strip()
        else:
            # 3. Check "Chief Guest: Name" or "Chief Guest Name"
            after_vip = re.search(r"(?:chief guest|guest of honour|keynote speaker)(?:\s*:|\s+is|\s+will be)?\s+([A-Z][a-zA-Z\.\s]{2,25}?)(?=[,\n\r]|\s+and|\s+will|\s+to|\s+from)", text, re.IGNORECASE)
            if after_vip and len(after_vip.group(1).strip().split()) <= 4:
                guest_name = after_vip.group(1).strip()

    # Title / Organization matching
    title_match = re.search(
        r"\b(former\s+[A-Za-z\s]+|chairman[^\n,.]*|director[^\n,.]*|ceo[^\n,.]*|founder[^\n,.]*|scientist[^\n,.]*|minister[^\n,.]*|president[^\n,.]*|vice chancellor[^\n,.]*)",
        text,
        re.IGNORECASE,
    )
    if title_match:
        guest_title = title_match.group(0).strip().title()

    # Venue matching
    if "auditorium" in lower:
        venue = "Central Auditorium"
    elif "seminar hall" in lower:
        hall_m = re.search(r"(seminar hall\s*(?:[a-zA-Z0-9]+)?)", text, re.IGNORECASE)
        venue = hall_m.group(1).title() if hall_m else "Seminar Hall"
    elif "quadrangle" in lower:
        venue = "Campus Quadrangle"

    # Event matching
    event_m = re.search(r"([A-Z][a-zA-Z0-9\s]{3,40}(?:Symposium|Conference|Inauguration|Summit|Fest|Meet|Workshop|Celebration))", text)
    if event_m:
        event_name = event_m.group(1).strip()

    time_str = event_dt.strftime("%I:%M %p")
    spoken_script = (
        f"Attention faculty and students. EchoSphere is proud to announce that distinguished Chief Guest, "
        f"{guest_name}, {guest_title}, will be gracing our campus today for the {event_name}. "
        f"The inaugural session commences at {time_str} in the {venue}. "
        f"All attendees and faculty members are cordially requested to take their seats 15 minutes prior to commencement."
    )

    return {
        "is_vip": True,
        "confidence_score": 0.88,
        "guest_name": guest_name,
        "guest_title": guest_title,
        "guest_organization": None,
        "event_name": event_name,
        "venue": venue,
        "spoken_script": spoken_script,
        "regional_script": f"Mukhyastithigalaadha {guest_name} avarannu samstheyatarafadinda hardikavagi swagatisuttēve.",
    }


def analyze_and_extract_vip(db: Session, announcement_id: int) -> Optional[AnnouncementVipProtocol]:
    """
    Analyzes an announcement using Gemini (or heuristic fallback) to extract dignitary
    details, generate an institutional radio script, synthesize ceremonial audio,
    and persist the VIP protocol record.
    """
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        return None

    combined_text = f"{ann.title}\n{ann.description}"
    if not is_potential_vip_notice(combined_text):
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    event_dt = ann.scheduled_at or (now + timedelta(hours=2))

    extracted = None

    # 1. Try Gemini Structured Extraction
    prompt = f"""You are an elite institutional Master of Ceremonies and Protocol Officer for a prestigious university.
Analyze the following campus notice to extract Chief Guest / VIP Dignitary details:

---
{combined_text}
---

Respond ONLY with a valid JSON object matching this schema:
{{
  "is_vip": true,
  "confidence_score": 0.95,
  "guest_name": "Full name with honorifics (e.g. Dr. K. Sivan)",
  "guest_title": "Designation/Affiliation (e.g. Former Chairman, ISRO)",
  "guest_organization": "Organization name or null",
  "event_name": "Name of symposium / ceremony",
  "venue": "Hall / Auditorium / Portico",
  "spoken_script": "A formal, welcoming, institutional radio announcement script suitable for PA speaker broadcast with proper pacing and respectful tone. Max 60 words.",
  "regional_script": "One brief polite welcome line in Kannada or Hindi or null"
}}
If this is not an actual dignitary event (e.g. routine guest pass, meme, student club), set is_vip to false and confidence_score below 0.5.
"""

    raw_response, model_used = call_modern_gemini(prompt)
    if raw_response:
        try:
            cleaned_json = raw_response.strip()
            if "```json" in cleaned_json:
                cleaned_json = cleaned_json.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_json:
                cleaned_json = cleaned_json.split("```")[1].split("```")[0].strip()
            parsed = json.loads(cleaned_json)
            if parsed.get("is_vip") and float(parsed.get("confidence_score", 0)) >= 0.80:
                extracted = parsed
        except Exception as e:
            logger.debug(f"Gemini JSON parse fallback for VIP extraction: {e}")

    # 2. Fallback to heuristic parser if Gemini returned None
    if not extracted:
        extracted = extract_vip_details_heuristic(combined_text, event_dt)

    if not extracted or not extracted.get("is_vip"):
        return None

    # 3. Synthesize ceremonial audio with Kokoro-82M TTS + Ceremonial Chime
    audio_url = None
    try:
        audio_info = generate_announcement_audio_sync(
            announcement_id=ann.id,
            text=extracted["spoken_script"],
            gender="female",
            accent="british",
            voice_preset="british_female",
            chime_type="ceremonial",
            priority="HIGH",
            category="VIP Protocol",
        )
        audio_url = audio_info.get("url_path")
    except Exception as te:
        logger.warning(f"Ceremonial audio synthesis error: {te}")

    # 4. Save or update AnnouncementVipProtocol record
    protocol = db.query(AnnouncementVipProtocol).filter(AnnouncementVipProtocol.announcement_id == announcement_id).first()
    if not protocol:
        protocol = AnnouncementVipProtocol(
            announcement_id=ann.id,
            guest_name=extracted.get("guest_name", "Distinguished Guest"),
            guest_title=extracted.get("guest_title", "Chief Guest"),
            guest_organization=extracted.get("guest_organization"),
            event_name=extracted.get("event_name", ann.title),
            venue=extracted.get("venue", "Central Auditorium"),
            event_datetime=event_dt,
            arrival_datetime=event_dt - timedelta(minutes=15),
            spoken_script=extracted["spoken_script"],
            regional_script=extracted.get("regional_script"),
            voice_profile="british_female",
            audio_url=audio_url,
            confidence_score=float(extracted.get("confidence_score", 0.90)),
            status="VERIFIED",
        )
        db.add(protocol)
    else:
        protocol.guest_name = extracted.get("guest_name", protocol.guest_name)
        protocol.guest_title = extracted.get("guest_title", protocol.guest_title)
        protocol.event_name = extracted.get("event_name", protocol.event_name)
        protocol.venue = extracted.get("venue", protocol.venue)
        protocol.spoken_script = extracted.get("spoken_script", protocol.spoken_script)
        protocol.regional_script = extracted.get("regional_script", protocol.regional_script)
        protocol.audio_url = audio_url or protocol.audio_url
        protocol.confidence_score = float(extracted.get("confidence_score", protocol.confidence_score))

    # Elevate announcement priority to HIGH
    ann.priority = AnnouncementPriority.HIGH
    db.commit()
    db.refresh(protocol)
    logger.info(f"✨ [VIP DETECTED] Chief Guest '{protocol.guest_name}' extracted for Announcement #{ann.id}")
    return protocol


def filter_suppressed_exam_nodes(db: Session, target_nodes: List[SpeakerNode]) -> Tuple[List[SpeakerNode], List[str]]:
    """
    Acoustic Exam Hall Shield:
    Inspects campus notices for active exams and filters out speaker nodes
    installed in academic exam blocks to prevent mid-test disturbances.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    active_exams = (
        db.query(Announcement)
        .filter(
            Announcement.status.in_(["Published", "PUBLISHED"]),
            Announcement.scheduled_at <= now + timedelta(hours=2),
            Announcement.scheduled_at >= now - timedelta(hours=3),
        )
        .all()
    )

    from app.models.department import Department
    all_depts = db.query(Department).all()
    exam_dept_ids = set()
    for exam in active_exams:
        comb = f"{exam.title} {exam.description}".lower()
        if any(kw in comb for kw in EXAM_KEYWORDS):
            if exam.creator and exam.creator.department_id:
                exam_dept_ids.add(exam.creator.department_id)
            for d in all_depts:
                d_name = (d.name or "").lower()
                d_code = (d.code or "").lower()
                if (d_code and re.search(rf"\b{re.escape(d_code)}\b", comb)) or (d_name and d_name in comb):
                    exam_dept_ids.add(d.id)

    safe_nodes = []
    muted_node_names = []

    for node in target_nodes:
        # Check if node belongs to a department currently administering exams
        if node.department_id and node.department_id in exam_dept_ids:
            muted_node_names.append(node.name)
        else:
            safe_nodes.append(node)

    return safe_nodes, muted_node_names


def dispatch_vip_arrival_fanfare(
    db: Session,
    announcement_id: int,
    current_user: User,
    target_zone: str = "Portico-Auditorium",
    custom_note: Optional[str] = None,
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
) -> dict:
    """
    On-Demand Live Arrival Fanfare:
    Triggered when the dignitary's car reaches the portico.
    Fast-tracks an arrival announcement into the SpeakerQueue ahead of routine notices.
    """
    protocol = db.query(AnnouncementVipProtocol).filter(AnnouncementVipProtocol.announcement_id == announcement_id).first()
    if not protocol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VIP Protocol record not found for Announcement #{announcement_id}.",
        )

    ann = protocol.announcement
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Formulate arrival broadcast script
    arrival_text = (
        f"Attention faculty, delegates, and students. Distinguished Chief Guest, "
        f"{protocol.guest_name}, {protocol.guest_title}, has arrived at the campus. "
        f"We cordially invite delegates and attendees to accord a warm welcome as the dignitaries proceed to the {protocol.venue}."
    )
    if custom_note:
        arrival_text += f" {custom_note}"

    # Generate dedicated arrival fanfare audio
    audio_info = generate_announcement_audio_sync(
        announcement_id=ann.id,
        text=arrival_text,
        gender="female",
        accent="british",
        voice_preset="british_female",
        chime_type="ceremonial",
        priority="HIGH",
        category="VIP Arrival",
    )
    audio_full_url = f"{base_url}{audio_info['url_path']}"

    # Target Node Filtering with Exam Hall Shield
    all_nodes = db.query(SpeakerNode).filter(SpeakerNode.is_active == True).all()
    if target_zone in ("Portico", "Auditorium", "Portico-Auditorium"):
        zone_nodes = [n for n in all_nodes if any(z in (n.zone or "") for z in ("Auditorium", "Portico", "Main Entrance", "Quadrangle"))]
        if not zone_nodes:
            zone_nodes = all_nodes
    else:
        zone_nodes = all_nodes

    safe_nodes, muted_node_names = filter_suppressed_exam_nodes(db, zone_nodes)

    # Fast-Track SpeakerQueue Insertion (Position #2, right behind current broadcast)
    active_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()
    should_play = active_playing is None

    # Shift all queued items down by 1 to guarantee VIP notice plays next
    db.query(SpeakerQueue).filter(SpeakerQueue.status == "Queued").update({
        SpeakerQueue.queue_position: SpeakerQueue.queue_position + 1
    })

    q_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann.id).first()
    if not q_item:
        q_item = SpeakerQueue(
            announcement_id=ann.id,
            queue_position=1 if should_play else 2,
            status="Playing" if should_play else "Next in Queue",
            scheduled_time=now,
            played_at=now if should_play else None,
            duration_seconds=int(len(arrival_text.split()) / 2.5) + 5,
        )
        db.add(q_item)
    else:
        q_item.queue_position = 1 if should_play else 2
        q_item.status = "Playing" if should_play else "Next in Queue"
        q_item.scheduled_time = now
        q_item.played_at = now if should_play else None
        q_item.duration_seconds = int(len(arrival_text.split()) / 2.5) + 5

    protocol.is_arrival_announced = True
    protocol.arrival_datetime = now
    db.commit()

    # Form and dispatch hardware control packet
    topic = "echosphere/speakers/vip/arrival"
    payload = {
        "command": "PLAY_VIP_ANNOUNCEMENT",
        "announcement_id": ann.id,
        "guest_name": protocol.guest_name,
        "title": f"VIP Arrival: {protocol.guest_name}",
        "message": arrival_text,
        "audio_url": audio_full_url,
        "volume": 88,
        "duration_seconds": q_item.duration_seconds,
        "timestamp": now.isoformat(),
    }

    publish_mqtt_command(topic, payload)
    queue_command_for_nodes(payload, db=db)

    logger.info(f"🎺 [VIP ARRIVAL FANFARE DISPATCHED] {protocol.guest_name} -> Broadcast on {topic}")
    return {
        "status": "success",
        "guest_name": protocol.guest_name,
        "audio_url": audio_full_url,
        "queue_position": q_item.queue_position,
        "queue_status": q_item.status,
        "muted_exam_nodes": muted_node_names,
        "active_nodes_count": len(safe_nodes),
    }


def evaluate_and_dispatch_vip_seating_calls(
    db: Session,
    simulated_now: Optional[datetime] = None,
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
) -> List[dict]:
    """
    Evaluates upcoming VIP events and triggers seating announcements at T-15 minutes.
    """
    now = simulated_now or datetime.now(timezone.utc).replace(tzinfo=None)
    upcoming_protocols = (
        db.query(AnnouncementVipProtocol)
        .filter(
            AnnouncementVipProtocol.is_seating_announced == False,
            AnnouncementVipProtocol.event_datetime <= now + timedelta(minutes=20),
            AnnouncementVipProtocol.event_datetime >= now - timedelta(minutes=5),
        )
        .all()
    )

    dispatched = []
    for proto in upcoming_protocols:
        ann = proto.announcement
        if getattr(ann, "status", None) not in ("Published", "PUBLISHED"):
            continue

        seating_call_text = (
            f"Attention all faculty, delegates, and registered attendees. "
            f"The {proto.event_name} featuring Chief Guest {proto.guest_name} "
            f"will commence in 15 minutes in the {proto.venue}. "
            f"All attendees are requested to take their seats promptly."
        )

        res = enqueue_and_broadcast_announcement(
            db=db,
            announcement_id=ann.id,
            title=f"Assembly Call: {proto.guest_name}",
            content=seating_call_text,
            department_code="ALL",
            zone="College-Wide",
            is_emergency=False,
            speaker_voice=proto.voice_profile,
            base_url=base_url,
        )

        proto.is_seating_announced = True
        db.commit()
        dispatched.append({
            "announcement_id": ann.id,
            "guest_name": proto.guest_name,
            "venue": proto.venue,
            "queue_position": res.get("queue_position"),
        })

    return dispatched
