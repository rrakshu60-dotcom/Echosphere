"""
EchoSphere Multi-Turn Dialogue Dataset Module
Contains 30+ comprehensive multi-turn dialogues including:
- 2-turn, 3-turn, and 4-turn progressive interactions
- Mid-conversation topic shifts (e.g. from coursework to circulars, from study tips to drafting)
- Contextual back-and-forth problem solving
"""

from typing import List, Tuple

MULTI_TURN_CONVERSATIONS: List[List[Tuple[str, str]]] = [
    # 1. 3-Turn: Exam Anxiety -> Daily Schedule -> Subject Triage
    [
        ("I'm feeling really stressed about upcoming semester exams and can't seem to focus.",
         "It's completely normal to feel overwhelmed during exam season, but you can regain control by taking small, structured steps:\n\n"
         "1. **Lower Activation Energy**: Don't try to study for 8 hours today. Commit to just one 25-minute Pomodoro block on a single high-yield topic.\n"
         "2. **Triage the Syllabus**: Focus first on high-weightage topics that appear consistently in previous years' question papers.\n"
         "3. **Clear Your Space**: Keep your study desk clean and put your phone in another room to eliminate cognitive distraction.\n\n"
         "Would you like help breaking down a specific subject syllabus into a manageable daily revision schedule?"),
        ("Yes, how should I organize a revision plan for 5 engineering subjects across 10 days?",
         "Here is an efficient 10-day multi-subject revision strategy:\n\n"
         "- **Dual-Subject Interleaving (Days 1–5)**:\n"
         "  - Study two subjects per day (one analytical/mathematical in the morning, one theory/conceptual in the afternoon).\n"
         "  - Day 1: Subject A (Morning) + Subject B (Afternoon)\n"
         "  - Day 2: Subject C + Subject D\n"
         "  - Day 3: Subject E + Subject A\n"
         "  - Rotate to keep concepts fresh and avoid mental fatigue.\n\n"
         "- **Past Paper Practice (Days 6–8)**:\n"
         "  - Solve 2 complete previous years' question papers per subject under timed conditions.\n\n"
         "- **Formula Sheets & Knowledge Gaps (Days 9–10)**:\n"
         "  - Review your consolidated formula sheets, circuit diagrams, and definitions. Prioritize sleep before exam day."),
        ("What if one subject is way harder for me than the others?",
         "If one subject is significantly harder, allocate your peak cognitive hours to it:\n\n"
         "1. **Eat the Frog First**: Study the hardest subject first thing in the morning when your working memory and glucose levels are freshest.\n"
         "2. **The 60/40 Split**: Devote 60% of your daily study time to the challenging subject and 40% to maintaining progress on the easier ones.\n"
         "3. **Deconstruct by PYQ Weightage**: You don't need to master 100% of the textbook to score well. Target the 3 core units that guarantee 60-70% of the marks.")
    ],

    # 2. 3-Turn: CNNs -> Pooling Removal -> Strided Convolutions
    [
        ("Can you explain how Convolutional Neural Networks process images?",
         "Convolutional Neural Networks (CNNs) process visual data through specialized hierarchical layers:\n\n"
         "1. **Convolutional Layers**: Learnable filters (e.g., 3x3 kernels) slide across input feature maps computing dot products, capturing local spatial correlations like edges, textures, and motifs.\n"
         "2. **Activation (ReLU)**: Introduces non-linearity f(x) = max(0, x), allowing the network to model complex patterns.\n"
         "3. **Pooling Layers (Max Pooling)**: Downsamples spatial dimensions to reduce computation and establish translation invariance.\n"
         "4. **Fully Connected Layers**: Flattens high-level spatial representations into class probability vectors."),
        ("What happens if we remove the pooling layers?",
         "Removing pooling layers retains full spatial resolution throughout the network:\n\n"
         "- **Trade-offs**:\n"
         "  1. *Computational Overhead*: Parameter count in subsequent dense layers increases significantly, elevating GPU memory and training time.\n"
         "  2. *Receptive Field*: Without pooling, the network requires deeper architectures or dilated convolutions to capture large-scale global context.\n"
         "  3. *Modern Practice*: Fully Convolutional Networks (FCNs) often replace pooling with strided convolutions (stride=2), enabling the network to learn downsampling dynamically."),
        ("How does a strided convolution learn downsampling better than fixed pooling?",
         "Fixed pooling (like Max Pooling or Average Pooling) uses a rigid, non-trainable mathematical rule (taking the maximum or mean). In contrast, a convolution with stride $s=2$ contains learnable kernel weights $W$. During backpropagation, the network adjusts these weights to optimize which frequency components and feature details to preserve and which to discard, leading to superior task-specific representation learning.")
    ],

    # 3. 3-Turn: TCP vs UDP -> Video Streaming -> QUIC / HTTP/3
    [
        ("What is the difference between TCP and UDP?",
         "TCP (Transmission Control Protocol) and UDP (User Datagram Protocol) represent fundamental transport layer trade-offs between reliability and latency:\n\n"
         "- **TCP (Connection-Oriented & Reliable)**:\n"
         "  - Establishes a 3-way handshake (SYN, SYN-ACK, ACK) before data transfer.\n"
         "  - Guarantees in-order packet delivery, error-checking, and flow/congestion control.\n"
         "  - Used for HTTP/HTTPS, file transfer (FTP), and database connections.\n\n"
         "- **UDP (Connectionless & Low Latency)**:\n"
         "  - Transmits datagrams without handshakes or delivery acknowledgments.\n"
         "  - Zero retransmission overhead, minimizing latency.\n"
         "  - Used for live video streaming, VoIP, DNS queries, and online multiplayer gaming."),
        ("Why does real-time video streaming prefer UDP over TCP?",
         "In real-time streaming, timeliness is prioritized over perfection. If a video packet is delayed or dropped, retransmitting it via TCP would introduce buffering stalls and latency, rendering the late frame useless. UDP delivers live packets immediately, tolerating minor packet drops for smooth, uninterrupted playback."),
        ("How does HTTP/3 combine the benefits of both using QUIC?",
         "HTTP/3 replaces TCP with **QUIC**, which runs over UDP in user space:\n\n"
         "1. **Zero Head-of-Line Blocking**: In TCP, if packet 1 is lost, packets 2 and 3 must wait. QUIC multiplexes independent streams over UDP—loss in one stream doesn't stall others.\n"
         "2. **0-RTT Connection Establishment**: QUIC bundles the transport handshake and TLS 1.3 cryptographic negotiation into a single round-trip (or zero round-trips on repeat visits).\n"
         "3. **Connection Migration**: QUIC identifies connections using a 64-bit Connection ID rather than IP/Port, so mobile clients can seamlessly switch from Wi-Fi to cellular data without dropping active connections.")
    ],

    # 4. 3-Turn: Notice Approval Workflow -> Authority -> Audio Broadcast
    [
        ("How does the notice approval workflow work in EchoSphere?",
         "The EchoSphere notice approval workflow ensures administrative integrity across campus:\n\n"
         "1. **Drafting**: Faculty author a notice specifying audience, department, priority, and broadcast channels.\n"
         "2. **HoD Review**: The draft routes to the Department HoD's dashboard for verification and approval.\n"
         "3. **Publishing**: Upon approval, the circular is published to student feeds and queued for corridor audio broadcast if enabled."),
        ("Can a Principal or College Admin publish without HoD approval?",
         "Yes. The Principal and College Admin roles hold executive broadcasting authority and can publish verified college-wide notices immediately with emergency siren override capabilities."),
        ("How does the system prevent corridor speakers from echoing or overlapping audio?",
         "EchoSphere uses an asynchronous priority playback queue on the hardware dispatch broker. Announcements are sequenced by timestamp and priority tier. Higher-priority notices (like emergency drills) immediately pause routine announcements, resume them once complete, and broadcast synchronized audio packets across nodes.")
    ],

    # 5. 4-Turn: Project Guidance -> Drafting -> Viva Preparation -> Presentation Slides
    [
        ("I need to write an email to a professor asking for project guidance. What should I include?",
         "A respectful and effective project guidance email should include:\n\n"
         "1. **Specific Interest**: Mention their research papers or domain expertise so they know you did your homework.\n"
         "2. **Your Background**: State your branch, semester, CGPA, and key technical skills.\n"
         "3. **Proposed Topic**: A 2-sentence summary of the problem area you want to investigate.\n"
         "4. **Low-Friction Request**: Ask for a brief 10-minute meeting at their convenience."),
        ("Can you draft that email for me?",
         "Subject: Request for Project Mentorship - [Your Name] (Department of {dept})\n\n"
         "Dear Professor [Professor's Last Name],\n\n"
         "I hope you are having a productive week.\n\n"
         "I am a [Semester] semester student in the Department of {dept}. I have been following your research in [Professor's Research Area] with great interest, particularly your work on [Specific Topic/Paper].\n\n"
         "Our project team is planning our upcoming academic project on [Proposed Topic] and would be honored to pursue this work under your mentorship. We have built foundational experience in [Relevant Skills/Tools, e.g., PyTorch / Embedded C].\n\n"
         "Could we schedule a brief 10-minute meeting at your office during your visiting hours this week to discuss our initial project outline?\n\n"
         "Thank you very much for your time and guidance.\n\n"
         "Sincerely,\n"
         "[Your Name]\n"
         "Roll No / USN: [Your ID]\n"
         "Contact: [Your Phone Number]"),
        ("Thanks! Once the project is done, how should we prepare for the final external viva?",
         "External viva examiners evaluate conceptual depth, practical implementation, and individual contributions:\n\n"
         "1. **Know Your System Architecture**: Be prepared to redraw your block diagram, database schema, and circuit schematics from memory on a whiteboard.\n"
         "2. **Clarify Individual Contribution**: Be ready to state exactly which modules you personally designed, implemented, and debugged.\n"
         "3. **Understand Edge Cases & Trade-offs**: Examiners always ask: 'Why didn't you use technology X instead?' and 'What happens if input Y is null?'.\n"
         "4. **Have a Live, Working Demo**: Pre-record a backup video of your demo in case of live network or hardware hiccups."),
        ("What is the ideal slide count and structure for the 15-minute viva presentation?",
         "For a 15-minute presentation, aim for **10 to 12 slides**:\n\n"
         "- Slide 1: Title, Team Members, Guide Name, Department\n"
         "- Slide 2: Problem Statement & Motivation (1 min)\n"
         "- Slide 3: Literature Survey & Research Gaps (1.5 mins)\n"
         "- Slide 4–5: Proposed Architecture / System Block Diagram (3 mins)\n"
         "- Slide 6–7: Implementation & Technical Challenges Solved (3 mins)\n"
         "- Slide 8–9: Results, Performance Graphs & Metrics (3 mins)\n"
         "- Slide 10: Conclusion, Limitations & Future Work (1.5 mins)\n"
         "- Slide 11: Key References (IEEE format)\n"
         "- Slide 12: Thank You & Q&A (2 mins buffer)")
    ],

    # 6. 3-Turn: Topic Shift from Academic DSA to Campus Notice Filtering
    [
        ("How does a Binary Search Tree maintain its ordering?",
         "A Binary Search Tree (BST) enforces the binary search invariant for every node $X$:\n\n"
         "- All keys in the **left subtree** of $X$ are strictly less than $X$'s key ($key(left) < key(X)$).\n"
         "- All keys in the **right subtree** of $X$ are strictly greater than $X$'s key ($key(right) > key(X)$).\n\n"
         "Performing an **In-Order Traversal** (Left -> Root -> Right) visits nodes in strictly sorted ascending order. In a balanced BST (like an AVL or Red-Black tree), search, insertion, and deletion execute in $O(\\log N)$ time."),
        ("Thanks! Switching gears, where can I see the latest exam notices on EchoSphere?",
         "Navigating you to active Examination circulars.\n\n"
         "Review upcoming theory schedules, lab viva batches, and hall ticket distribution updates.\n\n"
         "[[ACTION:navigate:{\"screen\":\"notices\",\"filter_category\":\"Examinations\"}]]"),
        ("Can I also toggle to dark mode from here?",
         "Updating your appearance preferences to Dark Mode.\n\n"
         "Enjoy EchoSphere's sleek dark glassmorphic design optimized for low-light campus use.\n\n"
         "[[ACTION:toggle_theme:{\"mode\":\"dark\"}]]")
    ],

    # 7. 3-Turn: Database Indexing -> Query Optimization -> Explain Analyze
    [
        ("Why is my SQL query running slow on a table with 500,000 student records?",
         "A query on 500,000 records typically slows down due to:\n\n"
         "1. **Full Table Scans (Seq Scan)**: The database is reading all 500,000 rows from disk because no index exists on your `WHERE` filtering columns.\n"
         "2. **Function Calls on Indexed Columns**: Writing `WHERE LOWER(email) = '...'` prevents the engine from using standard indexes on `email` unless a functional index exists.\n"
         "3. **Missing Composite Index**: If filtering on `department_id` and `semester`, a composite index `(department_id, semester)` is needed."),
        ("How do I inspect what the database query planner is doing under the hood?",
         "Use the `EXPLAIN ANALYZE` command before your query:\n\n"
         "```sql\n"
         "EXPLAIN ANALYZE\n"
         "SELECT * FROM students \n"
         "WHERE department = 'CSE' AND semester = 6;\n"
         "```\n\n"
         "This outputs the query execution plan showing:\n"
         "- **Node Type**: Sequential Scan vs Index Scan vs Bitmap Heap Scan.\n"
         "- **Cost**: Estimated startup cost and total execution cost units.\n"
         "- **Actual Time & Rows**: The actual milliseconds spent and exact rows returned per step."),
        ("If I see 'Bitmap Heap Scan', is that good or bad?",
         "'Bitmap Heap Scan' is generally a good, efficient plan! It means the engine first built a memory bitmap of matching physical page addresses using the index (**Bitmap Index Scan**), sorted the addresses to minimize random disk head seeks, and then visited only those specific memory pages (**Bitmap Heap Scan**). It is much faster than a sequential full table scan.")
    ]
]
