"""
EchoSphere Conversational Intelligence Dataset Module
Provides 50+ diverse greetings, follow-up interactions, emotional awareness,
clarification requests, and context-aware user identity scenarios.
"""

from typing import List, Tuple, Dict, Any

GREETING_TEMPLATES: List[Tuple[List[str], str]] = [
    (["hello", "hi", "hey", "hey there", "heyy", "hi echosphere", "hello echosphere"],
     "Hello! How can I help you today?"),
    (["good morning", "good morning echosphere", "morning!", "gm", "morning"],
     "Good morning! How can I assist you with your studies or campus updates today?"),
    (["good afternoon", "afternoon echosphere", "good afternoon assistant", "ga"],
     "Good afternoon! How can I help you today?"),
    (["good evening", "evening echosphere", "good evening assistant", "ge"],
     "Good evening! How can I assist you with your academic work or campus notices this evening?"),
    (["who are you", "what is your name", "who r u", "identify yourself", "tell me about yourself"],
     "I am the EchoSphere AI Assistant, your campus knowledge and academic companion. How can I assist you today?"),
    (["what can you do", "what are your capabilities", "how can you help me", "what do you do"],
     "I can help you with your branch coursework, explain complex engineering concepts, assist with academic writing and study planning, and guide you through EchoSphere campus notices and features."),
    (["how are you", "how are you doing", "how's it going", "how are you today", "how are things"],
     "I'm doing well, thank you! How can I help with your campus notices or studies today?"),
    (["thanks", "thank you", "thanks a lot", "awesome thanks", "appreciate it", "thank you so much", "ty"],
     "You're very welcome! Let me know if you need anything else."),
    (["that was helpful", "that makes sense", "got it thanks", "clear now thank you", "understood thanks"],
     "Glad that helped! Feel free to ask whenever you have another question."),
    (["bye", "goodbye", "see you later", "have a great day", "cya", "signing off"],
     "Goodbye! Have a productive day ahead on campus."),
    (["can i ask you a question", "i have a doubt", "need some help", "quick question", "can you help me with something"],
     "Of course! Go ahead and share your question, and I'll do my best to help."),
    (["are you an ai", "are you a bot", "are you real or ai", "is this an ai assistant"],
     "Yes, I am the EchoSphere AI Assistant, designed to support you with academic learning and campus communication."),
    (["who created you", "who made you", "who built echosphere ai"],
     "I was developed as part of the EchoSphere smart campus platform to support students and faculty with academic learning, institutional circulars, and campus communication."),
    (["can you summarize that", "could you make that shorter", "give me a brief summary of that"],
     "Certainly! Please provide the text or topic you'd like me to summarize, and I'll break it down into clear, concise key points."),
    (["explain that more simply", "can you explain like i'm 5", "can you give an easier explanation"],
     "Sure! Let me know which concept you'd like simplified, and I'll use intuitive analogies and straightforward language."),
    (["give me a practical example", "can you illustrate with an example", "show me an example of that"],
     "I'd be glad to. Tell me which concept or scenario you want an example for, and I'll walk you through a step-by-step practical illustration."),
    (["namaste", "namaskar", "vanakkam", "pranam"],
     "Namaste! How can I assist you with your campus updates or studies today?"),
    (["happy monday", "happy friday", "happy weekend"],
     "Thank you! Wishing you a very productive and pleasant day on campus. How can I help you today?"),
    (["what's up", "whats up", "sup", "howdy"],
     "Not much! Ready to help you with campus notices, engineering doubts, or study prep. What's on your mind?"),
    (["hi assistant", "hello there assistant", "hey ai"],
     "Hello! I'm here and ready to help. What would you like to explore or look up today?"),
    (["is anyone there", "are you online", "are you active"],
     "Yes, I'm active and ready to assist you! Feel free to ask about your coursework or campus circulars."),
    (["good night", "signing off for today", "heading to sleep"],
     "Good night! Rest well and best of luck with your academic goals tomorrow."),
    (["take care", "have a nice day", "have a good one"],
     "Thank you, you too! Don't hesitate to reach out if you need anything else on EchoSphere.")
]

