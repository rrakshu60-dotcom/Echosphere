import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Canonical audiences matching EchoSphere frontend
CANONICAL_AUDIENCES = [
    "Entire College",
    "AIML Department",
    "AIDS Department",
    "ISE Department",
    "CSE Department",
    "ECE Department",
    "EEE Department",
    "Mechanical Department",
    "Civil Department",
    "1st Year Students",
    "2nd Year Students",
    "3rd Year Students",
    "4th Year Students",
    "Faculty Members",
]

DEPARTMENT_PATTERNS: Dict[str, List[str]] = {
    "CSE Department": [
        r"\b(?:cse|computer science(?:\s+and\s+engineering)?|cs\s+dept|cs\s+department)\b",
        r"\b(?:operating systems lab|compiler design|data structures|algorithms lab|computer network(?:s)? lab)\b",
    ],
    "AIML Department": [
        r"\b(?:aiml|ai\s*(?:&|and|\/)\s*ml|artificial intelligence(?:\s+and\s+machine learning)?)\b",
        r"\b(?:machine learning lab|deep learning lab|computer vision lab)\b",
    ],
    "AIDS Department": [
        r"\b(?:aids|ai\s*(?:&|and|\/)\s*ds|artificial intelligence(?:\s+and\s+data science)?)\b",
        r"\b(?:big data lab|data analytics lab)\b",
    ],
    "ISE Department": [
        r"\b(?:ise|information science(?:\s+and\s+engineering)?|is\s+dept|is\s+department)\b",
        r"\b(?:software engineering lab|web technology lab)\b",
    ],
    "ECE Department": [
        r"\b(?:ece|electronics(?:\s+and\s+communication)?|ec\s+dept|ec\s+department)\b",
        r"\b(?:vlsi lab|embedded systems lab|dsp lab|digital signal processing|analog circuits)\b",
    ],
    "EEE Department": [
        r"\b(?:eee|electrical(?:\s+and\s+electronics)?|ee\s+dept|ee\s+department)\b",
        r"\b(?:power systems lab|transformers lab|electric machines lab)\b",
    ],
    "Mechanical Department": [
        r"\b(?:mechanical(?:\s+engineering)?|mech\s+dept|mech\s+department)\b",
        r"\b(?:thermodynamics|cad\/cam|fluid mechanics|automotive lab|workshop lab|lathe lab)\b",
    ],
    "Civil Department": [
        r"\b(?:civil(?:\s+engineering)?|civil\s+dept|civil\s+department)\b",
        r"\b(?:structural engineering|concrete lab|surveying lab|geotechnical lab)\b",
    ],
}

YEAR_PATTERNS: Dict[str, List[str]] = {
    "1st Year Students": [
        r"\b(?:1st\s+year|first\s+year|freshers?|induction\s+program)\b",
        r"\b(?:1st\s+sem(?:ester)?|2nd\s+sem(?:ester)?|sem\s*[12]|semester\s*[12])\b",
        r"\b(?:physics\s+cycle|chemistry\s+cycle)\b",
    ],
    "2nd Year Students": [
        r"\b(?:2nd\s+year|second\s+year|sophomores?)\b",
        r"\b(?:3rd\s+sem(?:ester)?|4th\s+sem(?:ester)?|sem\s*[34]|semester\s*[34])\b",
    ],
    "3rd Year Students": [
        r"\b(?:3rd\s+year|third\s+year|pre[\-\s]?final\s+year)\b",
        r"\b(?:5th\s+sem(?:ester)?|6th\s+sem(?:ester)?|sem\s*[56]|semester\s*[56])\b",
    ],
    "4th Year Students": [
        r"\b(?:4th\s+year|fourth\s+year|final\s+year|graduating\s+batch)\b",
        r"\b(?:7th\s+sem(?:ester)?|8th\s+sem(?:ester)?|sem\s*[78]|semester\s*[78])\b",
    ],
}

FACULTY_PATTERNS = [
    r"\b(?:faculty(?:\s+members?)?|teaching\s+staff|professors?|assistant\s+professors?|associate\s+professors?)\b",
    r"\b(?:faculty\s+meeting|staff\s+meeting|syllabus\s+completion|lesson\s+plan|evaluation\s+duty|invigilation\s+duty)\b",
    r"\b(?:hods?|heads\s+of\s+department|principal\s+meeting\s+with\s+staff)\b",
]

COLLEGE_WIDE_WHITELIST = [
    r"\b(?:holiday|vacation|campus\s+closed|campus\s+closure)\b",
    r"\b(?:annual\s+(?:sports|cultural|day)|college\s+fest|ethnic\s+day|republic\s+day|independence\s+day|kannada\s+rajyotsava)\b",
    r"\b(?:bus\s+(?:transport|routes?|schedule|facility))\b",
    r"\b(?:id\s+cards?|identity\s+cards?|dress\s+code|uniform|code\s+of\s+conduct)\b",
    r"\b(?:convocation|graduation\s+day)\b",
    r"\b(?:entire\s+college|all\s+students\s+and\s+faculty|all\s+departments|all\s+batches)\b",
    r"\b(?:general\s+fee\s+payment|tuition\s+fee|scholarship\s+portal)\b",
]


