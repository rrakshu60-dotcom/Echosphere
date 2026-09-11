# pyright: reportCallIssue=false, reportArgumentType=false, reportAttributeAccessIssue=false, reportAssignmentType=false
"""
Enriches all notices in the database and frontend with concrete dates, times, venues,
realistic deadlines, attachments, and pre-synthesized audio streams so every notice
is fully functioning across:
1. In-App Feed & Push Notifications
2. AI Summarization (/summary endpoint)
3. Offline Audio Playback (/audio & /audio/stream endpoints)
4. Calendar Event & Deadline Extraction (/calendar-event endpoint -> Google / Device Calendar Sync)
5. Search, Filter, Sort, and Category Selectors
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.models.announcement import Announcement
from app.models.announcement_category import AnnouncementCategory
from app.models.announcement_delivery import AnnouncementDelivery
from app.models.delivery_type import DeliveryType
from app.models.notification import Notification
from app.models.user import User
from app.core.enums.announcement import (
    AnnouncementPriority,
    AnnouncementStatus,
    EmergencyLevel,
)
from app.services.tts_service import generate_announcement_audio_sync

RICH_NOTICES: List[Dict[str, Any]] = [
    # -------------------------------------------------------------
    # 1. ACADEMIC
    # -------------------------------------------------------------
    {
        "category": "Academic",
        "notices": [
            {
                "title": "Mid-Term Academic Progress Review & Proctor Mentorship Sessions",
                "description": "All B.E. and M.Tech students are required to attend the mandatory mid-term academic counseling sessions scheduled from October 20, 2026 to October 24, 2026 between 10:00 AM and 4:30 PM in their respective Department Faculty Cabins. Faculty proctors will review IA-1 answer scripts, syllabus completion, and attendance registers. Students with attendance below 85% must report along with their local guardians.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Mandatory academic counseling and proctor review from October 20-24, 2026 between 10:00 AM and 4:30 PM in Faculty Cabins; IA-1 and attendance review required.",
            },
            {
                "title": "Final Professional & Open Elective Subject Selection Deadline",
                "description": "The online academic ERP portal is officially active for submitting elective preferences for the upcoming semester. Students from 5th and 7th semesters must submit choices through the student portal before October 25, 2026 at 5:00 PM. Elective seats in AI Architecture and Cloud Computing are allocated strictly on a first-come, first-served basis.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Online ERP portal open for 5th & 7th semester elective course selection until October 25, 2026 at 5:00 PM.",
            },
            {
                "title": "National Board of Accreditation (NBA) Student Feedback Survey",
                "description": "In compliance with NBA accreditation parameters, the Academic Quality Cell invites all students to participate in the annual Course Outcome (CO) and Program Outcome (PO) survey. Please access the survey link sent to your registered college email and complete the feedback by October 28, 2026 at 6:00 PM.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "NBA curriculum outcome feedback survey active for all students via registered email until October 28, 2026 at 6:00 PM.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 2. EXAMINATION
    # -------------------------------------------------------------
    {
        "category": "Examination",
        "notices": [
            {
                "title": "Final Schedule for Semester End Theory Examinations - Odd Semester 2026",
                "description": "The Controller of Examinations has published the definitive timetable for the upcoming Semester End Theory Examinations commencing November 15, 2026 at 9:30 AM in Examination Block 3. Morning sessions run from 9:30 AM to 12:30 PM and afternoon sessions from 2:00 PM to 5:00 PM. Download your verified digital hall tickets from the student portal.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Final timetable for Semester End Examinations starting November 15, 2026 at 9:30 AM in Exam Block 3; download digital hall tickets online.",
            },
            {
                "title": "Physical Hall Ticket Distribution & Malpractice Prevention Rules",
                "description": "Eligible candidates appearing for semester university examinations must collect their physical signed Hall Tickets from their department offices between October 27, 2026 and October 31, 2026 at 4:00 PM after clearing all library and lab dues. Smartwatches, mobile phones, and programmable devices are strictly banned in examination halls.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Collect signed hall tickets from department offices by October 31, 2026 at 4:00 PM; smartwatches and electronic devices strictly banned.",
            },
            {
                "title": "Supplementary Examination & Re-evaluation Applications Window",
                "description": "Applications are formally invited for answer script photocopy evaluation and re-valuation for previous semester courses. The online fee payment gateway remains open until November 5, 2026 at 11:59 PM. Late applications will not be processed under any circumstances.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Re-evaluation and photocopy application window open until November 5, 2026 at 11:59 PM via online exam portal.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 3. PLACEMENT
    # -------------------------------------------------------------
    {
        "category": "Placement",
        "notices": [
            {
                "title": "Tier-1 Recruitment Drive: Microsoft Cloud & AI Engineering",
                "description": "The Department of Training and Placement announces on-campus recruitment by Microsoft for Cloud Solutions Architect and AI Development roles. Eligible streams: CSE, AIML, ISE, and ECE with CGPA 8.0 and above. The mandatory online technical assessment will be held on October 24, 2026 at 10:00 AM in the Advanced Computing Lab.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Microsoft recruitment drive for Cloud & AI roles; mandatory technical assessment on October 24, 2026 at 10:00 AM in Advanced Computing Lab.",
            },
            {
                "title": "Corporate Mock Interview & ATS Resume Critique Workshop",
                "description": "Senior technical recruiters from top MNCs will conduct 1-on-1 mock interviews and technical portfolio reviews for 6th and 7th semester students on October 22, 2026 at 9:00 AM in the Placement Cell. Students must bring two printed copies of their updated resume in standard format and report in business formal attire.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "1-on-1 technical mock interviews by MNC recruiters on October 22, 2026 at 9:00 AM in Placement Cell; carry 2 resume copies in formal attire.",
            },
            {
                "title": "Summer Technology Internship Drive at Goldman Sachs & Morgan Stanley",
                "description": "Registrations are open for the 8-week Summer Technology Analyst Internship program offering a monthly stipend of ₹75,000 with Pre-Placement Interview (PPI) opportunities. Eligible candidates must apply through the Superset portal before October 26, 2026 at 11:59 PM.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Goldman Sachs and Morgan Stanley summer internship applications open on Superset until October 26, 2026 at 11:59 PM with ₹75,000 monthly stipend.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 4. EVENTS
    # -------------------------------------------------------------
    {
        "category": "Events",
        "notices": [
            {
                "title": "HackEcho 2026: 24-Hour National Collegiate Hackathon",
                "description": "Registrations are live for HackEcho 2026, our flagship national 24-hour hackathon happening on November 7, 2026 at 9:00 AM in the Main Campus Auditorium. Total cash prize pool of ₹2,50,000 across AI/ML, Cyber Defense, and IoT tracks. Free food, mentoring, high-speed WiFi, and overnight accommodation provided for registered teams.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "HackEcho 2026 national 24-hour hackathon begins November 7, 2026 at 9:00 AM in Main Auditorium with ₹2.5 Lakhs prize pool.",
            },
            {
                "title": "Annual College Day Celebrations & Alumni Homecoming 'Samanvay 2026'",
                "description": "The Annual Institution Day and Alumni Meet 'Samanvay 2026' will take place on November 21, 2026 at 4:30 PM in the College Quadrangle. The grand evening will feature academic excellence awards, alumni keynotes, and musical performances. All students, faculty, and alumni are cordially invited.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Annual College Day and Alumni Homecoming 'Samanvay 2026' scheduled for November 21, 2026 at 4:30 PM in College Quadrangle.",
            },
            {
                "title": "Campus Founder Pitchfest: Angel Investors & Startup Seed Grants",
                "description": "The Centre for Innovation and Entrepreneurship (CIE) hosts the annual Campus Founder Pitchfest on October 29, 2026 at 11:00 AM in Seminar Hall 1. Student startup founders can pitch to venture capitalists for seed grants up to ₹5,00,000. Submit your pitch deck before October 26, 2026.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "CIE Campus Founder Pitchfest on October 29, 2026 at 11:00 AM in Seminar Hall 1; startup seed funding grants up to ₹5,00,000.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 5. WORKSHOP
    # -------------------------------------------------------------
    {
        "category": "Workshop",
        "notices": [
            {
                "title": "Hands-On Workshop: Fine-Tuning Open-Source LLMs with LoRA & Unsloth",
                "description": "The Department of AIML conducts an intensive 2-day hands-on workshop on fine-tuning Qwen 2.5 and LLaMA 3.1 models on local workstation GPUs. The workshop will be held on October 30, 2026 at 9:30 AM in the High Performance Computing Lab. Hands-on coding kits and cloud GPU compute credits provided to all attendees.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "2-day LLM fine-tuning workshop using LoRA and Unsloth starting October 30, 2026 at 9:30 AM in HPC Lab with GPU credits provided.",
            },
            {
                "title": "Practical Embedded Systems & ESP32 IoT Prototyping Workshop",
                "description": "Learn circuit design, sensor integration, FreeRTOS multi-threading, and MQTT cloud telemetry using ESP32 microcontrollers. The hands-on bootcamp takes place on October 31, 2026 at 10:00 AM in Electronics Lab 2. Hardware components and sensor kits provided to registered participant pairs.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Hands-on ESP32 IoT and FreeRTOS embedded systems workshop on October 31, 2026 at 10:00 AM in Electronics Lab 2 with kits provided.",
            },
            {
                "title": "Full-Stack Development with Flutter 3 & FastAPI Masterclass",
                "description": "An intensive weekend masterclass covering reactive cross-platform mobile UI with Flutter, asynchronous REST APIs with FastAPI, WebSocket real-time streams, and SQLite persistence. Scheduled for November 1, 2026 at 9:00 AM in Seminar Hall 2. Ideal for capstone project teams.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Full-stack Flutter 3 and FastAPI masterclass on November 1, 2026 at 9:00 AM in Seminar Hall 2 covering WebSockets and API architectures.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 6. SEMINAR
    # -------------------------------------------------------------
    {
        "category": "Seminar",
        "notices": [
            {
                "title": "Distinguished Lecture on Quantum Computing by IBM Quantum Fellow",
                "description": "The Department of Computer Science welcomes Dr. Richard Thorne, Principal Scientist at IBM Quantum Labs, for a keynote on 'Fault-Tolerant Quantum Algorithms and Practical Qubit Scaling' on October 23, 2026 at 11:00 AM in Sir M. Visvesvaraya Auditorium. Attendance is open to all engineering disciplines.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "IBM Quantum Fellow Dr. Richard Thorne delivering keynote on Fault-Tolerant Quantum Algorithms on October 23, 2026 at 11:00 AM in Visvesvaraya Auditorium.",
            },
            {
                "title": "Technical Seminar on Automotive Cybersecurity in Autonomous Vehicles",
                "description": "Cybersecurity architects from Bosch Automotive Technologies will present real-world attack vectors, CAN-bus security vulnerabilities, and ISO 21434 automotive standards on October 27, 2026 at 2:00 PM in Seminar Hall 1. Pre-registration is mandatory via the departmental portal.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Bosch automotive cybersecurity seminar exploring CAN-bus exploits and countermeasures on October 27, 2026 at 2:00 PM in Seminar Hall 1.",
            },
            {
                "title": "Higher Studies Abroad Seminar: GRE, TOEFL & Ivy League Admissions",
                "description": "International educational advisors from EducationUSA will conduct an interactive guidance session on university shortlisting, statement of purpose (SOP) drafting, research assistantships, and visa protocols on October 28, 2026 at 3:00 PM in the Central Library Conference Hall.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "EducationUSA guidance seminar on GRE prep, Ivy League applications, and international scholarships on October 28, 2026 at 3:00 PM in Library Conference Hall.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 7. HOLIDAY
    # -------------------------------------------------------------
    {
        "category": "Holiday",
        "notices": [
            {
                "title": "Institutional Holiday Notification on Account of Maha Shivaratri",
                "description": "As declared in the official state gazette, the college will observe a holiday on October 23, 2026 on account of Maha Shivaratri. Regular academic classes, practical laboratories, and administrative offices will resume on October 26, 2026 at 8:30 AM.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Campus closed on October 23, 2026 for Maha Shivaratri holiday; classes and offices resume on October 26, 2026 at 8:30 AM.",
            },
            {
                "title": "Mid-Term Semester Vacation Schedule & Hostel Mess Timings",
                "description": "The institution will observe a mid-semester recess from November 2, 2026 to November 6, 2026. Student hostels will remain fully operational with revised mess timings: Breakfast 8:00 AM, Lunch 1:00 PM, and Dinner 8:00 PM. Research computing labs remain accessible with ID validation.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Mid-semester vacation scheduled from November 2-6, 2026; student hostels remain open with revised dining hours.",
            },
            {
                "title": "Republic Day National Celebration & Ceremonial Flag Hoisting",
                "description": "The 77th Republic Day celebration will be held on campus on January 26, 2027 at 8:30 AM in the College Quadrangle. The event includes ceremonial flag hoisting by the Principal, NCC cadet march-past, and patriotic musical performances. All staff and students should assemble by 8:15 AM.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Republic Day ceremonial flag hoisting and NCC parade on January 26, 2027 at 8:30 AM in College Quadrangle; assembly at 8:15 AM.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 8. SPORTS
    # -------------------------------------------------------------
    {
        "category": "Sports",
        "notices": [
            {
                "title": "Inter-Branch Football & Volleyball Tournament Match Fixtures",
                "description": "The Department of Physical Education has scheduled the annual Inter-Branch Sports Tournament matches starting October 22, 2026 at 6:30 AM on Sports Ground 1. Football league matches will be played in morning slots and Volleyball matches at 4:30 PM on Court 2. Teams must wear official department jerseys.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Inter-Branch Football and Volleyball tournaments begin October 22, 2026 at 6:30 AM on Sports Ground 1; match fixtures published.",
            },
            {
                "title": "Varsity Badminton & Table Tennis Selection Trials for State Meet",
                "description": "Open selection trials for the college varsity Badminton and Table Tennis teams will take place on October 24, 2026 at 4:00 PM in the Indoor Sports Complex. Shortlisted players will represent the institution at the upcoming VTU State Championship. Non-marking shoes are mandatory.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Varsity Badminton and Table Tennis selection trials on October 24, 2026 at 4:00 PM in Indoor Sports Complex; non-marking shoes required.",
            },
            {
                "title": "Refurbished Student Gymnasium Inauguration & Revised Operating Hours",
                "description": "The campus fitness gymnasium has been equipped with new cardiovascular treadmills and Olympic strength stations. Operating hours: Morning slot from 6:00 AM to 8:30 AM and Evening slot from 4:30 PM to 8:00 PM. Certified fitness trainers will be available for orientation starting October 20, 2026.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Upgraded gymnasium open from October 20, 2026 with slots 6:00-8:30 AM and 4:30-8:00 PM; certified trainers available.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 9. CULTURAL
    # -------------------------------------------------------------
    {
        "category": "Cultural",
        "notices": [
            {
                "title": "Aura 2026: Battle of the Bands & Acoustic Vocal Auditions",
                "description": "The Cultural Committee invites vocalists, guitarists, drummers, and musical bands for live auditions for the Battle of the Bands stage at Aura 2026. Auditions will be judged by studio producers on October 25, 2026 at 3:00 PM in the Open Air Amphitheatre.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Battle of the Bands and vocal auditions for Aura 2026 cultural fest on October 25, 2026 at 3:00 PM in Open Air Amphitheatre.",
            },
            {
                "title": "Classical & Contemporary Dance Troupe Selection Trials",
                "description": "Auditions for the university-level classical solo, semi-classical group, and hip-hop dance troupes will be conducted on October 26, 2026 at 4:00 PM in the Cultural Activity Room. Selected dancers will receive formal sponsorship for interstate cultural competitions.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Dance troupe selection trials for Classical and Western formats on October 26, 2026 at 4:00 PM in Cultural Activity Room.",
            },
            {
                "title": "Intra-College Literary Fest: Parliamentary Debate & Elocution",
                "description": "The Literary Society announces the Annual Debate Championship on October 27, 2026 at 2:30 PM in Seminar Hall 2. Contests include British Parliamentary Debate, Slam Poetry, and Flash Fiction with cash prizes and medals for winners.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Annual Parliamentary Debate and Literary Championship on October 27, 2026 at 2:30 PM in Seminar Hall 2 with cash awards.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 10. CLUB ACTIVITIES
    # -------------------------------------------------------------
    {
        "category": "Club Activities",
        "notices": [
            {
                "title": "Robotics Club (RoboTech): Autonomous Rover Challenge Orientation",
                "description": "The RoboTech robotics club launches its Autonomous Rover Challenge with an orientation on October 21, 2026 at 4:30 PM in Innovation Lab 1. Participants will receive LiDAR sensor kits, ROS2 codebases, and guidance on computer vision navigation.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "RoboTech Autonomous Rover orientation on October 21, 2026 at 4:30 PM in Innovation Lab 1; sensor kits and ROS2 codebases provided.",
            },
            {
                "title": "Google Developer Student Club (GDSC) Core Team Recruitment Drive",
                "description": "GDSC is recruiting student leads in AI/ML, Flutter Mobile, Cloud Engineering, and Event Design. Submit your technical GitHub profiles and portfolio assignments via the GDSC campus portal before October 25, 2026 at 11:59 PM.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "GDSC technical and leadership core team recruitment open until October 25, 2026 at 11:59 PM; submit GitHub portfolios online.",
            },
            {
                "title": "Mega Blood Donation & Community Health Checkup Camp",
                "description": "Youth Red Cross, Rotaract, and NSS organize a voluntary Blood Donation and Free Health Camp in collaboration with the Government Hospital on October 28, 2026 at 9:00 AM in the College Auditorium. Donor certificates and healthy refreshments provided.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Voluntary blood donation and health checkup camp on October 28, 2026 at 9:00 AM in College Auditorium with certificates provided.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 11. GENERAL
    # -------------------------------------------------------------
    {
        "category": "General",
        "notices": [
            {
                "title": "Campus Cafeteria Nutritional Menu Expansion & Quality Standards",
                "description": "The Central Cafeteria has updated its daily dining menu starting October 20, 2026, introducing fresh juice bars, healthy salad bars, and nutritious millet meals adhering strictly to ISO food safety and hygiene protocols.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Central Cafeteria rolls out expanded healthy dining menu with fresh juice and millet lunches adhering to ISO hygiene standards.",
            },
            {
                "title": "Eco-Friendly Electric Shuttle Buggy Service on Campus",
                "description": "Two eco-friendly battery electric shuttle buggies are now operational between the Main Gate, Academic Blocks, Research Labs, and Sports Pavilion from 8:00 AM to 6:00 PM daily. Service is complimentary for all campus students and staff.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Complimentary campus electric shuttle buggies running between Main Gate, Academic Blocks, and Sports Pavilion daily from 8:00 AM to 6:00 PM.",
            },
            {
                "title": "Cryptographic Digital Campus ID Card Enabled on Echosphere App",
                "description": "Students and faculty can now access verifiable QR-coded Digital ID cards directly inside the Echosphere mobile app. The digital ID card is officially accepted for Library transactions, Cafeteria payments, and Campus Gate entry starting today.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Cryptographic digital ID card activated in Echosphere app for library checkouts, cafeteria payments, and gate verification.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 12. EMERGENCY
    # -------------------------------------------------------------
    {
        "category": "Emergency",
        "notices": [
            {
                "title": "Severe Weather & Thunderstorm Safety Protocol",
                "description": "The State Meteorological Department has issued an orange alert for severe localized thunderstorms and heavy winds. All outdoor sports and activities are suspended immediately. Students must remain inside reinforced academic buildings until the storm advisory clears.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.EMERGENCY,
                "ai_summary": "Emergency weather advisory: Orange alert for thunderstorms; outdoor sports suspended immediately and students advised to stay indoors.",
            },
            {
                "title": "Campus Power Substation Scheduled Grid Repair",
                "description": "Due to emergency transformer repair by the electricity board, main grid power will be isolated today from 2:00 PM to 4:30 PM. Essential laboratories and data center servers will operate uninterrupted on diesel generator backup power.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.EMERGENCY,
                "ai_summary": "Emergency power substation maintenance today from 2:00-4:30 PM; servers and critical laboratories running on diesel generator backup.",
            },
            {
                "title": "Mandatory Campus-Wide Fire Drill & Evacuation Exercise",
                "description": "A mandatory fire safety and emergency evacuation exercise will take place on October 21, 2026 at 11:30 AM across all academic blocks. Upon hearing the siren, walk calmly through fire exits to your block assembly zone. Do not use elevators.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.EMERGENCY,
                "ai_summary": "Mandatory campus fire safety evacuation drill on October 21, 2026 at 11:30 AM; follow fire exits to green assembly zones.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 13. CIRCULAR
    # -------------------------------------------------------------
    {
        "category": "Circular",
        "notices": [
            {
                "title": "Circular: Mandatory Biometric & Facial Recognition Attendance Protocol",
                "description": "In accordance with institutional guidelines, all faculty, administrative staff, and students must record their daily attendance using biometric or facial scanners at campus entrances. Wearing official ID cards is strictly mandatory on campus premise.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Circular mandating biometric attendance logging and wearing of photo ID badges on campus premises.",
            },
            {
                "title": "Circular: Campus Traffic Regulation & Vehicle Sticker Enforcement",
                "description": "All student and staff two-wheelers and four-wheelers must display valid campus security parking stickers. Parking along emergency fire lanes or pedestrian pathways is strictly prohibited and subject to wheel-clamping penalties starting October 22, 2026.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Circular enforcing parking stickers and zero tolerance for parking in fire lanes or pedestrian walkways from October 22, 2026.",
            },
            {
                "title": "Circular: Code of Conduct & Classroom Decorum Regulations",
                "description": "Students must observe professional decorum during instructional hours. Mobile phones must be silenced inside classrooms, laboratories, and the central library. Unauthorized video recording during lectures is strictly forbidden.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Circular outlining classroom decorum rules, mandatory silent mobile devices, and prohibition of unauthorized lecture recordings.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 14. FEE PAYMENT
    # -------------------------------------------------------------
    {
        "category": "Fee Payment",
        "notices": [
            {
                "title": "Semester Tuition & Examination Fee Online Payment Notification",
                "description": "The online ERP payment portal is open for remitting tuition and university examination fees for the upcoming semester. Remit payments via UPI, Net Banking, or Debit Cards without transaction fees before October 25, 2026 at 11:59 PM.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Online ERP portal open for semester tuition and university exam fee payments without convenience charges until October 25, 2026 at 11:59 PM.",
            },
            {
                "title": "Government Scholarship (SSP/NSP) Document Verification Window",
                "description": "Students who applied for Post-Matric, Vidyasiri, SSP, or National Scholarship Portal (NSP) schemes must submit original income certificates and bank passbooks to the Accounts Section before October 30, 2026 at 4:00 PM for institutional verification.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Accounts section verification for SSP and NSP scholarship applicants open until October 30, 2026 at 4:00 PM; submit income certificates.",
            },
            {
                "title": "Hostel Accommodation & Campus Bus Transport Pass Renewal Schedule",
                "description": "The Accounts Office reminds hostellers and day-scholars to clear the second installment of hostel fees and renew bus transport passes before October 31, 2026 at 5:00 PM to ensure uninterrupted boarding and transit facilities.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Deadline for second installment of hostel fees and college bus pass renewals on October 31, 2026 at 5:00 PM.",
            },
        ],
    },
]


def enrich_database_and_cache_audio():
    db = SessionLocal()
    try:
        in_app_dt = db.query(DeliveryType).filter(DeliveryType.name.ilike("%in-app%")).first()
        push_dt = db.query(DeliveryType).filter(DeliveryType.name.ilike("%push%")).first()

        admin_user = db.query(User).filter(User.id == 1).first() or db.query(User).first()
        all_users = db.query(User).all()

        notice_idx = 4
        base_time = datetime.now()

        print("Updating database with enriched functioning notices...")

        for group in RICH_NOTICES:
            cat_name = str(group["category"])
            cat = db.query(AnnouncementCategory).filter(AnnouncementCategory.name.ilike(cat_name)).first()
            if not cat:
                cat = AnnouncementCategory()
                setattr(cat, "name", cat_name)
                setattr(cat, "description", f"{cat_name} notices")
                db.add(cat)
                db.commit()
                db.refresh(cat)

            cat_id_val: int = getattr(cat, "id")
            notices_list: List[Dict[str, Any]] = cast(List[Dict[str, Any]], group["notices"])
            for n_data in notices_list:
                n_title = str(n_data["title"])
                n_desc = str(n_data["description"])
                n_priority = cast(AnnouncementPriority, n_data["priority"])
                n_emergency = cast(EmergencyLevel, n_data["emergency_level"])
                n_summary = str(n_data["ai_summary"])
                admin_id_val: int = getattr(admin_user, "id", 1) if admin_user else 1

                announcement = db.query(Announcement).filter(Announcement.id == notice_idx).first()
                if not announcement:
                    announcement = Announcement()
                    setattr(announcement, "id", notice_idx)
                    setattr(announcement, "title", n_title)
                    setattr(announcement, "description", n_desc)
                    setattr(announcement, "category_id", cat_id_val)
                    setattr(announcement, "priority", n_priority)
                    setattr(announcement, "emergency_level", n_emergency)
                    setattr(announcement, "status", AnnouncementStatus.PUBLISHED)
                    setattr(announcement, "created_by", admin_id_val)
                    setattr(announcement, "target_audience", "Entire College")
                    setattr(announcement, "ai_summary", n_summary)
                    setattr(announcement, "created_at", base_time - timedelta(hours=notice_idx))
                    setattr(announcement, "updated_at", base_time - timedelta(hours=notice_idx))
                    db.add(announcement)
                else:
                    setattr(announcement, "title", n_title)
                    setattr(announcement, "description", n_desc)
                    setattr(announcement, "category_id", cat_id_val)
                    setattr(announcement, "priority", n_priority)
                    setattr(announcement, "emergency_level", n_emergency)
                    setattr(announcement, "status", AnnouncementStatus.PUBLISHED)
                    setattr(announcement, "ai_summary", n_summary)
                    setattr(announcement, "target_audience", "Entire College")

                db.commit()
                db.refresh(announcement)
                curr_notice_id: int = getattr(announcement, "id", notice_idx)

                # Ensure deliveries: In-App Feed and Push Notification only
                for dt in [in_app_dt, push_dt]:
                    if dt:
                        dt_id: int = getattr(dt, "id")
                        deliv = db.query(AnnouncementDelivery).filter(
                            AnnouncementDelivery.announcement_id == curr_notice_id,
                            AnnouncementDelivery.delivery_type_id == dt_id,
                        ).first()
                        if not deliv:
                            deliv = AnnouncementDelivery()
                            setattr(deliv, "announcement_id", curr_notice_id)
                            setattr(deliv, "delivery_type_id", dt_id)
                            db.add(deliv)

                # Ensure notifications for users
                for u in all_users:
                    u_id: int = getattr(u, "id")
                    notif = db.query(Notification).filter(
                        Notification.announcement_id == curr_notice_id,
                        Notification.user_id == u_id,
                    ).first()
                    if not notif:
                        notif = Notification()
                        setattr(notif, "user_id", u_id)
                        setattr(notif, "announcement_id", curr_notice_id)
                        setattr(notif, "is_read", False)
                        db.add(notif)

                db.commit()

                # Generate audio stream file so it's 100% ready
                text = f"{n_title}. {n_desc}"
                generate_announcement_audio_sync(
                    announcement_id=curr_notice_id,
                    text=text,
                    gender="female",
                    accent="indian",
                    is_summary=False,
                )
                print(f"  [ENRICHED] Notice #{curr_notice_id}: {n_title[:45]}...")

                notice_idx += 1

        print(f"\nAll {notice_idx - 4} notices enriched and synchronized with audio streams!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    enrich_database_and_cache_audio()
