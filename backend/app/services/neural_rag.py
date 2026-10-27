"""
EchoSphere notice search and chat grounding.

Finds the notices (and built-in app / coursework knowledge) that answer a question:
- Words are normalised first (plurals, "mid-sem" = "mid semester", "time table" = "timetable"), stop words dropped.
- Notices are read from the database on every search, filtered by what the asking role may see,
  so a notice is searchable the moment it is published.
- Ranking is TF-IDF cosine over those words. A notice must share enough of the question's words to count,
  so an unrelated notice is never returned just because it is recent or high priority.
- Dense embeddings (all-MiniLM-L6-v2) are added on top only if sentence-transformers is installed.
"""

import math
import re
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("echosphere.neural_rag")

# Institutional Knowledge Items for Campus Grounding
DEFAULT_CAMPUS_KNOWLEDGE: List[Dict[str, Any]] = [
    {
        "id": "rag_kb_overview",
        "category": "Platform",
        "title": "EchoSphere Institutional Announcement & Corridor Speaker System",
        "content": (
            "EchoSphere is an institutional announcement, circular, and smart speaker audio broadcast platform. "
            "It connects students, teachers, HoDs, and campus administrators by distributing verified departmental notices, "
            "examination timetables, placement alerts, event circulars, and emergency sirens through multi-channel delivery: "
            "In-App Feed, Push Notifications, and Corridor IoT Smart Speaker Nodes."
        ),
        "tags": ["echosphere", "platform", "announcement", "notice", "circular", "overview", "features", "app"]
    },
    {
        "id": "rag_kb_lifecycle",
        "category": "Administration",
        "title": "Notice Authoring, Approval Hierarchy & Priority Levels",
        "content": (
            "Notices on EchoSphere adhere to institutional role-based governance: "
            "1. Students have verified read-only access to view, filter, and bookmark active circulars. "
            "2. Faculty members author announcement drafts that automatically route to their Department HoD for review and sign-off. "
            "3. HoDs, College Admins, Principals, and Developer Admins have direct instant-publish authority. "
            "4. Priority tiers: Normal (standard in-app feed), High (urgent pinned notice), and Emergency (instant college-wide push and siren override across corridor smart speakers)."
        ),
        "tags": ["create notice", "post notice", "approval", "workflow", "teacher", "hod", "priority", "emergency", "siren"]
    },
    {
        "id": "rag_kb_speakers",
        "category": "Hardware",
        "title": "Corridor Smart Speaker Nodes & IoT Audio Broadcasting",
        "content": (
            "The EchoSphere Smart Speaker system consists of IoT hardware nodes deployed across departmental corridors, "
            "seminar halls, auditoriums, and campus plazas. When an announcement is approved with speaker delivery, "
            "high-clarity text-to-speech audio is queued and sent to the speakers over a secure live connection. "
            "Speaker queue management and hardware controls are strictly restricted to faculty and administrative roles."
        ),
        "tags": ["speaker", "audio", "hardware", "broadcast", "node", "queue", "corridor", "pa system"]
    },
    {
        "id": "rag_kb_exam_guidelines",
        "category": "Examinations",
        "title": "University Examination Timetable & Hall Ticket Protocols",
        "content": (
            "Semester examination circulars, Internal Assessment (IA) test timetables, and lab practical schedules "
            "are published under the Examinations category. Dates, venues and exam rules come from those notices."
        ),
        "tags": ["exam", "examinations", "timetable", "ia", "internal assessment", "hall ticket", "schedule", "rules"]
    },
    {
        "id": "rag_kb_placements",
        "category": "Placements",
        "title": "Campus Placement Drives, Corporate Eligibility & CTC Guidelines",
        "content": (
            "The Department of Training & Placement posts visiting recruiters, eligibility criteria, "
            "online assessment links, and interview schedules as notices under the Placements category."
        ),
        "tags": ["placement", "placements", "recruitment", "job", "internship", "cgpa", "interview", "drive", "package"]
    },
    {
        "id": "rag_kb_dsa_shortest_path",
        "category": "Academics",
        "title": "Data Structures & Algorithms: Dijkstra vs. Bellman-Ford Algorithms",
        "content": (
            "Shortest path algorithms in weighted directed graphs: "
            "1. Dijkstra's Algorithm: Greedy approach for graphs with non-negative edge weights. "
            "Maintains a Min-Heap priority queue of tentative distances. Time Complexity: O((V + E) log V); Space: O(V). "
            "Cannot handle negative edge weights. "
            "2. Bellman-Ford Algorithm: Dynamic programming approach that relaxes all |V|-1 edges iteratively. "
            "Can handle negative edge weights and detects negative weight cycles in graphs. Time Complexity: O(V * E); Space: O(V). "
            "3. Trade-off: Dijkstra is asymptotically faster for non-negative graphs; Bellman-Ford is mandatory when edges carry negative weights."
        ),
        "tags": ["dijkstra", "bellman ford", "shortest path", "graph", "algorithms", "dsa", "min heap", "relaxation", "negative cycle"]
    },
    {
        "id": "rag_kb_ml_backprop",
        "category": "Academics",
        "title": "Machine Learning: Backpropagation, Gradient Descent & Optimization",
        "content": (
            "Backpropagation computes the gradient of the loss function with respect to each network weight using the multivariate chain rule: "
            "1. Forward Pass: Compute layer activations a^[l] = sigma(W^[l] a^[l-1] + b^[l]) and output loss L(y_hat, y). "
            "2. Backward Pass: Compute output error delta^[L] = nabla_a L odot sigma'(z^[L]), then backpropagate delta^[l] = ((W^[l+1])^T delta^[l+1]) odot sigma'(z^[l]). "
            "3. Weight Update: Gradient step W^[l] := W^[l] - alpha (delta^[l] (a^[l-1])^T), where alpha is the learning rate."
        ),
        "tags": ["backprop", "backpropagation", "gradient descent", "loss", "neural network", "deep learning", "chain rule", "ml"]
    },
    {
        "id": "rag_kb_os_virtual_memory",
        "category": "Academics",
        "title": "Operating Systems: Virtual Memory Paging, TLB & Page Fault Handling",
        "content": (
            "Virtual memory separates logical address space from physical memory via paging: "
            "1. Logical Address: Divided into Page Number (p) and Page Offset (d). "
            "2. Translation Lookaside Buffer (TLB): High-speed associative hardware cache. On TLB hit, physical frame number is resolved in 1 clock cycle. "
            "3. Page Fault Sequence: If the valid-invalid bit in the page table is 0, a hardware trap occurs. The OS halts the process, locates the page in secondary backing store (swap), loads it into a free physical frame, updates the page table, and restarts the instruction."
        ),
        "tags": ["virtual memory", "paging", "page fault", "tlb", "operating systems", "os", "page table", "demand paging"]
    }
]


