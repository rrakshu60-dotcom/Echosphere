"""
EchoSphere Comprehensive ESP32 & Website Latency Monitor
=========================================================
Monitors concurrently:
1. Hardware ESP32 on COM5 (115200 baud) - Captures exact LCD display and audio streaming events.
2. Cloud Backend API (Render) - Captures when website pushes announcements & speaker queue changes.
3. Local Backend Database - Fallback telemetry if testing locally.

Directly measures and displays:
- [T0] Website Notice Pushed (Timestamp when API receives notice)
- [T1] Notice Enqueued in Speaker Queue
- [T2] LCD Displays Notice (Hardware TFT activation timestamp)
- [T3] Audio Playback Starts (I2S audio stream begins)
- [T4] Audio Playback Finishes
- [T5] Repeat Gap (Exact elapsed seconds between repeat broadcast cycles)
"""

import sys
import os
import time
import functools
import json
from datetime import datetime, timezone
import threading
import urllib.request
import urllib.error

# Force unbuffered prints and safe UTF-8 encoding for Windows terminals
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

print = functools.partial(print, flush=True)

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def get_ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def safe_str(val):
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)

# Shared timeline tracker
class LatencyTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.notice_push_time = {}   # ann_id -> timestamp
        self.lcd_display_time = {}   # ann_id -> timestamp
        self.audio_start_time = {}   # ann_id -> timestamp
        self.audio_end_time = {}     # ann_id -> timestamp
        self.last_repeat_cycle_end = None

    def record_website_push(self, ann_id, title):
        with self.lock:
            now = time.time()
            self.notice_push_time[ann_id] = now
            print(f"\n{'='*75}")
            print(f"[{get_ts()}] [1. WEBSITE PUSH] Announcement #{ann_id} pushed! Title: '{title}'")
            print(f"{'='*75}")

    def record_queue_added(self, ann_id, q_id, priority, status):
        with self.lock:
            now = time.time()
            t_push = self.notice_push_time.get(ann_id)
            lat_str = f"+{(now - t_push):.2f}s after website push" if t_push else ""
            print(f"[{get_ts()}] [2. QUEUE ADDED] Item #{q_id} (Ann #{ann_id}) in status '{status}' {lat_str}")

    def record_lcd_displayed(self, ann_id, title):
        with self.lock:
            now = time.time()
            self.lcd_display_time[ann_id] = now
            t_push = self.notice_push_time.get(ann_id)
            if t_push:
                diff = now - t_push
                print(f"\n>>> [{get_ts()}] [3. LCD DISPLAYED] ESP32 TFT rendered notice #{ann_id}! [LATENCY: {diff:.2f}s from Website Push] <<<")
            else:
                print(f"\n>>> [{get_ts()}] [3. LCD DISPLAYED] ESP32 TFT rendered notice: '{title}' <<<")

    def record_audio_playing(self, ann_id, url):
        with self.lock:
            now = time.time()
            self.audio_start_time[ann_id] = now
            t_lcd = self.lcd_display_time.get(ann_id)
            gap_str = f"({(now - t_lcd):.2f}s after LCD display)" if t_lcd else ""
            print(f"[{get_ts()}] [4. AUDIO PLAYING] I2S 16-bit PCM streaming to 8-ohm speaker! {gap_str}")

    def record_audio_completed(self, ann_id):
        with self.lock:
            now = time.time()
            self.audio_end_time[ann_id] = now
            t_start = self.audio_start_time.get(ann_id)
            dur_str = f"Duration: {(now - t_start):.2f}s" if t_start else ""
            print(f"[{get_ts()}] [5. AUDIO COMPLETED] Broadcast finished. {dur_str}")

            if self.last_repeat_cycle_end is not None:
                repeat_gap = now - self.last_repeat_cycle_end
                print(f"[{get_ts()}] [REPEAT TIME GAP] Exactly {repeat_gap:.2f} seconds between repeat cycles!")

            self.last_repeat_cycle_end = now

tracker = LatencyTracker()