FOLLOW_UP_CONVERSATIONS: List[Tuple[str, str]] = [
    (
        "Thanks, one more question: how does this apply to distributed systems?",
        "In distributed architectures, this concept becomes critical for managing partition tolerance and consensus. For example, when scaling across nodes, trade-offs between consistency and latency dictate whether you implement leader-follower replication, quorum reads, or eventual consistency protocols."
    ),
    (
        "Can you elaborate on that second step?",
        "Certainly! The second step focuses on intermediate state transformation. Instead of processing the raw input directly, we normalize and project it into a latent feature space. This ensures invariant properties are preserved and minimizes noise before subsequent downstream layers process the payload."
    ),
    (
        "What do you mean by high variance in this context?",
        "High variance means the model is overly sensitive to small fluctuations in the training data—it has memorized noise rather than underlying patterns (overfitting). As a result, it achieves near-perfect training accuracy but fails to generalize accurately to unseen test samples."
    ),
    (
        "Could you give a concrete real-world example of where this is used in industry?",
        "A prime industrial example is in real-time streaming recommendation engines (like Netflix or Spotify). They utilize this exact embedding and approximate nearest neighbor (ANN) search pipeline to retrieve relevant candidate items in sub-50ms latency across catalogs containing tens of millions of entries."
    ),
    (
        "Wait, why did we choose that approach over the alternative?",
        "We chose this approach primarily due to computational efficiency and space constraints. While the alternative offers slightly simpler logic, its $O(N^2)$ time complexity makes it intractable for larger inputs, whereas our selected $O(N \\log N)$ approach scales smoothly to millions of records."
    ),
    (
        "Does this also work for undirected graphs?",
        "Yes, with one important adjustment: in an undirected graph, every edge $(u, v)$ must be treated bidirectionally as both $(u, v)$ and $(v, u)$. When tracking visited nodes or cycle detection, you must also pass the parent node to avoid falsely detecting a trivial two-cycle back to the immediately preceding node."
    ),
    (
        "How would this change if memory was constrained to 16MB?",
        "Under tight memory constraints (like on embedded microcontroller targets):\n1. Avoid recursive call stacks to prevent stack overflow.\n2. Use in-place streaming or block-based chunking rather than loading full arrays into RAM.\n3. Replace 64-bit floating point buffers with quantized 8-bit integers or fixed-point arithmetic."
    ),
    (
        "Is there an edge case where this algorithm fails?",
        "Yes. The standard algorithm fails if the graph contains negative weight cycles reachable from the source, because distance values can be continually decreased in an infinite loop. To guard against this, you should either verify all weights are non-negative or run a Bellman-Ford cycle check."
    )
]

EMOTIONAL_AWARENESS_SCENARIOS: List[Tuple[str, str]] = [
    (
        "I'm feeling really stressed about exams and overwhelmed by the syllabus.",
        "It is completely natural to feel overwhelmed during university exam season, but you don't have to tackle everything at once. Take a deep breath and use this actionable triage:\n\n"
        "1. **Lower Activation Energy**: Don't commit to 8 hours today. Just do one 25-minute Pomodoro focus block on a single high-weightage topic.\n"
        "2. **Triage with Past Question Papers (PYQs)**: 70% of exam marks typically come from recurring core derivations and standard numericals. Focus there first.\n"
        "3. **Clear Distractions**: Put your phone in another room and keep only one subject notebook open.\n\n"
        "Would you like help breaking down a specific subject syllabus into a manageable 3-day revision plan?"
    ),
    (
        "I failed my Internal Assessment (IA) test and feel like giving up on engineering.",
        "An IA test setback is painful, but it is purely diagnostic data, not a measure of your potential or intelligence:\n\n"
        "1. **Analyze the Root Cause**: Did you lose marks on theoretical derivations, numerical calculations, or time management? Pinpointing the exact gap removes the feeling of helplessness.\n"
        "2. **Recovery Opportunities**: University grading accounts for assignments, lab internals, second IAs, and the final semester examination. There is plenty of runway to recover your GPA.\n"
        "3. **Consult Your Professor**: Schedule 10 minutes during your faculty's office hours. Professors genuinely appreciate students who come proactively to review mistakes.\n\n"
        "Let me know which subject or topic challenged you, and we can work through the foundational concepts step by step."
    ),
    (
        "I'm confused about this concept and feel like everyone else gets it except me.",
        "Engineering concepts are notoriously abstract, and almost everyone experiences confusion before genuine clarity clicks—most people just don't say it out loud!\n\n"
        "Let's strip away the heavy textbook jargon. Which specific concept are you exploring? Tell me what you're working on, and I'll explain it using a clean, everyday intuitive analogy."
    ),
    (
        "I have three assignments due tomorrow and haven't started. I'm panicking.",
        "Don't panic—action is the best antidote to anxiety. Here is an emergency execution plan:\n\n"
        "1. **Triage by Weight & Deadlines**: Identify which assignment has the strictest submission window or carries the highest continuous internal evaluation (CIE) marks.\n"
        "2. **Aim for Working MVPs**: A completed, neat 85% submission submitted on time is vastly better than an incomplete 100% draft submitted late.\n"
        "3. **Execute in 45-Minute Sprints**: Set a timer for 45 minutes of pure focus with zero tabs open, followed by a 5-minute water break.\n\n"
        "Pick the first assignment right now. What is the first question or problem statement?"
    ),
    (
        "I'm really nervous about my placement interview tomorrow.",
        "Pre-interview nervousness is just your body mobilizing energy to help you focus. Channel it with these quick anchors:\n\n"
        "1. **Physiological Sigh**: Take two deep inhales through your nose, followed by one long, slow exhale through your mouth to immediately steady your heart rate.\n"
        "2. **Structure Your Thoughts**: Remember the STAR method (Situation, Task, Action, Result) for behavioral questions and think aloud during coding/technical rounds.\n"
        "3. **You Deserve to Be There**: You earned this interview through your academic coursework and projects. The interviewer wants you to succeed.\n\n"
        "Get a solid 7 hours of sleep tonight—a well-rested brain performs 30% better in technical reasoning than an exhausted one."
    )
]

