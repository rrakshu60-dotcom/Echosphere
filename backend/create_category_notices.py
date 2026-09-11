"""
Seed script to create exactly 3 high-quality notices for every announcement category,
configured exclusively for In-App Feed and Push Notification deliveries (deliver_speaker=False).
"""

import os
import sys
from datetime import datetime, timedelta

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

NOTICES_DATA = [
    # -------------------------------------------------------------
    # 1. ACADEMIC
    # -------------------------------------------------------------
    {
        "category": "Academic",
        "notices": [
            {
                "title": "Mid-Term Academic Progress Review and Mentorship Meetings",
                "description": "All undergraduate and postgraduate students are required to attend the mid-term academic counseling and mentorship sessions scheduled with their respective faculty proctors this week. Proctors will review IA-1 marks, syllabus completion, and attendance records. Students with attendance below 85% must report along with their local guardians.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Mid-term academic counseling and proctor mentorship meetings scheduled this week; attendance and IA-1 performance review mandatory.",
            },
            {
                "title": "Elective Course Final Selection for Next Academic Semester",
                "description": "The academic portal is now active for submitting Open Elective and Professional Elective course selections for the upcoming semester. Students from 5th and 7th semesters must submit their choices through the student portal by Friday, 5:00 PM. Allotment will strictly be on a first-come, first-served basis subject to eligibility criteria.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Online portal open for 5th & 7th semester Open/Professional Elective subject selection until Friday 5:00 PM.",
            },
            {
                "title": "AI & Data Science Curriculum Feedback Survey 2026",
                "description": "In accordance with NBA accreditation guidelines, the Department of Academic Affairs invites all students to participate in the annual Course Outcome (CO) and Program Outcome (PO) feedback survey. Please access the survey link sent to your registered college email ID and submit constructive feedback by end of this week.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "NBA accreditation curriculum feedback survey open for all students via registered email until end of week.",
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
                "title": "Final Schedule for Semester End Theory Examinations",
                "description": "The Controller of Examinations has officially released the final timetable for the upcoming Semester End Theory Examinations for all B.E. and M.Tech programs. Morning sessions will run from 9:30 AM to 12:30 PM, and afternoon sessions from 2:00 PM to 5:00 PM. Hall tickets are available for download on the examination portal.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Final timetable for Semester End Theory Examinations published; morning and afternoon session timings announced and hall tickets available online.",
            },
            {
                "title": "Hall Ticket Collection & Mandatory Examination Rules",
                "description": "Students appearing for the upcoming university exams must collect their physical signed Hall Tickets from their department offices after clearing all pending library and department dues. Carrying mobile phones, smartwatches, or any electronic communication devices into examination halls is strictly prohibited and attracts severe malpractice penalties.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Collect physical hall tickets from department offices after clearing dues; smartwatches and electronic devices strictly banned in exam halls.",
            },
            {
                "title": "Supplementary and Re-valuation Registration Window",
                "description": "Applications are invited from eligible students for photocopy evaluation and re-valuation of answer scripts for the previously concluded semester examinations. The online payment window will remain open for 7 days. Late submissions will not be entertained under any circumstances.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Online portal open for 7 days for photocopy evaluation and re-valuation applications for recent semester examinations.",
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
                "title": "Tier-1 Placement Drive: Microsoft Cloud & AI Engineering",
                "description": "The Department of Training and Placement is thrilled to announce on-campus recruitment by Microsoft for Cloud Solutions Architect and AI Development roles. Eligible streams: CSE, AIML, ISE, and ECE with aggregate CGPA >= 8.0 and no active arrears. Online coding assessment will be held this Saturday on HackerEarth platform.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Microsoft recruitment drive for Cloud & AI roles; eligible students with CGPA 8.0+ must take coding assessment this Saturday.",
            },
            {
                "title": "Resume Building & Technical Mock Interview Sessions",
                "description": "Corporate trainers from top tier MNCs will conduct intensive 1-on-1 mock interviews and ATS-friendly resume review sessions for 6th and 7th semester students. Students must bring two hard copies of their updated resume in standard campus format and attend in formal business attire.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "1-on-1 technical mock interviews and resume workshops conducted by corporate trainers for 6th & 7th semester students.",
            },
            {
                "title": "Summer Internship Opportunities at Goldman Sachs & Morgan Stanley",
                "description": "Applications are open for the 8-week Summer Technology Analyst Internship program. Stipend: ₹75,000/month with pre-placement interview (PPI) opportunity. Interested students must submit their applications on the Superset placement portal before tomorrow 11:59 PM.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Summer internship applications open on Superset for Goldman Sachs and Morgan Stanley with ₹75,000 monthly stipend.",
            },
        ],
    },

    # -------------------------------------------------------------
    # 4. EVENTS / EVENT
    # -------------------------------------------------------------
    {
        "category": "Events",
        "notices": [
            {
                "title": "HackEcho 2026: 24-Hour National Collegiate Hackathon",
                "description": "Registrations are now live for HackEcho 2026, our flagship national level 24-hour hackathon. Grand prize pool of ₹2,50,000 across AI/ML, Cyber Defense, IoT/Smart Cities, and Open Innovation tracks. Free food, mentoring, high-speed WiFi, and overnight accommodation provided. Form teams of 2-4 members.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "HackEcho 2026 national 24-hour hackathon registrations open with ₹2.5 Lakhs prize pool across AI, IoT, and Cyber tracks.",
            },
            {
                "title": "Annual College Day Celebrations & Alumni Homecoming",
                "description": "The Annual Institution Day and Alumni Meet 'Samanvay 2026' will be held on campus. The event will feature presidential addresses, academic excellence awards, alumni panel discussions, and high-energy evening entertainment. All students, staff, and alumni are cordially invited.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Annual College Day and Alumni Homecoming 'Samanvay 2026' featuring academic excellence awards and evening celebrations.",
            },
            {
                "title": "Campus Founder Pitchfest: Angel Investors & Startup Showcase",
                "description": "The Centre for Innovation and Entrepreneurship (CIE) hosts the annual Founder Pitchfest. Student-led startups and project prototypes can pitch in front of leading venture capitalists and angel investors for seed funding grants up to ₹5,00,000. Registration closes this Thursday.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "CIE Founder Pitchfest offers student startups pitching opportunity for seed funding grants up to ₹5,00,000.",
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
                "title": "Hands-On Workshop on Fine-Tuning LLMs with LoRA & Unsloth",
                "description": "Department of AIML is hosting a comprehensive 2-day hands-on workshop on training and fine-tuning open-source LLMs (Qwen 2.5 and LLaMA 3) on local GPU hardware using PEFT, LoRA, and Unsloth. Participants will receive certificates and cloud GPU credits. Venue: High Performance Computing Lab.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "2-day hands-on workshop on fine-tuning open-source LLMs using LoRA/Unsloth in the HPC Lab with GPU credits provided.",
            },
            {
                "title": "Practical Embedded Systems & ESP32 IoT Prototyping Workshop",
                "description": "Learn circuit design, sensor integration, FreeRTOS programming, and MQTT cloud telemetry with ESP32 microcontrollers. Kits will be provided to all registered pairs. Organised jointly by IEEE Student Branch and Department of Electronics. Seats limited to 60 participants.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Hands-on ESP32 IoT and FreeRTOS embedded systems prototyping workshop with hardware kits provided for 60 participants.",
            },
            {
                "title": "Full-Stack Development with Flutter & FastAPI Masterclass",
                "description": "An intensive weekend bootcamp covering high-performance cross-platform mobile apps with Flutter 3, asynchronous RESTful APIs with FastAPI, WebSocket real-time streams, and SQLite database persistence. Ideal for pre-final and final year project builders.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Weekend masterclass on building scalable full-stack applications with Flutter, FastAPI, and WebSockets.",
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
                "description": "The Department of Computer Science welcomes Dr. Richard Thorne, Principal Quantum Scientist at IBM Quantum Labs, for an exclusive lecture on 'Fault-Tolerant Quantum Algorithms and Practical Qubit Scaling'. Venue: Sir M. Visvesvaraya Auditorium, Friday 11:00 AM.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "IBM Quantum Fellow Dr. Richard Thorne delivering distinguished lecture on Fault-Tolerant Quantum Algorithms this Friday.",
            },
            {
                "title": "Seminar on Cybersecurity in Autonomous Vehicles & Robotics",
                "description": "Industry veterans from Bosch Automotive Technologies will deliver an in-depth seminar exploring CAN-bus security vulnerabilities, sensor spoofing countermeasures, and ISO 21434 automotive cyber standards. Open to all engineering branches.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Bosch engineers conducting technical seminar on autonomous vehicle cybersecurity and CAN-bus attack mitigations.",
            },
            {
                "title": "Higher Studies Abroad: GRE, TOEFL & Ivy League Admissions Guidance",
                "description": "International education advisors from EducationUSA will conduct an interactive seminar detailing scholarship opportunities, statement of purpose (SOP) crafting, professor outreach for research assistantships, and visa protocols for MS/PhD programs in USA, Germany, and Canada.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Interactive seminar by EducationUSA covering GRE prep, university applications, and scholarships for MS/PhD abroad.",
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
                "title": "Declaration of Institutional Holiday on Account of Maha Shivaratri",
                "description": "As per the official state government gazette, the college will remain closed on Friday on account of Maha Shivaratri. Regular academic schedules, laboratory classes, and administrative services will resume on the following Monday.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "College closed on Friday for Maha Shivaratri holiday; regular classes and offices resume on Monday.",
            },
            {
                "title": "Mid-Term Semester Vacation Schedule & Hostels Protocol",
                "description": "The campus will observe a mid-semester break from October 12th to October 18th. Hostels will remain operational with mess timings revised. The library and research computing facilities will remain open from 10:00 AM to 4:00 PM for project researchers.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Mid-semester vacation scheduled from Oct 12-18; hostels remain open with revised mess hours and library operational 10am-4pm.",
            },
            {
                "title": "National Holiday Observance: Republic Day Flag Hoisting Ceremony",
                "description": "The 77th Republic Day will be solemnly celebrated on campus. The National Flag hoisting ceremony will be held at 8:30 AM at the College Quadrangle, followed by addresses by the Principal and NCC cadet parade. All staff and students are requested to assemble by 8:15 AM.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Republic Day celebrations and National Flag hoisting at 8:30 AM in the Quadrangle; assembly at 8:15 AM.",
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
                "title": "Annual Inter-Branch Football & Volleyball Tournament Fixtures",
                "description": "The Department of Physical Education has released the official fixtures for the Annual Inter-Branch Sports Tournament. Football league matches will commence at 6:30 AM on Ground 1, and Volleyball matches at 4:30 PM on Court 2. Students must represent in official departmental jerseys.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Fixtures announced for Inter-Branch Football and Volleyball tournaments starting this week on sports grounds.",
            },
            {
                "title": "Badminton & Table Tennis Selection Trials for State University Meet",
                "description": "Open trials for selecting the Men's and Women's Badminton and Table Tennis varsity teams will be conducted at the Indoor Sports Complex this Wednesday starting at 4:00 PM. Interested players should carry non-marking badminton shoes and standard equipment.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Varsity selection trials for Badminton and Table Tennis at Indoor Sports Complex this Wednesday at 4:00 PM.",
            },
            {
                "title": "College Gymnasium Upgraded with Modern Cardio & Strength Equipment",
                "description": "The student gymnasium has been refurbished with state-of-the-art cardiovascular and strength training equipment. New operational hours: Morning session: 6:00 AM to 8:30 AM, Evening session: 4:30 PM to 8:00 PM. Certified fitness trainers will be available for guidance.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Student gymnasium upgraded with new cardio/strength equipment; open 6:00-8:30 AM and 4:30-8:00 PM with trainers available.",
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
                "title": "Aura 2026: Battle of the Bands & Acoustic Music Auditions",
                "description": "The College Cultural Committee invites solo vocalists, drummers, guitarists, and Western/Eastern bands for auditions for the flagship Battle of the Bands stage at Aura 2026. Auditions will be evaluated by renowned music producers in the Open Air Amphitheatre.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Auditions for Battle of the Bands and solo music artists for Aura 2026 cultural fest in the Open Air Amphitheatre.",
            },
            {
                "title": "Inter-Collegiate Classical & Contemporary Dance Competition",
                "description": "Auditions for the college core dance troupe for representational entry into university-level cultural fests will take place this Thursday in the Cultural Activity Room. Categories include Classical Solo, Semi-Classical Group, and Western Hip-Hop.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Dance troupe selection auditions for Classical, Semi-Classical, and Western Hip-Hop this Thursday in Cultural Room.",
            },
            {
                "title": "Literary Fest: Parliamentary Debate, Elocution & Creative Writing",
                "description": "The College Literary and Debating Society announces the Intra-College Literary Championship. Events include British Parliamentary Debate, Slam Poetry, Flash Fiction, and General Quiz. Cash awards and certificates for all category finalists.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Intra-college Literary Championship with Parliamentary Debate, Poetry, and Quizzing; cash awards for finalists.",
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
                "description": "The RoboTech club is kickstarting its annual Autonomous Rover competition. Students will learn LiDAR mapping, ROS2 simulation, computer vision with OpenCV, and motor driver telemetry. First orientation and kit unboxing on Wednesday at 4:30 PM in Innovation Lab.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "RoboTech club orientation for Autonomous Rover Challenge with ROS2 and computer vision on Wednesday at 4:30 PM.",
            },
            {
                "title": "Google Developer Student Club (GDSC) Core Team Recruitment",
                "description": "GDSC is accepting applications for technical leads, web/app developers, AI leads, and event coordinators for the upcoming academic tenure. Interested candidates should submit their GitHub portfolios and complete the short technical assignment by Sunday.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "GDSC core team recruitment open for technical leads and event organizers; submit GitHub portfolio by Sunday.",
            },
            {
                "title": "Rotaract & NSS Blood Donation Camp & Health Awareness Drive",
                "description": "The Youth Red Cross, Rotaract, and NSS units are organizing a Mega Voluntary Blood Donation and Health Checkup Camp in partnership with the Government Hospital. Refreshments and donor appreciation certificates will be provided to all volunteers.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Voluntary blood donation and health checkup camp organized by Rotaract and NSS in partnership with Govt Hospital.",
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
                "title": "Campus Cafeteria Menu Expansion & Hygiene Standards Compliance",
                "description": "Following recommendations by the Student-Faculty Food Committee, the Central Cafeteria has revamped its daily menu to introduce healthy breakfast alternatives, freshly squeezed juice counters, and nutritious millets-based lunches. Strict ISO food hygiene standards are enforced.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Central Cafeteria introduces expanded menu with healthy breakfast options and fresh juices adhering to food safety standards.",
            },
            {
                "title": "Campus Electric Shuttle Services & Eco-Friendly Transit Routes",
                "description": "To support our green campus sustainability initiative, two new battery-operated electric shuttle buggies have been deployed between the main entrance gate, academic blocks, research labs, and sports pavilion. Rides are complimentary for all students and staff.",
                "priority": AnnouncementPriority.LOW,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Complimentary electric shuttle buggy service launched between campus entrance, academic blocks, and sports pavilion.",
            },
            {
                "title": "Digital Campus ID Card App Integration on Echosphere",
                "description": "Students and staff can now access their verifiable cryptographic QR-coded Digital ID cards directly inside the Echosphere mobile app. The digital ID is fully recognized for library book checkouts, cafeteria cashless payments, and campus gate entry.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Cryptographic digital ID cards enabled inside Echosphere app for library checkouts and gate entry.",
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
                "title": "Urgent Weather Advisory - Severe Storm & Campus Safety",
                "description": "The Meteorological Department has issued an orange alert for severe localized thunderstorms and gusty winds in the district. All outdoor sports and activities are suspended immediately. Students are advised to remain indoors inside reinforced concrete academic buildings.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.EMERGENCY,
                "ai_summary": "Emergency weather advisory: Orange alert for thunderstorms; outdoor activities halted and students advised to stay indoors.",
            },
            {
                "title": "Campus Power Substation Scheduled Maintenance Shutdown",
                "description": "Due to emergency transformer repairs and grid load balancing by the electricity board, main grid power will be isolated between 2:00 PM and 4:30 PM today. Critical servers and laboratory equipment are running on diesel generator backup.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.EMERGENCY,
                "ai_summary": "Emergency power substation maintenance today from 2:00-4:30 PM; critical labs and servers operating on generator backup.",
            },
            {
                "title": "Fire Drill Evacuation Exercise - Wednesday 11:30 AM",
                "description": "A mandatory unannounced fire safety and emergency evacuation drill will be conducted across all academic and administrative blocks. When emergency alarms sound, please walk calmly towards designated assembly zones. Do not use elevators.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.EMERGENCY,
                "ai_summary": "Mandatory campus fire safety evacuation drill scheduled; assemble at designated green zones upon hearing alarms.",
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
                "title": "Circular: Mandatory Biometric Attendance & Identity Badge Regulation",
                "description": "In accordance with institutional regulatory standards, all faculty, administrative staff, and students must punch in/out using facial recognition or biometric scanners. Wearing physical or digital ID badges with photo credentials is strictly mandatory on campus premise.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Circular regarding mandatory biometric/facial punch in-out and wearing of ID badges on campus premises.",
            },
            {
                "title": "Circular: Parking Regulations & Zero Emission Vehicle Priority Zones",
                "description": "All two-wheelers and four-wheelers must display valid college vehicle registration stickers issued by campus security. Parking on pedestrian walkways or fire access lanes is strictly prohibited and subject to wheel-clamping fines.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Circular on campus vehicle parking guidelines, mandatory registration stickers, and penalties for walkway obstruction.",
            },
            {
                "title": "Circular: Code of Conduct During Academic Hours & Mobile Device Policy",
                "description": "Students are strictly required to observe institutional decorum inside lecture halls, laboratories, and libraries. Mobile devices must remain silenced or powered off during ongoing instructional periods. Violations will lead to confiscation.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Circular mandating silent mobile devices and adherence to academic decorum inside classrooms and laboratories.",
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
                "title": "Semester Tuition & Examination Fee Payment Portal Notification",
                "description": "The online ERP payment gateway is now open for remitting tuition and university examination fees for the upcoming semester. Students can pay via UPI, Net Banking, or Credit/Debit cards with zero convenience charge. Deadline: 25th of this month.",
                "priority": AnnouncementPriority.HIGH,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Online portal open for semester tuition and examination fee payments with zero transaction charges until the 25th.",
            },
            {
                "title": "Scholarship Disbursement & National Scholarship Portal (NSP) Verification",
                "description": "Students who have applied for Post-Matric, Vidyasiri, SSP, or NSP merit-cum-means scholarships are requested to submit physical copies of income certificates and bank passbooks to the accounts section for final institutional verification.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Accounts section verification open for SSP, NSP, and Vidyasiri scholarship applicants; submit income documents.",
            },
            {
                "title": "Hostel & Transport Fee Installment Schedule for Academic Year 2026",
                "description": "Notice regarding the second installment of hostel accommodation and college bus transport fees. Students availing bus facility must renew their transport passes before the end of next week to ensure uninterrupted service.",
                "priority": AnnouncementPriority.NORMAL,
                "emergency_level": EmergencyLevel.NORMAL,
                "ai_summary": "Second installment deadline for hostel and college bus transport fees; renew bus passes before end of next week.",
            },
        ],
    },
]


