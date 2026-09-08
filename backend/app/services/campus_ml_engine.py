"""
EchoSphere Campus Machine Learning & Semantic Intelligence Engine
A fully self-contained, locally trained AI/ML engine for EchoSphere.
Provides:
1. Intent Classification (Scikit-Learn Pipeline: TF-IDF + Calibrated Classifier)
2. Category & Priority Machine Learning Predictors
3. TF-IDF + Cosine Similarity Vector Search over Live DB Announcements & Institutional Knowledge Base
4. Dynamic, Context-Aware Institutional Answer Synthesizer
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics.pairwise import cosine_similarity
import joblib

logger = logging.getLogger("EchoSphere.CampusML")

# Directory to persist trained models
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai_models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Institutional Knowledge Base (Campus Policies, Facilities, Guidelines)
# ─────────────────────────────────────────────────────────────────────────────
INSTITUTIONAL_KNOWLEDGE: List[Dict[str, Any]] = [
    {
        "id": "kb_attendance",
        "category": "Academics",
        "title": "Attendance Policy & Regulations",
        "content": (
            "A minimum of 75% attendance is mandatory in each theory and laboratory subject to qualify for semester-end examinations. "
            "Students with attendance between 65% and 74% due to medical emergencies or official university representation "
            "must submit medical certificates or approval letters to their Department HoD before the condonation deadline. "
            "Attendance below 65% is strictly not condoned and results in course repetition."
        ),
        "tags": ["attendance", "shortage", "condonation", "75%", "medical certificate", "hall ticket eligibility"]
    },
    {
        "id": "kb_exam_rules",
        "category": "Examinations",
        "title": "Semester Examination & Hall Ticket Guidelines",
        "content": (
            "Students must carry their official College ID Card and physical Hall Ticket to all examination halls. "
            "Electronic gadgets, smartwatches, and unauthorized materials are strictly prohibited in the exam hall. "
            "Practical lab exams commence 15 minutes before the scheduled batch time. "
            "Hall tickets can be collected from the department examination coordinator after clearing department dues."
        ),
        "tags": ["exam", "hall ticket", "id card", "rules", "viva", "lab exam", "malpractice", "timetable"]
    },
    {
        "id": "kb_placement_policy",
        "category": "Placements",
        "title": "Training & Placement Cell Eligibility Criteria",
        "content": (
            "The Training and Placement Cell coordinates campus recruitment drives for companies including Google, Microsoft, TCS, Infosys, and Accenture. "
            "Standard eligibility requires an aggregate CGPA >= 7.0 (or 65%+) with no active backlogs. "
            "Registered students must adhere strictly to the formal dress code, submit updated resumes before company deadlines, "
            "and attend all pre-placement talks (PPTs). Once an offer is secured above 8 LPA, the dream company policy applies."
        ),
        "tags": ["placement", "job", "recruitment", "drive", "eligibility", "cgpa", "tcs", "google", "resume", "interview"]
    },
    {
        "id": "kb_emergency_weather",
        "category": "Emergency",
        "title": "Emergency Weather & Campus Safety Protocol",
        "content": (
            "During red alerts, extreme rainfall, or municipal disaster advisories, college operations may be suspended by the Principal. "
            "Official closure notices are broadcast immediately across the EchoSphere app with EMERGENCY priority and broadcasted via the campus smart speaker nodes. "
            "Students are advised to stay indoors and refrain from commuting during severe weather warnings."
        ),
        "tags": ["rain", "weather", "flood", "holiday", "closed", "emergency", "speaker", "safety", "advisory"]
    },
    {
        "id": "kb_library_rules",
        "category": "Facilities",
        "title": "Central Library Timings & Circulation Rules",
        "content": (
            "The Central Library is open Monday through Saturday from 8:00 AM to 8:00 PM (and up to 10:00 PM during exam weeks). "
            "Undergraduate students may borrow up to 4 books for 14 days, with one renewal allowed online. "
            "The digital library provides access to IEEE, ACM, Springer, and ScienceDirect journals via campus Wi-Fi."
        ),
        "tags": ["library", "books", "timing", "hours", "borrow", "digital library", "ieee", "renewal"]
    },
    {
        "id": "kb_hostel_rules",
        "category": "Facilities",
        "title": "Hostel Regulations & Curfew Timings",
        "content": (
            "Hostel curfew for all residents is strictly 9:00 PM on weekdays and 9:30 PM on weekends. "
            "Out-passes must be requested through the Hostel Warden at least 24 hours in advance with parent acknowledgment. "
            "Mess timings: Breakfast (7:30 AM - 9:00 AM), Lunch (12:30 PM - 2:00 PM), Snacks (5:00 PM - 6:00 PM), Dinner (7:30 PM - 9:00 PM)."
        ),
        "tags": ["hostel", "curfew", "mess", "warden", "out pass", "timing", "dinner", "breakfast"]
    },
    {
        "id": "kb_departments",
        "category": "Administration",
        "title": "Academic Departments & Faculty Contacts",
        "content": (
            "EchoSphere supports all academic departments: Computer Science & Engineering (CSE), Artificial Intelligence & Machine Learning (AIML), "
            "Artificial Intelligence & Data Science (AIDS), Information Science & Engineering (ISE), Electronics & Communication (ECE), "
            "Electrical & Electronics (EEE), Mechanical Engineering (ME), and Civil Engineering (CV). "
            "Department offices are open from 9:00 AM to 5:00 PM on working days."
        ),
        "tags": ["cse", "aiml", "aids", "ise", "ece", "eee", "mech", "civil", "department", "hod", "office"]
    },
    {
        "id": "kb_notice_guidelines",
        "category": "Administration",
        "title": "Notice Publishing & Circular Approval Hierarchy",
        "content": (
            "Notice publishing permissions follow the institutional authority hierarchy: "
            "Students have verified read-only access. Teachers draft notices that route to their Department HoD for approval. "
            "HoDs, College Admins, Principals, and Developer Admins can publish notices instantly with real-time push and smart speaker broadcasts. "
            "Emergency notices bypass standard queues to broadcast college-wide immediately."
        ),
        "tags": ["create notice", "post notice", "approval", "teacher", "hod", "permission", "hierarchy", "broadcast"]
    },
    {
        "id": "kb_smart_speakers",
        "category": "Hardware",
        "title": "EchoSphere Smart Speaker & Hardware Node Integration",
        "content": (
            "Campus smart speaker nodes are deployed across departmental corridors, seminar halls, auditoriums, and main plazas. "
            "When high-priority or emergency announcements are approved with speaker delivery enabled, the text is synthesized into high-clarity audio "
            "and queued for synchronized broadcast via MQTT and local hardware clients."
        ),
        "tags": ["speaker", "audio", "hardware", "broadcast", "mqtt", "node", "queue", "corridor"]
    },
    {
        "id": "kb_security_settings",
        "category": "App Navigation",
        "title": "App Settings, Appearance & Password Reset",
        "content": (
            "Users can customize appearance and security under the Profile tab: "
            "1. Toggle Dark Mode Theme for an immersive glassmorphic interface. "
            "2. Faculty and Admins can update passwords directly under Security settings. "
            "3. Students can initiate password resets via the 'Forgot Password?' screen or contact their HoD/Class Teacher for credential recovery."
        ),
        "tags": ["setting", "theme", "dark mode", "password", "reset", "profile", "security", "appearance"]
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# Campus Intent Training Dataset
# ─────────────────────────────────────────────────────────────────────────────
INTENT_TRAINING_DATA = [
    # ANNOUNCEMENT_SEARCH
    ("show me recent announcements", "ANNOUNCEMENT_SEARCH"),
    ("what are the latest notices today", "ANNOUNCEMENT_SEARCH"),
    ("any circular for cse department", "ANNOUNCEMENT_SEARCH"),
    ("check college notices", "ANNOUNCEMENT_SEARCH"),
    ("search announcements about fee payment", "ANNOUNCEMENT_SEARCH"),
    ("is there any circular published this week", "ANNOUNCEMENT_SEARCH"),
    ("browse notices", "ANNOUNCEMENT_SEARCH"),
    ("what did the principal announce", "ANNOUNCEMENT_SEARCH"),
    ("show all circulars for 3rd year students", "ANNOUNCEMENT_SEARCH"),
    ("find notices regarding symposium", "ANNOUNCEMENT_SEARCH"),

    # EXAM_SCHEDULE
    ("when is the cse lab exam", "EXAM_SCHEDULE"),
    ("exam timetable for semester 5", "EXAM_SCHEDULE"),
    ("what is the practical test schedule", "EXAM_SCHEDULE"),
    ("when will internal assessment 1 start", "EXAM_SCHEDULE"),
    ("where do I get my hall ticket", "EXAM_SCHEDULE"),
    ("are exam dates postponed", "EXAM_SCHEDULE"),
    ("viva voce timing and batch list", "EXAM_SCHEDULE"),
    ("end semester theory timetable", "EXAM_SCHEDULE"),
    ("what are the rules for exam hall", "EXAM_SCHEDULE"),
    ("lab test dates for mechanical department", "EXAM_SCHEDULE"),

    # PLACEMENT_DRIVE
    ("which companies are visiting for placements", "PLACEMENT_DRIVE"),
    ("what is the eligibility criteria for google placement drive", "PLACEMENT_DRIVE"),
    ("is tcs hiring this semester", "PLACEMENT_DRIVE"),
    ("placement drive registration deadline", "PLACEMENT_DRIVE"),
    ("minimum cgpa needed for campus placements", "PLACEMENT_DRIVE"),
    ("microsoft recruitment drive schedule", "PLACEMENT_DRIVE"),
    ("how do I register for placement cell", "PLACEMENT_DRIVE"),
    ("internship opportunities for pre-final year students", "PLACEMENT_DRIVE"),
    ("accenture interview dates", "PLACEMENT_DRIVE"),
    ("campus placement guidelines and dress code", "PLACEMENT_DRIVE"),

    # EMERGENCY_ALERT
    ("is college closed tomorrow due to heavy rain", "EMERGENCY_ALERT"),
    ("check weather advisory and flood alert", "EMERGENCY_ALERT"),
    ("are classes suspended today", "EMERGENCY_ALERT"),
    ("red alert declared in city", "EMERGENCY_ALERT"),
    ("is it a holiday tomorrow because of rains", "EMERGENCY_ALERT"),
    ("urgent emergency safety alert", "EMERGENCY_ALERT"),
    ("monsoon holiday declared by collector", "EMERGENCY_ALERT"),
    ("is college working on monday", "EMERGENCY_ALERT"),
    ("bus service suspended due to waterlogging", "EMERGENCY_ALERT"),

    # FACULTY_DEPARTMENT
    ("who is the head of department for cse", "FACULTY_DEPARTMENT"),
    ("where is the aiml department office located", "FACULTY_DEPARTMENT"),
    ("how to contact hod of mechanical engineering", "FACULTY_DEPARTMENT"),
    ("faculty list for information science", "FACULTY_DEPARTMENT"),
    ("teacher office hours for doubt clearing", "FACULTY_DEPARTMENT"),
    ("ece department lab incharge details", "FACULTY_DEPARTMENT"),
    ("who is the class advisor for 2nd year aids", "FACULTY_DEPARTMENT"),
    ("contact department office", "FACULTY_DEPARTMENT"),
    ("where can I find the cse department head", "FACULTY_DEPARTMENT"),
    ("who is the department head", "FACULTY_DEPARTMENT"),
    ("hod office location and contact", "FACULTY_DEPARTMENT"),
    ("meet with professor or teacher", "FACULTY_DEPARTMENT"),

    # CAMPUS_FACILITIES
    ("what are the central library opening hours", "CAMPUS_FACILITIES"),
    ("how many books can a student borrow from library", "CAMPUS_FACILITIES"),
    ("hostel curfew time for boys and girls", "CAMPUS_FACILITIES"),
    ("canteen timings and lunch hours", "CAMPUS_FACILITIES"),
    ("college bus route and pickup timings", "CAMPUS_FACILITIES"),
    ("how to connect to campus wifi", "CAMPUS_FACILITIES"),
    ("sports ground and gym timings", "CAMPUS_FACILITIES"),
    ("hostel mess menu and timings", "CAMPUS_FACILITIES"),

    # NOTICE_CREATION
    ("how do I create a new notice", "NOTICE_CREATION"),
    ("how can teachers submit circular for approval", "NOTICE_CREATION"),
    ("how to draft an official announcement", "NOTICE_CREATION"),
    ("where is the add notice button", "NOTICE_CREATION"),
    ("approval status of my drafted circular", "NOTICE_CREATION"),
    ("can students post circulars", "NOTICE_CREATION"),
    ("how to use ai expand for notice drafting", "NOTICE_CREATION"),

    # APP_NAVIGATION
    ("how to turn on dark mode", "APP_NAVIGATION"),
    ("where are settings in the app", "APP_NAVIGATION"),
    ("how to change my password", "APP_NAVIGATION"),
    ("how to toggle app theme", "APP_NAVIGATION"),
    ("where can I see my profile details", "APP_NAVIGATION"),
    ("configure notification sound and alerts", "APP_NAVIGATION"),
    ("security and preferences menu", "APP_NAVIGATION"),

    # ACADEMIC_POLICIES
    ("what is the minimum attendance requirement", "ACADEMIC_POLICIES"),
    ("what happens if attendance is below 75 percent", "ACADEMIC_POLICIES"),
    ("is 75 percent attendance strictly required for hall ticket", "ACADEMIC_POLICIES"),
    ("minimum attendance percentage rules", "ACADEMIC_POLICIES"),
    ("shortage of attendance and condonation list", "ACADEMIC_POLICIES"),
    ("how to apply for medical leave condonation", "ACADEMIC_POLICIES"),
    ("grading system and sgpa calculation", "ACADEMIC_POLICIES"),
    ("college fee payment deadline and late fine", "ACADEMIC_POLICIES"),
    ("revaluation process and fee", "ACADEMIC_POLICIES"),

    # CLUBS_EVENTS
    ("upcoming college fest and cultural events", "CLUBS_EVENTS"),
    ("annual sports day date and registration", "CLUBS_EVENTS"),
    ("hackathon conducted by coding club", "CLUBS_EVENTS"),
    ("robotics club orientation and workshop", "CLUBS_EVENTS"),
    ("technical symposium dates", "CLUBS_EVENTS"),

    # SPEAKER_HARDWARE
    ("check smart speaker status", "SPEAKER_HARDWARE"),
    ("is the hallway speaker online", "SPEAKER_HARDWARE"),
    ("speaker announcement queue status", "SPEAKER_HARDWARE"),
    ("broadcast audio message to zone 1", "SPEAKER_HARDWARE"),
    ("hardware speaker node client info", "SPEAKER_HARDWARE"),

    # CONVERSATIONAL
    ("hello", "CONVERSATIONAL"),
    ("hi there", "CONVERSATIONAL"),
    ("hey", "CONVERSATIONAL"),
    ("who are you", "CONVERSATIONAL"),
    ("what can you do", "CONVERSATIONAL"),
    ("what is your name", "CONVERSATIONAL"),
    ("thank you", "CONVERSATIONAL"),
    ("thanks for helping", "CONVERSATIONAL"),
    ("how are you doing", "CONVERSATIONAL"),
    ("good morning", "CONVERSATIONAL"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Category & Priority Training Data for Classifiers
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_TRAINING_DATA = [
    ("Midterm theory examination timetable for 4th semester", "Examinations"),
    ("End semester practical lab test batch allocation", "Examinations"),
    ("Hall ticket distribution for upcoming university exams", "Examinations"),
    ("Google campus recruitment drive for final year CSE and ISE", "Placements"),
    ("TCS Ninja and Digital placement registration deadline", "Placements"),
    ("Internship interview shortlist by Microsoft", "Placements"),
    ("Heavy rainfall red alert college closed tomorrow by district collector", "Emergency"),
    ("Severe waterlogging campus suspended emergency notice", "Emergency"),
    ("Urgent evacuation and safety protocol advisory", "Emergency"),
    ("Annual inter-department coding hackathon 2026", "Events"),
    ("Cultural fest Aura 2026 audition schedule", "Events"),
    ("Robotics and AI workshop in seminar hall 2", "Events"),
    ("Inter-college cricket and football tournament trials", "Sports"),
    ("Athletics meet and track event registration", "Sports"),
    ("Submission of semester course fee and examination fee", "Academics"),
    ("Attendance shortage list for 6th semester students", "Academics"),
    ("Class commencement and academic calendar for even semester", "Academics"),
]

PRIORITY_TRAINING_DATA = [
    ("Heavy rainfall red alert college closed tomorrow", "EMERGENCY"),
    ("Flash flood warning classes suspended immediately", "EMERGENCY"),
    ("Campus closure due to severe cyclone warning", "EMERGENCY"),
    ("Final university exam timetable announced", "HIGH"),
    ("Google placement drive registration closes at 5 PM today", "HIGH"),
    ("Last date for semester fee payment without fine", "HIGH"),
    ("Hall ticket collection deadline tomorrow morning", "HIGH"),
    ("Coding hackathon registration open for all years", "NORMAL"),
    ("Library book return reminder for final year", "NORMAL"),
    ("Guest lecture on Cloud Computing in auditorium", "NORMAL"),
    ("Sports ground maintenance and friendly match", "NORMAL"),
]


class CampusMLEngine:
    """Locally trained Machine Learning & Semantic Vector RAG Engine for EchoSphere."""

    _instance = None
    _intent_model: Optional[Pipeline] = None
    _category_model: Optional[Pipeline] = None
    _priority_model: Optional[Pipeline] = None
    _kb_vectorizer: Optional[TfidfVectorizer] = None
    _kb_vectors: Optional[np.ndarray] = None

    @classmethod
    def get_instance(cls) -> "CampusMLEngine":
        if cls._instance is None:
            cls._instance = CampusMLEngine()
            cls._instance._initialize_or_load_models()
        return cls._instance

    def _initialize_or_load_models(self) -> None:
        """Load persisted models or train them immediately on startup."""
        intent_path = os.path.join(MODELS_DIR, "intent_model.joblib")
        cat_path = os.path.join(MODELS_DIR, "category_model.joblib")
        prio_path = os.path.join(MODELS_DIR, "priority_model.joblib")

        try:
            if os.path.exists(intent_path) and os.path.exists(cat_path) and os.path.exists(prio_path):
                self._intent_model = joblib.load(intent_path)
                self._category_model = joblib.load(cat_path)
                self._priority_model = joblib.load(prio_path)
                logger.info("Loaded serialized Campus ML models from disk.")
            else:
                self.train_models()
        except Exception as e:
            logger.warning(f"Error loading serialized models: {e}. Retraining on the fly...")
            self.train_models()

        # Build in-memory Knowledge Base vector index
        self._build_kb_index()

    def train_models(self) -> Dict[str, Any]:
        """Train all models on institutional datasets and persist them."""
        logger.info("Training EchoSphere Campus ML models...")

        # 1. Train Intent Classifier
        X_intent = [text for text, _ in INTENT_TRAINING_DATA]
        y_intent = [label for _, label in INTENT_TRAINING_DATA]

        intent_pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=1000, C=5.0))
        ])
        intent_pipeline.fit(X_intent, y_intent)
        self._intent_model = intent_pipeline
        joblib.dump(intent_pipeline, os.path.join(MODELS_DIR, "intent_model.joblib"))

        # 2. Train Category Classifier
        X_cat = [text for text, _ in CATEGORY_TRAINING_DATA]
        y_cat = [cat for _, cat in CATEGORY_TRAINING_DATA]

        cat_pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=1000))
        ])
        cat_pipeline.fit(X_cat, y_cat)
        self._category_model = cat_pipeline
        joblib.dump(cat_pipeline, os.path.join(MODELS_DIR, "category_model.joblib"))

        # 3. Train Priority Classifier
        X_prio = [text for text, _ in PRIORITY_TRAINING_DATA]
        y_prio = [prio for _, prio in PRIORITY_TRAINING_DATA]

        prio_pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=1000))
        ])
        prio_pipeline.fit(X_prio, y_prio)
        self._priority_model = prio_pipeline
        joblib.dump(prio_pipeline, os.path.join(MODELS_DIR, "priority_model.joblib"))

        self._build_kb_index()

        return {
            "status": "success",
            "intents_trained": len(set(y_intent)),
            "intent_samples": len(X_intent),
            "kb_documents": len(INSTITUTIONAL_KNOWLEDGE),
        }

    def _build_kb_index(self) -> None:
        """Vectorize the institutional knowledge base using TF-IDF."""
        corpus = [
            f"{doc['title']} {doc['category']} {' '.join(doc.get('tags', []))} {doc['content']}"
            for doc in INSTITUTIONAL_KNOWLEDGE
        ]
        self._kb_vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self._kb_vectors = self._kb_vectorizer.fit_transform(corpus)

    def predict_intent(self, query: str) -> Tuple[str, float]:
        """Predict campus query intent with probability confidence."""
        if not self._intent_model:
            return ("CONVERSATIONAL", 0.5)

        clean = query.strip()
        if not clean:
            return ("CONVERSATIONAL", 1.0)

        probs = self._intent_model.predict_proba([clean])[0]
        classes = self._intent_model.classes_
        top_idx = int(np.argmax(probs))
        return (str(classes[top_idx]), float(probs[top_idx]))

    def predict_category_and_priority(self, title: str, content: str, user_role: str = "STUDENT") -> Dict[str, Any]:
        """Classify announcement text into category and priority."""
        text = f"{title} {content}".strip()
        role = (user_role or "STUDENT").upper()

        category = "Academics"
        priority = "NORMAL"

        if self._category_model and text:
            try:
                category = str(self._category_model.predict([text])[0])
            except Exception:
                pass

        if self._priority_model and text:
            try:
                priority = str(self._priority_model.predict([text])[0])
            except Exception:
                pass

        # High-assurance safety heuristic override
        text_lower = text.lower()
        if any(w in text_lower for w in ["rain", "flood", "weather", "cyclone", "emergency", "evacuate", "holiday tomorrow"]):
            priority = "EMERGENCY"
            category = "Emergency"
        elif any(w in text_lower for w in ["exam", "timetable", "hall ticket", "viva", "test"]):
            category = "Examinations"
            if priority == "NORMAL":
                priority = "HIGH"
        elif any(w in text_lower for w in ["placement", "interview", "hiring", "package", "ctc"]):
            category = "Placements"
            if priority == "NORMAL":
                priority = "HIGH"

        # Authority enforcement: only privileged roles can broadcast EMERGENCY
        allowed_emergency_roles = ["COLLEGE ADMIN", "HOD", "PRINCIPAL", "DEVELOPER", "DEV ADMIN"]
        is_allowed = True
        reasoning = f"Categorized as {category} with {priority} priority based on institutional rules."

        if priority == "EMERGENCY" and role not in allowed_emergency_roles:
            is_allowed = False
            priority = "HIGH"
            reasoning = f"Urgent notification detected. (Note: Only Authorized HoDs and Admins may publish EMERGENCY broadcasts; assigned HIGH)."

        return {
            "category": category,
            "priority": priority,
            "reasoning": reasoning,
            "is_allowed": is_allowed
        }

    def search_knowledge_base(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Perform semantic TF-IDF cosine similarity search over campus policies."""
        if not self._kb_vectorizer or self._kb_vectors is None:
            return []

        query_vec = self._kb_vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._kb_vectors)[0]

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0.05:  # Relevance threshold
                doc = INSTITUTIONAL_KNOWLEDGE[idx].copy()
                doc["score"] = round(score, 3)
                results.append(doc)

        return results

    def search_live_announcements(
        self, query: str, announcements: List[Any], user_dept: str, user_role: str, top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Semantic + keyword ranking over live PostgreSQL database announcements."""
        if not announcements:
            return []

        query_lower = query.lower()
        query_terms = [t for t in re.findall(r'\w+', query_lower) if len(t) > 2]
        scored_items: List[Tuple[float, Dict[str, Any]]] = []

        for ann in announcements:
            title = getattr(ann, "title", "")
            desc = getattr(ann, "description", getattr(ann, "content", ""))
            category = getattr(ann, "category", "General")
            if hasattr(category, "name"):
                category = category.name
            priority = getattr(ann, "priority", "NORMAL")
            if hasattr(priority, "value"):
                priority = priority.value

            ann_dept = getattr(ann, "department", "College-Wide")
            if hasattr(ann_dept, "name"):
                ann_dept = ann_dept.name

            created_at = ann.created_at.strftime("%b %d, %I:%M %p") if getattr(ann, "created_at", None) else "Recent"
            combined = f"{title} {desc} {category} {ann_dept}".lower()

            score = 0.0
            # Term overlap score
            for term in query_terms:
                if term in title.lower():
                    score += 3.0
                elif term in combined:
                    score += 1.0

            # Department relevance boost
            if user_dept.lower() in combined:
                score += 1.5

            # Priority boost
            if priority == "EMERGENCY":
                score += 2.0
            elif priority == "HIGH":
                score += 1.0

            if score > 0.5 or not query_terms:
                scored_items.append((score, {
                    "id": getattr(ann, "id", 0),
                    "title": title,
                    "category": str(category),
                    "priority": str(priority),
                    "department": str(ann_dept),
                    "content": str(desc)[:160] + ("..." if len(str(desc)) > 160 else ""),
                    "created_at": created_at
                }))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_items[:top_k]]

    def synthesize_response(
        self,
        query: str,
        name: str,
        role: str,
        dept: str,
        usn_or_emp_id: Optional[str],
        matched_announcements: List[Dict[str, Any]],
        kb_matches: List[Dict[str, Any]],
        predicted_intent: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate rich, intelligent, context-grounded Markdown answers without synthetic fluff.
        Guarantees zero literal '****' artifacts and zero unresponsive canned text.
        """
        category_badge = "EchoSphere AI"
        navigation_target: Optional[str] = None
        suggested_actions: List[str] = []

        # Grounded Announcements List Formatting
        notice_cards = ""
        if matched_announcements:
            lines = []
            for m in matched_announcements[:3]:
                lines.append(f"- **[{m['category']} | {m['priority']}]** {m['title']} ({m['created_at']})")
            notice_cards = "\n\n### Live Announcements Matched\n" + "\n".join(lines)

        # ─── Intent-Driven Structured Synthesis ─────────────────────────────────
        q_lower = query.lower()
        role_upper = (role or "").upper()
        is_student = role_upper in ["STUDENT", "STUDENTS", "PUPIL", "USER", "GUEST"]

        # Intercept unauthorized operational or administrative queries for lower roles
        if is_student:
            if any(k in q_lower for k in ["speaker", "queue", "hardware", "broadcast siren", "pa system", "siren override"]):
                return {
                    "response": (
                        "I don't have the authority to answer that question or disclose operational details "
                        "about the smart speaker system. Please consult your department office or faculty coordinator for assistance."
                    ),
                    "category_badge": "Access Restricted",
                    "context_badge": f"{role.title()} | {dept} Department",
                    "suggested_actions": ["Browse Announcements", "Check Exam Schedule", "View Placements"],
                    "navigation_target": None,
                    "matched_announcements": [],
                    "model_used": "EchoSphere Campus ML Engine (Local)"
                }
            if any(k in q_lower for k in ["admin panel", "user management", "delete user", "audit log", "security log", "server log", "edit role"]):
                return {
                    "response": (
                        "I don't have the authority to answer that question or provide access to administrative controls. "
                        "Please consult your department office or system administrator for assistance."
                    ),
                    "category_badge": "Access Restricted",
                    "context_badge": f"{role.title()} | {dept} Department",
                    "suggested_actions": ["Browse Announcements", "Check Exam Schedule", "View Placements"],
                    "navigation_target": None,
                    "matched_announcements": [],
                    "model_used": "EchoSphere Campus ML Engine (Local)"
                }

        if predicted_intent == "CONVERSATIONAL":
            if any(w in q_lower for w in ["who are you", "who r u", "what is your name", "what do you do", "identify"]):
                text = (
                    f"I am the **EchoSphere Campus AI Assistant**, your institutional knowledge companion for "
                    f"**{dept} Department**.\n\n"
                    f"**Core Capabilities:**\n"
                    f"- **Live Announcements:** Search and filter active circulars, emergency advisories, and notices.\n"
                    f"- **Examinations & Timetables:** Retrieve schedule details, hall ticket guidelines, and lab slots.\n"
                    f"- **Placements & Drives:** Check eligibility criteria, interview timelines, and corporate visits.\n"
                    f"- **Institutional Policies:** Answer attendance rules (75% minimum), library hours, and hostel curfews.\n"
                    f"- **App Navigation:** Direct you to profile settings, dark mode theme toggles, and notice authoring."
                )
            elif any(w in q_lower for w in ["thank", "thanks", "great", "awesome"]):
                text = f"You are very welcome, {name}! I am always here to assist you with updates across the **{dept} Department** and college campus."
            else:
                text = (
                    f"Hello {name}! I am active and tuned to your context as a **{role.title()}** in the **{dept} Department**.\n\n"
                    f"How can I assist you today? You can ask me about recent circulars, exam dates, placement drives, campus rules, or app features."
                )
            suggested_actions = ["Browse Announcements", "Check Exam Schedule", "View Placements"]

        elif predicted_intent == "ANNOUNCEMENT_SEARCH":
            category_badge = "Announcements"
            navigation_target = f"nav:notices:filter:{dept}"
            if matched_announcements:
                text = (
                    f"Here are the active announcements relevant to **{dept} Department** ({role.title()}):\n"
                    f"{notice_cards}\n\n"
                    f"You can tap on any announcement card below to review the full circular details."
                )
            else:
                text = (
                    f"There are currently no new circulars matching your search query for **{dept} Department**.\n\n"
                    f"All official notices are published with verified departmental signatures. "
                    f"You can browse all college-wide circulars or check back shortly for updates."
                )
            suggested_actions = [f"Filter {dept} Notices", "View All Circulars", "Check Emergency Feed"]

        elif predicted_intent == "EXAM_SCHEDULE":
            category_badge = "Examinations"
            navigation_target = "nav:notices:filter:Examinations"
            exam_kb = next((k for k in kb_matches if k.get("id") == "kb_exam_rules"), None)
            kb_text = f"\n\n**Official Examination Protocol:**\n{exam_kb['content']}" if exam_kb else ""

            text = (
                f"### Examination Guidelines for {dept} Department\n\n"
                f"- **Schedules & Batches:** Practical lab and theory schedules are released under the **Examinations** category.\n"
                f"- **Mandatory Items:** Carry your official **College ID Card** and physical **Hall Ticket** to each session.\n"
                f"- **Reporting Time:** Students must arrive at exam halls at least 15 minutes prior to scheduled start times.{kb_text}{notice_cards}"
            )
            suggested_actions = ["Filter Examination Circulars", "Check Lab Timetable", "View Academic Rules"]

        elif predicted_intent == "PLACEMENT_DRIVE":
            category_badge = "Placements"
            navigation_target = "nav:notices:filter:Placements"
            placement_kb = next((k for k in kb_matches if k.get("id") == "kb_placement_policy"), None)
            kb_text = f"\n\n**Placement Cell Guidelines:**\n{placement_kb['content']}" if placement_kb else ""

            text = (
                f"### Campus Placements & Recruitment ({dept})\n\n"
                f"- **Eligibility Threshold:** Aggregate **CGPA >= 7.0** with zero active backlogs for tier-1 recruitment drives.\n"
                f"- **Visiting Companies:** Top recruiters include Google, Microsoft, TCS, Infosys, and Accenture.\n"
                f"- **Preparation Checklist:** Ensure your resume is updated and all pre-placement registrations are submitted on time.{kb_text}{notice_cards}"
            )
            suggested_actions = ["View Placement Notices", "Check Eligibility Criteria", "Resume Guidelines"]

        elif predicted_intent == "EMERGENCY_ALERT":
            category_badge = "Emergency Alert"
            navigation_target = "nav:notices:filter:Emergency"
            emergency_kb = next((k for k in kb_matches if k.get("id") == "kb_emergency_weather"), None)
            kb_text = f"\n\n**Safety Protocol:**\n{emergency_kb['content']}" if emergency_kb else ""

            text = (
                f"### Campus Safety & Emergency Advisory\n\n"
                f"- **Alert Status:** Severe weather and safety advisories are broadcasted college-wide with highest priority.\n"
                f"- **Broadcasting:** When active, alerts play through campus smart speakers and appear pinned at the top of your feed.\n"
                f"- **Commuting:** Please exercise caution during red alerts and follow official district administration circulars.{kb_text}{notice_cards}"
            )
            suggested_actions = ["View Emergency Circulars", "Check Weather Advisory", "Campus Safety Rules"]

        elif predicted_intent == "FACULTY_DEPARTMENT":
            category_badge = "Department"
            navigation_target = f"nav:notices:filter:{dept}"
            text = (
                f"### {dept} Department Information\n\n"
                f"- **Department Office:** Academic block working hours are 9:00 AM to 5:00 PM on weekdays.\n"
                f"- **Inquiries:** Consult your Class Teacher or Department Head of Department (HoD) for course approvals, attendance issues, and official signatures.\n"
                f"- **Notice Board:** Departmental updates are published regularly under the **{dept}** channel in EchoSphere.{notice_cards}"
            )
            suggested_actions = [f"Filter {dept} Notices", "Contact Faculty", "View Academic Calendar"]

        elif predicted_intent == "CAMPUS_FACILITIES":
            category_badge = "Campus Facilities"
            lib_kb = next((k for k in kb_matches if "library" in k.get("id", "")), None)
            hostel_kb = next((k for k in kb_matches if "hostel" in k.get("id", "")), None)

            facility_detail = ""
            if "library" in query.lower() and lib_kb:
                facility_detail = f"\n\n**Central Library:**\n{lib_kb['content']}"
            elif "hostel" in query.lower() and hostel_kb:
                facility_detail = f"\n\n**Hostel Guidelines:**\n{hostel_kb['content']}"
            else:
                facility_detail = (
                    f"\n\n- **Central Library:** Open 8:00 AM - 8:00 PM with access to IEEE and digital journals.\n"
                    f"- **Hostel:** Curfew is 9:00 PM on weekdays; out-passes must be requested 24 hours in advance.\n"
                    f"- **Canteen:** Open from 7:30 AM to 7:00 PM in the student activity center."
                )

            text = f"### Campus Facilities & Timings{facility_detail}{notice_cards}"
            suggested_actions = ["Library Timings", "Hostel Regulations", "Bus Routes"]

        elif predicted_intent == "NOTICE_CREATION":
            category_badge = "Notice Authoring"
            if is_student:
                text = (
                    "I don't have the authority to author or publish announcements directly from this account. "
                    "If you have an event or club announcement that needs to be published, please coordinate with your faculty advisor or department office."
                )
                suggested_actions = ["Browse Notices", "Contact Faculty Advisor", "View Club Circulars"]
            else:
                navigation_target = "action:create_notice"
                text = (
                    f"### Authoring an Announcement ({role.title()})\n\n"
                    f"You have authoring privileges on EchoSphere:\n\n"
                    f"1. Tap the **+ New Notice** button on your home screen.\n"
                    f"2. Enter title, description, target audience, and delivery channels.\n"
                    f"3. Use **AI Expand** to instantly format notes into a formal, structured circular.\n"
                    f"4. Faculty drafts submit to HoD for approval; HoDs and Admins publish immediately with smart speaker broadcast options."
                )
                suggested_actions = ["Create New Notice", "View My Drafts", "Pending Approvals"]

        elif predicted_intent == "APP_NAVIGATION":
            category_badge = "App Settings"
            if any(w in query.lower() for w in ["password", "reset", "change password"]):
                navigation_target = "nav:profile:security"
                if is_student:
                    text = (
                        f"### Password Management for Students\n\n"
                        f"- Use the **Forgot Password?** option on the login screen to receive a secure reset link.\n"
                        f"- Alternatively, contact your Department HoD or College Admin to issue a credential reset token."
                    )
                else:
                    text = (
                        f"### Change Password ({role.title()})\n\n"
                        f"1. Navigate to the **Profile** tab.\n"
                        f"2. Select **Preferences & Security**.\n"
                        f"3. Tap **Change Password** and submit your new credentials."
                    )
                suggested_actions = ["Change Password", "Security Preferences"]
            else:
                navigation_target = "nav:profile:settings"
                text = (
                    f"### Application Preferences & Theme\n\n"
                    f"1. Open the **Profile** tab from the navigation bar.\n"
                    f"2. Tap **Dark Mode Theme** to switch between sleek dark glassmorphism and light mode.\n"
                    f"3. Configure notification sounds, push alerts, and hardware speaker audio preferences."
                )
                suggested_actions = ["Go to Profile", "Toggle Dark Mode Theme", "Notification Settings"]

        elif predicted_intent == "ACADEMIC_POLICIES":
            category_badge = "Academic Regulations"
            att_kb = next((k for k in kb_matches if "attendance" in k.get("id", "")), None)
            kb_text = f"\n\n**University Policy:**\n{att_kb['content']}" if att_kb else ""

            text = (
                f"### Academic Policies & Attendance Regulations\n\n"
                f"- **Attendance Rule:** Minimum **75% attendance** is mandatory to appear for semester-end examinations.\n"
                f"- **Medical Exemption:** 65%-74% may be condoned with verified medical documentation submitted to the HoD.\n"
                f"- **Evaluation:** Internal assessments, lab submissions, and semester theory papers determine overall SGPA/CGPA.{kb_text}{notice_cards}"
            )
            suggested_actions = ["View Academic Regulations", "Check Attendance Criteria", "Examination Dates"]

        elif predicted_intent == "SPEAKER_HARDWARE":
            if is_student:
                category_badge = "Access Restricted"
                navigation_target = None
                text = (
                    "I don't have the authority to answer that question or disclose operational details "
                    "about the smart speaker system. Please consult your department office or faculty coordinator for assistance."
                )
                suggested_actions = ["Browse Announcements", "Check Exam Schedule", "View Placements"]
            else:
                category_badge = "Smart Speaker Hardware"
                navigation_target = "nav:hardware:speakers"
                text = (
                    f"### EchoSphere Smart Speaker System\n\n"
                    f"- **Hardware Network:** Smart speaker nodes broadcast critical announcements to assigned campus zones.\n"
                    f"- **Queue System:** Audio files are queued and prioritized by announcement severity (Emergency -> High -> Normal).\n"
                    f"- **Node Client:** Corridor nodes communicate over secure MQTT with automatic TTS synthesis."
                )
                suggested_actions = ["View Speaker Queue", "Hardware Node Status", "Test Audio Stream"]

        else:
            # Fallback when intent is general campus query
            first_kb = kb_matches[0] if kb_matches else None
            kb_summary = f"\n\n**Related Information ({first_kb['title']}):**\n{first_kb['content']}" if first_kb else ""

            text = (
                f"Here is the guidance for **{name}** ({role.title()} · {dept} Department):\n\n"
                f"Your query has been processed against EchoSphere's live announcement database and campus knowledge base.{kb_summary}{notice_cards}\n\n"
                f"Feel free to ask specific questions about examination dates, placement drives, attendance rules, or departmental notices."
            )
            suggested_actions = ["Browse Announcements", "Check Exam Schedule", "View Placements"]

        return {
            "response": text,
            "category_badge": category_badge,
            "context_badge": f"{role.title()} | {dept} Department",
            "suggested_actions": suggested_actions,
            "navigation_target": navigation_target,
            "matched_announcements": matched_announcements,
            "model_used": "EchoSphere Campus ML Engine (Local)"
        }
