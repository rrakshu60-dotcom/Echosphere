import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def ask_gemini(prompt: str, system_instruction: str = "") -> str:
    key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

    if key and key != "YOUR_ACTUAL_GEMINI_API_KEY":
        # 1. Try REST API
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
            resp = requests.post(url, json=payload, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        return parts[0].get("text").strip()
        except Exception as e:
            print(f"[AIML Gemini REST Error]: {e}")

        # 2. Try SDK
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(full_prompt)
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[AIML Gemini SDK Error]: {e}")

    return _local_fallback_response(prompt)

def _local_fallback_response(prompt: str) -> str:
    text = prompt.lower()
    if "category" in text:
        if any(w in text for w in ['exam', 'test', 'marks', 'viva']):
            return "Category: Academic\nReason: Examination or academic schedule detected."
        if any(w in text for w in ['rain', 'closed', 'flood', 'suspended']):
            return "Category: Emergency\nReason: Weather alert or campus suspension."
        if any(w in text for w in ['placement', 'job', 'interview', 'hiring']):
            return "Category: Placements\nReason: Recruitment drive notification."
        if any(w in text for w in ['sports', 'match', 'cricket']):
            return "Category: Sports\nReason: Athletic or sports activity."
        return "Category: Academic\nReason: General campus announcement."

    if "priority" in text:
        if any(w in text for w in ['emergency', 'rain', 'closed', 'flood']):
            return "Priority: Emergency\nReason: High severity campus alert."
        if any(w in text for w in ['exam', 'timetable', 'hall ticket', 'placement']):
            return "Priority: High\nReason: Academic or placement deadline."
        return "Priority: Normal\nReason: Standard announcement."

    if "expand" in text:
        return (
            f"Official Announcement Circular:\n\n"
            f"This is to notify all concerned students and faculty regarding the recent update: {prompt.strip()}.\n\n"
            f"Please adhere strictly to the published schedule and check the EchoSphere portal for further details."
        )

    if "summarize" in text:
        return f"Summary: Important update regarding campus schedule and departmental guidelines."

    return "EchoSphere AI: Processed request successfully in natural language."