def seed_notices():
    db = SessionLocal()
    try:
        # Fetch or create delivery types
        in_app_dt = db.query(DeliveryType).filter(DeliveryType.name.ilike("%in-app%")).first()
        if not in_app_dt:
            in_app_dt = DeliveryType(name="In-App Feed")
            db.add(in_app_dt)
            db.commit()
            db.refresh(in_app_dt)

        push_dt = db.query(DeliveryType).filter(DeliveryType.name.ilike("%push%")).first()
        if not push_dt:
            push_dt = DeliveryType(name="Push Notification")
            db.add(push_dt)
            db.commit()
            db.refresh(push_dt)

        # Get Admin User as default creator
        admin_user = db.query(User).filter(User.id == 1).first()
        if not admin_user:
            admin_user = db.query(User).first()

        all_users = db.query(User).all()

        total_created = 0
        base_time = datetime.utcnow()

        for group in NOTICES_DATA:
            cat_name = group["category"]
            category = db.query(AnnouncementCategory).filter(AnnouncementCategory.name.ilike(cat_name)).first()
            if not category:
                category = AnnouncementCategory(name=cat_name, description=f"{cat_name} notices")
                db.add(category)
                db.commit()
                db.refresh(category)

            print(f"\nProcessing Category: {category.name} (ID: {category.id})")

            for i, item in enumerate(group["notices"]):
                # Check if notice with this title already exists
                existing = db.query(Announcement).filter(Announcement.title == item["title"]).first()
                if existing:
                    print(f"  [EXISTS] Notice '{item['title']}' already in DB (ID: {existing.id})")
                    announcement = existing
                else:
                    notice_time = base_time - timedelta(hours=(total_created * 2 + i + 1))
                    announcement = Announcement(
                        title=item["title"],
                        description=item["description"],
                        category_id=category.id,
                        priority=item["priority"],
                        emergency_level=item["emergency_level"],
                        status=AnnouncementStatus.PUBLISHED,
                        created_by=admin_user.id,
                        target_audience="Entire College",
                        ai_summary=item["ai_summary"],
                        created_at=notice_time,
                        updated_at=notice_time,
                    )
                    db.add(announcement)
                    db.commit()
                    db.refresh(announcement)
                    total_created += 1
                    print(f"  [CREATED] Notice '{item['title']}' (ID: {announcement.id})")

                # Attach delivery channels: In-App Feed and Push Notification
                for dt in [in_app_dt, push_dt]:
                    delivery_exists = db.query(AnnouncementDelivery).filter(
                        AnnouncementDelivery.announcement_id == announcement.id,
                        AnnouncementDelivery.delivery_type_id == dt.id,
                    ).first()
                    if not delivery_exists:
                        db.add(AnnouncementDelivery(
                            announcement_id=announcement.id,
                            delivery_type_id=dt.id,
                        ))

                # Create notifications for users
                for u in all_users:
                    notif_exists = db.query(Notification).filter(
                        Notification.announcement_id == announcement.id,
                        Notification.user_id == u.id,
                    ).first()
                    if not notif_exists:
                        db.add(Notification(
                            user_id=u.id,
                            announcement_id=announcement.id,
                            is_read=False,
                        ))

                db.commit()

        print(f"\nSuccessfully seeded notices! Total created in this run: {total_created}")
        
        # Verify count per category
        print("\nSummary of Notices per Category in DB:")
        cats = db.query(AnnouncementCategory).all()
        total_all = 0
        for c in cats:
            count = db.query(Announcement).filter(Announcement.category_id == c.id).count()
            print(f"  - {c.name}: {count} notices")
            total_all += count
        print(f"Total Notices in DB: {total_all}")

    except Exception as ex:
        db.rollback()
        print(f"Error during notice seeding: {ex}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_notices()