_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "do", "does", "did", "will", "shall", "can",
    "could", "would", "should", "may", "might", "must", "has", "have", "had", "i", "me", "my", "we", "our", "you",
    "your", "it", "its", "this", "that", "these", "those", "there", "here", "what", "when", "where", "which", "who",
    "whom", "why", "how", "of", "in", "on", "at", "to", "for", "from", "by", "with", "about", "into", "and", "or",
    "but", "not", "no", "any", "all", "some", "please", "tell", "know", "show", "give", "get", "let", "us", "any",
    "notice", "notices", "circular", "circulars", "announcement", "announcements", "college", "campus", "so", "if",
    "than", "then", "also", "just", "up", "out", "being", "going", "happening", "regarding", "today's", "anything",
}

# Phrases that mean the same thing are rewritten to one form before splitting into words.
_PHRASES = [
    (r"\bmid[\s-]*sem(ester)?s?\b", " midsemester "),
    (r"\bend[\s-]*sem(ester)?s?\b", " endsemester "),
    (r"\btime[\s-]+tables?\b", " timetable "),
    (r"\bhall[\s-]+tickets?\b", " hallticket "),
    (r"\bi\.?a\.?\b", " internal "),
]

# Single words that mean the same thing.
_SYNONYMS = {
    "sem": "semester", "exams": "exam", "examination": "exam", "examinations": "exam", "test": "exam",
    "tests": "exam", "recruitment": "placement", "recruiter": "placement", "recruiters": "placement",
    "hiring": "placement", "drive": "placement", "drives": "placement", "fees": "fee", "lib": "library",
    "dept": "department", "hackathons": "hackathon", "fests": "fest", "lab": "lab", "labs": "lab",
    "timings": "time", "timing": "time", "hrs": "hours", "hour": "hours",
}


