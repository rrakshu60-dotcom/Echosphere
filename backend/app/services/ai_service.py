import os
import re
import json
import requests
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.announcement import Announcement

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def call_gemini_api(prompt: str, system_instruction: str = "") -> Optional[str]:
    """Call Google Gemini API via REST API or google.generativeai SDK if key exists."""
    key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    if not key or key == "YOUR_ACTUAL_GEMINI_API_KEY":
        return None

    full_prompt = f"{system_instruction}\n\nUser Query: {prompt}" if system_instruction else prompt

    # 1. Try REST API endpoint (Fast & direct)
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }]
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts and parts[0].get("text"):
                    return parts[0].get("text").strip()
    except Exception as e:
        print(f"[Gemini REST Warning]: {e}")

    # 2. Try Python SDK fallback
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(full_prompt)
        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"[Gemini SDK Warning]: {e}")

    return None


class AIService:
    @staticmethod
    def process_chat(
        prompt: str,
        user_role: str = "STUDENT",
        department: Optional[str] = None,
        full_name: Optional[str] = None,
        usn_or_emp_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        query = prompt.strip()
        query_lower = query.lower()
        role = (user_role or "STUDENT").upper()
        dept = department or "CSE"
        name = full_name or ("Student" if role == "STUDENT" else "Faculty Member")

        matched_announcements: List[Dict[str, Any]] = []
        suggested_actions: List[str] = []
        navigation_target: Optional[str] = None
        category_badge = "EchoSphere AI"
        context_badge = f"{role.title()} • {dept} Department"

        # ─── Step 1: Database RAG Context Grounding ─────────────────────────
        live_notices_text = []
        if db:
            try:
                announcements = db.query(Announcement).order_by(Announcement.created_at.desc()).limit(15).all()

                for ann in announcements:
                    content_text = getattr(ann, 'description', getattr(ann, 'content', ''))
                    ann_title = getattr(ann, 'title', '')
                    ann_cat = getattr(ann, 'category', 'General')
                    if hasattr(ann_cat, 'name'):
                        ann_cat = ann_cat.name
                    ann_prio = getattr(ann, 'priority', 'NORMAL')
                    if hasattr(ann_prio, 'value'):
                        ann_prio = ann_prio.value

                    is_relevant = (
                        dept.lower() in str(content_text).lower() or
                        dept.lower() in str(ann_title).lower() or
                        role.lower() in str(content_text).lower() or
                        any(term in ann_title.lower() or term in str(content_text).lower() for term in query_lower.split() if len(term) > 3)
                    )

                    if is_relevant:
                        formatted_date = ann.created_at.strftime("%b %d, %I:%M %p") if getattr(ann, 'created_at', None) else "Recent"
                        matched_announcements.append({
                            "id": ann.id,
                            "title": ann_title,
                            "category": str(ann_cat),
                            "priority": str(ann_prio),
                            "department": dept,
                            "content": str(content_text)[:150] + ("..." if len(str(content_text)) > 150 else ""),
                            "created_at": formatted_date
                        })
                        live_notices_text.append(f"- [{ann_cat} | {ann_prio}] {ann_title}: {content_text[:120]} ({formatted_date})")
                        if len(matched_announcements) >= 4:
                            break
            except Exception as e:
                print(f"[AI Service DB RAG Warning]: {e}")

        # Determine Intent & Navigation Target
        if any(w in query_lower for w in ["setting", "theme", "dark mode", "appearance", "light mode"]):
            navigation_target = "nav:profile:settings"
            suggested_actions = ["Go to Profile", "Toggle Dark Mode"]
        elif any(w in query_lower for w in ["password", "reset password", "change password"]):
            navigation_target = "nav:profile:security"
            suggested_actions = ["Change Password", "Security Settings"]
        elif any(w in query_lower for w in ["create notice", "post notice", "new notice", "submit notice"]):
            if role != "STUDENT":
                navigation_target = "action:create_notice"
                suggested_actions = ["Create New Notice", "View My Notices"]
            else:
                suggested_actions = ["Browse Notices", "Contact Faculty"]
        elif any(w in query_lower for w in ["exam", "timetable", "test", "viva", "practical", "hall ticket"]):
            category_badge = "Examinations"
            navigation_target = "nav:notices:filter:Examinations"
            suggested_actions = ["Filter Examinations", "Check Lab Timetable"]
        elif any(w in query_lower for w in ["rain", "weather", "flood", "closed", "holiday", "emergency"]):
            category_badge = "Emergency Alert"
            navigation_target = "nav:notices:filter:Emergency"
            suggested_actions = ["View Emergency Notices", "Check Weather Advisory"]
        elif any(w in query_lower for w in ["placement", "drive", "job", "hiring", "tcs", "google", "microsoft"]):
            category_badge = "Placements"
            navigation_target = "nav:notices:filter:Placements"
            suggested_actions = ["View Placement Drives", "Check Guidelines"]
        elif any(w in query_lower for w in ["dept", "department", "cse", "ece", "ise", "eee", "me"]):
            navigation_target = f"nav:notices:filter:{dept}"
            suggested_actions = [f"Filter {dept} Notices", "View All Categories"]
        else:
            suggested_actions = ["Search Announcements", "Check Exam Schedule", "View Placements"]

        # ─── Step 2: Gemini API Call or Natural Language Generator ─────────────
        system_instruction = (
            f"You are EchoSphere AI, an intelligent, helpful, and natural language assistant for the EchoSphere Smart Campus Announcement System.\n"
            f"User Context:\n"
            f"- Name: {name}\n"
            f"- Role: {role} (Authority hierarchy: Student -> Teacher -> HoD -> College Admin -> Principal -> DevAdmin)\n"
            f"- Department: {dept}\n"
            f"- User Identifier: {usn_or_emp_id or 'Registered User'}\n\n"
            f"Live Database Notices Grounding Context:\n"
            f"{chr(10).join(live_notices_text) if live_notices_text else 'No specific DB notices matched directly.'}\n\n"
            f"Rules for Response Generation:\n"
            f"1. Respond in clear, natural, friendly, and conversational English like Gemini or ChatGPT.\n"
            f"2. Use clean Markdown formatting (bolding, headers, bullet lists).\n"
            f"3. DO NOT use robotic templates, nonsensical characters (such as *****), or emoji clutter.\n"
            f"4. If answering about notices or exams, refer naturally to the student's department ({dept}) and role ({role}).\n"
            f"5. Maintain a professional institutional tone."
        )

        ai_response = call_gemini_api(prompt, system_instruction=system_instruction)

        if not ai_response:
            # Fallback to fluid natural language engine (Zero template junk)
            ai_response = AIService._generate_natural_fallback(query_lower, name, role, dept, usn_or_emp_id, matched_announcements)

        return {
            "response": ai_response,
            "category_badge": category_badge,
            "context_badge": context_badge,
            "suggested_actions": suggested_actions,
            "navigation_target": navigation_target,
            "matched_announcements": matched_announcements
        }

    @staticmethod
    def _generate_natural_fallback(
        query: str, name: str, role: str, dept: str, usn_or_emp_id: Optional[str], matched: List[Dict[str, Any]]
    ) -> str:
        """Generate high-quality natural language Markdown text when Gemini API key is offline."""

        if any(term in query for term in ["who r u", "who are you", "what is your name", "identify yourself", "what do you do"]):
            return (
                f"I am the **EchoSphere AI Assistant**, your intelligent campus communication companion.\n\n"
                f"I am customized for **{name}** as a **{role.title()}** in the **{dept} Department**.\n\n"
                f"**How I can assist you:**\n"
                f"- **Announcements & Notices:** Find the latest circulars for {dept} or college-wide updates.\n"
                f"- **Exams & Schedules:** Retrieve lab timetables, exam dates, and hall ticket requirements.\n"
                f"- **Placements & Events:** Track active recruitment drives and campus events.\n"
                f"- **Notice Creation:** Expand short notes into formal circulars and polish tone using AI.\n"
                f"- **App Navigation:** Guide you to profile settings, theme toggles, or password updates."
            )

        if any(query.startswith(w) or query == w for w in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"]):
            return (
                f"Hello {name}! I am tuned to your context in the **{dept} Department** ({role.title()}).\n\n"
                f"How can I help you today? You can ask me about recent announcements, exam schedules, placement drives, or app navigation."
            )

        if any(w in query for w in ["thank", "thanks", "awesome", "great", "cool", "nice"]):
            return (
                f"You're very welcome, {name}! I am always here to keep you updated on **{dept} Department** notices and campus announcements."
            )

        if any(w in query for w in ["how are you", "how r u", "how's it going"]):
            return (
                f"I'm doing great and fully operating to help you stay informed! How can I assist you today in **{dept} Department**?"
            )

        if any(w in query for w in ["setting", "theme", "dark mode", "appearance", "light mode"]):
            return (
                f"To adjust your application settings or switch themes:\n\n"
                f"1. Navigate to the **Profile** tab on the main navigation bar.\n"
                f"2. Tap **Dark Mode Theme** to toggle between light and dark glassmorphism styling.\n"
                f"3. You can also configure notification preferences and smart speaker audio options there."
            )

        if any(w in query for w in ["password", "reset password", "change password"]):
            if role == "STUDENT":
                return (
                    f"As a **Student** ({usn_or_emp_id or 'Registered USN'}):\n\n"
                    f"- Password resets can be requested through your Department HoD or Class Teacher.\n"
                    f"- Alternatively, use the **Forgot Password?** option on the sign-in screen to receive a reset token."
                )
            return (
                f"As a **{role.title()}**, you can change your password directly:\n\n"
                f"1. Open the **Profile** tab.\n"
                f"2. Select **Preferences & Security**.\n"
                f"3. Tap **Change Password** and set your new credentials."
            )

        if any(w in query for w in ["create notice", "post notice", "new notice", "submit notice", "how to post"]):
            if role == "STUDENT":
                return (
                    f"According to campus communication guidelines, **Students** have read-only access to preserve notice authenticity.\n\n"
                    f"If you need an announcement published for a student event or club, please contact your **Department Faculty Advisor** or **HoD**."
                )
            return (
                f"To draft and publish an announcement:\n\n"
                f"1. Tap the floating **+ New Notice** button on your home dashboard.\n"
                f"2. Enter the title, content, target audience, and delivery channels.\n"
                f"3. Use the **AI Expand** feature to transform short bullet points into an official circular.\n"
                f"4. Faculty announcements submit for HoD approval, while HoD and Administrator notices publish immediately."
            )

        if any(w in query for w in ["exam", "timetable", "test", "viva", "practical", "hall ticket"]):
            return (
                f"Here is the examination guidance for **{dept} Department**:\n\n"
                f"- Practical lab and end-semester timetables are listed under the **Examinations** category.\n"
                f"- Please bring your official College ID Card and Hall Ticket to exam halls.\n"
                f"- Check the active notice feed for detailed batch timings."
            )

        if any(w in query for w in ["rain", "weather", "flood", "closed", "holiday", "emergency"]):
            return (
                f"**Emergency Status Update:**\n\n"
                f"- Active rainfall and weather alerts are broadcasted college-wide with highest priority.\n"
                f"- Urgent campus closure alerts appear at the top of your feed and play via campus speakers."
            )

        if any(w in query for w in ["placement", "drive", "job", "hiring", "tcs", "google", "microsoft"]):
            return (
                f"**Placements & Recruitment Drives ({dept}):**\n\n"
                f"- Active placement drives (TCS, Google, Microsoft, Infosys) are tagged under **Placements**.\n"
                f"- Minimum Eligibility: CGPA ≥ 7.0 with no active backlogs.\n"
                f"- Ensure your resume and documentation are submitted before the posted deadlines."
            )

        # Grounded live notices append
        notice_block = ""
        if matched:
            items = [f"- **[{m['category']}]** {m['title']} ({m['created_at']})" for m in matched[:3]]
            notice_block = "\n\n**Relevant Live Announcements:**\n" + "\n".join(items)

        return (
            f"I am ready to help you, **{name}** ({role.title()} · {dept} Department).\n\n"
            f"You can ask me to search campus notices, check exam timetables, view placement drives, or guide you through app features.{notice_block}"
        )

    @staticmethod
    def draft_announcement(topic: str, category: str = "Academics", target_role: str = "STUDENT", department: Optional[str] = None) -> Dict[str, str]:
        prompt = f"Draft a formal, professional college announcement on the topic: '{topic}'. Category: {category}, Target Audience: {target_role}, Department: {department or 'General'}."
        sys_inst = "You are an AI assistant creating formal college circulars. Respond with a JSON object: {\"title\": \"...\", \"content\": \"...\", \"suggested_priority\": \"...\", \"suggested_category\": \"...\"}"

        raw_res = call_gemini_api(prompt, system_instruction=sys_inst)
        if raw_res:
            try:
                json_match = re.search(r'\{.*\}', raw_res, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    return {
                        "title": parsed.get("title", f"Notice: {topic.title()}"),
                        "content": parsed.get("content", ""),
                        "suggested_priority": parsed.get("suggested_priority", "NORMAL"),
                        "suggested_category": parsed.get("suggested_category", category or "Academics")
                    }
            except Exception:
                pass

        rec = AIService.recommend_priority(topic, topic)
        cat = category if category and category != "Academics" else rec["category"]
        dept_str = f" - {department} Department" if department else ""

        title = f"Notice: {topic.strip().title()}"
        content = (
            f"OFFICIAL ANNOUNCEMENT{dept_str.upper()}\n\n"
            f"This is to inform all concerned {target_role.lower()}s regarding: {topic.strip()}.\n\n"
            f"Instructions & Schedule:\n"
            f"1. All target individuals are requested to note the guidelines and adhere strictly to schedule.\n"
            f"2. Detailed instructions are available on the portal desk.\n"
            f"3. For queries, contact the Department Office or Administrative Desk.\n\n"
            f"Issued By:\nEchoSphere Administration & Department Faculty"
        )

        return {
            "title": title,
            "content": content,
            "suggested_priority": rec["priority"],
            "suggested_category": cat
        }

    @staticmethod
    def expand_text(text: str, category: str = "Academics") -> str:
        clean = text.strip()
        if not clean:
            return ""

        prompt = f"Expand this short note into a formal, structured official college circular:\n\n'{clean}'"
        sys_inst = "You are an AI tool for formal campus notices. Expand short notes into polite, formal, clear institutional announcements. Output only the expanded text."

        expanded = call_gemini_api(prompt, system_instruction=sys_inst)
        if expanded:
            return expanded

        return (
            f"Official Circular:\n\n"
            f"This is to inform all concerned students and faculty members regarding {clean}.\n\n"
            f"Please take note of this update, adhere to the specified guidelines, and check the EchoSphere portal for further updates. "
            f"For clarifications, please visit the Department Office."
        )

    @staticmethod
    def check_grammar(text: str) -> Dict[str, Any]:
        clean = text.strip()
        if not clean:
            return {"original": text, "corrected_text": text, "improvements": []}

        prompt = f"Correct grammar, spelling, and tone for this college notice:\n\n'{clean}'"
        sys_inst = "You are a professional grammar and tone editor. Return JSON: {\"corrected_text\": \"...\", \"improvements\": [\"...\"]}"

        raw_res = call_gemini_api(prompt, system_instruction=sys_inst)
        if raw_res:
            try:
                json_match = re.search(r'\{.*\}', raw_res, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    return {
                        "original": text,
                        "corrected_text": parsed.get("corrected_text", clean),
                        "improvements": parsed.get("improvements", ["Corrected sentence structure."])
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
            improvements.append("Added ending punctuation.")

        return {
            "original": text,
            "corrected_text": corrected,
            "improvements": improvements or ["Formatting and professional tone verified."]
        }

    @staticmethod
    def validate_content(title: str, text: str) -> Dict[str, Any]:
        combined = f"{title} {text}".lower()
        missing = []

        if len(title.strip()) < 5:
            missing.append("Descriptive Title (min 5 characters)")

        if len(text.strip()) < 20:
            missing.append("Detailed Content (min 20 characters)")

        has_time = any(w in combined for w in ["am", "pm", "time", "clock", "hours", "schedule", "at "])
        has_venue = any(w in combined for w in ["room", "lab", "hall", "auditorium", "building", "campus", "online", "venue", "block"])
        has_date = any(w in combined for w in ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "2026", "2025", "date"])

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
        lower = text.lower()
        flags = []

        spam_keywords = ['win money', 'free cash', 'crypto', 'subscribe', 'buy now', 'cheap', 'click link', 'earn $$$', 'whatsapp group', 'free iPhone']
        found_keywords = [w for w in spam_keywords if w in lower]
        if found_keywords:
            flags.append(f"Contains non-institutional promotional keywords: {', '.join(found_keywords)}")

        words = text.split()
        if len(words) >= 5:
            caps_count = sum(1 for w in words if w.isupper() and len(w) > 1)
            if caps_count / len(words) > 0.5:
                flags.append("Excessive ALL CAPS detected.")

        is_spam = len(flags) > 0
        reason = "; ".join(flags) if is_spam else "Official institutional content verified."

        return {
            "is_spam": is_spam,
            "reason": reason,
            "flags": flags
        }

    @staticmethod
    def check_duplicate(new_title: str, new_text: str, department: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
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
            return {"is_duplicate": False, "similarity_score": 0.0, "matched_title": None, "reason": f"Duplicate check failed: {e}"}

    @staticmethod
    def recommend_priority(title: str, content: str, user_role: str = "STUDENT") -> Dict[str, Any]:
        text = f"{title} {content}".lower()
        role = (user_role or "STUDENT").upper()

        if any(w in text for w in ['rain', 'flood', 'weather', 'closed', 'suspended', 'emergency', 'disaster', 'evacuation']):
            priority = "EMERGENCY"
            category = "Emergency"
            reasoning = "Campus emergency or weather advisory detected."
        elif any(w in text for w in ['exam', 'timetable', 'hall ticket', 'test', 'viva', 'practical', 'schedule']):
            priority = "HIGH"
            category = "Examinations"
            reasoning = "Academic examination event detected."
        elif any(w in text for w in ['placement', 'interview', 'drive', 'hiring', 'recruitment', 'google', 'microsoft']):
            priority = "HIGH"
            category = "Placements"
            reasoning = "Placement drive activity with strict registration deadline."
        elif any(w in text for w in ['hackathon', 'fest', 'workshop', 'seminar', 'symposium', 'event', 'club']):
            priority = "NORMAL"
            category = "Events"
            reasoning = "Campus event or workshop notification."
        elif any(w in text for w in ['sports', 'tournament', 'match', 'cricket', 'football']):
            priority = "NORMAL"
            category = "Sports"
            reasoning = "Sports announcement."
        else:
            priority = "NORMAL"
            category = "Academics"
            reasoning = "General campus announcement."

        # Role authority enforcement
        allowed_roles = ["COLLEGE ADMIN", "HOD", "PRINCIPAL", "DEVELOPER", "DEV ADMIN"]
        is_allowed = True
        if priority == "EMERGENCY" and role not in allowed_roles:
            is_allowed = False
            priority = "HIGH"
            reasoning += " (Note: Only Authorized Admins/HoDs may issue Emergency priority; priority set to HIGH)."

        return {
            "priority": priority,
            "category": category,
            "reasoning": reasoning,
            "is_allowed": is_allowed
        }

    @staticmethod
    def summarize(content: str) -> str:
        if not content:
            return "No content provided."
        clean = content.strip()
        if len(clean) <= 90:
            return clean

        prompt = f"Summarize this college notice in 1 clear, concise sentence:\n\n'{clean}'"
        summary = call_gemini_api(prompt)
        if summary:
            return summary

        sentences = re.split(r'(?<=[.!?])\s+', clean)
        if sentences:
            return f"Summary: {sentences[0]}"
        return f"Summary: {clean[:85]}..."
