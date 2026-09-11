"""
EchoSphere Smart Notice Intake Service
Provides:
1. Voice Notice Dictation (Speech-to-Circular AI):
   Transcribes spoken audio memos / voice dictation and synthesizes informal speech
   into an official, structured campus circular with title, bulleted body,
   category, priority, target audience, and calendar event extraction.
2. Circular Document OCR & Auto-Digitizer:
   Extracts text and institutional structure from scanned paper circulars, photos,
   and PDF documents, removing letterhead noise and formatting clean, broadcast-ready circulars.
"""

import os
import re
import json
import base64
import logging
import datetime
import requests
from typing import Dict, Any, List, Optional, Tuple

from app.services.ai_service import call_modern_gemini
from app.services.ai_text_sanitizer import sanitize_ai_markdown

logger = logging.getLogger("EchoSphere.SmartIntakeService")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()


class SmartIntakeService:
    """Multi-tier AI service for Voice Dictation and Document OCR Notice Intake."""

    # -------------------------------------------------------------------------
    # 1. VOICE NOTICE DICTATION (Speech-to-Circular)
    # -------------------------------------------------------------------------

    @classmethod
    def voice_to_notice(
        cls,
        audio_base64: Optional[str] = None,
        audio_format: str = "m4a",
        raw_transcript: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Converts voice audio or spoken dictation into an official structured circular.
        """
        transcription = (raw_transcript or "").strip()

        # Step 1: If audio bytes provided and no transcription, transcribe audio
        if audio_base64 and not transcription:
            transcription = cls._transcribe_audio(audio_base64, audio_format)

        if not transcription:
            transcription = "Spoken campus notice dictation."

        # Step 2: Transform speech transcript into structured circular
        structured = cls._structure_spoken_transcript(transcription)
        structured["transcription"] = transcription
        return structured

    @classmethod
    def _transcribe_audio(cls, audio_base64: str, audio_format: str) -> str:
        """Transcribes audio using Gemini Multimodal Audio or Cloudflare Whisper."""
        # Tier 1: Gemini Audio Transcription
        key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
        if key and key != "YOUR_ACTUAL_GEMINI_API_KEY":
            try:
                mime_map = {
                    "m4a": "audio/m4a",
                    "mp3": "audio/mp3",
                    "wav": "audio/wav",
                    "aac": "audio/aac",
                    "ogg": "audio/ogg",
                    "webm": "audio/webm",
                }
                mime = mime_map.get(audio_format.lower(), f"audio/{audio_format}")

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": "Transcribe this spoken college announcement audio accurately. Return only the verbatim spoken transcription, no commentary."
                                },
                                {
                                    "inline_data": {
                                        "mime_type": mime,
                                        "data": audio_base64
                                    }
                                }
                            ]
                        }
                    ]
                }
                resp = requests.post(url, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts).strip()
                        if text:
                            logger.info(f"[Voice Intake] Transcribed via Gemini: {text[:60]}...")
                            return text
            except Exception as e:
                logger.debug(f"[Voice Intake] Gemini audio transcription error: {e}")

        # Tier 2: Cloudflare Workers AI Whisper
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", CLOUDFLARE_ACCOUNT_ID).strip()
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", CLOUDFLARE_API_TOKEN).strip()
        if cf_account and cf_token:
            try:
                audio_bytes = base64.b64decode(audio_base64)
                url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/run/@cf/openai/whisper"
                headers = {"Authorization": f"Bearer {cf_token}"}
                resp = requests.post(url, headers=headers, data=audio_bytes, timeout=30)
                if resp.status_code == 200:
                    res = resp.json().get("result", {})
                    text = res.get("text", "").strip()
                    if text:
                        logger.info(f"[Voice Intake] Transcribed via Cloudflare Whisper: {text[:60]}...")
                        return text
            except Exception as e:
                logger.debug(f"[Voice Intake] Cloudflare Whisper error: {e}")

        return "Announcement voice note recorded."

    @classmethod
    def _structure_spoken_transcript(cls, transcript: str) -> Dict[str, Any]:
        """Converts raw conversational speech into an official institutional circular."""
        system_instruction = (
            "You are EchoSphere's Smart Campus Circular Structurer. "
            "You transform raw, informal spoken notes, audio transcriptions, and casual faculty dictations "
            "into formal, polished, professional college circulars.\n"
            "Rules:\n"
            "1. Output ONLY a valid JSON object without markdown fences, code blocks, or preamble.\n"
            "2. Required JSON keys:\n"
            '   - "title": Concise, official institutional title (e.g. "Postponement of 3rd Year CSE Lab Examination")\n'
            '   - "content": Clean, professional circular text with formal greeting, background, bullet points for key dates/venues, and signature line.\n'
            '   - "suggested_category": One of ["Academic", "Examination", "Placement", "Event", "Emergency", "Sports", "Administrative"]\n'
            '   - "suggested_priority": One of ["NORMAL", "HIGH", "URGENT"]\n'
            '   - "suggested_audience": One of ["Entire College", "AIML Department", "CSE Department", "ECE Department", "1st Year Students", "2nd Year Students", "3rd Year Students", "4th Year Students", "Faculty Members"]\n'
            '   - "extracted_event": Optional object with {"title", "start_time", "end_time", "location", "action_required"} or null if no event.\n'
        )

        user_prompt = f"Spoken dictation transcript to convert:\n\"\"\"\n{transcript}\n\"\"\""

        # Tier 1: Gemini Structuring
        key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
        if key and key != "YOUR_ACTUAL_GEMINI_API_KEY":
            try:
                text, _ = call_modern_gemini(user_prompt, system_instruction=system_instruction)
                if text:
                    parsed = cls._parse_json_response(text)
                    if parsed and "title" in parsed and "content" in parsed:
                        parsed["content"] = sanitize_ai_markdown(parsed["content"])
                        return parsed
            except Exception as e:
                logger.debug(f"[Voice Intake] Gemini structuring error: {e}")

        # Tier 2: Cloudflare LLaMA 3.1 8B
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", CLOUDFLARE_ACCOUNT_ID).strip()
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", CLOUDFLARE_API_TOKEN).strip()
        if cf_account and cf_token:
            try:
                url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/run/@cf/meta/llama-3.1-8b-instruct"
                headers = {"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"}
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ]
                resp = requests.post(url, headers=headers, json={"messages": messages, "temperature": 0.2}, timeout=20)
                if resp.status_code == 200:
                    text = resp.json().get("result", {}).get("response", "")
                    parsed = cls._parse_json_response(text)
                    if parsed and "title" in parsed and "content" in parsed:
                        parsed["content"] = sanitize_ai_markdown(parsed["content"])
                        return parsed
            except Exception as e:
                logger.debug(f"[Voice Intake] Cloudflare LLaMA structuring error: {e}")

        # Tier 3: Deterministic Campus Fallback
        return cls._deterministic_voice_to_notice(transcript)

    @classmethod
    def _deterministic_voice_to_notice(cls, transcript: str) -> Dict[str, Any]:
        """Deterministic NLP and regex campus circular builder for voice dictation."""
        lower = transcript.lower()

        # Category Detection (Emergency checked first with priority)
        category = "Academic"
        if re.search(r'\b(emergency|fire|drill|evacuate|evacuation|danger|hazard)\b', lower):
            category = "Emergency"
        elif re.search(r'\b(exam|examination|test|ia-?1|ia-?2|midterm|hall\s*ticket|reval)\b', lower):
            category = "Examination"
        elif re.search(r'\b(placement|interview|recruitment|drive|package|internship|hiring)\b', lower):
            category = "Placement"
        elif re.search(r'\b(sport|sports|cricket|football|badminton|tournament|athletics)\b', lower):
            category = "Sports"
        elif re.search(r'\b(holiday|closed|suspend|suspended|vacation|festival)\b', lower):
            category = "Academic"
        elif re.search(r'\b(fest|workshop|hackathon|seminar|cultural|event|symposium|conference)\b', lower):
            category = "Event"


        # Priority Detection
        priority = "NORMAL"
        if any(w in lower for w in ["emergency", "evacuate", "immediate", "urgent"]):
            priority = "URGENT"
        elif any(w in lower for w in ["postpone", "reschedul", "mandatory", "deadline", "fee payment", "strict"]):
            priority = "HIGH"

        # Audience Detection
        audience = "Entire College"
        if "aiml" in lower:
            audience = "AIML Department"
        elif "cse" in lower or "computer science" in lower:
            audience = "CSE Department"
        elif "ece" in lower or "electronics" in lower:
            audience = "ECE Department"
        elif "mech" in lower:
            audience = "Mechanical Department"
        elif "civil" in lower:
            audience = "Civil Department"
        elif "1st year" in lower or "first year" in lower:
            audience = "1st Year Students"
        elif "2nd year" in lower or "second year" in lower:
            audience = "2nd Year Students"
        elif "3rd year" in lower or "third year" in lower or "5th sem" in lower or "6th sem" in lower:
            audience = "3rd Year Students"
        elif "4th year" in lower or "final year" in lower or "7th sem" in lower or "8th sem" in lower:
            audience = "4th Year Students"
        elif "faculty" in lower or "professors" in lower or "teachers" in lower:
            audience = "Faculty Members"

        # Extract Dates, Venues & Times
        venue_match = re.search(r'\b(room\s*\d+|auditorium|seminar hall|lab\s*\d*|turing lab|ground)\b', lower)
        venue = venue_match.group(0).title() if venue_match else "Campus Premises"

        time_match = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b', lower)
        event_time = time_match.group(0).upper() if time_match else None

        date_match = re.search(r'\b(tomorrow|friday|monday|tuesday|wednesday|thursday|saturday|sunday|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)\b', lower)
        event_date = date_match.group(0).title() if date_match else "Scheduled Date"

        # Build clean institutional title
        clean_text = re.sub(r'^(um|uh|please note that|hey guys|listen|attention)\s*', '', transcript, flags=re.IGNORECASE).strip()
        words = clean_text.split()
        short_subject = " ".join(words[:6]).title()
        if not short_subject.endswith((".", "Notice", "Circular", "Update")):
            short_subject += " Notice"
        title = f"{category}: {short_subject}"

        # Build clean bulleted body
        bullets = []
        if event_date or event_time:
            bullets.append(f"- Timing: {event_date} {f'at {event_time}' if event_time else ''}".strip())
        if venue and venue != "Campus Premises":
            bullets.append(f"- Venue / Location: {venue}")
        bullets.append("- Action: Please check with your department coordinator for further guidelines.")

        content = (
            f"This is an official circular issued regarding {clean_text.rstrip('.')}.\n\n"
            f"Key Details:\n" + "\n".join(bullets) + "\n\n"
            f"All concerned {audience.lower()} are advised to take note and strictly comply."
        )

        extracted_event = None
        if event_date or event_time:
            extracted_event = {
                "title": title,
                "location": venue,
                "action_required": f"Attend {title}",
            }

        return {
            "title": title,
            "content": content,
            "suggested_category": category,
            "suggested_priority": priority,
            "suggested_audience": audience,
            "extracted_event": extracted_event,
        }

    # -------------------------------------------------------------------------
    # 2. CIRCULAR DOCUMENT OCR & AUTO-DIGITIZER
    # -------------------------------------------------------------------------

    @classmethod
    def ocr_document_to_notice(
        cls,
        file_base64: str,
        mime_type: str = "image/jpeg",
        filename: str = "circular.jpg"
    ) -> Dict[str, Any]:
        """
        Extracts structured circular information from an image or PDF document.
        """
        # Tier 1: Gemini Vision / Multimodal Document Understanding
        key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
        if key and key != "YOUR_ACTUAL_GEMINI_API_KEY":
            try:
                system_instruction = (
                    "You are EchoSphere's Institutional Circular Document OCR & Digitizer. "
                    "You are analyzing a scanned paper circular, official notification photo, or PDF circular.\n"
                    "Instructions:\n"
                    "1. Read the document text thoroughly, filtering out letterhead noise, decorative borders, and institutional logos.\n"
                    "2. Extract the official circular Reference Number if visible (e.g. 'Ref: RVCE/CSE/2026/042' or 'Circular No. 14').\n"
                    "3. Extract the Subject line into a clean, concise 'title'.\n"
                    "4. Structure the body of the notice into 'content' formatted in clean markdown with bullet points for dates, fees, venues, and requirements.\n"
                    "5. Assign 'suggested_category' from: ['Academic', 'Examination', 'Placement', 'Event', 'Emergency', 'Sports', 'Administrative'].\n"
                    "6. Assign 'suggested_priority' from: ['NORMAL', 'HIGH', 'URGENT'].\n"
                    "7. Assign 'suggested_audience' from: ['Entire College', 'AIML Department', 'CSE Department', 'ECE Department', '1st Year Students', '2nd Year Students', '3rd Year Students', '4th Year Students', 'Faculty Members'].\n"
                    "8. Extract any calendar event with date, time, venue, and fee.\n"
                    "Output ONLY a valid JSON object without markdown fences, matching keys:\n"
                    '{"title", "content", "suggested_category", "suggested_priority", "suggested_audience", "reference_number", "extracted_event", "raw_text"}\n'
                )

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": system_instruction},
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": file_base64
                                    }
                                }
                            ]
                        }
                    ]
                }
                resp = requests.post(url, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts).strip()
                        parsed = cls._parse_json_response(text)
                        if parsed and "title" in parsed and "content" in parsed:
                            parsed["content"] = sanitize_ai_markdown(parsed["content"])
                            logger.info(f"[Document OCR] Successfully parsed document via Gemini Vision: {parsed.get('title')}")
                            return parsed
            except Exception as e:
                logger.debug(f"[Document OCR] Gemini Vision error: {e}")

        # Tier 2: Deterministic Document Extraction Fallback
        return cls._deterministic_ocr_to_notice(file_base64, filename)

    @classmethod
    def _deterministic_ocr_to_notice(cls, file_base64: str, filename: str) -> Dict[str, Any]:
        """
        Deterministic fallback when multimodal LLMs are offline.
        Inspects embedded text or generates institutional template structure.
        """
        raw_text = ""
        try:
            # Try to decode any UTF-8 text strings inside decoded bytes (e.g. from text or PDF text streams)
            decoded = base64.b64decode(file_base64)
            ascii_text = decoded.decode('utf-8', errors='ignore')
            clean_lines = [line.strip() for line in ascii_text.splitlines() if len(line.strip()) > 3]
            raw_text = "\n".join(clean_lines[:30])
        except Exception:
            raw_text = ""

        ref_match = re.search(r'\b(Ref(?:erence)?\s*(?:No\.?)?[:\s]*[\w/-]+|Circular\s*No\.?[:\s]*[\w/-]+)\b', raw_text, re.IGNORECASE)
        ref_no = ref_match.group(0) if ref_match else f"CIR/{datetime.date.today().year}/{filename[:8].upper()}"

        clean_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()

        title = f"Official Circular: {clean_name}" if "circular" not in clean_name.lower() else clean_name
        category = "Academic"
        if any(k in clean_name.lower() for k in ["exam", "test", "timetable", "schedule"]):
            category = "Examination"
        elif any(k in clean_name.lower() for k in ["placement", "interview", "drive"]):
            category = "Placement"
        elif any(k in clean_name.lower() for k in ["sports", "tournament", "athletics"]):
            category = "Sports"

        content = (
            f"Reference: {ref_no}\n"
            f"Date: {datetime.date.today().strftime('%d %B %Y')}\n\n"
            f"This is to officially notify all concerned students and faculty members regarding {clean_name}.\n\n"
            f"Key Instructions:\n"
            f"- Please refer to the attached official institutional document for complete details, schedule, and guidelines.\n"
            f"- All required forms and submissions must be completed before the specified deadline.\n"
            f"- Adherence to campus conduct and regulations is strictly mandatory.\n\n"
            f"By Order,\nOffice of the Principal / Dean Academics"
        )

        return {
            "title": title,
            "content": content,
            "suggested_category": category,
            "suggested_priority": "NORMAL",
            "suggested_audience": "Entire College",
            "reference_number": ref_no,
            "extracted_event": None,
            "raw_text": raw_text[:500] if raw_text else None,
        }

    @staticmethod
    def _parse_json_response(text: str) -> Optional[Dict[str, Any]]:
        """Safely parses JSON from LLM output, stripping fences and extra whitespace."""
        if not text:
            return None
        text = text.strip()
        # Remove markdown fences
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except Exception:
            # Fallback regex search for { ... }
            match = re.search(r'(\{[\s\S]*\})', text)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
        return None
