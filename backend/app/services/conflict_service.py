import datetime
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.enums.announcement import AnnouncementStatus
from app.models.announcement import Announcement
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

GENERIC_VENUES = {
    "",
    "campus",
    "college campus",
    "tbd",
    "online",
    "google meet",
    "zoom",
    "microsoft teams",
    "virtual",
    "n/a",
}

EXAM_KEYWORDS = [
    "exam",
    "examination",
    "mid-sem",
    "mid sem",
    "finals",
    "internal assessment",
    "ia 1",
    "ia 2",
    "ia test",
    "lab exam",
    "viva",
]

MAJOR_CAMPUS_EVENT_KEYWORDS = [
    "placement",
    "placement drive",
    "recruitment",
    "interview",
    "campus fest",
    "sports meet",
    "annual sports",
    "sports fest",
    "cultural fest",
    "hackathon",
    "symposium",
    "workshop",
    "annual day",
]

CAMPUS_ALTERNATIVE_VENUES = {
    "seminar hall b": ["Seminar Hall A", "Central Auditorium", "Conference Hall 1"],
    "seminar hall a": ["Seminar Hall B", "Central Auditorium", "Conference Hall 1"],
    "central auditorium": ["Mini Auditorium", "Seminar Hall A", "Open Air Theatre"],
    "mini auditorium": ["Central Auditorium", "Seminar Hall B"],
    "room 302": ["Room 303", "Room 304", "Seminar Hall A"],
    "room 301": ["Room 302", "Room 303", "Seminar Hall B"],
    "placement cell": ["Seminar Hall A", "Conference Hall 2", "Room 201"],
    "cs lab 1": ["CS Lab 2", "AI/ML Lab", "ISE Project Lab"],
}