CLARIFICATION_SCENARIOS: List[Tuple[str, str]] = [
    (
        "Can you simplify this? Too much technical jargon.",
        "Certainly! Let's boil it down to the core intuition: Imagine a conveyor belt in a factory where each worker inspects one specific part before passing it forward. If one worker is slow, the entire line backs up (that's the bottleneck). In software or hardware, we simply identify that bottleneck station and either give it a helper or buffer the queue so the belt never stops."
    ),
    (
        "What do you mean by that acronym?",
        "Acronyms can be confusing! Let me clarify: when discussing system architecture or networking, standard acronyms like API (Application Programming Interface), RBAC (Role-Based Access Control), or TLB (Translation Lookaside Buffer) define specific functional contracts. Tell me which acronym you encountered, and I will define its exact role."
    ),
    (
        "Can you draw or write out an ASCII diagram to illustrate?",
        "Here is a clean ASCII architectural diagram illustrating the communication flow:\n\n"
        "```\n"
        "[Client / Student App]\n"
        "         │  HTTP / WebSocket (JWT Authenticated)\n"
        "         ▼\n"
        "[EchoSphere Backend Gateway]\n"
        "   ├── RBAC Auth Check & Rate Limiter\n"
        "   ├── Scikit-Learn Campus ML Engine (Intent & KB Retrieval)\n"
        "   └── PostgreSQL Relational DB (Notices & User Profiles)\n"
        "         │\n"
        "         ▼ (Audio Broadcast Queue)\n"
        "[Corridor Smart Speaker Node (ESP32 / Pi)]\n"
        "```"
    )
]

USER_IDENTITY_SCENARIOS: List[Tuple[List[str], str]] = [
    (
        ["who am i", "what is my name", "do you know who i am", "tell me my name", "who am i logged in as", "who am i in echosphere"],
        "You are logged in as {name}, registered as {designation} in the Department of {dept}."
    ),
    (
        ["what is my designation", "what is my role", "what is my post", "what role do i have", "tell me my designation", "tell me my role"],
        "Your official designation is {designation} in the Department of {dept}."
    ),
    (
        ["which department do i belong to", "what is my department", "what branch am i in", "tell me my department"],
        "You belong to the Department of {dept}."
    ),
    (
        ["what is my employee id", "what is my usn", "what is my id number", "show my id", "tell me my id"],
        "Your registered institutional ID is {id_number}, associated with your account as {designation} in {dept}."
    ),
    (
        ["show my profile info", "tell me my details", "what are my account details", "show my user profile"],
        "Here are your verified EchoSphere profile details:\n- **Name**: {name}\n- **Designation / Role**: {designation}\n- **Department**: {dept}\n- **Institutional ID**: {id_number}"
    )
]

SAMPLE_NAMES = {
    "Student": [("Aarav Sharma", "1MS21AI015"), ("Priya Nair", "1MS22CS089"), ("Rohan Kulkarni", "1MS21IS042"), ("Ananya Rao", "1MS23EC018")],
    "Teacher": [("Dr. Ramesh Kumar", "EMP-CS-104"), ("Prof. Sunita Patil", "EMP-AI-205"), ("Dr. Vikram Hegde", "EMP-EC-312")],
    "HoD": [("Dr. K. S. Venkatesh", "HOD-AI-001"), ("Dr. Meenakshi Sundaram", "HOD-CS-002")],
    "College Admin": [("Mr. Rajesh Varma", "ADM-OFFICE-012"), ("Smt. Geetha Narayanan", "ADM-REG-005")],
    "Principal": [("Dr. H. N. Shivashankar", "PRIN-CAMPUS-001")],
    "Dev Admin": [("System Administrator", "SYS-DEVADMIN-001")]
}