class AudienceGuardService:
    """
    Analyzes announcement drafts in real-time to prevent accidental campus-wide spam,
    verifying if departmental, batch-specific, or faculty-only notices are targeted appropriately.
    """

    @classmethod
    def analyze_target_audience(
        cls,
        title: str,
        content: str,
        selected_audience: str,
    ) -> Dict[str, Any]:
        """
        Evaluate draft text against selected audience.
        Returns mismatch details and recommended narrowing chips.
        """
        combined = f"{title}\n{content}".strip()
        if not combined or len(combined) < 15:
            return {
                "has_mismatch": False,
                "detected_audience": None,
                "suggested_audiences": [],
                "warning_message": None,
                "mismatch_type": None,
            }

        # Step 1: Check if content is legitimately college-wide
        for white_pat in COLLEGE_WIDE_WHITELIST:
            if re.search(white_pat, combined, re.IGNORECASE):
                # Genuinely institutional / college-wide notice
                if selected_audience == "Entire College":
                    return {
                        "has_mismatch": False,
                        "detected_audience": "Entire College",
                        "suggested_audiences": [],
                        "warning_message": None,
                        "mismatch_type": None,
                    }

        # Step 2: Detect specific department, year, or faculty cues
        detected_departments: List[str] = []
        for dept_name, pats in DEPARTMENT_PATTERNS.items():
            for pat in pats:
                if re.search(pat, combined, re.IGNORECASE):
                    if dept_name not in detected_departments:
                        detected_departments.append(dept_name)
                    break

        detected_years: List[str] = []
        for year_name, pats in YEAR_PATTERNS.items():
            for pat in pats:
                if re.search(pat, combined, re.IGNORECASE):
                    if year_name not in detected_years:
                        detected_years.append(year_name)
                    break

        is_faculty = False
        for fac_pat in FACULTY_PATTERNS:
            if re.search(fac_pat, combined, re.IGNORECASE):
                # Confirm it is directed TO faculty, not just mentioning "faculty advisor"
                if re.search(r"\b(?:all\s+faculty|for\s+faculty|attention\s+faculty|faculty\s+meeting|staff\s+meeting|invigilation|duty)\b", combined, re.IGNORECASE):
                    is_faculty = True
                    break

        # Step 3: Compare detected targets against selected_audience
        suggested: List[str] = []
        warning_msg: Optional[str] = None
        mismatch_type: Optional[str] = None

        # Case A: Faculty notice addressed to Entire College or student audiences
        if is_faculty and selected_audience != "Faculty Members":
            warning_msg = (
                "⚠️ Audience Warning: This notice appears specifically for Faculty & Staff, "
                f"but target audience is set to '{selected_audience}'. Avoid notifying students."
            )
            suggested.append("Faculty Members")
            mismatch_type = "faculty_only"

        # Case B: Specific Department or Year notice addressed to 'Entire College'
        elif selected_audience == "Entire College":
            if detected_departments and not detected_years:
                dept = detected_departments[0]
                warning_msg = (
                    f"⚠️ Audience Warning: This notice specifically mentions {dept}, "
                    "but target audience is set to 'Entire College' (alerting 2,400+ students across all branches)."
                )
                suggested.append(dept)
                mismatch_type = "overly_broad_department"

            elif detected_years and not detected_departments:
                yr = detected_years[0]
                warning_msg = (
                    f"⚠️ Audience Warning: Notice targets {yr}, "
                    "but is addressed to 'Entire College'. Avoid sending to all semesters."
                )
                suggested.append(yr)
                mismatch_type = "overly_broad_year"

            elif detected_departments and detected_years:
                dept = detected_departments[0]
                yr = detected_years[0]
                warning_msg = (
                    f"⚠️ Audience Warning: Notice mentions {yr} ({dept}), "
                    "but target audience is set to 'Entire College'."
                )
                suggested.append(yr)
                suggested.append(dept)
                mismatch_type = "overly_broad_combined"

        # Case C: Cross-Department Mismatch (e.g. Mechanical notice sent to CSE Department)
        elif selected_audience.endswith("Department") and detected_departments:
            if selected_audience not in detected_departments:
                actual_dept = detected_departments[0]
                warning_msg = (
                    f"⚠️ Department Mismatch: Notice mentions {actual_dept}, "
                    f"but audience is set to '{selected_audience}'."
                )
                suggested.append(actual_dept)
                mismatch_type = "wrong_department"

        # Case D: Cross-Year Mismatch (e.g. 1st Year notice sent to 4th Year Students)
        elif selected_audience.endswith("Students") and detected_years:
            if selected_audience not in detected_years:
                actual_yr = detected_years[0]
                warning_msg = (
                    f"⚠️ Batch Mismatch: Notice mentions {actual_yr}, "
                    f"but audience is set to '{selected_audience}'."
                )
                suggested.append(actual_yr)
                mismatch_type = "wrong_year"

        primary_detected = suggested[0] if suggested else None

        return {
            "has_mismatch": len(suggested) > 0,
            "detected_audience": primary_detected,
            "suggested_audiences": suggested,
            "warning_message": warning_msg,
            "mismatch_type": mismatch_type,
        }
