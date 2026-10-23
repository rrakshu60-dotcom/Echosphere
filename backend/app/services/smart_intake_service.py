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
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            resp = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=timeout)
            if resp.status_code != 200:
                logger.info(f"[Gemini] {model} answered HTTP {resp.status_code}; trying the next model")
                continue
            candidates = resp.json().get("candidates", [])
            if candidates:
                text = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", [])).strip()
                if text:
                    return text
        except Exception as e:
            logger.info(f"[Gemini] {model} failed: {e}")
    return ""
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
        category = "Academic"
        if re.search(r'\b(emergency|fire|drill|evacuate|evacuation|danger|hazard)\b', lower):
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
        if any(w in lower for w in ["emergency", "evacuate", "immediate", "urgent"]):
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
        filename: str = "circular.jpg",
        raw_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts structured circular information from an image or PDF document.
        Tiers:
        1. Gemini Vision (if API key is active and online)
        2. Local RapidOCR & pypdf (100% Free, zero tokens, zero limits, runs offline on CPU)
        3. Deterministic template fallback (if file has no text/corrupt)
        """
        file_bytes = b""
        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception:
            file_bytes = b""

        # Extract real text using 100% Free local offline engines if not already provided
        extracted_text = (raw_text or "").strip()
        if not extracted_text and file_bytes:
            extracted_text = cls._extract_text_from_document_bytes(file_bytes, mime_type, filename)

        # Tier 1: Gemini Vision reads the document (configured model, then fallbacks)
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
        text = _gemini_generate([
            {"text": system_instruction},
            {"inline_data": {"mime_type": mime_type, "data": file_base64}},
        ]) if file_bytes else ""
        parsed = cls._parse_json_response(text) if text else None
        if parsed and "title" in parsed and "content" in parsed:
            parsed["content"] = sanitize_ai_markdown(parsed["content"])
            if not parsed.get("raw_text") and extracted_text:
                parsed["raw_text"] = extracted_text[:3000]
            logger.info(f"[Document OCR] Read the document via Gemini Vision: {parsed.get('title')}")
            return parsed

        # Tier 2: 100% Free Local Offline OCR & Heuristic Structurer (No API, No Limits)
        if extracted_text and len(extracted_text) >= 10:
            return cls._structure_extracted_circular_text(extracted_text, filename)

        # Nothing readable: say so instead of inventing a circular from the file's raw bytes
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail="Couldn't read any text from this document. Try a clearer photo, or a PDF with selectable text.",
        )

    @classmethod
    def _extract_text_from_document_bytes(cls, file_bytes: bytes, mime_type: str, filename: str) -> str:
        """
        Extracts raw textual content from document bytes using 100% free, local on-device engines:
        - PDF documents: pypdf native text stream extraction (< 50ms)
        - Images/Photos: RapidOCR ONNX CPU neural OCR engine (~0.8s)
        """
        is_pdf = (
            "pdf" in mime_type.lower()
            or filename.lower().endswith(".pdf")
            or file_bytes[:4] == b"%PDF"
        )

        # 1. PDF Text Extraction via pypdf
        if is_pdf:
            try:
                import io
                import pypdf
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages_text = []
                for idx, page in enumerate(pdf_reader.pages):
                    txt = page.extract_text()
                    if txt and txt.strip():
                        pages_text.append(txt.strip())
                if pages_text:
                    full_text = "\n\n".join(pages_text)
                    logger.info(f"[Document OCR] Extracted {len(full_text)} chars from {len(pages_text)} PDF page(s) via pypdf.")
                    return full_text
            except Exception as pdf_err:
                logger.debug(f"[Document OCR] pypdf extraction note: {pdf_err}")

        # 2. Image OCR via RapidOCR (ONNX CPU)
        try:
            import io
            import numpy as np
            from PIL import Image
            from rapidocr_onnxruntime import RapidOCR

            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            max_dim = 1800
            if max(img.size) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            ocr_engine = RapidOCR()
            result, _ = ocr_engine(np.array(img))
            if result:
                lines = [r[1].strip() for r in result if r and len(r) > 1 and r[1] and r[1].strip()]
                if lines:
                    extracted_text = "\n".join(lines).strip()
                    logger.info(f"[Document OCR] RapidOCR extracted {len(lines)} line(s) ({len(extracted_text)} chars) from image.")
                    return extracted_text
        except Exception as ocr_err:
            logger.debug(f"[Document OCR] RapidOCR engine note: {ocr_err}")

        # 3. Plain-text files only: decoding an image or PDF as text produced garbage like "IHDR..."
        if not (mime_type or "").lower().startswith("text/"):
            return ""
        try:
            ascii_text = file_bytes.decode('utf-8', errors='ignore')
            clean_lines = [line.strip() for line in ascii_text.splitlines() if len(line.strip()) > 3]
            if len(clean_lines) >= 3:
                return "\n".join(clean_lines[:30])
        except Exception:
            pass

        return ""

    @classmethod
    def _structure_extracted_circular_text(cls, raw_text: str, filename: str) -> Dict[str, Any]:
        """
        Parses raw extracted OCR text into a formal, broadcast-ready institutional circular
        with accurate Reference Number, Subject, Category, Priority, Audience, Dates, and Deadlines.
        100% Free, zero tokens, zero limits, zero external APIs.
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        lower_text = raw_text.lower()

        # 1. Reference Number Detection
        ref_match = re.search(
            r'\b(Ref(?:erence)?\s*(?:No\.?)?[:\s]*[\w/-]+|Circular\s*No\.?[:\s]*[\w/-]+|No\.\s*[\w/-]+)\b',
            raw_text,
            re.IGNORECASE,
        )
        if ref_match:
            ref_no = ref_match.group(0).strip()
        else:
            ref_no = f"CIR/{datetime.date.today().year}/{filename[:8].upper()}"

        # 2. Date Detection
        # 2. Date Detection (Circular issue date vs event dates)
        date_header_match = re.search(
            r'Date[:\s]*(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(?:\d{2,4})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            raw_text,
            re.IGNORECASE,
        )
        circular_date = date_header_match.group(1).strip() if date_header_match else datetime.date.today().strftime('%d %B %Y')

        # 3. Subject / Title Extraction
        subject_line = None
        for line in lines:
            sub_m = re.match(r'^(?:Sub(?:ject)?|Regarding|Notice regarding)[:\s]*(.+)$', line, re.IGNORECASE)
            if sub_m:
                candidate = sub_m.group(1).strip()
                if len(candidate) > 4:
                    subject_line = candidate
                    break

        if not subject_line:
            for line in lines:
                l_lower = line.lower()
                if any(noise in l_lower for noise in ["college of", "university", "bengaluru", "department of", "ref no", "date:", "p.o. box", "autonomous"]):
                    continue
                if len(line) > 10 and not line.isupper():
                    subject_line = line
                    break
                elif len(line) > 8 and "circular" not in l_lower:
                    subject_line = line
                    break

        if not subject_line:
            clean_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
            subject_line = f"Official Circular: {clean_name}"

        subject_line = subject_line.strip(". -:")
        if not subject_line.endswith(("Notice", "Circular", "Update", "Schedule", "Timetable", "Guidelines")):
            title = f"{subject_line} Circular"
        else:
            title = subject_line

        # 4. Category Classification
        category = "Academic"
        if re.search(r'\b(exam|examination|test|ia|cie|midterm|hall ticket|reval|grade|marksheet)\b', lower_text):
            category = "Examination"
        elif re.search(r'\b(placement|interview|drive|package|ctc|lpa|internship|recruit|shortlist)\b', lower_text):
            category = "Placement"
        elif re.search(r'\b(emergency|evacuate|rain|flood|cyclone|red alert|danger|fire drill)\b', lower_text):
            category = "Emergency"
        elif re.search(r'\b(sport|sports|cricket|football|tournament|badminton|athletics|selection|trials)\b', lower_text):
            category = "Sports"
        elif re.search(r'\b(workshop|hackathon|seminar|fest|symposium|conference|cultural)\b', lower_text):
            category = "Event"
        elif re.search(r'\b(maintenance|canteen|bus|transport|hostel|library|fee|payment)\b', lower_text):
            category = "Administrative"

        # 5. Priority Classification
        priority = "NORMAL"
        if any(w in lower_text for w in ["emergency", "evacuate", "immediate", "urgent", "red alert", "cancelled", "postponed"]):
            priority = "URGENT"
        elif any(w in lower_text for w in ["strict", "mandatory", "deadline", "penalty", "hall ticket", "fee payment", "last date", "cie"]):
            priority = "HIGH"

        # 6. Audience Detection
        audience = "Entire College"
        if "aiml" in lower_text:
            audience = "AIML Department"
        elif "cse" in lower_text or "computer science" in lower_text:
            audience = "CSE Department"
        elif "ece" in lower_text or "electronics" in lower_text:
            audience = "ECE Department"
        elif "mech" in lower_text:
            audience = "Mechanical Department"
        elif "civil" in lower_text:
            audience = "Civil Department"
        elif "1st year" in lower_text or "first year" in lower_text:
            audience = "1st Year Students"
        elif "2nd year" in lower_text or "second year" in lower_text:
            audience = "2nd Year Students"
        elif "3rd year" in lower_text or "third year" in lower_text or "5th sem" in lower_text or "6th sem" in lower_text:
            audience = "3rd Year Students"
        elif "4th year" in lower_text or "final year" in lower_text or "7th sem" in lower_text or "8th sem" in lower_text:
            audience = "4th Year Students"
        elif "faculty" in lower_text or "professors" in lower_text or "teachers" in lower_text:
            audience = "Faculty Members"

        # 7. Venue, Time & Event Detection
        venue_match = re.search(r'\b(Room\s*\d+|Auditorium|Seminar Hall|Turing Lab|Lab\s*\d*|Ground|Sports Complex|Library)\b', raw_text, re.IGNORECASE)
        venue = venue_match.group(0).title() if venue_match else None

        time_match = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\b', raw_text)
        event_time = time_match.group(0).upper() if time_match else None

        body_date_match = re.search(
            r'(?:from|on|commence(?:s)?\s*(?:from)?|held\s*on|deadline|scheduled\s*(?:for)?)\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(?:\d{2,4})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            raw_text,
            re.IGNORECASE,
        )
        if body_date_match:
            event_date = body_date_match.group(1).strip()
        else:
            all_dates = re.findall(
                r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(?:\d{2,4})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                raw_text,
                re.IGNORECASE,
            )
            other_dates = [d for d in all_dates if d.strip().lower() != circular_date.lower()]
            event_date = other_dates[0] if other_dates else (all_dates[0] if all_dates else None)

        # 8. Build Key Bullet Points from actual text
        bullets = []
        if event_date or event_time:
            timing_str = f"{event_date} {f'at {event_time}' if event_time else ''}".strip()
            bullets.append(f"- Timing / Schedule: {timing_str}")
        if venue:
            bullets.append(f"- Venue / Location: {venue}")

        for line in lines:
            line_l = line.lower()
            if any(k in line_l for k in ["mandatory", "must report", "hall ticket", "fees", "fee", "penalty", "deadline", "last date", "instructions", "eligibility"]):
                if not any(b.endswith(line) for b in bullets) and len(line) < 140:
                    clean_clause = line.lstrip("-*• ").strip()
                    if clean_clause and not clean_clause.startswith(("-", "*")):
                        bullets.append(f"- {clean_clause}")

        if not bullets:
            bullets.append("- Please refer to the attached official institutional circular for complete schedule and instructions.")
        bullets.append(f"- All concerned {audience.lower()} are required to strictly comply with the guidelines.")

        content = (
            f"Reference: {ref_no}\n"
            f"Date: {circular_date}\n\n"
            f"Subject: {title}\n\n"
            f"This is to officially notify all {audience} regarding the matters set forth in official circular {ref_no}.\n\n"
            f"Key Instructions & Guidelines:\n" + "\n".join(bullets) + "\n\n"
            f"By Order,\nOffice of the Principal / Dean Academics"
        )

        extracted_event = None
        if event_date or venue:
            extracted_event = {
                "title": title,
                "location": venue or "Campus Premises",
                "date": event_date,
                "time": event_time,
                "action_required": f"Attend {title}",
            }

        return {
            "title": title,
            "content": content,
            "suggested_category": category,
            "suggested_priority": priority,
            "suggested_audience": audience,
            "reference_number": ref_no,
            "extracted_event": extracted_event,
            "raw_text": raw_text[:3000],
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
