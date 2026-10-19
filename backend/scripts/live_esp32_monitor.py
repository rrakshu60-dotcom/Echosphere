"""
EchoSphere ESP32 Live Telemetry & Latency Monitor
=================================================
Monitors:
1. COM7 Serial Port at 115200 baud (Direct hardware ESP32 logs).
2. Backend Database Queue & Repeat Schedule events (Millisecond latency tracking).
3. Live notice transitions: Creation -> TTS Audio -> ESP32 Enqueue -> ESP32 Playback -> Repeat Gap.
"""

import sys
import os
import time
import functools
from datetime import datetime, timezone
import threading

# Force unbuffered prints
print = functools.partial(print, flush=True)

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.database import SessionLocal
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.models.announcement import Announcement
from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule

def get_ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def serial_monitor_thread(stop_event):
    """
    Watches for COM7 (or any new COM port) and reads serial lines at 115200 baud.
    Uses win32file for reliable, zero-dependency Windows serial communications.
    """
    import win32file
    import win32con

    target_port = "COM7"
    handle = None

    print(f"[{get_ts()}] [SERIAL] Waiting for {target_port} to connect at 115200 baud...")

    while not stop_event.is_set():
        if handle is None:
            try:
                handle = win32file.CreateFile(
                    f"\\\\.\\{target_port}",
                    win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                    0,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None,
                )
                dcb = win32file.GetCommState(handle)
                dcb.BaudRate = 115200
                dcb.ByteSize = 8
                dcb.Parity = win32file.NOPARITY
                dcb.StopBits = win32file.ONESTOPBIT
                win32file.SetCommState(handle, dcb)

                timeouts = win32file.COMMTIMEOUTS()
                timeouts.ReadIntervalTimeout = 20
                timeouts.ReadTotalTimeoutConstant = 50
                timeouts.ReadTotalTimeoutMultiplier = 10
                win32file.SetCommTimeouts(handle, timeouts)

                print(f"[{get_ts()}] [SERIAL] >>> CONNECTED TO ESP32 ON {target_port} (115200 baud) <<<")
            except Exception:
                handle = None
                time.sleep(1.0)
                continue

        try:
            err, data = win32file.ReadFile(handle, 512)
            if data:
                text = data.decode("utf-8", errors="replace")
                lines = text.splitlines()
                for line in lines:
                    line_str = line.strip()
                    if line_str:
                        print(f"[{get_ts()}] [ESP32 SERIAL {target_port}] {line_str}")
            time.sleep(0.02)
        except Exception as e:
            print(f"[{get_ts()}] [SERIAL] {target_port} disconnected or read error: {e}")
            try:
                win32file.CloseHandle(handle)
            except Exception:
                pass
            handle = None
            time.sleep(1.0)

    if handle:
        try:
            win32file.CloseHandle(handle)
        except Exception:
            pass


def backend_queue_monitor_thread(stop_event):
    """
    Polls the backend database every 250ms for:
    - New announcements published or scheduled
    - SpeakerQueue item status changes (PENDING -> PLAYING -> COMPLETED)
    - Repeat schedule triggers
    - Measures precise latency intervals
    """
    seen_announcements = set()
    seen_queue_items = {} # id -> status
    last_completed_time = None
    last_enqueued_time = None

    print(f"[{get_ts()}] [BACKEND MONITOR] Telemetry engine active. Monitoring SpeakerQueue and RepeatSchedules...")

    while not stop_event.is_set():
        db = SessionLocal()
        try:
            # 1. Check recent announcements (last 10 minutes)
            recent_anns = db.query(Announcement).order_by(Announcement.id.desc()).limit(5).all()
            for ann in recent_anns:
                if ann.id not in seen_announcements:
                    seen_announcements.add(ann.id)
                    print(
                        f"[{get_ts()}] [ANNOUNCEMENT CREATED] ID #{ann.id} | Title: '{ann.title}' "
                        f"| Status: {ann.status} | DeliverSpeaker: {ann.deliver_speaker} | AudioURL: {bool(ann.audio_url)}"
                    )

            # 2. Check Speaker Queue items
            queue_items = db.query(SpeakerQueue).order_by(SpeakerQueue.id.desc()).limit(10).all()
            for q in queue_items:
                prev_status = seen_queue_items.get(q.id)
                current_status = q.status

                if prev_status is None:
                    seen_queue_items[q.id] = current_status
                    if current_status in ["PENDING", "PLAYING"]:
                        last_enqueued_time = time.time()
                        repeat_info = f" (Round {q.repeat_round} of {q.max_repeats})" if q.is_repeat else " (Initial Broadcast)"
                        print(
                            f"[{get_ts()}] [QUEUE ENQUEUED] Item #{q.id} | AnnID: #{q.announcement_id} "
                            f"| Priority: {q.priority} | Status: {current_status}{repeat_info} "
                            f"| Scheduled: {q.scheduled_time}"
                        )
                elif prev_status != current_status:
                    seen_queue_items[q.id] = current_status
                    now_time = time.time()

                    if current_status == "PLAYING":
                        latency = f"{(now_time - last_enqueued_time):.2f}s" if last_enqueued_time else "N/A"
                        print(
                            f"[{get_ts()}] [BROADCAST PLAYING] Item #{q.id} (Ann #{q.announcement_id}) "
                            f"is NOW PLAYING on ESP32! (Pickup Latency: {latency})"
                        )
                    elif current_status == "COMPLETED":
                        gap = f"{(now_time - last_completed_time):.2f}s" if last_completed_time else "First Notice"
                        last_completed_time = now_time
                        print(
                            f"[{get_ts()}] [BROADCAST FINISHED] Item #{q.id} (Ann #{q.announcement_id}) "
                            f"COMPLETED playback. (Repeat Gap: {gap})"
                        )
                    else:
                        print(f"[{get_ts()}] [QUEUE STATUS] Item #{q.id} transitioned {prev_status} -> {current_status}")

            # 3. Check Repeat Schedules
            repeat_schedules = db.query(AnnouncementRepeatSchedule).filter(AnnouncementRepeatSchedule.is_active == True).all()
            for rs in repeat_schedules:
                key = f"rs_{rs.id}_{rs.total_played_count}_{rs.last_repeat_at}"
                if key not in seen_queue_items:
                    seen_queue_items[key] = True
                    slots = rs.selected_slots or []
                    custom_range = f" | Window: {rs.custom_start_time} - {rs.custom_end_time}" if "CUSTOM_WINDOW" in slots else ""
                    print(
                        f"[{get_ts()}] [REPEAT SCHEDULE ACTIVE] Ann #{rs.announcement_id} "
                        f"| Slots: {slots}{custom_range} | Total Played: {rs.total_played_count} "
                        f"| Next Due: {rs.next_repeat_at}"
                    )

        except Exception as e:
            print(f"[{get_ts()}] [MONITOR ERROR] {e}")
        finally:
            db.close()

        time.sleep(0.3)


if __name__ == "__main__":
    print("=" * 70)
    print("  EchoSphere Live ESP32 & Repeat Latency Debugging Monitor")
    print("  Port: COM7 (115200 baud) | Backend: SQLite Session DB")
    print("=" * 70)

    stop_event = threading.Event()

    t_serial = threading.Thread(target=serial_monitor_thread, args=(stop_event,), daemon=True)
    t_queue = threading.Thread(target=backend_queue_monitor_thread, args=(stop_event,), daemon=True)

    t_serial.start()
    t_queue.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        stop_event.set()
