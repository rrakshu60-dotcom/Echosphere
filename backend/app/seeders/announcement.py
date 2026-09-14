from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.enums.announcement import (
    AnnouncementPriority,
    AnnouncementStatus,
    EmergencyLevel,
)
from app.models.announcement import Announcement
from app.models.announcement_category import AnnouncementCategory
from app.models.user import User


def seed_announcements(db: Session):
    """
    Seeds essential campus announcements across diverse categories if none exist.
    """
    if db.query(Announcement).count() > 0:
        return

    admin_user = db.query(User).filter(User.username == "ESDev01").first()
    if not admin_user:
        admin_user = db.query(User).first()

    creator_id = admin_user.id if admin_user else 1

    categories = {cat.name.lower(): cat.id for cat in db.query(AnnouncementCategory).all()}

    now = datetime.now(timezone.utc)

    samples = [
        {
            "title": "Mid-Term Academic Progress Review & Proctor Mentorship Sessions",
            "description": "All B.E. and M.Tech students are required to attend the mandatory mid-term academic counseling sessions scheduled from October 20, 2026 to October 24, 2026 between 10:00 AM and 4:30 PM in their respective Department Faculty Cabins. Faculty proctors will review IA-1 answer scripts, syllabus completion, and attendance registers.",
            "category": "academic",
            "priority": AnnouncementPriority.NORMAL,
            "emergency_level": EmergencyLevel.NORMAL,
            "status": AnnouncementStatus.PUBLISHED,
            "target_audience": "Entire College",
        },
        {
            "title": "Final Professional & Open Elective Subject Selection Deadline",
            "description": "The online academic ERP portal is officially active for submitting elective preferences for the upcoming semester. Students from 5th and 7th semesters must submit choices through the student portal before October 25, 2026 at 5:00 PM.",
            "category": "academic",
            "priority": AnnouncementPriority.HIGH,
            "emergency_level": EmergencyLevel.NORMAL,
            "status": AnnouncementStatus.PUBLISHED,
            "target_audience": "Entire College",
        },
        {
            "title": "Final Schedule for Semester End Theory Examinations - Odd Semester 2026",
            "description": "The Controller of Examinations has published the definitive timetable for the upcoming Semester End Theory Examinations commencing November 15, 2026 at 9:30 AM in Examination Block 3. Download your verified digital hall tickets from the student portal.",
            "category": "examination",
            "priority": AnnouncementPriority.HIGH,
            "emergency_level": EmergencyLevel.NORMAL,
            "status": AnnouncementStatus.PUBLISHED,
            "target_audience": "Entire College",
        },
        {
            "title": "Tier-1 Recruitment Drive: Microsoft Cloud & AI Engineering",
            "description": "The Department of Training and Placement announces on-campus recruitment by Microsoft for Cloud Solutions Architect and AI Development roles. Eligible streams: CSE, AIML, ISE, and ECE with CGPA 8.0 and above. Mandatory online test on October 24, 2026 at 10:00 AM.",
            "category": "placement",
            "priority": AnnouncementPriority.HIGH,
            "emergency_level": EmergencyLevel.NORMAL,
            "status": AnnouncementStatus.PUBLISHED,
            "target_audience": "Entire College",
        },
        {
            "title": "Guest Lecture: Scalable Microservices Architecture with Kubernetes",
            "description": "The Department of Computer Science invites all pre-final and final year students to an exclusive technical session delivered by Principal Architects from Google Cloud on Saturday, October 24, 2026 at 11:00 AM in Seminar Hall 1.",
            "category": "seminar",
            "priority": AnnouncementPriority.NORMAL,
            "emergency_level": EmergencyLevel.NORMAL,
            "status": AnnouncementStatus.PUBLISHED,
            "target_audience": "Entire College",
        },
        {
            "title": "Annual Inter-Collegiate Techno-Cultural Fest 'ECHO-FEST 2026' Registrations",
            "description": "Registrations are formally open for our flagship annual technical hackathon, robotics arena, and cultural stage battles scheduled from November 6 to November 8, 2026. Early bird passes available through student activity coordinators.",
            "category": "cultural",
            "priority": AnnouncementPriority.NORMAL,
            "emergency_level": EmergencyLevel.NORMAL,
            "status": AnnouncementStatus.PUBLISHED,
            "target_audience": "Entire College",
        },
        {
            "title": "Campus Wide Fire Safety Drill & Evacuation Protocol Briefing",
            "description": "A mandatory fire safety drill and alarm simulation will be conducted across all academic and laboratory wings this Wednesday at 3:30 PM. Floor wardens will guide smooth evacuation to designated open assembly zones.",
            "category": "emergency",
            "priority": AnnouncementPriority.EMERGENCY,
            "emergency_level": EmergencyLevel.CRITICAL,
            "status": AnnouncementStatus.PUBLISHED,
            "target_audience": "Entire College",
            "deliver_speaker": True,
        },
        {
            "title": "Proposal: Hands-On Generative AI Lab Session for 6th Semester",
            "description": "Proposed practical workshop covering open-source LLM fine-tuning and LoRA deployment using PyTorch in the AIML High Performance Computing Lab.",
            "category": "workshop",
            "priority": AnnouncementPriority.HIGH,
            "emergency_level": EmergencyLevel.NORMAL,
            "status": AnnouncementStatus.PENDING_APPROVAL,
            "target_audience": "AIML Department",
        },
        {
            "title": "Guest Lecture Proposal: Distributed Cloud Architectures",
            "description": "Proposal for hosting an expert talk by AWS Solution Architect next Friday in Auditorium 2. Focus on multi-region failover strategies.",
            "category": "seminar",
            "priority": AnnouncementPriority.NORMAL,
            "emergency_level": EmergencyLevel.NORMAL,
            "status": AnnouncementStatus.PENDING_APPROVAL,
            "target_audience": "Entire College",
        },
    ]

    for item in samples:
        cat_id = categories.get(item["category"], 1)
        announcement = Announcement(
            title=item["title"],
            description=item["description"],
            category_id=cat_id,
            priority=item["priority"],
            emergency_level=item["emergency_level"],
            status=item["status"],
            target_audience=item.get("target_audience", "Entire College"),
            deliver_speaker=item.get("deliver_speaker", False),
            deliver_in_app=True,
            deliver_push=True,
            created_by=creator_id,
            created_at=now,
        )
        db.add(announcement)

    db.commit()
    print(f"Seeded {len(samples)} baseline announcements successfully.")