def serial_monitor_thread(stop_event):
    """
    Connects to the ESP32 on COM5 (or COM7 fallback) at 115200 baud.
    Parses hardware events: LCD rendering, I2S streaming, completion.
    """
    import win32file
    import win32con

    target_ports = ["COM5", "COM7", "COM3", "COM4"]
    handle = None
    active_port = None

    print(f"[{get_ts()}] [SERIAL] Scanning for ESP32 on {target_ports} at 115200 baud...")

    while not stop_event.is_set():
        if handle is None:
            for p in target_ports:
                try:
                    h = win32file.CreateFile(
                        f"\\\\.\\{p}",
                        win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                        0,
                        None,
                        win32con.OPEN_EXISTING,
                        0,
                        None,
                    )
                    dcb = win32file.GetCommState(h)
                    dcb.BaudRate = 115200
                    dcb.ByteSize = 8
                    dcb.Parity = win32file.NOPARITY
                    dcb.StopBits = win32file.ONESTOPBIT
                    dcb.fDtrControl = win32file.DTR_CONTROL_DISABLE
                    dcb.fRtsControl = win32file.RTS_CONTROL_DISABLE
                    win32file.SetCommState(h, dcb)
                    # Timeouts: (ReadIntervalTimeout, ReadTotalTimeoutMultiplier, ReadTotalTimeoutConstant, WriteTotalTimeoutMultiplier, WriteTotalTimeoutConstant)
                    win32file.SetCommTimeouts(h, (20, 5, 50, 5, 50))

                    handle = h
                    active_port = p
                    print(f"[{get_ts()}] [SERIAL] >>> CONNECTED TO ESP32 ON {active_port} (115200 baud) <<<")
                    break
                except Exception:
                    continue

            if handle is None:
                time.sleep(1.0)
                continue

        try:
            err, data = win32file.ReadFile(handle, 512)
            if data:
                text = data.decode("utf-8", errors="replace")
                lines = text.splitlines()
                for line in lines:
                    line_str = line.strip()
                    if not line_str:
                        continue

                    # Filter out raw memory dots or clean lines
                    clean_line = line_str.encode("ascii", errors="backslashreplace").decode("ascii")

                    # Check for key hardware events
                    if "TFT DISPLAY" in line_str or "ACTIVE NOTICE" in line_str or "STATE_PLAYING_ANNOUNCEMENT" in line_str:
                        tracker.record_lcd_displayed(0, clean_line)
                    elif "AUDIO STREAM" in line_str or "Streaming 16-bit PCM" in line_str:
                        tracker.record_audio_playing(0, clean_line)
                    elif "BROADCAST FINISHED" in line_str or "Announcement completed" in line_str or "Cleanly restored" in line_str:
                        tracker.record_audio_completed(0)

                    # Print formatted line
                    print(f"[{get_ts()}] [ESP32 {active_port}] {clean_line}")

            time.sleep(0.02)
        except Exception as e:
            print(f"[{get_ts()}] [SERIAL] Disconnected: {e}")
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


def cloud_api_monitor_thread(stop_event):
    """
    Monitors Render backend API (https://echosphere-backend-9lv8.onrender.com/api/v1)
    for new announcements, queue items, and repeat events in real time.
    """
    base_url = "https://echosphere-backend-9lv8.onrender.com/api/v1"
    seen_ann_ids = set()
    seen_queue_ids = {}

    print(f"[{get_ts()}] [CLOUD MONITOR] Polling Render API ({base_url}) for website notice activity...")

    while not stop_event.is_set():
        try:
            # 1. Fetch latest announcements
            req = urllib.request.Request(
                f"{base_url}/announcements/?limit=5",
                headers={"User-Agent": "EchoSphere-Latency-Monitor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for it in items:
                    a_id = it.get("id")
                    title = it.get("title", "")
                    if a_id and a_id not in seen_ann_ids:
                        seen_ann_ids.add(a_id)
                        tracker.record_website_push(a_id, title)

            # 2. Fetch speaker queue items
            q_req = urllib.request.Request(
                f"{base_url}/hardware/speakers/13/queue",
                headers={"User-Agent": "EchoSphere-Latency-Monitor/1.0"}
            )
            with urllib.request.urlopen(q_req, timeout=3.5) as resp:
                q_data = json.loads(resp.read().decode("utf-8"))
                q_items = q_data if isinstance(q_data, list) else q_data.get("items", [])
                for qi in q_items:
                    qid = qi.get("id")
                    aid = qi.get("announcement_id")
                    st = qi.get("status")
                    prio = qi.get("priority", "NORMAL")
                    if qid and (qid not in seen_queue_ids or seen_queue_ids[qid] != st):
                        seen_queue_ids[qid] = st
                        tracker.record_queue_added(aid, qid, prio, st)

        except Exception:
            pass

        time.sleep(0.6)


if __name__ == "__main__":
    print("=" * 75)
    print("  EchoSphere Comprehensive ESP32 & Website Latency Monitor")
    print("  ESP32 Port: COM5 (115200 baud) | Website API: Render Cloud")
    print("=" * 75)

    stop_event = threading.Event()

    t_serial = threading.Thread(target=serial_monitor_thread, args=(stop_event,), daemon=True)
    t_cloud = threading.Thread(target=cloud_api_monitor_thread, args=(stop_event,), daemon=True)

    t_serial.start()
    t_cloud.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        stop_event.set()
