import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.announcement import Announcement
from app.models.announcement_delivery import AnnouncementDelivery
from app.models.announcement_approval import AnnouncementApproval
from app.models.announcement_archive import AnnouncementArchive
from app.models.announcement_vip_protocol import AnnouncementVipProtocol
from app.models.announcement_repeat_schedule import (
    AnnouncementRepeatSchedule,
    RepeatSlotExecutionLog,
)
from app.models.speaker_queue import SpeakerQueue
from app.models.speaker_command import SpeakerCommand
from app.models.notification import Notification

def purge_all_notices():
    db = SessionLocal()
    try:
        print("Starting notice purge...")

        # 1. Delete repeat slot execution logs
        num_logs = db.query(RepeatSlotExecutionLog).delete()
        print(f"Deleted {num_logs} repeat slot execution logs.")

        # 2. Delete announcement repeat schedules
        num_scheds = db.query(AnnouncementRepeatSchedule).delete()
        print(f"Deleted {num_scheds} announcement repeat schedules.")

        # 3. Delete speaker queue items
        num_queue = db.query(SpeakerQueue).delete()
        print(f"Deleted {num_queue} speaker queue items.")

        # 4. Delete speaker commands referencing announcements
        num_cmds = db.query(SpeakerCommand).delete()
        print(f"Deleted {num_cmds} speaker commands.")

        # 5. Delete announcement approvals
        num_approvals = db.query(AnnouncementApproval).delete()
        print(f"Deleted {num_approvals} announcement approvals.")

        # 6. Delete announcement deliveries
        num_deliveries = db.query(AnnouncementDelivery).delete()
        print(f"Deleted {num_deliveries} announcement deliveries.")

        # 7. Delete announcement archives
        num_archives = db.query(AnnouncementArchive).delete()
        print(f"Deleted {num_archives} announcement archives.")

        # 8. Delete announcement VIP protocols
        num_vip = db.query(AnnouncementVipProtocol).delete()
        print(f"Deleted {num_vip} announcement VIP protocols.")

        # 9. Delete notifications associated with announcements
        num_notifs = db.query(Notification).filter(Notification.announcement_id != None).delete()
        print(f"Deleted {num_notifs} announcement notifications.")

        # 10. Delete all announcements
        num_announcements = db.query(Announcement).delete()
        print(f"Deleted {num_announcements} announcements.")

        db.commit()
        print("Database commit successful.")

        # 11. Remove generated announcement audio streams
        static_audio_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app",
            "static",
            "audio_streams",
        )
        removed_audio_count = 0
        if os.path.isdir(static_audio_dir):
            for audio_path in glob.glob(os.path.join(static_audio_dir, "announcement_*.*")):
                try:
                    os.remove(audio_path)
                    removed_audio_count += 1
                except Exception as e:
                    print(f"Error removing {audio_path}: {e}")
        print(f"Removed {removed_audio_count} generated audio files from audio_streams/.")

        # 12. Verification check
        remaining_announcements = db.query(Announcement).count()
        print(f"Verification: {remaining_announcements} announcements remaining in database.")

        return remaining_announcements == 0
    except Exception as e:
        db.rollback()
        print(f"Error during purge: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    success = purge_all_notices()
    if success:
        print("\nAll notices have been successfully purged from the database!")
    else:
        print("\nNotice purge failed.")
        sys.exit(1)