def _stem(word: str) -> str:
    if word in _SYNONYMS:
        return _SYNONYMS[word]
    if len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"
    elif len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    return _SYNONYMS.get(word, word)


def normalize_words(text: str) -> List[str]:
    """Lower-case content words of a text, with plurals and common campus synonyms unified."""
    clean = (text or "").lower()
    for pattern, replacement in _PHRASES:
        clean = re.sub(pattern, replacement, clean)
    words = re.findall(r"[a-z0-9]+", clean)
    return [_stem(w) for w in words if w not in _STOPWORDS and len(w) > 1]


def _enum_text(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


class NeuralRAG:
    """Notice search and grounding context for the campus chatbot."""
    _instance: Optional["NeuralRAG"] = None

    # How much of the question a notice must cover to count as an answer.
    MIN_QUERY_COVERAGE = 0.4
    MAX_NOTICES_SCANNED = 500

    def __init__(self):
        self._embedder = None
        self._static_docs: List[Dict[str, Any]] = [
            {**item, "words": normalize_words(f"{item['title']} {item['content']} {' '.join(item.get('tags', []))}")}
            for item in DEFAULT_CAMPUS_KNOWLEDGE
        ]
        self._initialize_model()

    @classmethod
    def get_instance(cls) -> "NeuralRAG":
        if cls._instance is None:
            cls._instance = NeuralRAG()
        return cls._instance

    def _initialize_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            try:
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
            except Exception:
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("NeuralRAG: all-MiniLM-L6-v2 embedding model loaded.")
        except Exception as e:
            logger.info(f"NeuralRAG: sentence-transformers not available ({e}); using word search only.")
            self._embedder = None

    # ------------------------------------------------------------------ ranking

    def _rank(self, query: str, docs: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """Rank docs (each with a "words" list and a "text" string) against the query."""
        q_words = list(dict.fromkeys(normalize_words(query)))
        if not q_words or not docs:
            return []

        n_docs = len(docs)
        doc_freq: Dict[str, int] = {}
        for doc in docs:
            for w in set(doc["words"]):
                doc_freq[w] = doc_freq.get(w, 0) + 1
        idf = {w: math.log((1 + n_docs) / (1 + doc_freq.get(w, 0))) + 1.0 for w in q_words}

        required = max(1, math.ceil(len(q_words) * self.MIN_QUERY_COVERAGE))
        q_norm = math.sqrt(sum(idf[w] ** 2 for w in q_words))

        dense = None
        if self._embedder is not None:
            try:
                q_emb = self._embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
                d_emb = self._embedder.encode([d["text"] for d in docs], convert_to_numpy=True, normalize_embeddings=True)
                dense = np.dot(d_emb, q_emb)
            except Exception as e:
                logger.debug(f"NeuralRAG: dense scoring skipped: {e}")

        ranked = []
        for idx, doc in enumerate(docs):
            counts: Dict[str, int] = {}
            for w in doc["words"]:
                counts[w] = counts.get(w, 0) + 1
            matched = [w for w in q_words if w in counts]
            if len(matched) < required:
                continue
            dot = sum(idf[w] * (1 + math.log(counts[w])) * idf[w] for w in matched)
            d_norm = math.sqrt(sum(((1 + math.log(c)) * idf.get(w, 1.0)) ** 2 for w, c in counts.items()))
            score = dot / (q_norm * d_norm) if d_norm else 0.0
            # Covering more of the question matters more than repeating one word.
            score = 0.5 * score + 0.5 * (len(matched) / len(q_words))
            if dense is not None:
                score = 0.6 * score + 0.4 * float(dense[idx])
            ranked.append((score, idx))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [{**docs[idx], "score": round(score, 3)} for score, idx in ranked[:top_k]]

    # ------------------------------------------------------------------ notices

    @staticmethod
    def visible_notices(db, role: str = "STUDENT", limit: int = MAX_NOTICES_SCANNED) -> List[Any]:
        """Notices the asking role may read: students only published ones, teachers also drafts and pending."""
        from app.core.enums.announcement import AnnouncementStatus
        from app.models.announcement import Announcement

        role_upper = (role or "STUDENT").upper()
        query = db.query(Announcement)
        if role_upper in ("STUDENT", "STUDENTS", "GUEST", "USER"):
            query = query.filter(Announcement.status == AnnouncementStatus.PUBLISHED)
        elif role_upper == "TEACHER":
            query = query.filter(Announcement.status.in_([
                AnnouncementStatus.PUBLISHED, AnnouncementStatus.PENDING_APPROVAL, AnnouncementStatus.DRAFT,
            ]))
        return query.order_by(Announcement.created_at.desc()).limit(limit).all()

    @staticmethod
    def _notice_doc(notice: Any) -> Dict[str, Any]:
        category = getattr(notice, "category", None)
        category_name = getattr(category, "name", None) or "General"
        title = str(getattr(notice, "title", "") or "")
        description = str(getattr(notice, "description", "") or "")
        created = getattr(notice, "created_at", None)
        emergency = _enum_text(getattr(notice, "emergency_level", "")).upper()
        priority = "EMERGENCY" if emergency and emergency != "NORMAL" else _enum_text(getattr(notice, "priority", "")).upper() or "NORMAL"
        return {
            "id": getattr(notice, "id", 0),
            "title": title,
            "content": description,
            "category": str(category_name),
            "priority": priority,
            "department": str(getattr(notice, "target_audience", None) or "Entire College"),
            "created_at": created.strftime("%b %d, %I:%M %p") if created else "Recent",
            # Title words count twice: a notice is usually about what its title says.
            "words": normalize_words(f"{title} {title} {description} {category_name}"),
            "text": f"{title}. {description}",
        }

    def search_notices(self, db, query: str, role: str = "STUDENT", top_k: int = 4) -> List[Dict[str, Any]]:
        """Notices that answer the question, best first. Empty when no notice is about it."""
        if db is None or not (query or "").strip():
            return []
        docs = [self._notice_doc(n) for n in self.visible_notices(db, role)]
        hits = self._rank(query, docs, top_k)
        for hit in hits:
            hit.pop("words", None)
            hit.pop("text", None)
        return hits

    # ------------------------------------------------------------------ built-in knowledge

    def search_knowledge(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        docs = [{**d, "text": f"{d['title']}. {d['content']}"} for d in self._static_docs]
        return [{k: v for k, v in hit.items() if k not in ("words", "text")} for hit in self._rank(query, docs, top_k)]

    def build_grounding_context(
        self,
        query: str,
        db_session=None,
        department: Optional[str] = None,
        top_k: int = 3,
        role: str = "STUDENT",
    ) -> str:
        """Matching notices and built-in knowledge, as plain text for the model prompt."""
        blocks = []
        for m in self.search_notices(db_session, query, role=role, top_k=top_k):
            blocks.append(f"[{m['category']} | Live Campus Notice] {m['title']}:\n{m['content']}")
        for k in self.search_knowledge(query, top_k=2):
            blocks.append(f"[{k['category']} | Institutional Knowledge] {k['title']}:\n{k['content']}")
        return "\n\n".join(blocks)
