import os
import re
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.announcement import Announcement
from app.services.campus_ml_engine import CampusMLEngine
from app.services.ai_text_sanitizer import sanitize_ai_markdown
from app.services.model_router import ModelRouter

logger = logging.getLogger("EchoSphere.AIService")

# Read configuration from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODELS = [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.0-flash,gemini-1.5-flash").split(",") if m.strip()]


def call_modern_gemini(
    prompt: str,
    system_instruction: str = "",
    history: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Call Google Gemini using the latest available models (gemini-2.5-flash, gemini-2.0-flash).
    Tries:
      1. Modern google.genai Client (new Google GenAI SDK)
      2. Modern REST API v1beta endpoint
      3. Legacy google.generativeai SDK fallback
    Returns: (generated_text, model_name_used) or (None, None)
    """
    key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
    if not key or key == "YOUR_ACTUAL_GEMINI_API_KEY":
        return None, None

    candidate_models = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]

    for model_name in candidate_models:
        # 1. Try modern google.genai Client
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            config = None
            if system_instruction:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )

            # Build multi-turn contents if history provided
            contents: Any = []
            if history:
                for turn in history[-6:]:  # Keep recent 3 turns
                    role = "user" if turn.get("isUser", True) or turn.get("role") == "user" else "model"
                    text = turn.get("text", turn.get("content", ""))
                    if text:
                        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
            contents.append(prompt)

            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            if response and response.text:
                return response.text.strip(), f"Google {model_name}"
        except Exception as e:
            logger.debug(f"[google.genai SDK attempt ({model_name})]: {e}")

        # 2. Try REST API v1beta endpoint
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            contents_payload = []
            if history:
                for turn in history[-6:]:
                    role = "user" if turn.get("isUser", True) or turn.get("role") == "user" else "model"
                    text = turn.get("text", turn.get("content", ""))
                    if text:
                        contents_payload.append({"role": role, "parts": [{"text": text}]})

            contents_payload.append({"role": "user", "parts": [{"text": prompt}]})

            payload: Dict[str, Any] = {"contents": contents_payload}
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        return parts[0].get("text").strip(), f"Google {model_name} (REST)"
        except Exception as e:
            logger.debug(f"[REST API attempt ({model_name})]: {e}")

        # 3. Try legacy google.generativeai SDK
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=key)
            full_prompt = f"{system_instruction}\n\nUser Query: {prompt}" if system_instruction else prompt
            legacy_model = legacy_genai.GenerativeModel(model_name)
            response = legacy_model.generate_content(full_prompt)
            if response and hasattr(response, "text") and response.text:
                return response.text.strip(), f"Google {model_name} (SDK)"
        except Exception as e:
            logger.debug(f"[Legacy SDK attempt ({model_name})]: {e}")

    return None, None


class AIService:
    @staticmethod
    def process_chat(
        prompt: str,
        user_role: str = "STUDENT",
        department: Optional[str] = None,
        full_name: Optional[str] = None,
        usn_or_emp_id: Optional[str] = None,
        db: Optional[Session] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user chat with hybrid intelligence:
        - Scikit-Learn Campus ML Engine classifies intent and extracts semantic knowledge
        - Live Database RAG grounds announcements
        - Modern Gemini 2.5 / 2.0 Flash generates conversational answers when configured
        - Campus ML Engine synthesizes complete, structured answers when offline or without API key
        """
        query = prompt.strip()
        role = (user_role or "STUDENT").upper()
        dept = department or "CSE"
        name = full_name or ("Student" if role == "STUDENT" else "Faculty Member")

        ml_engine = CampusMLEngine.get_instance()

        # Step 1: Predict Campus Intent with calibrated local ML model
        predicted_intent, intent_conf = ml_engine.predict_intent(query)

        # Step 2: Semantic search across Institutional Knowledge Base
        kb_matches = ml_engine.search_knowledge_base(query, top_k=3)

        # Step 3: Database Announcements Retrieval & Grounding (Strict RBAC Enforced)
        matched_announcements: List[Dict[str, Any]] = []
        live_announcements_raw = []
        if db:
            try:
                from app.core.enums.announcement import AnnouncementStatus
                ann_query = db.query(Announcement)

                # RBAC Data Privacy Filter
                if role == "STUDENT":
                    # Students strictly see only PUBLISHED notices (never drafts or unapproved items)
                    ann_query = ann_query.filter(Announcement.status == AnnouncementStatus.PUBLISHED)
                elif role == "TEACHER":
                    # Teachers see published circulars, their department pending approvals, and drafts
                    ann_query = ann_query.filter(Announcement.status.in_([
                        AnnouncementStatus.PUBLISHED,
                        AnnouncementStatus.PENDING_APPROVAL,
                        AnnouncementStatus.DRAFT
                    ]))
                # HoD, Principal, College Admin, and DevAdmin have administrative oversight

                live_announcements_raw = ann_query.order_by(Announcement.created_at.desc()).limit(25).all()
                matched_announcements = ml_engine.search_live_announcements(
                    query=query,
                    announcements=live_announcements_raw,
                    user_dept=dept,
                    user_role=role,
                    top_k=4
                )
            except Exception as e:
                logger.warning(f"Live database announcement retrieval warning: {e}")

        # Step 4: Determine navigation target and action suggestions
        category_badge = "EchoSphere AI"
        navigation_target: Optional[str] = None
        suggested_actions: List[str] = []

        q_lower = query.lower()
        if any(w in q_lower for w in ["setting", "theme", "dark mode", "appearance", "light mode"]):
            navigation_target = "nav:profile:settings"
            suggested_actions = ["Go to Profile", "Toggle Dark Mode"]
            category_badge = "App Settings"
        elif any(w in q_lower for w in ["password", "reset password", "change password"]):
            navigation_target = "nav:profile:security"
            suggested_actions = ["Change Password", "Security Settings"]
            category_badge = "Security"
        elif any(w in q_lower for w in ["create notice", "post notice", "new notice", "submit notice"]):
            if role != "STUDENT":
                navigation_target = "action:create_notice"
                suggested_actions = ["Create New Notice", "View My Drafts"]
            else:
                suggested_actions = ["Browse Notices", "Contact Faculty Advisor"]
            category_badge = "Notice Creation"
        elif predicted_intent == "EXAM_SCHEDULE":
            category_badge = "Examinations"
            navigation_target = "nav:notices:filter:Examinations"
            suggested_actions = ["Filter Examinations", "Check Lab Timetable", "View Exam Rules"]
        elif predicted_intent == "EMERGENCY_ALERT":
            category_badge = "Emergency Alert"
            navigation_target = "nav:notices:filter:Emergency"
            suggested_actions = ["View Emergency Circulars", "Check Weather Advisory"]
        elif predicted_intent == "PLACEMENT_DRIVE":
            category_badge = "Placements"
            navigation_target = "nav:notices:filter:Placements"
            suggested_actions = ["View Placement Drives", "Check CGPA Criteria", "Resume Guidelines"]
        elif predicted_intent == "CAMPUS_FACILITIES":
            category_badge = "Campus Facilities"
            suggested_actions = ["Library Timings", "Hostel Rules", "Bus Schedule"]
        elif predicted_intent == "SPEAKER_HARDWARE":
            if role == "STUDENT":
                category_badge = "Access Restricted"
                navigation_target = None
                suggested_actions = ["Browse Announcements", "Check Exam Schedule", "View Placements"]
            else:
                category_badge = "Smart Speaker Hardware"
                navigation_target = "nav:hardware:speakers"
                suggested_actions = ["View Speaker Queue", "Hardware Node Status"]
        elif predicted_intent == "ACADEMIC_POLICIES":
            category_badge = "Academic Regulations"
            suggested_actions = ["Attendance Rules (75%)", "Grading System", "Condonation Info"]
        else:
            suggested_actions = ["Browse Announcements", "Check Exam Schedule", "View Placements"]

        # Step 5: Try Modern Gemini 2.5 / 2.0 Flash with Rich Dynamic System Context
        kb_text = "\n".join([f"- [{k['category']}] {k['title']}: {k['content'][:140]}" for k in kb_matches])
        live_notices_text = "\n".join([
            f"- [{m['category']} | {m['priority']}] {m['title']} ({m['department']}): {m['content'][:120]}"
            for m in matched_announcements
        ])

        system_instruction = (
            f"You are the EchoSphere Campus AI Assistant, an intelligent, authoritative institutional companion.\n\n"
            f"User Profile & Context:\n"
            f"- Name: {name}\n"
            f"- Role: {role} (Authority hierarchy: Student -> Teacher -> HoD -> College Admin -> Principal -> DevAdmin)\n"
            f"- Department: {dept}\n"
            f"- User ID / USN: {usn_or_emp_id or 'Verified Campus Member'}\n\n"
            f"Live Database Announcements Context (Filtered by RBAC):\n"
            f"{live_notices_text if live_notices_text else 'No directly matching active notices in database.'}\n\n"
            f"Institutional Campus Knowledge Base Context:\n"
            f"{kb_text if kb_text else 'Standard campus policies apply.'}\n\n"
            f"Mandatory RBAC & Formatting Directives:\n"
            f"1. CRITICAL COURTESY & RBAC DIRECTIVE: When responding to inquiries about restricted operational capabilities (e.g. smart speaker queue, hardware nodes, broadcast overrides, administrative configurations, unapproved drafts), ALWAYS respond politely and unoffensively. NEVER say 'You are a student and not allowed' or patronize the user. Instead, state calmly and respectfully: 'I don't have the authority to answer that question or disclose this operational information. Please consult your department office or faculty coordinator for assistance.'\n"
            f"2. Students have verified read-only announcement access. If they ask to post or publish notices, reply politely: 'I don't have the authority to author announcements directly. If you have an event or club announcement to publish, please coordinate with your faculty advisor or department office.'\n"
            f"3. Respond in clear, professional, natural, and friendly Markdown.\n"
            f"4. STRICTLY PROHIBITED: Do NOT output raw asterisk clutter (e.g. ****), nonsensical tokens, or excessive emojis.\n"
            f"5. Never say 'I am ready to help' and then stop. Directly answer the user's specific question with facts, dates, and clear instructions.\n"
            f"6. If answering about notices or exams, refer specifically to the user's department ({dept}) and role ({role})."
        )

        # Step 5: Route through Multi-Model Congestion-Aware Router (Gemma -> Cloudflare LLaMA / Gemini 2.5 -> Campus ML)
        router = ModelRouter.get_instance()
        return router.route_and_generate(
            prompt=query,
            user_role=role,
            department=dept,
            full_name=name,
            system_instruction=system_instruction,
            history=history,
            category_badge=category_badge,
            suggested_actions=suggested_actions,
            navigation_target=navigation_target,
            matched_announcements=matched_announcements,
            kb_matches=kb_matches,
            predicted_intent=predicted_intent
        )

    @staticmethod
    def draft_announcement(
        topic: str,
        category: str = "Academics",
        target_role: str = "STUDENT",
        department: Optional[str] = None
    ) -> Dict[str, str]:
        """Draft a formal institutional announcement circular."""
        clean_topic = topic.strip()
        dept_str = f" - {department} Department" if department else ""

        prompt = (
            f"Draft an official, highly professional college circular on: '{clean_topic}'.\n"
            f"Category: {category}, Target Audience: {target_role}, Department: {department or 'College-Wide'}.\n"
            f"Return ONLY a JSON object with keys: 'title', 'content', 'suggested_priority', 'suggested_category'."
        )
        sys_inst = "You are an official college administrative secretary drafting notices. Return strictly valid JSON."

        raw_res = None
        router = ModelRouter.get_instance()

        # 1. Try Cloudflare Workers AI first for fast sub-4-second structured drafting
        if router.cloudflare_provider.is_configured():
            try:
                raw_res = router.cloudflare_provider.generate(prompt, system_instruction=sys_inst, timeout=6.0)
            except Exception as e:
                logger.debug(f"[Cloudflare draft attempt]: {e}")

        # 2. Try Google Gemini if Cloudflare is unconfigured or failed
        if not raw_res:
            try:
                raw_res, _ = call_modern_gemini(prompt, system_instruction=sys_inst)
            except Exception as e:
                logger.debug(f"[Gemini draft attempt]: {e}")

        if raw_res:
            try:
                json_match = re.search(r'\{.*\}', raw_res, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    return {
                        "title": parsed.get("title", f"Notice: {clean_topic.title()}"),
                        "content": sanitize_ai_markdown(parsed.get("content", "")),
                        "suggested_priority": parsed.get("suggested_priority", "NORMAL"),
                        "suggested_category": parsed.get("suggested_category", category or "Academics")
                    }
            except Exception:
                pass

        # Local Campus ML drafting fallback
        ml_engine = CampusMLEngine.get_instance()
        class_res = ml_engine.predict_category_and_priority(clean_topic, clean_topic)
        final_cat = category if category and category != "Academics" else class_res["category"]

        title = f"Notice: {clean_topic.title()}"
        content = (
            f"OFFICIAL CIRCULAR{dept_str.upper()}\n\n"
            f"This is to formally notify all concerned {target_role.lower()}s regarding: {clean_topic}.\n\n"
            f"Key Instructions & Guidelines:\n"
            f"1. All target candidates must review the published requirements and adhere strictly to all deadlines.\n"
            f"2. For further details, circular documents and updates are maintained on the EchoSphere departmental portal.\n"
            f"3. For questions or exceptions, please contact the Department Office or Administrative Coordinator.\n\n"
            f"Issued By Authority:\nEchoSphere Institutional Administration"
        )

        return {
            "title": title,
            "content": sanitize_ai_markdown(content),
            "suggested_priority": class_res["priority"],
            "suggested_category": final_cat
        }

    @staticmethod
    def expand_text(text: str, category: str = "Academics") -> str:
        """Expand a brief memo into an official institutional circular."""
        clean = text.strip()
        if not clean:
            return ""

        prompt = f"Expand this brief note into a formal, structured official college announcement circular:\n\n'{clean}'"
        sys_inst = "You are an AI for official college circulars. Expand short bullet points into polite, clear, formal announcements. Output only the circular text."

        expanded, _ = call_modern_gemini(prompt, system_instruction=sys_inst)
        if expanded:
            return sanitize_ai_markdown(expanded)

        fallback_text = (
            f"Official Announcement Circular:\n\n"
            f"This is to notify all concerned students and faculty members regarding {clean}.\n\n"
            f"Please take note of this update, adhere strictly to all published guidelines, and monitor the EchoSphere portal for detailed schedules. "
            f"For clarifications, please consult your Department Office."
        )
        return sanitize_ai_markdown(fallback_text)

    @staticmethod
    def check_grammar(text: str) -> Dict[str, Any]:
        """Check grammar, spelling, and institutional tone."""
        clean = text.strip()
        if not clean:
            return {"original": text, "corrected_text": text, "improvements": []}

        prompt = f"Correct grammar, spelling, and institutional tone for this circular:\n\n'{clean}'"
        sys_inst = "You are a professional university editor. Return JSON: {\"corrected_text\": \"...\", \"improvements\": [\"...\"]}"

        raw_res, _ = call_modern_gemini(prompt, system_instruction=sys_inst)
        if raw_res:
            try:
                json_match = re.search(r'\{.*\}', raw_res, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    return {
                        "original": text,
                        "corrected_text": parsed.get("corrected_text", clean),
                        "improvements": parsed.get("improvements", ["Corrected syntax and institutional tone."])
                    }
            except Exception:
                pass

        # Rule-based fallback
        corrected = clean[0].upper() + clean[1:]
        if not corrected.endswith(('.', '!', '?')):
            corrected += '.'

        improvements = []
        if not clean[0].isupper():
            improvements.append("Capitalized initial sentence letter.")
        if not clean.endswith(('.', '!', '?')):
            improvements.append("Added terminal punctuation.")

        return {
            "original": text,
            "corrected_text": corrected,
            "improvements": improvements or ["Verified professional tone and structure."]
        }

    @staticmethod
    def recommend_priority(title: str, content: str, user_role: str = "STUDENT") -> Dict[str, Any]:
        """Classify priority and category using local Campus ML Engine."""
        ml_engine = CampusMLEngine.get_instance()
        return ml_engine.predict_category_and_priority(title=title, content=content, user_role=user_role)

    @staticmethod
    def validate_content(title: str, text: str) -> Dict[str, Any]:
        """Validate announcement completeness against institutional checklist."""
        combined = f"{title} {text}".lower()
        missing = []

        if len(title.strip()) < 5:
            missing.append("Descriptive Title (min 5 characters)")
        if len(text.strip()) < 20:
            missing.append("Detailed Content (min 20 characters)")

        has_time = any(w in combined for w in ["am", "pm", "time", "clock", "hours", "schedule", "at "])
        has_venue = any(w in combined for w in ["room", "lab", "hall", "auditorium", "building", "campus", "online", "venue", "block", "corridor"])
        has_date = any(w in combined for w in [
            "today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "2026", "2025", "date"
        ])

        if not has_time:
            missing.append("Time / Schedule")
        if not has_venue:
            missing.append("Venue / Location")
        if not has_date:
            missing.append("Date / Deadline")

        is_valid = len(missing) == 0
        reason = "Content is complete and ready for publishing." if is_valid else f"Notice is missing: {', '.join(missing)}."
        suggestion = f"Please specify: {', '.join(missing)}." if not is_valid else None

        return {
            "is_valid": is_valid,
            "missing_fields": missing,
            "reason": reason,
            "suggestion": suggestion
        }

    @staticmethod
    def check_spam(text: str) -> Dict[str, Any]:
        """Detect spam and non-academic solicitations."""
        lower = text.lower()
        flags = []

        spam_keywords = ['win money', 'free cash', 'crypto', 'subscribe', 'buy now', 'cheap', 'click link', 'earn $$$', 'whatsapp group', 'free iphone']
        found = [w for w in spam_keywords if w in lower]
        if found:
            flags.append(f"Contains non-institutional promotional keywords: {', '.join(found)}")

        words = text.split()
        if len(words) >= 5:
            caps_count = sum(1 for w in words if w.isupper() and len(w) > 1)
            if caps_count / len(words) > 0.5:
                flags.append("Excessive ALL CAPS detected.")

        is_spam = len(flags) > 0
        return {
            "is_spam": is_spam,
            "reason": "; ".join(flags) if is_spam else "Official institutional content verified.",
            "flags": flags
        }

    @staticmethod
    def check_duplicate(new_title: str, new_text: str, department: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        """Check duplicate circulars against recent announcements in database."""
        if not db:
            return {"is_duplicate": False, "similarity_score": 0.0, "matched_title": None, "reason": "Database session unavailable."}

        try:
            recent_notices = db.query(Announcement).order_by(Announcement.created_at.desc()).limit(20).all()
            new_combined = f"{new_title} {new_text}".lower()
            new_words = set(re.findall(r'\w+', new_combined))

            best_match_title = None
            highest_score = 0.0

            for notice in recent_notices:
                desc = getattr(notice, 'description', getattr(notice, 'content', ''))
                existing_combined = f"{getattr(notice, 'title', '')} {desc}".lower()
                existing_words = set(re.findall(r'\w+', existing_combined))

                if not existing_words or not new_words:
                    continue

                intersection = new_words.intersection(existing_words)
                union = new_words.union(existing_words)
                jaccard_score = len(intersection) / len(union)

                if jaccard_score > highest_score:
                    highest_score = jaccard_score
                    best_match_title = notice.title

            is_dup = highest_score >= 0.45
            reason = f"High similarity ({int(highest_score * 100)}%) detected with notice: '{best_match_title}'." if is_dup else "Notice content is unique."

            return {
                "is_duplicate": is_dup,
                "similarity_score": round(highest_score, 2),
                "matched_title": best_match_title if is_dup else None,
                "reason": reason
            }
        except Exception as e:
            return {"is_duplicate": False, "similarity_score": 0.0, "matched_title": None, "reason": f"Duplicate check error: {e}"}

    @staticmethod
    def summarize(content: str) -> str:
        """Summarize announcement into 1 concise sentence."""
        clean = content.strip()
        if not clean:
            return "No content provided."
        if len(clean) <= 90:
            return sanitize_ai_markdown(clean)

        prompt = f"Summarize this college circular in 1 clear, concise institutional sentence:\n\n'{clean}'"
        summary, _ = call_modern_gemini(prompt)
        if summary:
            return sanitize_ai_markdown(summary)

        sentences = re.split(r'(?<=[.!?])\s+', clean)
        if sentences:
            return sanitize_ai_markdown(f"Summary: {sentences[0]}")
        return sanitize_ai_markdown(f"Summary: {clean[:85]}...")

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Return operational health of AI engine, models, and router stats."""
        key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
        has_gemini = bool(key and key != "YOUR_ACTUAL_GEMINI_API_KEY")
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
        has_cf = bool(cf_token and cf_token != "YOUR_CLOUDFLARE_API_TOKEN")
        from app.services.campus_ml_engine import INSTITUTIONAL_KNOWLEDGE

        router = ModelRouter.get_instance()
        return {
            "engine": "EchoSphere Tri-Model AI (Gemma + Gemini 2.5 + Cloudflare LLaMA + Campus ML)",
            "gemini_model": PRIMARY_MODEL,
            "is_gemini_available": has_gemini,
            "is_cloudflare_available": has_cf,
            "local_ml_available": True,
            "kb_indexed_documents": len(INSTITUTIONAL_KNOWLEDGE),
            "router_metrics": router.get_router_status()
        }

    @staticmethod
    def train_models() -> Dict[str, Any]:
        """Train or retrain local Campus ML models."""
        engine = CampusMLEngine.get_instance()
        return engine.train_models()
