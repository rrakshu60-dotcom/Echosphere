"""
EchoSphere SOTA Gemma Instruction Dataset Generator (Deep Training Overhaul)
Synthesizes 50,000+ high-fidelity, diverse conversational instruction-tuning samples:
1. Conversational Intelligence:
   - 50+ contextual greetings with natural, warm responses
   - Follow-up conversations, emotional awareness, clarification requests (ELI5)
   - User identity handling (accurate identification when asked, unprompted modesty)
2. Smart Guardrails & Adversarial Hardening:
   - Nuanced, contextual refusals (soft redirects, polite declines, boundary reasoning)
   - 200+ adversarial prompt examples (jailbreaks, DAN, prompt injection, authority spoofing)
   - Borderline allowed vs disallowed training pairs (teaching boundary discernment)
3. Deep Academic Tutoring (80+ unique scenarios across all 8 branches):
   - AIML, CSE, ISE, ECE, EEE, MECH, CIVIL, BT
   - Multi-step reasoning chains (problem -> approach -> solution -> verification)
   - "Explain like I'm 5" (ELI5) intuitive conceptual analogies
   - Comparison questions & practice problem walkthroughs
4. Context-Aware Personalization & Role-Specific Response Depth:
   - Student (tutoring, study methods, exam prep)
   - Teacher (notice drafting, assignment rubrics, lab viva)
   - HoD (approval workflows, department coordination)
   - College Admin & Principal (campus broadcasts, emergency sirens)
   - Dev Admin (system diagnostics, IoT telemetry)
5. Multi-Turn Depth:
   - 30+ dialogues including 2-turn, 3-turn, and 4-turn progressions and mid-chat topic shifts
6. Academic Productivity & Cognitive Study Mentorship:
   - Feynman Technique, Spaced Repetition, Pomodoro, Cornell Notes, 14-day revision plans
7. Institutional Drafting & Platform Navigation:
   - Leave letters, OD requests, LoR emails, FDP notices, [[ACTION:...]] tags
"""

import os
import sys
import json
import random
import re
from typing import List, Dict, Any, Tuple

# Add local directory to path for submodules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from data.conversational import (
    GREETING_TEMPLATES,
    FOLLOW_UP_CONVERSATIONS,
    EMOTIONAL_AWARENESS_SCENARIOS,
    CLARIFICATION_SCENARIOS,
    USER_IDENTITY_SCENARIOS,
    SAMPLE_NAMES
)
from data.guardrails import (
    SMART_REFUSALS,
    GUARDRAIL_PROMPTS,
    ADVERSARIAL_ATTACK_PATTERNS,
    ANTI_JAILBREAK_RESPONSES,
    BORDERLINE_DISCERNMENT_SCENARIOS
)
from data.academic_scenarios import ACADEMIC_SCENARIOS
from data.multi_turn import MULTI_TURN_CONVERSATIONS
from data.personalization import ROLE_SPECIFIC_SCENARIOS

OUTPUT_DIR = CURRENT_DIR
DATASET_FILE = os.path.join(OUTPUT_DIR, "echosphere_gemma_dataset.jsonl")
OLD_DATASET_FILE = os.path.join(OUTPUT_DIR, "echosphere_campus_gemma_dataset.jsonl")

DEPARTMENTS = ["AIML", "CSE", "ISE", "ECE", "EEE", "MECH", "CIVIL", "BT"]
ROLES = ["Student", "Teacher", "HoD", "College Admin", "Principal", "Dev Admin"]

