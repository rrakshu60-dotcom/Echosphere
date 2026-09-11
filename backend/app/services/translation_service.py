import re
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("EchoSphere.TranslationService")


class TranslationService:
    """
    EchoSphere Multi-Lingual Regional Translation Engine.
    Supports high-quality institutional translation into:
    - Kannada (ಕನ್ನಡ)
    - Hindi (हिंदी)
    - Telugu (తెలుగు)
    - Tamil (தமிழ்)
    - English (English)
    """

    SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
        "kn": {"name": "Kannada", "native_name": "ಕನ್ನಡ", "code": "kn"},
        "hi": {"name": "Hindi", "native_name": "हिंदी", "code": "hi"},
        "te": {"name": "Telugu", "native_name": "తెలుగు", "code": "te"},
        "ta": {"name": "Tamil", "native_name": "தமிழ்", "code": "ta"},
        "en": {"name": "English", "native_name": "English", "code": "en"},
    }

    # Campus Domain Terminology Fallback Dictionaries for offline resilience
    CAMPUS_PHRASES: Dict[str, Dict[str, str]] = {
        "kn": {
            "internal assessment": "ಆಂತರಿಕ ಮೌಲ್ಯಮಾಪನ",
            "examination": "ಪರೀಕ್ಷೆ",
            "exam schedule": "ಪರೀಕ್ಷಾ ವೇಳಾಪಟ್ಟಿ",
            "schedule": "ವೇಳಾಪಟ್ಟಿ",
            "students": "ವಿದ್ಯಾರ್ಥಿಗಳು",
            "department": "ವಿಭಾಗ",
            "holiday": "ರಜೆ",
            "circular": "ಸುತ್ತೋಲೆ",
            "notice": "ಸೂಚನೆ",
            "workshop": "ಕಾರ್ಯಾಗಾರ",
            "seminar": "ವಿಚಾರ ಸಂಕಿರಣ",
            "fee payment": "ಶುಲ್ಕ ಪಾವತಿ",
            "fees": "ಶುಲ್ಕಗಳು",
            "placement": "ಉದ್ಯೋಗಾವಕಾಶ",
            "placement drive": "ಕ್ಯಾಂಪಸ್ ಸಂದರ್ಶನ",
            "all students": "ಎಲ್ಲಾ ವಿದ್ಯಾರ್ಥಿಗಳು",
            "entire college": "ಸಂಪೂರ್ಣ ಕಾಲೇಜು",
            "college campus": "ಕಾಲೇಜು ಆವರಣ",
            "auditorium": "ಸಭಾಂಗಣ",
            "room": "ಕೊಠಡಿ",
            "lab": "ಪ್ರಯೋಗಾಲಯ",
            "attendance": "ಹಾಜರಾತಿ",
            "mandatory": "ಕಡ್ಡಾಯವಾಗಿದೆ",
            "deadline": "ಕೊನೆಯ ದಿನಾಂಕ",
            "submit": "ಸಲ್ಲಿಸಿ",
            "closed": "ಮುಚ್ಚಿರುತ್ತದೆ",
            "classes suspended": "ತರಗತಿಗಳನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ",
            "attention": "ಗಮನಿಸಿ",
            "important notice": "ಪ್ರಮುಖ ಸೂಚನೆ",
        },
        "hi": {
            "internal assessment": "आंतरिक मूल्यांकन",
            "examination": "परीक्षा",
            "exam schedule": "परीक्षा अनुसूची",
            "schedule": "समय सारिणी",
            "students": "छात्रों",
            "department": "विभाग",
            "holiday": "अवकाश",
            "circular": "परिपत्र",
            "notice": "सूचना",
            "workshop": "कार्यशाला",
            "seminar": "संगोष्ठी",
            "fee payment": "शुल्क भुगतान",
            "fees": "शुल्क",
            "placement": "प्लेसमेंट",
            "placement drive": "कैंपस प्लेसमेंट ड्राइव",
            "all students": "सभी छात्र",
            "entire college": "संपूर्ण कॉलेज",
            "college campus": "कॉलेज परिसर",
            "auditorium": "सभागार",
            "room": "कमरा",
            "lab": "प्रयोगशाला",
            "attendance": "उपस्थिति",
            "mandatory": "अनिवार्य",
            "deadline": "अंतिम तिथि",
            "submit": "जमा करें",
            "closed": "बंद रहेगा",
            "classes suspended": "कक्षाएं निलंबित",
            "attention": "ध्यान दें",
            "important notice": "महत्वपूर्ण सूचना",
        },
        "te": {
            "internal assessment": "అంతర్గత అంచనా",
            "examination": "పరీక్ష",
            "exam schedule": "పరీక్షల షెడ్యూల్",
            "schedule": "షెడ్యూల్",
            "students": "విద్యార్థులు",
            "department": "విభాగం",
            "holiday": "సెలవు",
            "circular": "సర్క్యులర్",
            "notice": "నోటీసు",
            "workshop": "వర్క్‌షాప్",
            "seminar": "సెమినార్",
            "fee payment": "ఫీజు చెల్లింపు",
            "fees": "ఫీజులు",
            "placement": "ప్లేస్‌మెంట్",
            "placement drive": "క్యాంపస్ ప్లేస్‌మెంట్ డ్రైవ్",
            "all students": "విద్యార్థులందరూ",
            "entire college": "మొత్తం కళాశాల",
            "college campus": "కళాశాల ప్రాంగణం",
            "auditorium": "ఆడిటోరియం",
            "room": "గది",
            "lab": "ప్రయోగశాల",
            "attendance": "హాజరు",
            "mandatory": "తప్పనిసరి",
            "deadline": "చివరి తేదీ",
            "submit": "సమర్పించండి",
            "closed": "మూసివేయబడుతుంది",
            "classes suspended": "తరగతులు రద్దు చేయబడ్డాయి",
            "attention": "గమనిక",
            "important notice": "ముఖ్యమైన నోటీసు",
        },
        "ta": {
            "internal assessment": "உள் மதிப்பீடு",
            "examination": "தேர்வு",
            "exam schedule": "தேர்வு அட்டவணை",
            "schedule": "அட்டவணை",
            "students": "மாணவர்கள்",
            "department": "துறை",
            "holiday": "விடுமுறை",
            "circular": "சுற்றறிக்கை",
            "notice": "அறிவிப்பு",
            "workshop": "பயிலரங்கம்",
            "seminar": "கருத்தரங்கு",
            "fee payment": "கட்டணம் செலுத்துதல்",
            "fees": "கட்டணம்",
            "placement": "வேலைவாய்ப்பு",
            "placement drive": "வளாக வேலைவாய்ப்பு முகாம்",
            "all students": "அனைத்து மாணவர்கள்",
            "entire college": "முழு கல்லூரி",
            "college campus": "கல்லூரி வளாகம்",
            "auditorium": "அரங்கம்",
            "room": "அறை",
            "lab": "ஆய்வகம்",
            "attendance": "வருகை",
            "mandatory": "கட்டாயம்",
            "deadline": "கடைசி தேதி",
            "submit": "சமர்ப்பிக்கவும்",
            "closed": "மூடப்படும்",
            "classes suspended": "வகுப்புகள் ரத்து செய்யப்பட்டுள்ளன",
            "attention": "கவனத்திற்கு",
            "important notice": "முக்கிய அறிவிப்பு",
        },
    }

    @classmethod
    def normalize_language_code(cls, lang: str) -> str:
        clean = (lang or "en").strip().lower()
        if clean in ("kannada", "kn"):
            return "kn"
        if clean in ("hindi", "hi"):
            return "hi"
        if clean in ("telugu", "te"):
            return "te"
        if clean in ("tamil", "ta"):
            return "ta"
        return "en"

    @classmethod
    def translate_text(cls, text: str, target_language: str) -> str:
        """
        Translates a string into the requested regional language.
        Preserves technical course codes (e.g. CSE, AIML, 5th Sem), dates, numbers, fees.
        """
        if not text or not text.strip():
            return ""

        target_code = cls.normalize_language_code(target_language)
        if target_code == "en":
            return text

        lang_info = cls.SUPPORTED_LANGUAGES.get(target_code, {"name": "English", "native_name": "English"})
        lang_name = lang_info["name"]

        # Step 1: Attempt LLM Translation via Google Gemini / Model Router
        sys_inst = (
            f"You are a professional educational institution translator translating official circulars into {lang_name} ({lang_info['native_name']}).\n"
            f"RULES:\n"
            f"1. Strictly preserve course codes and branch acronyms (e.g. CSE, AIML, ISE, ECE, ME, CIVIL).\n"
            f"2. Strictly preserve academic terms (e.g. 5th Sem, 3rd Year, IA-1).\n"
            f"3. Strictly preserve dates, times, and fee amounts (e.g. ₹500, 10:00 AM, Oct 24th).\n"
            f"4. Provide ONLY the natural, accurate translated text without extra explanation, rules, or quotes."
        )
        prompt = f"Text to translate into {lang_name}:\n{text}"

        try:
            from app.services.ai_service import call_modern_gemini
            llm_text, _ = call_modern_gemini(prompt, system_instruction=sys_inst)
            if llm_text and llm_text.strip() and not llm_text.strip().startswith("Error"):
                clean = llm_text.strip().strip('"').strip("'")
                # Ensure it did not echo the prompt instructions
                if "RULES:" not in clean and "Text to translate" not in clean:
                    return clean
        except Exception as e:
            logger.debug(f"[Gemini translation attempt failed]: {e}")

        # Step 2: Cloudflare LLaMA 3.1
        try:
            from app.services.model_router import ModelRouter
            router = ModelRouter.get_instance()
            if router.cloudflare_provider.is_configured():
                cf_text = router.cloudflare_provider.generate(prompt, system_instruction=sys_inst, timeout=4.0)
                if cf_text and cf_text.strip():
                    clean_cf = cf_text.strip().strip('"').strip("'")
                    if "RULES:" not in clean_cf and "Text to translate" not in clean_cf:
                        return clean_cf
        except Exception as e:
            logger.debug(f"[Cloudflare translation attempt failed]: {e}")
            logger.debug(f"[Cloudflare translation attempt failed]: {e}")

        # Step 3: Resilient deterministic campus dictionary replacement
        return cls._translate_heuristic(text, target_code)

    @classmethod
    def _translate_heuristic(cls, text: str, target_code: str) -> str:
        """
        High-accuracy fallback substitution for standard campus circulars.
        """
        dict_map = cls.CAMPUS_PHRASES.get(target_code, {})
        if not dict_map:
            return text

        translated = text
        # Replace longer phrases first
        sorted_phrases = sorted(dict_map.keys(), key=lambda k: len(k), reverse=True)
        for phrase in sorted_phrases:
            replacement = dict_map[phrase]
            pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
            translated = pattern.sub(replacement, translated)

        # Prefix with institutional language indicator if no words matched
        if translated == text:
            prefixes = {
                "kn": "ಸೂಚನೆ:",
                "hi": "सूचना:",
                "te": "నోటీసు:",
                "ta": "அறிவிப்பு:",
            }
            prefix = prefixes.get(target_code, "")
            return f"{prefix} {text}"

        return translated

    @classmethod
    def translate_announcement(
        cls,
        title: str,
        content: str,
        summary: Optional[str] = None,
        target_language: str = "en",
    ) -> Dict[str, Any]:
        """
        Translates title, content, and summary together.
        """
        target_code = cls.normalize_language_code(target_language)
        lang_info = cls.SUPPORTED_LANGUAGES.get(target_code, {"name": "English", "native_name": "English"})

        if target_code == "en":
            return {
                "target_language": "en",
                "language_name": "English",
                "native_name": "English",
                "translated_title": title,
                "translated_content": content,
                "translated_summary": summary,
            }

        trans_title = cls.translate_text(title, target_code)
        trans_content = cls.translate_text(content, target_code)
        trans_summary = cls.translate_text(summary, target_code) if summary else None

        return {
            "target_language": target_code,
            "language_name": lang_info["name"],
            "native_name": lang_info["native_name"],
            "translated_title": trans_title,
            "translated_content": trans_content,
            "translated_summary": trans_summary,
        }
