"""
EchoSphere Context-Aware Personalization Dataset Module
Provides role-specific response depth and dynamic personalization patterns for:
- Student (Academic tutoring, study methods, exam preparation)
- Teacher (Notice drafting, assignment rubric design, lab viva guidelines)
- Head of Department (Notice approval workflows, faculty workload, department committees)
- College Admin & Principal (Campus-wide broadcasts, emergency sirens, policy governance)
- Developer Administrator (System diagnostics, database health, IoT telemetry)
"""

from typing import List, Tuple, Dict, Any

ROLE_SPECIFIC_SCENARIOS = {
    "Student": [
        (
            "How do I balance my final year project with placement preparation?",
            "Balancing project work with placement preparation requires disciplined weekly block scheduling:\n\n"
            "1. **Morning Algorithm Blocks (7:30 AM - 9:00 AM)**:\n"
            "   - Solve 2 LeetCode / DSA problems daily while your algorithmic reasoning is sharp.\n"
            "2. **Core Academic Classes & Labs (Daytime)**:\n"
            "   - Use lab hours efficiently to write and test your project code with team members so project work doesn't spill into study evenings.\n"
            "3. **Evening System Design & Core CS (7:00 PM - 8:30 PM)**:\n"
            "   - Alternate evenings between DBMS (SQL, indexing), Operating Systems, and Computer Networks revision.\n"
            "4. **Weekend Project Milestones**:\n"
            "   - Dedicate Saturday mornings to end-to-end integration and sprint reviews with your project guide."
        ),
        (
            "What should I do if my lab code doesn't produce the expected output during testing?",
            "Systematic debugging protocol for engineering labs:\n\n"
            "1. **Isolate Inputs**: Test with the simplest trivial input (e.g., $N=1$, empty array, or 1V DC input).\n"
            "2. **Trace State Transitions**: Print variable values or probe test points on your circuit board after every intermediate stage.\n"
            "3. **Check Ground & Connections**: In hardware labs, 80% of unexpected readings stem from floating grounds, loose breadboard jumper wires, or incorrect resistor color codes.\n"
            "4. **Consult the Reference Spec Sheet**: Verify device pinouts (e.g., IC 7408 pin 7 is GND, pin 14 is VCC) against the official manufacturer datasheet."
        )
    ],
    "Teacher": [
        (
            "How do I structure an objective assessment rubric for a machine learning lab assignment?",
            "A balanced 50-mark ML lab assessment rubric:\n\n"
            "1. **Data Preprocessing & EDA (10 Marks)**:\n"
            "   - Handling missing values, scaling, feature correlation analysis.\n"
            "2. **Model Implementation & Architecture (15 Marks)**:\n"
            "   - Correctness of algorithm implementation, appropriate choice of loss function and optimizer.\n"
            "3. **Evaluation Metrics & Validation (10 Marks)**:\n"
            "   - Confusion matrix, precision/recall/F1-score, cross-validation to prevent data leakage.\n"
            "4. **Code Quality & Documentation (5 Marks)**:\n"
            "   - Clean modular functions, inline comments, PEP 8 compliance.\n"
            "5. **Viva Voce & Conceptual Defense (10 Marks)**:\n"
            "   - Ability to explain why specific hyperparameters were chosen and diagnose bias/variance trade-offs."
        ),
        (
            "How do I submit an Internal Assessment notice for departmental review?",
            "To submit an IA circular for review:\n"
            "1. Open **Announcements > Create Notice**.\n"
            "2. Select your department ({dept}) and target semester batches.\n"
            "3. Enter the IA schedule details, venue, and rules.\n"
            "4. Click **Submit for HoD Review** to route it to your department Head for approval.\n\n"
            "[[ACTION:create_announcement_draft:{}]]"
        )
    ],
    "HoD": [
        (
            "What criteria should I review before approving a departmental circular?",
            "As Head of Department, review the following before authorizing publication:\n\n"
            "1. **Target Audience Scope**: Confirm whether the notice applies to specific semester sections or the entire department.\n"
            "2. **Schedule Conflict Verification**: Verify that the proposed event or exam dates do not clash with existing university examination schedules or college symposiums.\n"
            "3. **Audio Broadcast Appropriateness**: Ensure that corridor speaker broadcast is enabled only for urgent or time-sensitive departmental announcements to avoid instructional disruption.\n"
            "4. **Clarity & Contact Information**: Check that venue, reporting time, and faculty coordinator contact details are explicitly stated."
        ),
        (
            "How do I review pending circular drafts submitted by department faculty?",
            "Navigating to the Department Approval Queue.\n\n"
            "- Review pending notices submitted by faculty in the Department of {dept}.\n"
            "- Authorize publication to student feeds and corridor audio nodes, or return drafts with revision remarks.\n\n"
            "[[ACTION:navigate:{\"screen\":\"notices\",\"filter_status\":\"pending_approval\"}]]"
        )
    ],
    "College Admin": [
        (
            "How do I initiate a campus-wide emergency broadcast across all speaker nodes?",
            "Navigating to Emergency Hardware Broadcast.\n\n"
            "- Enter the urgent advisory headline and content.\n"
            "- Set priority to **EMERGENCY** to automatically trigger a siren alert and override background audio across all campus corridor nodes simultaneously.\n\n"
            "[[ACTION:navigate:{\"screen\":\"speaker_queue\",\"mode\":\"emergency_override\"}]]"
        ),
        (
            "Where can I review active hardware speaker node telemetry and connectivity status?",
            "Navigating to Hardware Infrastructure Management.\n\n"
            "- Monitor live heartbeat pings from ESP32/Pi corridor playback clients.\n"
            "- Inspect latency, active volume levels, and audio stream buffer health.\n\n"
            "[[ACTION:navigate:{\"screen\":\"hardware_management\"}]]"
        )
    ],
    "Principal": [
        (
            "How do I publish an executive institutional circular to all students and faculty?",
            "Opening the Executive Broadcast Authoring panel.\n\n"
            "- Author college-wide circulars with direct instantaneous publication authority (no intermediary review required).\n"
            "- Enable multi-channel delivery: In-App Feed, Push Notifications, and Corridor IoT Smart Speakers.\n\n"
            "[[ACTION:create_announcement_draft:{\"scope\":\"college_wide\",\"priority\":\"HIGH\"}]]"
        ),
        (
            "What governance controls exist in EchoSphere to ensure authentic institutional communication?",
            "EchoSphere enforces multi-layered institutional communication governance:\n\n"
            "1. **Cryptographic Role-Based Access Control (RBAC)**: All user actions are verified against database credentials and signed JWT tokens.\n"
            "2. **Mandatory HoD Review Gate**: Faculty notices cannot reach student feeds without explicit department Head authorization.\n"
            "3. **Executive Override**: Only the Principal and College Admin hold college-wide immediate broadcast rights.\n"
            "4. **Audit Trail**: Every draft submission, modification, and approval timestamp is recorded in immutable PostgreSQL audit logs."
        )
    ],
    "Dev Admin": [
        (
            "How do I inspect the status of the local ML model router and API service health?",
            "Displaying EchoSphere System Health & Model Telemetry:\n\n"
            "- **Campus ML Engine**: Local Scikit-Learn intent classifier & TF-IDF institutional knowledge base active.\n"
            "- **Model Router**: FineTunedGemmaProvider probing `/health` with automatic non-blocking fallback.\n"
            "- **Database Connection Pool**: PostgreSQL active with verified connection pooling.\n"
            "- **Hardware Dispatch Service**: WebSocket broker listening for speaker node heartbeat pings.\n\n"
            "[[ACTION:navigate:{\"screen\":\"system_diagnostics\"}]]"
        )
    ]
}