def clean_training_text(text: str) -> str:
    """Cleans markdown clutter while strictly PRESERVING [[ACTION:...]] tags for model training."""
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r'\s*Feel free to ask about[^\.\n]*\.?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*Ask me about recent circulars[^\.\n]*\.?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*Ask me about[^\.\n]*\.?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^(#{1,6})\s*\$([a-zA-Z0-9_]+)', r'\1 \2', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^[ \t]*(-{3,}|\*{3,}|_{3,}|={3,})[ \t]*$', '\n', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\*{4,}', '**', cleaned)
    cleaned = re.sub(r'\*{3}([^\*\n]+)\*{3}', r'**\1**', cleaned)
    cleaned = re.sub(r'I am (?:the )?\*\*([^\*]+)\*\*', r'I am \1', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'Hello,?\s*\*\*([^\*]+)\*\*', r'Hello \1', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def get_human_designation(role: str) -> str:
    designations = {
        "Dev Admin": "Developer Administrator",
        "devadmin": "Developer Administrator",
        "HoD": "Head of Department",
        "hod": "Head of Department",
        "Teacher": "Faculty Member / Assistant Professor",
        "teacher": "Faculty Member / Assistant Professor",
        "College Admin": "College Administrator",
        "college_admin": "College Administrator",
        "Principal": "Principal",
        "principal": "Principal",
        "Student": "Undergraduate Student",
        "student": "Undergraduate Student",
    }
    return designations.get(role, role)

# ══════════════════════════════════════════════════════════════════════════════
# ACADEMIC PRODUCTIVITY & STUDY MENTORSHIP SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
ACADEMIC_PRODUCTIVITY_SCENARIOS = [
    (
        "How does the Feynman Technique work and how can I use it to study engineering?",
        "The Feynman Technique is a four-step mental model designed to achieve deep conceptual mastery rather than rote memorization:\n\n"
        "1. **Choose a Concept**:\n"
        "   - Write the name of the topic at the top of a blank page (e.g., 'Virtual Memory Paging' or 'Bipolar Junction Transistor Biasing').\n\n"
        "2. **Explain it to a 10-Year-Old**:\n"
        "   - Write out an explanation using plain, everyday language and simple analogies. Avoid technical jargon; if you must use a technical term, define it immediately.\n\n"
        "3. **Identify Knowledge Gaps**:\n"
        "   - Notice whenever you hesitate, reach for jargon, or cannot clearly explain why a step happens. Return to your textbook or lecture notes to clarify that specific mechanism.\n\n"
        "4. **Refine and Simplify**:\n"
        "   - Re-craft your explanation into a seamless, intuitive narrative. If you can explain the core intuition without consulting notes, you genuinely understand it."
    ),
    (
        "What is Spaced Repetition and Active Recall, and why are they better than re-reading notes?",
        "Active Recall and Spaced Repetition leverage cognitive science to build durable long-term memory:\n\n"
        "1. **Active Recall vs. Passive Re-reading**:\n"
        "   - Passive re-reading creates an 'illusion of competence'—material feels familiar because your eyes recognize it, but your brain hasn't practiced retrieval.\n"
        "   - Active Recall forces your brain to retrieve information from memory without looking at notes (e.g., flashcards, practice questions, or closed-book brain dumps).\n\n"
        "2. **Spaced Repetition (The Forgetting Curve)**:\n"
        "   - Ebbinghaus demonstrated that memory decays exponentially without review.\n"
        "   - Reviewing material just as you are about to forget it resets the forgetting curve with a flatter slope.\n"
        "   - Recommended intervals: Day 1 (initial learning) -> Day 3 -> Day 7 -> Day 14 -> Day 30.\n\n"
        "Tools like Anki or digital flashcards automate this scheduling so you spend study time only on cards where retrieval is challenging."
    ),
    (
        "How do I use the Pomodoro Technique effectively for long study sessions?",
        "The Pomodoro Technique maintains cognitive stamina and prevents mental fatigue during intense study sessions:\n\n"
        "1. **The Classic Protocol**:\n"
        "   - **25 Minutes (Focus Block)**: Work on a single specific objective (e.g., derive 3 Maxwell equations) with zero interruptions.\n"
        "   - **5 Minutes (Short Break)**: Step away from screens, stretch, drink water, or walk around.\n"
        "   - **After 4 Cycles**: Take a longer 20-30 minute restorative break.\n\n"
        "2. **Best Practices for Engineering Students**:\n"
        "   - For deep problem-solving or coding, consider extending the cycle to **50 minutes work / 10 minutes break** to stay in deep flow.\n"
        "   - Keep your phone in another room or in Do Not Disturb mode.\n"
        "   - Keep a scratchpad for 'distraction notes'—if a random thought occurs, write it down and return to your focus block."
    ),
    (
        "Explain the Cornell Note-Taking System for engineering lectures",
        "The Cornell System divides a standard notebook page into three functional zones to streamline both in-class recording and post-class revision:\n\n"
        "1. **Right Column (Notes Area, ~70% width)**:\n"
        "   - During the lecture, record main ideas, derivations, circuit diagrams, and professor emphasis using bullet points and abbreviations.\n\n"
        "2. **Left Column (Cue / Question Column, ~30% width)**:\n"
        "   - Immediately after class, review your notes and write concise keywords, formulas, and potential exam questions corresponding to each note block.\n\n"
        "3. **Bottom Band (Summary Section, ~2 inches tall)**:\n"
        "   - Write a 2-3 sentence summary in your own words synthesizing the lecture's core takeaway.\n\n"
        "**Revision Strategy**: Cover the right column and use the left column questions to test yourself with active recall."
    ),
    (
        "I have semester exams in two weeks. How should I structure my revision plan?",
        "Here is a proven 14-day university examination revision framework:\n\n"
        "1. **Days 1–4 (High-Weightage Core Topics)**:\n"
        "   - Map the university syllabus and identify Units 1 through 5.\n"
        "   - Focus on guaranteed core derivations, theorems, and fundamental design problems that appear every year.\n\n"
        "2. **Days 5–8 (Previous Years' Question Papers - PYQs)**:\n"
        "   - Solve the last 5 years of university question papers.\n"
        "   - Practice full numerical questions and circuit diagrams under timed conditions.\n\n"
        "3. **Days 9–11 (Knowledge Gap Remediation)**:\n"
        "   - Address the topics you hesitated on during PYQ practice.\n"
        "   - Create a single-sheet formula and definition cheat sheet for each subject.\n\n"
        "4. **Days 12–14 (Mock Exams & Rapid Review)**:\n"
        "   - Conduct a 3-hour closed-book mock exam.\n"
        "   - Review your summary sheets and prioritize 7–8 hours of restful sleep before exam day."
    ),
    (
        "How should I approach an unseen Data Structures and Algorithms (DSA) problem in a coding interview?",
        "Follow this structured 5-step problem-solving roadmap during technical interviews:\n\n"
        "1. **Clarify Inputs, Outputs & Constraints (2–3 mins)**:\n"
        "   - Ask about array sizes ($N \\le 10^5$ suggests $O(N \\log N)$ or $O(N)$), negative values, duplicates, and edge cases ($N=0$ or null).\n\n"
        "2. **Walk Through Concrete Examples**:\n"
        "   - Trace an example on scratchpad. Identify the pattern before writing any code.\n\n"
        "3. **Develop the Brute Force Solution First**:\n"
        "   - State the naive approach and analyze its Time & Space Complexity (e.g., $O(N^2)$ with nested loops).\n\n"
        "4. **Optimize using Pattern Matching**:\n"
        "   - Ask: Can a Hash Map reduce search from $O(N)$ to $O(1)$? Does sorting enable Two Pointers or Binary Search? Is there overlapping substructure for Dynamic Programming?\n\n"
        "5. **Write Clean Code & Dry Run**:\n"
        "   - Use descriptive variable names. Dry run your code line-by-line with an edge case before submitting."
    ),
    (
        "What is the Google XYZ formula for writing engineering resume bullet points?",
        "The Google XYZ formula transforms passive job descriptions into impactful achievements:\n\n"
        "**Formula**: *'Accomplished [X] as measured by [Y], by doing [Z]'*\n\n"
        "- **Weak Example**: 'Worked on the department website backend using Node.js.'\n"
        "- **Google XYZ Example**: 'Engineered high-throughput REST APIs for the campus circular system using Node.js and Redis, reducing response latency by 42% across 1,500 concurrent student users.'\n\n"
        "**Key Elements**:\n"
        "- **X (Action & Outcome)**: What you achieved.\n"
        "- **Y (Metric)**: Measurable percentage, latency reduction, user count, or accuracy metric.\n"
        "- **Z (Methodology)**: Technologies, algorithms, or architectural patterns utilized."
    )
]

# ══════════════════════════════════════════════════════════════════════════════
# FORMAL INSTITUTIONAL DRAFTING SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
FORMAL_DRAFTING_SCENARIOS = [
    (
        "Draft a formal medical leave letter to my Head of Department (HoD)",
        "Subject: Application for Medical Leave - [Your Name] (Roll No: [Your Roll No])\n\n"
        "To,\n"
        "The Head of Department,\n"
        "Department of [Your Department],\n"
        "[College Name]\n\n"
        "Respected Sir/Madam,\n\n"
        "I am writing to formally request medical leave from [Start Date] to [End Date] due to [brief illness, e.g., viral fever/medical treatment], as advised by my physician. A copy of the medical certificate is attached for your verification.\n\n"
        "I will ensure that I catch up with missed lecture topics, tutorial assignments, and laboratory records promptly upon my return. I kindly request you to grant me leave for the specified period and consider my attendance accordingly.\n\n"
        "Thank you.\n\n"
        "Yours sincerely,\n"
        "[Your Name]\n"
        "Semester & Section: [e.g., 6th Sem, Section A]\n"
        "Roll No / USN: [Your ID]\n"
        "Contact No: [Your Phone Number]"
    ),
    (
        "Draft an On-Duty (OD) attendance request letter for participating in an inter-college Hackathon",
        "Subject: Request for On-Duty (OD) Attendance - Inter-College Hackathon Participation\n\n"
        "To,\n"
        "The Head of Department,\n"
        "Department of [Your Department],\n"
        "[College Name]\n\n"
        "Respected Sir/Madam,\n\n"
        "We are pleased to inform you that our project team has been shortlisted for the final round of [Hackathon Name], organized by [Host Institution Name] on [Dates of Event].\n\n"
        "To represent our college at this technical competition, we kindly request On-Duty (OD) attendance for [Number of Days] days from [Start Date] to [End Date]. The event invitation letter and team confirmation are attached for your reference.\n\n"
        "Participating Team Members:\n"
        "1. [Student Name 1] - [USN/Roll No]\n"
        "2. [Student Name 2] - [USN/Roll No]\n"
        "3. [Student Name 3] - [USN/Roll No]\n\n"
        "We assure you that we will submit all pending assignments and lab work immediately after the event.\n\n"
        "Thank you for your encouragement and support.\n\n"
        "Yours faithfully,\n"
        "[Team Lead Name]\n"
        "[Department & Semester]"
    ),
    (
        "Draft an email to a professor requesting a Letter of Recommendation (LoR) for higher studies",
        "Subject: Request for Letter of Recommendation - [Your Name] (Class of [Year])\n\n"
        "Dear Professor [Professor's Last Name],\n\n"
        "I hope this email finds you well.\n\n"
        "I am writing to respectfully request your support with an academic Letter of Recommendation for my applications to Master's degree programs in [Field of Study, e.g., Computer Science] for the [Semester/Year] intake.\n\n"
        "I thoroughly enjoyed your course on [Course Name] during my [Semester] semester, where I secured an [Grade/Score]. Under your guidance, I also completed [mention project name or research topic], which deepened my interest in [Specific Research Area].\n\n"
        "I have attached my updated resume, academic transcripts, and a summary of the universities and programs I am applying to, along with their respective deadlines. The first submission deadline is [Date].\n\n"
        "I would be deeply grateful for your mentorship and recommendation. Please let me know if you would like to review any additional materials or schedule a brief meeting.\n\n"
        "Thank you very much for your time and guidance.\n\n"
        "Warm regards,\n"
        "[Your Full Name]\n"
        "USN / Roll Number: [Your ID]\n"
        "Department of [Your Department]\n"
        "[Your Contact Number]"
    )
]

# ══════════════════════════════════════════════════════════════════════════════
# PLATFORM NAVIGATION & ACTION SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
PLATFORM_SCENARIOS = [
    (
        "how do i switch to dark mode",
        "Updating your appearance preferences to Dark Mode.\n\n"
        "Enjoy EchoSphere's sleek dark glassmorphic design optimized for low-light campus use.\n\n"
        "[[ACTION:toggle_theme:{\"mode\":\"dark\"}]]"
    ),
    (
        "switch to light mode",
        "Updating your appearance preferences to Light Mode.\n\n"
        "Enjoy a crisp, high-contrast interface optimized for bright outdoor readability.\n\n"
        "[[ACTION:toggle_theme:{\"mode\":\"light\"}]]"
    ),
    (
        "where can i change my password and review security settings",
        "Directing you to Preferences & Security.\n\n"
        "- Update your institutional login credentials.\n"
        "- Review active device tokens and active sessions.\n\n"
        "[[ACTION:navigate:{\"screen\":\"security_preferences\"}]]"
    ),
    (
        "where can i find exam timetables",
        "Directing you to active Examination circulars.\n\n"
        "Review theory exam schedules, practical lab viva batches, and hall ticket release notices.\n\n"
        "[[ACTION:navigate:{\"screen\":\"notices\",\"filter_category\":\"Examinations\"}]]"
    ),
    (
        "show me placement notices and job drives",
        "Filtering circulars for Placements & Recruitment.\n\n"
        "Review visiting enterprise recruiters, eligibility CGPA cutoffs, assessment links, and interview schedules.\n\n"
        "[[ACTION:navigate:{\"screen\":\"notices\",\"filter_category\":\"Placements\"}]]"
    ),
    (
        "how do i filter notices for {dept} department",
        "Filtering circulars for {dept} Department.\n\n"
        "Review departmental memos, lab batch schedules, faculty notices, and symposium updates.\n\n"
        "[[ACTION:navigate:{\"screen\":\"notices\",\"filter_dept\":\"{dept}\"}]]"
    ),
    (
        "take me to the smart speaker queue",
        "Navigating to the EchoSphere Smart Speaker System.\n\n"
        "- Monitor active corridor broadcast nodes.\n"
        "- Review the real-time announcement audio playback queue.\n\n"
        "[[ACTION:navigate:{\"screen\":\"speaker_queue\"}]]"
    ),
    (
        "how do i draft a new announcement",
        "Opening the Announcement Authoring workspace.\n\n"
        "- Enter circular headline, content, priority, and department.\n"
        "- Select delivery channels: In-App Feed, Push Notification, and Corridor Smart Speakers.\n\n"
        "[[ACTION:create_announcement_draft:{}]]"
    )
]

# ══════════════════════════════════════════════════════════════════════════════
# DATASET GENERATION ENGINE (50,000+ SAMPLES)
# ══════════════════════════════════════════════════════════════════════════════
def generate_dataset(target_samples: int = 50000) -> int:
    """Synthesize 50,000+ SOTA instruction-tuning samples in Gemma 2 turn syntax."""
    samples: List[Dict[str, Any]] = []
    print(f"[Dataset] Synthesizing {target_samples} SOTA instruction samples across 8 branches & safety categories...")

    sample_id = 0

    # 1. Base Greetings & Small Talk
    for prompts, resp in GREETING_TEMPLATES:
        for p in prompts:
            for dept in DEPARTMENTS:
                for role in ROLES:
                    clean_resp = clean_training_text(resp)
                    gemma_text = (
                        f"<start_of_turn>user\n{p}<end_of_turn>\n"
                        f"<start_of_turn>model\n{clean_resp}<end_of_turn>"
                    )
                    samples.append({
                        "id": f"sota_sample_{sample_id:06d}",
                        "category": "Conversational Intelligence",
                        "department": dept,
                        "role": role,
                        "text": gemma_text,
                        "prompt": p,
                        "response": clean_resp
                    })
                    sample_id += 1

    # 2. Base Follow-Ups, Emotional Awareness, & Clarifications
    for p, resp in FOLLOW_UP_CONVERSATIONS + EMOTIONAL_AWARENESS_SCENARIOS + CLARIFICATION_SCENARIOS:
        for dept in DEPARTMENTS:
            for role in ["Student", "Teacher"]:
                clean_resp = clean_training_text(resp)
                gemma_text = (
                    f"<start_of_turn>user\n{p}<end_of_turn>\n"
                    f"<start_of_turn>model\n{clean_resp}<end_of_turn>"
                )
                samples.append({
                    "id": f"sota_sample_{sample_id:06d}",
                    "category": "Conversational Intelligence",
                    "department": dept,
                    "role": role,
                    "text": gemma_text,
                    "prompt": p,
                    "response": clean_resp
                })
                sample_id += 1

    # 3. Base User Identity & Designation Awareness
    for prompts, resp_tmpl in USER_IDENTITY_SCENARIOS:
        for p in prompts:
            for dept in DEPARTMENTS:
                for role in ROLES:
                    names = SAMPLE_NAMES.get(role, [("Verified User", "EMP-001")])
                    name, id_num = random.choice(names)
                    desig = get_human_designation(role)
                    resp = (
                        resp_tmpl.replace("{name}", name)
                        .replace("{designation}", desig)
                        .replace("{dept}", dept)
                        .replace("{id_number}", id_num)
                    )
                    clean_resp = clean_training_text(resp)
                    gemma_text = (
                        f"<start_of_turn>user\n{p}<end_of_turn>\n"
                        f"<start_of_turn>model\n{clean_resp}<end_of_turn>"
                    )
                    samples.append({
                        "id": f"sota_sample_{sample_id:06d}",
                        "category": "User Identity & Personalization",
                        "department": dept,
                        "role": role,
                        "text": gemma_text,
                        "prompt": p,
                        "response": clean_resp
                    })
                    sample_id += 1

    # 4. Base Role-Specific Personalization
    for role, scenarios in ROLE_SPECIFIC_SCENARIOS.items():
        for prompt, resp in scenarios:
            for dept in DEPARTMENTS:
                user_text = prompt.replace("{dept}", dept)
                model_text = clean_training_text(resp.replace("{dept}", dept))
                gemma_text = (
                    f"<start_of_turn>user\n{user_text}<end_of_turn>\n"
                    f"<start_of_turn>model\n{model_text}<end_of_turn>"
                )
                samples.append({
                    "id": f"sota_sample_{sample_id:06d}",
                    "category": "User Identity & Personalization",
                    "department": dept,
                    "role": role,
                    "text": gemma_text,
                    "prompt": user_text,
                    "response": model_text
                })
                sample_id += 1

    # 5. Base Anti-Jailbreak Hardening
    for attack in ADVERSARIAL_ATTACK_PATTERNS:
        for dept in ["CSE", "AIML"]:
            resp = random.choice(ANTI_JAILBREAK_RESPONSES)
            clean_resp = clean_training_text(resp)
            gemma_text = (
                f"<start_of_turn>user\n{attack}<end_of_turn>\n"
                f"<start_of_turn>model\n{clean_resp}<end_of_turn>"
            )
            samples.append({
                "id": f"sota_sample_{sample_id:06d}",
                "category": "Anti-Jailbreak & Adversarial Defense",
                "department": dept,
                "role": "Student",
                "text": gemma_text,
                "prompt": attack,
                "response": clean_resp
            })
            sample_id += 1

    # 6. Base Borderline Discernment Scenarios
    for prompt, resp in BORDERLINE_DISCERNMENT_SCENARIOS:
        for dept in DEPARTMENTS:
            clean_resp = clean_training_text(resp.replace("{dept}", dept))
            gemma_text = (
                f"<start_of_turn>user\n{prompt}<end_of_turn>\n"
                f"<start_of_turn>model\n{clean_resp}<end_of_turn>"
            )
            samples.append({
                "id": f"sota_sample_{sample_id:06d}",
                "category": "Borderline Discernment",
                "department": dept,
                "role": "Student",
                "text": gemma_text,
                "prompt": prompt,
                "response": clean_resp
            })
            sample_id += 1

    # 7. Base Multi-Turn Dialogues (2-turn, 3-turn, 4-turn)
    for dialog in MULTI_TURN_CONVERSATIONS:
        for dept in DEPARTMENTS:
            conversation_history = ""
            for turn_idx, (turn_user, turn_model) in enumerate(dialog):
                t_user = turn_user.replace("{dept}", dept)
                t_model = clean_training_text(turn_model.replace("{dept}", dept))
                conversation_history += (
                    f"<start_of_turn>user\n{t_user}<end_of_turn>\n"
                    f"<start_of_turn>model\n{t_model}<end_of_turn>\n"
                )
                if turn_idx >= 1:  # Multi-turn sample
                    samples.append({
                        "id": f"sota_sample_{sample_id:06d}",
                        "category": "Multi-Turn Depth",
                        "department": dept,
                        "role": "Student",
                        "text": conversation_history.strip(),
                        "prompt": t_user,
                        "response": t_model
                    })
                    sample_id += 1

    # 8. Base Academic Tutoring (80+ unique scenarios across 8 branches)
    for prompt, resp in ACADEMIC_SCENARIOS:
        for dept in DEPARTMENTS:
            for role in ["Student", "Teacher"]:
                clean_resp = clean_training_text(resp)
                gemma_text = (
                    f"<start_of_turn>user\n{prompt}<end_of_turn>\n"
                    f"<start_of_turn>model\n{clean_resp}<end_of_turn>"
                )
                samples.append({
                    "id": f"sota_sample_{sample_id:06d}",
                    "category": "Deep Academic Tutoring",
                    "department": dept,
                    "role": role,
                    "text": gemma_text,
                    "prompt": prompt,
                    "response": clean_resp
                })
                sample_id += 1

    # 9. Base Academic Productivity & Study Mentorship
    for prompt, resp in ACADEMIC_PRODUCTIVITY_SCENARIOS:
        for dept in DEPARTMENTS:
            for role in ["Student", "Teacher"]:
                clean_resp = clean_training_text(resp)
                gemma_text = (
                    f"<start_of_turn>user\n{prompt}<end_of_turn>\n"
                    f"<start_of_turn>model\n{clean_resp}<end_of_turn>"
                )
                samples.append({
                    "id": f"sota_sample_{sample_id:06d}",
                    "category": "Academic Productivity & Mentorship",
                    "department": dept,
                    "role": role,
                    "text": gemma_text,
                    "prompt": prompt,
                    "response": clean_resp
                })
                sample_id += 1

    # 10. Base Platform Navigation & Actions
    for prompt_tmpl, resp_tmpl in PLATFORM_SCENARIOS:
        for dept in DEPARTMENTS:
            for role in ROLES:
                user_text = prompt_tmpl.replace("{dept}", dept).replace("{role}", role)
                model_text = clean_training_text(resp_tmpl.replace("{dept}", dept).replace("{role}", role))
                gemma_text = (
                    f"<start_of_turn>user\n{user_text}<end_of_turn>\n"
                    f"<start_of_turn>model\n{model_text}<end_of_turn>"
                )
                samples.append({
                    "id": f"sota_sample_{sample_id:06d}",
                    "category": "App Knowledge & Actions",
                    "department": dept,
                    "role": role,
                    "text": gemma_text,
                    "prompt": user_text,
                    "response": model_text
                })
                sample_id += 1

    print(f"[Dataset] Base diverse corpus assembled: {len(samples)} distinct samples.")

    # 11. Scale to target_samples with balanced domain weighting
    categories_weights = [
        ("conversational", 0.14),
        ("personalization", 0.10),
        ("anti_jailbreak", 0.10),
        ("borderline_discernment", 0.10),
        ("academic_tutoring", 0.23),
        ("academic_productivity", 0.11),
        ("formal_drafting", 0.08),
        ("multi_turn", 0.05),
        ("platform", 0.09)
    ]
    cats, weights = zip(*categories_weights)

    random.seed(42)
    while sample_id < target_samples:
        choice = random.choices(cats, weights=weights, k=1)[0]
        dept = random.choice(DEPARTMENTS)
        role = random.choice(ROLES)

        if choice == "conversational":
            sub = random.choice(["greeting", "followup", "emotional", "clarification"])
            if sub == "greeting":
                prompts, resp = random.choice(GREETING_TEMPLATES)
                user_text = random.choice(prompts)
                model_text = clean_training_text(resp)
            elif sub == "followup":
                user_text, resp = random.choice(FOLLOW_UP_CONVERSATIONS)
                model_text = clean_training_text(resp)
            elif sub == "emotional":
                user_text, resp = random.choice(EMOTIONAL_AWARENESS_SCENARIOS)
                model_text = clean_training_text(resp)
            else:
                user_text, resp = random.choice(CLARIFICATION_SCENARIOS)
                model_text = clean_training_text(resp)
            cat = "Conversational Intelligence"

        elif choice == "personalization":
            sub = random.choice(["identity", "role_specific"])
            if sub == "identity":
                prompts, resp_tmpl = random.choice(USER_IDENTITY_SCENARIOS)
                user_text = random.choice(prompts)
                names = SAMPLE_NAMES.get(role, [("Verified User", "EMP-001")])
                name, id_num = random.choice(names)
                desig = get_human_designation(role)
                model_text = clean_training_text(
                    resp_tmpl.replace("{name}", name)
                    .replace("{designation}", desig)
                    .replace("{dept}", dept)
                    .replace("{id_number}", id_num)
                )
            else:
                scenarios = ROLE_SPECIFIC_SCENARIOS.get(role, ROLE_SPECIFIC_SCENARIOS["Student"])
                prompt, resp = random.choice(scenarios)
                user_text = prompt.replace("{dept}", dept)
                model_text = clean_training_text(resp.replace("{dept}", dept))
            cat = "User Identity & Personalization"

        elif choice == "anti_jailbreak":
            user_text = random.choice(ADVERSARIAL_ATTACK_PATTERNS)
            model_text = clean_training_text(random.choice(ANTI_JAILBREAK_RESPONSES))
            cat = "Anti-Jailbreak & Adversarial Defense"

        elif choice == "borderline_discernment":
            sub = random.choice(["borderline", "soft_guardrail"])
            if sub == "borderline":
                prompt, resp = random.choice(BORDERLINE_DISCERNMENT_SCENARIOS)
                user_text = prompt.replace("{dept}", dept)
                model_text = clean_training_text(resp.replace("{dept}", dept))
            else:
                user_text = random.choice(GUARDRAIL_PROMPTS)
                model_text = clean_training_text(random.choice(SMART_REFUSALS))
            cat = "Borderline Discernment"

        elif choice == "academic_tutoring":
            prompt, resp = random.choice(ACADEMIC_SCENARIOS)
            user_text = prompt
            model_text = clean_training_text(resp)
            cat = "Deep Academic Tutoring"

        elif choice == "academic_productivity":
            prompt, resp = random.choice(ACADEMIC_PRODUCTIVITY_SCENARIOS)
            user_text = prompt
            model_text = clean_training_text(resp)
            cat = "Academic Productivity & Mentorship"

        elif choice == "formal_drafting":
            prompt_tmpl, resp_tmpl = random.choice(FORMAL_DRAFTING_SCENARIOS)
            user_text = prompt_tmpl.replace("{dept}", dept).replace("{role}", role)
            model_text = clean_training_text(resp_tmpl.replace("{dept}", dept).replace("{role}", role))
            cat = "Formal Drafting & Correspondence"

        elif choice == "multi_turn":
            dialog = random.choice(MULTI_TURN_CONVERSATIONS)
            max_turn = random.randint(1, len(dialog) - 1)
            conversation_history = ""
            for t_i in range(max_turn + 1):
                t_user = dialog[t_i][0].replace("{dept}", dept)
                t_model = clean_training_text(dialog[t_i][1].replace("{dept}", dept))
                conversation_history += (
                    f"<start_of_turn>user\n{t_user}<end_of_turn>\n"
                    f"<start_of_turn>model\n{t_model}<end_of_turn>\n"
                )
            samples.append({
                "id": f"sota_sample_{sample_id:06d}",
                "category": "Multi-Turn Depth",
                "department": dept,
                "role": "Student",
                "text": conversation_history.strip(),
                "prompt": t_user,
                "response": t_model
            })
            sample_id += 1
            continue

        else: # platform
            prompt_tmpl, resp_tmpl = random.choice(PLATFORM_SCENARIOS)
            user_text = prompt_tmpl.replace("{dept}", dept).replace("{role}", role)
            model_text = clean_training_text(resp_tmpl.replace("{dept}", dept).replace("{role}", role))
            cat = "App Knowledge & Actions"

        gemma_text = (
            f"<start_of_turn>user\n{user_text}<end_of_turn>\n"
            f"<start_of_turn>model\n{model_text}<end_of_turn>"
        )
        samples.append({
            "id": f"sota_sample_{sample_id:06d}",
            "category": cat,
            "department": dept,
            "role": role,
            "text": gemma_text,
            "prompt": user_text,
            "response": model_text
        })
        sample_id += 1

    # Shuffle for uniform distribution
    random.shuffle(samples)

    with open(DATASET_FILE, "w", encoding="utf-8") as f:
        for item in samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(OLD_DATASET_FILE, "w", encoding="utf-8") as f:
        for item in samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Audit statistics
    cat_counts = {}
    for s in samples:
        c = s.get("category", "Other")
        cat_counts[c] = cat_counts.get(c, 0) + 1

    print("\n" + "=" * 68)
    print(f"  ECHOSPHERE SOTA DATASET OVERHAUL COMPLETE ({len(samples)} SAMPLES)")
    print("=" * 68)
    for c, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(samples)) * 100
        print(f"  {c:<40}: {count:>6} samples ({pct:>5.1f}%)")
    print("=" * 68)
    print(f"  Target File:  {DATASET_FILE}")
    print(f"  Mirror File:  {OLD_DATASET_FILE}")
    print("=" * 68 + "\n")

    return len(samples)


if __name__ == "__main__":
    generate_dataset(50000)
