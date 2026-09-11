import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class RelevanceScoringService:
    """
    Contextual Relevance & Feed Scoring Engine.
    Computes a personalized affinity score (0.0 to 1.0) and explanatory reasons
    for campus announcements based on a student/staff profile.
    """

    DEPARTMENT_SYNONYMS = {
        "AIML": ["aiml", "ai & ml", "ai and ml", "artificial intelligence", "machine learning"],
        "AIDS": ["aids", "ai & ds", "ai and ds", "data science"],
        "CSE": ["cse", "computer science", "cs engineering", "comp sci"],
        "ISE": ["ise", "information science", "is engineering"],
        "ECE": ["ece", "electronics", "communication engineering"],
        "EEE": ["eee", "electrical", "electrical & electronics"],
        "ME": ["mechanical", "mech", "me "],
        "CIVIL": ["civil", "cv "],
    }

    SEMESTER_TERMS = {
        1: ["1st sem", "sem 1", "semester 1", "first sem", "1st semester", "i sem", "freshers"],
        2: ["2nd sem", "sem 2", "semester 2", "second sem", "2nd semester", "ii sem"],
        3: ["3rd sem", "sem 3", "semester 3", "third sem", "3rd semester", "iii sem"],
        4: ["4th sem", "sem 4", "semester 4", "fourth sem", "4th semester", "iv sem"],
        5: ["5th sem", "sem 5", "semester 5", "fifth sem", "5th semester", "v sem"],
        6: ["6th sem", "sem 6", "semester 6", "sixth sem", "6th semester", "vi sem"],
        7: ["7th sem", "sem 7", "semester 7", "seventh sem", "7th semester", "vii sem"],
        8: ["8th sem", "sem 8", "semester 8", "eighth sem", "8th semester", "viii sem", "final year", "graduating"],
    }

    YEAR_TERMS = {
        1: ["1st year", "first year", "1st-year", "freshers", "1st/2nd sem"],
        2: ["2nd year", "second year", "2nd-year", "sophomore", "3rd/4th sem"],
        3: ["3rd year", "third year", "3rd-year", "pre-final", "5th/6th sem"],
        4: ["4th year", "fourth year", "4th-year", "final year", "graduating batch", "7th/8th sem"],
    }

    @classmethod
    def get_academic_year(cls, semester: Optional[int]) -> Optional[int]:
        if semester is None or semester <= 0:
            return None
        if semester in (1, 2):
            return 1
        elif semester in (3, 4):
            return 2
        elif semester in (5, 6):
            return 3
        elif semester in (7, 8):
            return 4
        return None

    @classmethod
    def calculate_score(
        cls,
        user_profile: Dict[str, Any],
        notice: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculates affinity score between a user profile and an announcement.
        """
        raw_score = 0.0
        reasons: List[str] = []

        user_role = str(user_profile.get("role") or "Student").strip()
        user_dept = str(user_profile.get("department") or "").strip().upper()
        user_sem = user_profile.get("semester")
        try:
            user_sem = int(user_sem) if user_sem is not None else None
        except (ValueError, TypeError):
            user_sem = None

        user_year = cls.get_academic_year(user_sem)

        # Notice fields
        notice_id = notice.get("id") or notice.get("announcement_id") or 0
        title = str(notice.get("title") or "").strip()
        content = str(notice.get("description") or notice.get("content") or "").strip()
        combined_text = f"{title} {content}".lower()

        notice_dept = str(notice.get("department") or notice.get("department_name") or "").strip().upper()
        target_audience = str(notice.get("target_audience") or "Entire College").strip().lower()
        category = str(notice.get("category") or notice.get("category_name") or "General").strip()
        priority = str(notice.get("priority") or "NORMAL").strip().upper()
        emergency_level = str(notice.get("emergency_level") or "NORMAL").strip().upper()

        # ── 1. Priority & Emergency Factors ──────────────────────────────────
        if priority == "EMERGENCY" or emergency_level == "CRITICAL":
            raw_score += 0.55
            reasons.append("Emergency Alert")
        elif priority in ("HIGH", "URGENT"):
            raw_score += 0.20
            reasons.append("High Priority Notice")
        elif priority == "NORMAL":
            raw_score += 0.05

        # ── 2. Department Affinity ───────────────────────────────────────────
        if user_dept:
            if notice_dept and (notice_dept == user_dept or user_dept in notice_dept or notice_dept in user_dept):
                raw_score += 0.30
                reasons.append(f"Direct match for your department ({user_dept})")
            else:
                # Check for department keywords/synonyms in title & content
                synonyms = cls.DEPARTMENT_SYNONYMS.get(user_dept, [user_dept.lower()])
                matched_syn = any(re.search(rf"\b{re.escape(s)}\b", combined_text) for s in synonyms)
                if matched_syn:
                    raw_score += 0.20
                    reasons.append(f"Mentions your field of study ({user_dept})")
                elif notice_dept in ("GENERAL", "COLLEGE-WIDE", "ENTIRE COLLEGE", "ALL", ""):
                    raw_score += 0.10
                    reasons.append("College-Wide Circular")
                else:
                    # Notice is for another specific department
                    pass

        # ── 3. Semester & Academic Year Affinity (Students) ─────────────────
        if user_role.lower() == "student" and user_sem is not None:
            # Check exact semester match
            sem_terms = cls.SEMESTER_TERMS.get(user_sem, [])
            matches_sem = any(
                re.search(rf"\b{re.escape(term)}\b", combined_text) or
                re.search(rf"\b{re.escape(term)}\b", target_audience)
                for term in sem_terms
            )

            # Check year match
            year_terms = cls.YEAR_TERMS.get(user_year, []) if user_year else []
            matches_year = any(
                re.search(rf"\b{re.escape(term)}\b", combined_text) or
                re.search(rf"\b{re.escape(term)}\b", target_audience)
                for term in year_terms
            )

            if matches_sem:
                raw_score += 0.35
                reasons.append(f"Targeted to Semester {user_sem}")
            elif matches_year:
                raw_score += 0.25
                year_label = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(user_year, f"{user_year}th")
                reasons.append(f"Targeted to {year_label} Year Students")

            # Check if notice explicitly targets a DIFFERENT semester exclusively
            is_different_sem = False
            for other_sem, other_terms in cls.SEMESTER_TERMS.items():
                if other_sem != user_sem:
                    if any(term in target_audience for term in other_terms):
                        is_different_sem = True
                        break
            if is_different_sem and not matches_sem and not matches_year:
                raw_score = max(0.0, raw_score - 0.20)

        # ── 4. Category & Actionable Relevance ───────────────────────────────
        cat_lower = category.lower()
        if any(c in cat_lower for c in ["exam", "examination"]):
            raw_score += 0.15
            reasons.append("Examination Schedule")
        elif "fee" in cat_lower:
            raw_score += 0.15
            reasons.append("Fee Payment Deadline")
        elif "placement" in cat_lower:
            if user_year and user_year >= 3:
                raw_score += 0.20
                reasons.append("Campus Placement Drive")
            else:
                raw_score += 0.05
        elif any(c in cat_lower for c in ["workshop", "seminar"]):
            raw_score += 0.10
            reasons.append("Technical Workshop / Seminar")
        elif "holiday" in cat_lower:
            raw_score += 0.10
            reasons.append("Institutional Holiday Notice")
        elif any(c in cat_lower for c in ["event", "cultural", "sports"]):
            raw_score += 0.05

        # ── 5. Faculty / Staff Role Specific Relevance ───────────────────────
        if user_role.lower() in ("teacher", "hod", "college admin", "principal", "staff"):
            if "faculty" in target_audience or "staff" in target_audience or "meeting" in combined_text:
                raw_score += 0.30
                reasons.append("Faculty & Staff Circular")

        # ── 6. Recency Adjustment ────────────────────────────────────────────
        created_at_val = notice.get("created_at")
        if created_at_val:
            try:
                if isinstance(created_at_val, str):
                    clean_iso = created_at_val.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(clean_iso)
                elif isinstance(created_at_val, datetime):
                    dt = created_at_val
                else:
                    dt = None

                if dt:
                    now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
                    diff_hours = (now - dt).total_seconds() / 3600.0
                    if diff_hours <= 24:
                        raw_score *= 1.0
                    elif diff_hours <= 72:
                        raw_score *= 0.95
                    elif diff_hours <= 168:  # 7 days
                        raw_score *= 0.90
                    else:
                        raw_score *= 0.85
            except Exception:
                pass

        final_score = round(min(1.0, max(0.0, raw_score)), 2)

        unique_reasons: List[str] = []
        for r in reasons:
            if r not in unique_reasons:
                unique_reasons.append(r)

        return {
            "announcement_id": notice_id,
            "score": final_score,
            "is_highly_relevant": final_score >= 0.65,
            "reasons": unique_reasons,
        }

    @classmethod
    def calculate_batch(
        cls,
        user_profile: Dict[str, Any],
        announcements: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Calculates scores for a list of announcements for a given user profile.
        """
        results = []
        for a in announcements:
            item_score = cls.calculate_score(user_profile, a)
            results.append(item_score)
        return results
