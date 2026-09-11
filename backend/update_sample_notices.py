import os
import re
from enrich_notices import RICH_NOTICES

controller_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "lib",
    "controllers",
    "announcement_controller.dart",
)

with open(controller_path, "r", encoding="utf-8") as f:
    content = f.read()

entries = []
id_counter = 1

for group in RICH_NOTICES:
    cat = group["category"]
    cat_tag = "Event" if cat == "Events" else cat

    for n in group["notices"]:
        title = n["title"].replace("'", "\\'")
        desc = n["description"].replace("'", "\\'")
        summary = n["ai_summary"].replace("'", "\\'")
        priority = n["priority"].value.upper()
        emergency = n["emergency_level"].value.upper()

        dept = "Institution"
        if cat in ["Academic", "Workshop"]:
            dept = "AIML"
        elif cat == "Examination":
            dept = "Examinations"
        elif cat == "Placement":
            dept = "Placements"
        elif cat == "Sports":
            dept = "Sports"
        elif cat == "Cultural":
            dept = "Cultural"
        elif cat == "Club Activities":
            dept = "Student Affairs"
        elif cat == "Fee Payment":
            dept = "Finance"
        elif cat == "Circular":
            dept = "Administration"
        elif cat == "Seminar":
            dept = "CSE"

        creator = "College Admin"
        creator_role = "College Admin"
        if cat in ["Academic", "Workshop"]:
            creator = "Dr. B Kursheed"
            creator_role = "Teacher"
        elif cat == "Examination":
            creator = "Controller of Examinations"
            creator_role = "HoD"
        elif cat == "Placement":
            creator = "Placement Officer"
            creator_role = "Faculty / Official"
        elif cat == "Sports":
            creator = "Director of Physical Education"
            creator_role = "Faculty / Official"
        elif cat == "Cultural":
            creator = "Cultural Coordinator"
            creator_role = "Faculty / Official"
        elif cat in ["Emergency", "Holiday"]:
            creator = "Dr. Principal"
            creator_role = "Principal"

        att = "const []"
        t_low = title.lower()
        if "exam" in t_low or "timetable" in t_low or "hall ticket" in t_low:
            att = "const ['Exam_Timetable_Final.pdf']"
        elif "hackathon" in t_low or "hackecho" in t_low:
            att = "const ['HackEcho_Rulebook_2026.pdf']"
        elif "fee" in t_low or "scholarship" in t_low:
            att = "const ['Fee_Structure_2026.pdf', 'Scholarship_Application.pdf']"
        elif "curriculum" in t_low or "syllabus" in t_low or "elective" in t_low:
            att = "const ['Course_Syllabus_2026.pdf']"
        elif "circular" in t_low:
            att = "const ['Official_Circular_Gazette.pdf']"
        elif "sports" in t_low or "football" in t_low or "badminton" in t_low:
            att = "const ['Tournament_Fixtures_Map.pdf']"

        hours_ago = (id_counter * 2) % 60 + 1

        entry = f"""      AnnouncementModel(
        id: {id_counter},
        title: '{title}',
        description: '{desc}',
        priority: '{priority}',
        emergencyLevel: '{emergency}',
        status: 'PUBLISHED',
        creatorName: '{creator}',
        creatorRole: '{creator_role}',
        department: '{dept}',
        category: '{cat_tag}',
        createdAt: now.subtract(const Duration(hours: {hours_ago})),
        aiSummary: '{summary}',
        attachments: {att},
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),"""
        entries.append(entry)
        id_counter += 1

# Add sample draft for pending approvals testing
entries.append("""      AnnouncementModel(
        id: 99,
        title: 'Draft Notice: Guest Lecture on Distributed Cloud Systems',
        description: 'Draft proposal for hosting an expert talk by AWS Lead Architect next Friday in Auditorium 2.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PENDING_APPROVAL',
        creatorName: 'Dr. B Kursheed',
        creatorRole: 'Teacher',
        department: 'AIML',
        category: 'Academic',
        createdAt: now.subtract(const Duration(hours: 2)),
        aiSummary: 'Pending HoD approval for guest lecture on Cloud Systems next Friday.',
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),""")

# Add sample archived notice
entries.append("""      AnnouncementModel(
        id: 100,
        title: 'Archived: Mid-Term Examination Retest Guidelines & Instructions',
        description: 'Official guidelines for students eligible for the Mid-Term Retests. Submissions must be approved by respective HoDs before the deadline.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'ARCHIVED',
        creatorName: 'Controller of Examinations',
        creatorRole: 'HoD',
        department: 'Examinations',
        category: 'Examination',
        createdAt: now.subtract(const Duration(days: 12)),
        aiSummary: 'Archived circular: Mid-term retest instructions and HoD approval requirements.',
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),""")

new_body = "\n".join(entries)
sample_pattern = r"(List<AnnouncementModel> _getSampleAnnouncements\(\) \{\s+final now = DateTime\.now\(\);\s+return \[)[\s\S]*?(\n    \];\s+\})"

if not re.search(sample_pattern, content):
    print("Pattern NOT found!")
    exit(1)

replacement = f"\\1\n{new_body}\\2"
updated_content = re.sub(sample_pattern, replacement, content)

with open(controller_path, "w", encoding="utf-8") as f:
    f.write(updated_content)

print(f"Successfully updated _getSampleAnnouncements with {id_counter - 1} rich category notices!")
