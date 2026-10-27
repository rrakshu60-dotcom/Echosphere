"""
EchoSphere Smart Notice Intake Service
Provides:
1. Voice Notice Dictation (Speech-to-Circular AI):
   Transcribes spoken audio memos / voice dictation and synthesizes informal speech
   into an official, structured campus circular with title, bulleted body,
   category, priority, target audience, and calendar event extraction.
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


def _gemini_models() -> List[str]:
    """The configured Gemini model first, then the router's fallbacks (no hard-coded, retired model names)."""
    from app.services.model_router import GEMINI_FALLBACK_MODELS, GEMINI_PRIMARY_MODEL
    primary = os.getenv("GEMINI_MODEL", GEMINI_PRIMARY_MODEL).strip()
    return [primary] + [m for m in GEMINI_FALLBACK_MODELS if m != primary]


def _gemini_generate(parts: List[Dict[str, Any]], timeout: int = 30) -> str:
    """Text of the first Gemini model that answers, or "" when none is configured or reachable."""
    key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
    if not key or key == "YOUR_ACTUAL_GEMINI_API_KEY":
        return ""
    for model in _gemini_models():
        try:
            # Key in a header, never in the URL: request errors include the URL and are logged
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            resp = requests.post(url, json={"contents": [{"parts": parts}]}, headers={"x-goog-api-key": key}, timeout=timeout)
            if resp.status_code != 200:
                logger.info(f"[Gemini] {model} answered HTTP {resp.status_code}; trying the next model")
                continue
            candidates = resp.json().get("candidates", [])
            if candidates:
                text = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", [])).strip()
                if text:
                    return text
        except Exception as e:
            logger.info(f"[Gemini] {model} failed: {type(e).__name__}")
    return ""
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()


class SmartIntakeService:
    """Multi-tier AI service for Voice Dictation Notice Intake."""

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
        # Tier 1: Gemini audio transcription (configured model, then fallbacks)
        mime_map = {"m4a": "audio/m4a", "mp3": "audio/mp3", "wav": "audio/wav", "aac": "audio/aac", "ogg": "audio/ogg", "webm": "audio/webm"}
        mime = mime_map.get(audio_format.lower(), f"audio/{audio_format}")
        text = _gemini_generate([
            {"text": "Transcribe this spoken college announcement audio accurately. Return only the verbatim spoken transcription, no commentary."},
            {"inline_data": {"mime_type": mime, "data": audio_base64}},
        ], timeout=25)
        if text:
            logger.info(f"[Voice Intake] Transcribed via Gemini: {text[:60]}...")
            return text

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

        # Nothing understood: never invent a transcript (it became a made-up notice)
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Couldn't understand the recording. Please try again, closer to the microphone.")

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
        from app.services.echosphere_ml_engine import detect_emergency
        is_emergency, _ = detect_emergency(transcript)

        category = "Academic"
        if is_emergency:
            category = "Emergency"
        elif re.search(r'\b(exam|examination|test|ia-?1|ia-?2|midterm|hall\s*ticket|reval|sem\s*exam|semester)\b', lower):
            category = "Examination"
        elif re.search(r'\b(placement|interview|recruitment|drive|package|internship|hiring)\b', lower):
            category = "Placement"
        elif re.search(r'\b(lost\s*and\s*found|lost|found|canteen|maintenance)\b', lower):
            category = "General"
        elif re.search(r'\b(sport|sports|cricket|football|badminton|tournament|athletics|volley|volleyball|selection|trials)\b', lower):
            category = "Sports"
        elif re.search(r'\b(holiday|closed|suspend|suspended|vacation|festival)\b', lower):
            category = "Academic"
        elif re.search(r'\b(fest|workshop|hackathon|seminar|cultural|event|symposium|conference)\b', lower):
            category = "Event"

        # Priority Detection
        priority = "NORMAL"
        if is_emergency:
            priority = "URGENT"
        elif any(w in lower for w in ["exam", "examination", "test", "midterm", "hall ticket", "sem exam", "postpone", "reschedul", "mandatory", "deadline", "fee payment", "strict"]):
            priority = "HIGH"
        elif any(w in lower for w in ["lost and found", "lost & found", "lost item", "found item", "lost", "found", "canteen", "maintenance", "reminder"]):
            priority = "LOW"
        elif any(w in lower for w in ["volley", "volleyball", "selection", "trials", "sports", "cricket", "football", "tournament", "hackathon", "workshop"]):
            priority = "NORMAL"

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
        event_time = re.sub(r'\s*(am|pm)$', r' \1', time_match.group(0)).upper() if time_match else None

        date_match = re.search(r'\b(tomorrow|friday|monday|tuesday|wednesday|thursday|saturday|sunday|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)\b', lower)
        event_date = date_match.group(0).title() if date_match else "Scheduled Date"

        # Build a clean title: drop spoken filler, then the time, date, venue and audience (they go in the body)
        clean_text = re.sub(
            r"\b(um+|uh+|erm|hey|hi|guys|everyone|folks|so|okay|ok|like|basically|listen|attention|please note that)\b[,.]?\s*",
            "", transcript, flags=re.IGNORECASE,
        )
        clean_text = re.sub(r"\s+", " ", clean_text).strip(" ,.")
        subject = clean_text
        for pattern in (
            r"\b(at|by|from)?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
            r"\b(on|this|next|by)?\s*(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            r"\b(on)?\s*\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b",
            r"\b(in|at)\s+(the\s+)?(room\s*\d+|auditorium|seminar hall|lab\s*\d*|turing lab|ground)\b",
            r"\bfor\s+(all\s+)?(the\s+)?(final|first|second|third|fourth|\d(?:st|nd|rd|th))\s+years?\b",
            r"\bfor\s+(all\s+)?(aiml|cse|ece|eee|mech|civil|faculty|students|teachers)\b.*$",
        ):
            subject = re.sub(pattern, " ", subject, flags=re.IGNORECASE)
        subject_words = re.sub(r"\s+", " ", subject).strip(" ,.").split()[:6]
        short_subject = " ".join(subject_words).title() or f"{category} Notice"
        when = ", ".join(x for x in (event_date if date_match else None, event_time) if x)
        title = f"{short_subject} - {when}" if when else short_subject
        sentence = clean_text[:1].upper() + clean_text[1:] if clean_text else short_subject

        # Build clean bulleted body
        bullets = []
        if date_match or event_time:
            bullets.append(f"- Timing: {event_date if date_match else 'Date to be announced'}{f' at {event_time}' if event_time else ''}")
        if venue and venue != "Campus Premises":
            bullets.append(f"- Venue / Location: {venue}")
        bullets.append("- Action: Please check with your department coordinator for further guidelines.")

        content = (
            f"{sentence.rstrip('.')}.\n\n"
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