class ConflictService:
    """
    AI Schedule Conflict & Overlap Detector.
    Scans active institutional circulars to detect venue collisions
    and clashing major academic events before publication.
    """

    @staticmethod
    def normalize_venue(venue: Optional[str]) -> str:
        """Standardize venue strings for collision comparison."""
        if not venue:
            return ""
        v = venue.strip().lower()
        v = re.sub(r'^(?:in|at|the)\s+', '', v)
        v = re.sub(r'[#\-_,]', ' ', v)
        v = re.sub(r'\s+', ' ', v).strip()
        return v

    @classmethod
    def are_venues_colliding(cls, venue_a: Optional[str], venue_b: Optional[str]) -> bool:
        """Determine whether two venue strings refer to the exact same facility."""
        norm_a = cls.normalize_venue(venue_a)
        norm_b = cls.normalize_venue(venue_b)

        if not norm_a or not norm_b:
            return False
        if norm_a in GENERIC_VENUES or norm_b in GENERIC_VENUES:
            return False

        if norm_a == norm_b:
            return True

        # Check common patterns: "Seminar Hall B" vs "Seminar Hall - B"
        if "seminar hall" in norm_a and "seminar hall" in norm_b:
            suffix_a = re.sub(r'.*seminar hall\s*', '', norm_a).strip()
            suffix_b = re.sub(r'.*seminar hall\s*', '', norm_b).strip()
            if suffix_a and suffix_b:
                return suffix_a == suffix_b
            return False

        # Room numbers: "room 302" vs "room #302"
        if "room" in norm_a and "room" in norm_b:
            num_a = re.findall(r'\d+[a-z]?', norm_a)
            num_b = re.findall(r'\d+[a-z]?', norm_b)
            if num_a and num_b:
                return num_a[0] == num_b[0]

        # Labs: "cs lab 1" vs "lab 1"
        if "lab" in norm_a and "lab" in norm_b:
            num_a = re.findall(r'\d+', norm_a)
            num_b = re.findall(r'\d+', norm_b)
            if num_a and num_b:
                return num_a[0] == num_b[0]

        # Auditoriums
        if "auditorium" in norm_a and "auditorium" in norm_b:
            qual_a = "mini" if "mini" in norm_a else ("main" if "main" in norm_a or "central" in norm_a else "generic")
            qual_b = "mini" if "mini" in norm_b else ("main" if "main" in norm_b or "central" in norm_b else "generic")
            if qual_a != "generic" and qual_b != "generic":
                return qual_a == qual_b
            return True

        return False

    @staticmethod
    def are_times_overlapping(
        start_a: datetime.datetime,
        end_a: datetime.datetime,
        start_b: datetime.datetime,
        end_b: datetime.datetime,
        buffer_minutes: int = 15,
    ) -> bool:
        """
        Check if two datetime intervals overlap.
        Includes an optional turnover buffer for campus halls.
        """
        buff = datetime.timedelta(minutes=buffer_minutes)
        return (start_a < (end_b + buff)) and ((end_a + buff) > start_b)

    @classmethod
    def check_academic_event_clash(
        cls,
        title_a: str,
        text_a: str,
        start_a: datetime.datetime,
        title_b: str,
        text_b: str,
        start_b: datetime.datetime,
    ) -> Tuple[bool, str]:
        """
        Detect if high-stakes conflicting events are scheduled on the same date/time window
        (e.g., Examination vs. Major Placement Drive or Campus Fest).
        """
        # Must be on the exact same calendar date
        if start_a.date() != start_b.date():
            return False, ""

        # Within +/- 3.5 hours on the same date
        time_diff = abs((start_a - start_b).total_seconds())
        if time_diff > (3.5 * 3600):
            return False, ""

        comb_a = f"{title_a} {text_a}".lower()
        comb_b = f"{title_b} {text_b}".lower()

        is_exam_a = any(k in comb_a for k in EXAM_KEYWORDS)
        is_major_b = any(k in comb_b for k in MAJOR_CAMPUS_EVENT_KEYWORDS)

        is_exam_b = any(k in comb_b for k in EXAM_KEYWORDS)
        is_major_a = any(k in comb_a for k in MAJOR_CAMPUS_EVENT_KEYWORDS)

        if (is_exam_a and is_major_b) or (is_exam_b and is_major_a):
            exam_title = title_a if is_exam_a else title_b
            event_title = title_b if is_exam_a else title_a
            return True, f"Examination Schedule Conflict: '{exam_title}' clashes with '{event_title}'"

        return False, ""

    @classmethod
    def generate_alternative_slots(
        cls,
        target_start: datetime.datetime,
        target_end: datetime.datetime,
        venue: str,
        occupied_intervals: List[Tuple[datetime.datetime, datetime.datetime]],
    ) -> List[Dict[str, Any]]:
        """
        Generate 2-3 intelligent, collision-free alternative time slots and venues.
        """
        duration = target_end - target_start
        if duration.total_seconds() < 1800:
            duration = datetime.timedelta(hours=1)

        suggestions: List[Dict[str, Any]] = []

        # Candidate 1: Same day later (e.g. +2.5 hours or after conflicting slots)
        same_day_later_start = target_end + datetime.timedelta(minutes=30)
        same_day_later_end = same_day_later_start + duration
        if same_day_later_end.hour <= 18 and same_day_later_end.date() == target_start.date():
            # Ensure not occupied
            is_free = not any(
                cls.are_times_overlapping(same_day_later_start, same_day_later_end, occ_s, occ_e)
                for occ_s, occ_e in occupied_intervals
            )
            if is_free:
                suggestions.append({
                    "label": f"{same_day_later_start.strftime('%b %d, %I:%M %p')} - {same_day_later_end.strftime('%I:%M %p')} (Same Day, Later)",
                    "start_time": same_day_later_start.isoformat(),
                    "end_time": same_day_later_end.isoformat(),
                    "venue": venue,
                    "slot_type": "same_day_later",
                })

        # Candidate 2: Same day morning session (e.g. 10:00 AM - 11:30 AM)
        if target_start.hour >= 13:
            morning_start = datetime.datetime(
                target_start.year, target_start.month, target_start.day, 10, 0, 0
            )
            morning_end = morning_start + duration
            is_free = not any(
                cls.are_times_overlapping(morning_start, morning_end, occ_s, occ_e)
                for occ_s, occ_e in occupied_intervals
            )
            if is_free:
                suggestions.append({
                    "label": f"{morning_start.strftime('%b %d, %I:%M %p')} - {morning_end.strftime('%I:%M %p')} (Morning Session)",
                    "start_time": morning_start.isoformat(),
                    "end_time": morning_end.isoformat(),
                    "venue": venue,
                    "slot_type": "same_day_morning",
                })

        # Candidate 3: Next business day at the original requested time
        next_day_start = target_start + datetime.timedelta(days=1)
        if next_day_start.weekday() == 6:  # Sunday -> Monday
            next_day_start += datetime.timedelta(days=1)
        next_day_end = next_day_start + duration
        suggestions.append({
            "label": f"{next_day_start.strftime('%b %d, %I:%M %p')} - {next_day_end.strftime('%I:%M %p')} (Next Business Day)",
            "start_time": next_day_start.isoformat(),
            "end_time": next_day_end.isoformat(),
            "venue": venue,
            "slot_type": "next_day",
        })

        # Candidate 4: Alternative nearby venue at the same requested time slot
        norm_v = cls.normalize_venue(venue)
        alt_venues = CAMPUS_ALTERNATIVE_VENUES.get(norm_v, [])
        for alt_v in alt_venues:
            if len(suggestions) >= 3:
                break
            suggestions.append({
                "label": f"{target_start.strftime('%b %d, %I:%M %p')} in {alt_v} (Alternative Venue)",
                "start_time": target_start.isoformat(),
                "end_time": target_end.isoformat(),
                "venue": alt_v,
                "slot_type": "alternative_venue",
            })

        return suggestions[:3]

    @classmethod
    def detect_schedule_conflicts(
        cls,
        db: Optional[Session],
        title: str,
        content: str,
        scheduled_at: Optional[datetime.datetime] = None,
        category: Optional[str] = None,
        exclude_notice_id: Optional[int] = None,
        active_notices_override: Optional[List[Dict[str, Any]]] = None,
        fast_scan: bool = True,
    ) -> Dict[str, Any]:
        """
        Primary pre-flight check method.
        Scans active announcements to detect venue collisions or academic event clashes.
        Uses deterministic heuristic extraction for sub-millisecond real-time responsiveness.
        """
        # Step 1: Extract event metadata from draft
        if fast_scan:
            draft_event = AIService._extract_calendar_event_heuristic(title, content)
        else:
            draft_event = AIService.extract_calendar_event(title, content)

        if not draft_event or not draft_event.get("has_event"):
            # Check if explicit scheduled_at was passed
            if scheduled_at:
                draft_start = scheduled_at
                draft_end = scheduled_at + datetime.timedelta(hours=1)
                venue = "College Campus"
                draft_event = {
                    "has_event": True,
                    "title": title[:60],
                    "start_time": draft_start.isoformat(),
                    "end_time": draft_end.isoformat(),
                    "location": venue,
                }
            else:
                return {
                    "has_conflict": False,
                    "draft_event": None,
                    "conflicts": [],
                    "suggested_alternatives": [],
                }

        current_year = datetime.datetime.now().year
        try:
            draft_start = datetime.datetime.fromisoformat(draft_event["start_time"])
            draft_end = datetime.datetime.fromisoformat(draft_event["end_time"])
            if draft_start.year < current_year:
                draft_start = draft_start.replace(year=current_year)
            if draft_end.year < current_year:
                draft_end = draft_end.replace(year=current_year)
            if draft_end <= draft_start:
                draft_end = draft_start + datetime.timedelta(hours=1)
        except Exception:
            draft_start = scheduled_at or datetime.datetime.now()
            draft_end = draft_start + datetime.timedelta(hours=1)

        draft_venue = draft_event.get("location", "College Campus")

        # Step 2: Fetch active announcements from database or override
        candidate_notices: List[Dict[str, Any]] = []

        if active_notices_override is not None:
            candidate_notices = active_notices_override
        elif db is not None:
            try:
                # Query notices that are not archived or rejected
                query = db.query(Announcement).filter(
                    Announcement.status.in_([
                        AnnouncementStatus.PUBLISHED,
                        AnnouncementStatus.APPROVED,
                        AnnouncementStatus.SCHEDULED,
                    ])
                )
                if exclude_notice_id:
                    query = query.filter(Announcement.id != exclude_notice_id)
                notices = query.order_by(Announcement.created_at.desc()).limit(100).all()

                for n in notices:
                    dept = "Academic Dept"
                    if n.creator:
                        if hasattr(n.creator, "department") and n.creator.department:
                            dept = n.creator.department.name
                        elif hasattr(n.creator, "role") and n.creator.role:
                            dept = n.creator.role.name

                    candidate_notices.append({
                        "id": n.id,
                        "title": n.title,
                        "description": n.description,
                        "department": dept,
                        "scheduled_at": n.scheduled_at,
                    })
            except Exception as e:
                logger.warning(f"Error fetching active notices for conflict scan: {e}")

        # Step 3: Compare against candidate notices
        conflicts: List[Dict[str, Any]] = []
        occupied_intervals: List[Tuple[datetime.datetime, datetime.datetime]] = []

        for item in candidate_notices:
            if exclude_notice_id and item.get("id") == exclude_notice_id:
                continue

            n_id = item.get("id", 0)
            n_title = item.get("title", "")
            n_desc = item.get("description", "")
            n_dept = item.get("department", "Department")

            # Extract event data for candidate using fast deterministic heuristic
            cand_event = AIService._extract_calendar_event_heuristic(n_title, n_desc)

            if not cand_event or not cand_event.get("has_event"):
                if item.get("scheduled_at"):
                    s_at = item["scheduled_at"]
                    if isinstance(s_at, str):
                        try:
                            s_at = datetime.datetime.fromisoformat(s_at)
                        except Exception:
                            continue
                    cand_start = s_at
                    cand_end = s_at + datetime.timedelta(hours=1)
                    cand_venue = "College Campus"
                else:
                    continue
            else:
                try:
                    cand_start = datetime.datetime.fromisoformat(cand_event["start_time"])
                    cand_end = datetime.datetime.fromisoformat(cand_event["end_time"])
                    if cand_start.year < current_year:
                        cand_start = cand_start.replace(year=current_year)
                    if cand_end.year < current_year:
                        cand_end = cand_end.replace(year=current_year)
                    if cand_end <= cand_start:
                        cand_end = cand_start + datetime.timedelta(hours=1)
                    cand_venue = cand_event.get("location", "College Campus")
                except Exception:
                    continue

            # 1. Venue Collision Check
            venue_collision = cls.are_venues_colliding(draft_venue, cand_venue)
            time_overlap = cls.are_times_overlapping(draft_start, draft_end, cand_start, cand_end)

            if venue_collision and time_overlap:
                occupied_intervals.append((cand_start, cand_end))
                time_str = cand_start.strftime("%b %d, %I:%M %p")
                conflicts.append({
                    "conflicting_notice_id": n_id,
                    "conflicting_title": n_title,
                    "conflicting_department": n_dept,
                    "conflicting_venue": cand_venue,
                    "conflicting_time": time_str,
                    "conflict_type": "venue_collision",
                    "conflict_message": (
                        f"⚠️ Conflict Detected: {n_dept} has booked {cand_venue} "
                        f"on {time_str} (Notice #{n_id})."
                    ),
                })
                continue

            # 2. Critical Academic Event Clash
            is_clash, clash_reason = cls.check_academic_event_clash(
                draft_event.get("title", title),
                draft_event.get("description", content),
                draft_start,
                n_title,
                n_desc,
                cand_start,
            )
            if is_clash:
                time_str = cand_start.strftime("%b %d, %I:%M %p")
                conflicts.append({
                    "conflicting_notice_id": n_id,
                    "conflicting_title": n_title,
                    "conflicting_department": n_dept,
                    "conflicting_venue": cand_venue,
                    "conflicting_time": time_str,
                    "conflict_type": "academic_clash",
                    "conflict_message": f"⚠️ {clash_reason} on {time_str} (Notice #{n_id}).",
                })

        # Step 4: Suggest alternatives if conflicts exist
        suggested_alternatives = []
        if conflicts:
            suggested_alternatives = cls.generate_alternative_slots(
                draft_start, draft_end, draft_venue, occupied_intervals
            )

        return {
            "has_conflict": len(conflicts) > 0,
            "draft_event": draft_event,
            "conflicts": conflicts,
            "suggested_alternatives": suggested_alternatives,
        }
