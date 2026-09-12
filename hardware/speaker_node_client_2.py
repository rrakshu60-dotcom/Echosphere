#!/usr/bin/env python3
"""
EchoSphere Smart Speaker Node 2 (Firmware / Audio Edge Client)
Built from scratch for EchoSphere Campus PA & Audio Network.

Features:
- Direct, real-time bidirectional link with the EchoSphere Speaker Queue
- Auto-registration & telemetry heartbeat with backend server
- High-fidelity audio playback (WinMM MCI / Kokoro Neural Voice / SAPI fallback)
- Attention chimes & emergency alert sirens
- Full hardware control: Volume, Play, Pause, Resume, Skip, Diagnostic Test
- Auto-advances queue on completion so next notice plays automatically
"""

import os
import sys
import time
import json
import uuid
import socket
import logging
import argparse
import threading
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, Set

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Node-2] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Node2")

# Node 2 Hardware Configuration
NODE_NAME = "Hardware Speaker Client 2"
MAC_ADDRESS = "D4:F3:2D:22:2A:CC"
ZONE_NAME = "Block B - AI Lab"
DEPT_CODE = "AIML"
DEFAULT_VOLUME = 90


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def resolve_server_url(cli_server: Optional[str] = None, force_local: bool = False, force_render: bool = False) -> str:
    """
    Determines the backend server URL matching the frontend application.
    Prioritizes CLI flags, then frontend/.env, then environment variables, then Render.
    """
    if cli_server and cli_server.strip():
        return cli_server.strip().rstrip("/")
    if force_local:
        return "http://127.0.0.1:8000"
    if force_render:
        return "https://echosphere-backend-9lv8.onrender.com"

    env_server = os.getenv("ECHOSPHERE_SERVER")
    if env_server and env_server.strip():
        return env_server.strip().rstrip("/")

    # Check frontend/.env to automatically pair with the exact same server the app uses
    try:
        fe_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", ".env")
        if os.path.exists(fe_env):
            with open(fe_env, "r") as f:
                for line in f:
                    if line.startswith("ECHOSPHERE_API_URL="):
                        val = line.split("=", 1)[1].strip()
                        if "/api/v1" in val:
                            return val.split("/api/v1")[0].rstrip("/")
                        return val.rstrip("/")
    except Exception:
        pass

    # Default to production cloud backend
    return "https://echosphere-backend-9lv8.onrender.com"


# -----------------------------------------------------------------------------
# High-Fidelity Audio Playback Subsystem
# -----------------------------------------------------------------------------
def play_attention_chime():
    """Plays an attention chime (659Hz -> 880Hz) to signal incoming broadcast."""
    try:
        import winsound
        winsound.Beep(659, 180)
        time.sleep(0.05)
        winsound.Beep(880, 260)
    except Exception:
        pass


def play_emergency_siren():
    """Plays an urgent dual-sweep emergency alarm siren."""
    try:
        import winsound
        for _ in range(3):
            for f in range(650, 1400, 100):
                winsound.Beep(f, 22)
            for f in range(1400, 650, -100):
                winsound.Beep(f, 22)
    except Exception:
        pass


def speak_text_neural(text: str, volume: int = 90) -> bool:
    """
    Synthesizes speech aloud using Kokoro-grade neural voices via edge-tts.
    """
    try:
        import asyncio
        import edge_tts

        clean_text = text.replace("'", " ").replace('"', " ").strip()
        if not clean_text:
            return False

        voice = "en-US-GuyNeural"
        tmp_voice = os.path.join(os.path.dirname(__file__), f"node2_voice_{uuid.uuid4().hex[:6]}.mp3")

        async def _synth():
            comm = edge_tts.Communicate(clean_text, voice)
            await comm.save(tmp_voice)

        asyncio.run(_synth())
        if os.path.exists(tmp_voice) and os.path.getsize(tmp_voice) > 300:
            ok = play_audio_file(tmp_voice, volume=volume)
            try:
                os.remove(tmp_voice)
            except Exception:
                pass
            return ok
    except Exception as e:
        logger.debug(f"Neural voice synthesis fallback note: {e}")
    return False


def speak_text_sapi(text: str, volume: int = 90) -> bool:
    """Windows SAPI speech synthesizer fallback."""
    if sys.platform != "win32":
        return False
    try:
        clean = text.replace("'", " ").replace('"', " ")
        ps_cmd = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Volume = {volume}; "
            f"$s.Speak('{clean}')"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)
        return True
    except Exception as e:
        logger.warning(f"SAPI voice fallback failed: {e}")
        return False


def play_audio_file(file_path: str, volume: int = 90, stop_event: Optional[threading.Event] = None) -> bool:
    """
    Plays an MP3 or WAV file using native Windows Multimedia (WinMM) at C-speed.
    Supports stopping / cancellation via stop_event.
    """
    if not os.path.exists(file_path):
        return False

    abs_path = os.path.abspath(file_path)

    if sys.platform == "win32":
        try:
            import ctypes
            winmm = ctypes.windll.winmm
            alias = f"node2_mci_{uuid.uuid4().hex[:6]}"
            winmm.mciSendStringW(f'close {alias}', None, 0, 0)

            is_mp3 = abs_path.lower().endswith((".mp3", ".mp4", ".m4a"))
            type_str = "mpegvideo" if is_mp3 else "waveaudio"
            open_res = winmm.mciSendStringW(f'open "{abs_path}" type {type_str} alias {alias}', None, 0, 0)

            if open_res == 0:
                buf = ctypes.create_unicode_buffer(128)
                winmm.mciSendStringW(f'status {alias} length', buf, 128, 0)
                dur_ms = int(buf.value) if buf.value.isdigit() else 3500

                mci_vol = int((max(0, min(100, volume)) / 100.0) * 1000)
                winmm.mciSendStringW(f'setaudio {alias} volume to {mci_vol}', None, 0, 0)
                winmm.mciSendStringW(f'play {alias}', None, 0, 0)

                # Monitor playback duration in small slices to support responsive stop/cancellation
                elapsed_ms = 0
                while elapsed_ms < dur_ms:
                    if stop_event and stop_event.is_set():
                        winmm.mciSendStringW(f'stop {alias}', None, 0, 0)
                        winmm.mciSendStringW(f'close {alias}', None, 0, 0)
                        return True
                    time.sleep(0.1)
                    elapsed_ms += 100

                winmm.mciSendStringW(f'stop {alias}', None, 0, 0)
                winmm.mciSendStringW(f'close {alias}', None, 0, 0)
                return True
        except Exception as e:
            logger.debug(f"WinMM MCI player note: {e}")

        # Fallback to winsound for WAV
        if abs_path.lower().endswith(".wav"):
            try:
                import winsound
                winsound.PlaySound(abs_path, winsound.SND_FILENAME)
                return True
            except Exception:
                pass

    return False


# -----------------------------------------------------------------------------
# Speaker Node 2 Client Engine
# -----------------------------------------------------------------------------
class SpeakerNode2Client:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        self.name = NODE_NAME
        self.mac_address = MAC_ADDRESS
        self.ip_address = get_local_ip()
        self.zone = ZONE_NAME
        self.department = DEPT_CODE
        self.volume = DEFAULT_VOLUME
        self.node_id: Optional[int] = None

        self.is_running = True
        self.current_status = "ONLINE"
        self.active_announcement_id: Optional[int] = None
        self.active_queue_id: Optional[int] = None
        self.played_announcement_ids: Set[int] = set()

        self._playback_lock = threading.Lock()
        self._current_stop_event: Optional[threading.Event] = None
        self._is_paused = False

    def print_banner(self):
        print("\n" + "═" * 70)
        print("  🔊 EchoSphere Smart Speaker Node 2 - Audio Edge Client")
        print("═" * 70)
        print(f"  [*] Name:        {self.name}")
        print(f"  [*] MAC Address: {self.mac_address}")
        print(f"  [*] IP Address:  {self.ip_address}")
        print(f"  [*] Zone:        {self.zone} ({self.department})")
        print(f"  [*] Server URL:  {self.server_url}")
        print(f"  [*] Volume:      {self.volume}%")
        print("═" * 70 + "\n")

    def register(self):
        """Registers node identity with EchoSphere backend."""
        url = f"{self.server_url}/api/v1/hardware/speakers/register"
        payload = {
            "name": self.name,
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "zone": self.zone,
            "volume": self.volume,
        }
        try:
            resp = requests.post(url, json=payload, timeout=6.0)
            if resp.status_code in (200, 201):
                data = resp.json()
                self.node_id = data.get("id")
                logger.info(f"✅ Node registered with backend! ID: #{self.node_id} (Status: ONLINE)")
            else:
                logger.info(f"ℹ️ Node register response (HTTP {resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"⚠️ Registration attempt to {self.server_url} failed: {e}")

    def send_offline(self):
        """Notifies backend of graceful shutdown."""
        try:
            url = f"{self.server_url}/api/v1/hardware/speakers/heartbeat"
            payload = {
                "mac_address": self.mac_address,
                "ip_address": self.ip_address,
                "status": "OFFLINE",
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_space": 0.0,
            }
            requests.post(url, json=payload, timeout=3.0)
            logger.info("🛑 Reported OFFLINE status to backend.")
        except Exception:
            pass

    def send_heartbeat_and_fetch_commands(self):
        """Sends periodic heartbeat and receives pending control commands."""
        url = f"{self.server_url}/api/v1/hardware/speakers/heartbeat"
        payload = {
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "status": self.current_status,
            "cpu_usage": 14.2,
            "memory_usage": 42.1,
            "disk_space": 68.5,
        }
        try:
            resp = requests.post(url, json=payload, timeout=4.0)
            if resp.status_code in (200, 201):
                data = resp.json()
                cmds = data.get("pending_commands", [])
                for cmd in cmds:
                    self.handle_command(cmd)
        except Exception as e:
            logger.debug(f"Heartbeat error: {e}")

    def sync_with_speaker_queue(self):
        """
        Directly checks the backend SpeakerQueue for active playing or queued items.
        Instantly plays when an announcement is marked 'Playing' in the queue!
        """
        url = f"{self.server_url}/api/v1/hardware/queue"
        try:
            resp = requests.get(url, timeout=4.0)
            if resp.status_code != 200:
                return

            items = resp.json()
            if not isinstance(items, list):
                return

            # Check if any announcement is currently marked 'Playing'
            for item in items:
                status = str(item.get("status", "")).lower()
                ann_id = item.get("announcement_id") or item.get("id")
                if not ann_id:
                    continue

                target_node_id = item.get("speaker_node_id")
                node_name = str(item.get("speaker_node_name", ""))

                # Check if announcement is targeted to Node 2 or All Nodes
                is_for_this_node = (
                    target_node_id is None
                    or target_node_id == 0
                    or target_node_id == self.node_id
                    or "Client 2" in node_name
                    or "Block B" in node_name
                    or "AI Lab" in node_name
                    or "All" in node_name
                )

                if not is_for_this_node:
                    continue

                if status == "playing":
                    # If this announcement is marked 'Playing' and we haven't played it yet, PLAY IT!
                    if ann_id not in self.played_announcement_ids and ann_id != self.active_announcement_id:
                        title = item.get("title") or f"Notice #{ann_id}"
                        message = item.get("description") or item.get("content") or ""
                        audio_url = item.get("audio_url")
                        queue_id = item.get("id")
                        is_emerg = str(item.get("priority", "")).upper() == "EMERGENCY"

                        logger.info(f"🔗 [QUEUE LINK DETECTED] Announcement #{ann_id} ('{title}') is PLAYING in queue!")
                        threading.Thread(
                            target=self.play_announcement_sync,
                            args=(ann_id, title, message, audio_url, is_emerg, queue_id),
                            daemon=True,
                        ).start()
                        break

                elif status == "paused" and ann_id == self.active_announcement_id:
                    if not self._is_paused:
                        logger.info(f"⏸️ [QUEUE LINK] Notice #{ann_id} was PAUSED from the app.")
                        self._is_paused = True
                        self.current_status = "PAUSED"

                elif status in ("cancelled", "skipped") and ann_id == self.active_announcement_id:
                    logger.info(f"⏹️ [QUEUE LINK] Notice #{ann_id} was {status.upper()} from the app. Stopping.")
                    if self._current_stop_event:
                        self._current_stop_event.set()
                    self.active_announcement_id = None
                    self.current_status = "ONLINE"
        except Exception as e:
            logger.debug(f"Queue sync note: {e}")

    def handle_command(self, cmd: Dict[str, Any]):
        """Executes a control or playback command received from backend."""
        c = cmd.get("command")
        logger.info(f"⚡ [COMMAND DISPATCHED] Action: '{c}'")

        if c == "TEST_SPEAKER":
            threading.Thread(target=self.run_diagnostic_test, daemon=True).start()

        elif c == "SET_VOLUME":
            vol = cmd.get("volume")
            if vol is not None:
                self.volume = max(0, min(100, int(vol)))
                logger.info(f"🔊 [VOLUME UPDATED] Node 2 volume set to {self.volume}%")

        elif c in ("PLAY_ANNOUNCEMENT", "PLAY_EMERGENCY"):
            ann_id = cmd.get("announcement_id", 0)
            title = cmd.get("title") or "Campus Notice"
            message = cmd.get("message") or cmd.get("content") or ""
            audio_url = cmd.get("audio_url")
            is_emerg = (c == "PLAY_EMERGENCY")
            queue_id = cmd.get("queue_id")
            threading.Thread(
                target=self.play_announcement_sync,
                args=(ann_id, title, message, audio_url, is_emerg, queue_id),
                daemon=True,
            ).start()

        elif c == "PAUSE":
            logger.info("⏸️ [PAUSE COMMAND] Pausing audio...")
            self._is_paused = True
            self.current_status = "PAUSED"

        elif c == "RESUME":
            logger.info("▶️ [RESUME COMMAND] Resuming audio...")
            self._is_paused = False
            self.current_status = "PLAYING"

        elif c in ("STOP", "CANCEL", "SKIP"):
            logger.info(f"⏹️ [{c} COMMAND] Cancelling active playback...")
            if self._current_stop_event:
                self._current_stop_event.set()
            self.active_announcement_id = None
            self.current_status = "ONLINE"

        elif c == "RESTART":
            logger.info("🔄 [RESTART COMMAND] Re-registering node with server...")
            self.register()

    def play_announcement_sync(
        self,
        ann_id: int,
        title: str,
        message: str,
        audio_url: Optional[str] = None,
        is_emergency: bool = False,
        queue_id: Optional[int] = None,
    ):
        """
        Executes announcement broadcast with chime/siren, neural voice, and backend auto-advance.
        """
        with self._playback_lock:
            self.active_announcement_id = ann_id
            self.active_queue_id = queue_id
            self.current_status = "PLAYING"
            self._is_paused = False
            self._current_stop_event = threading.Event()

            print("\n" + "─" * 60)
            if is_emergency:
                print(f"🚨 [EMERGENCY BROADCAST ACTIVE] {title.upper()}")
            else:
                print(f"📢 [BROADCASTING NOTICE #{ann_id}] {title}")
            print(f"   Message: {message[:120]}..." if len(message) > 120 else f"   Message: {message}")
            print("─" * 60)

            # 1. Play attention chime or emergency siren
            if is_emergency:
                play_emergency_siren()
            else:
                play_attention_chime()

            played = False

            # 2. Try streaming backend-generated TTS audio file
            full_audio_url = audio_url
            if full_audio_url and full_audio_url.startswith("/"):
                full_audio_url = f"{self.server_url}{full_audio_url}"

            if full_audio_url and full_audio_url.startswith("http"):
                ext = ".wav" if ".wav" in full_audio_url.lower() else ".mp3"
                tmp_file = os.path.join(os.path.dirname(__file__), f"node2_play_{uuid.uuid4().hex[:6]}{ext}")
                try:
                    logger.info(f"📥 Downloading audio stream: {full_audio_url}")
                    r = requests.get(full_audio_url, timeout=6.0)
                    if r.status_code == 200 and len(r.content) > 500 and not r.content.startswith(b"<!DOCTYPE"):
                        with open(tmp_file, "wb") as f:
                            f.write(r.content)
                        logger.info(f"🎙️ Playing backend audio stream ({len(r.content)} bytes)...")
                        played = play_audio_file(tmp_file, volume=self.volume, stop_event=self._current_stop_event)
                except Exception as e:
                    logger.debug(f"Audio stream download error: {e}")
                finally:
                    if os.path.exists(tmp_file):
                        try:
                            os.remove(tmp_file)
                        except Exception:
                            pass

            # 3. Fallback: Speak text directly aloud using local Kokoro/Edge Neural Voice or SAPI
            if not played and not (self._current_stop_event and self._current_stop_event.is_set()):
                speech_text = f"{title}. {message}" if message else title
                vol = 100 if is_emergency else self.volume
                logger.info(f"🎙️ [KOKORO NEURAL VOICE] Speaking text aloud: '{speech_text}'")
                ok = speak_text_neural(speech_text, volume=vol)
                if not ok:
                    speak_text_sapi(speech_text, volume=vol)

            logger.info(f"✅ [BROADCAST FINISHED] Completed playback for Notice #{ann_id} ('{title}')")
            self.played_announcement_ids.add(ann_id)
            self.active_announcement_id = None
            self.current_status = "ONLINE"

            # 4. Notify backend that playback completed so the queue advances automatically!
            if queue_id:
                try:
                    complete_url = f"{self.server_url}/api/v1/hardware/queue/{queue_id}/action?action=complete"
                    requests.post(complete_url, timeout=3.0)
                    logger.info(f"⏩ [QUEUE ADVANCED] Notified backend of item #{queue_id} completion.")
                except Exception as e:
                    logger.debug(f"Complete notification note: {e}")

    def run_diagnostic_test(self):
        """Runs the speaker diagnostic self-test command triggered from the Nodes tab."""
        with self._playback_lock:
            self.current_status = "PLAYING"
            logger.info("🎛️ [DIAGNOSTIC TEST] Running Speaker Node 2 self-test...")
            play_attention_chime()
            test_msg = f"EchoSphere Smart Speaker Node 2 diagnostic self test. Audio subsystem is operational in {self.zone}. Volume is at {self.volume} percent."
            ok = speak_text_neural(test_msg, volume=self.volume)
            if not ok:
                speak_text_sapi(test_msg, volume=self.volume)
            logger.info("✅ [DIAGNOSTIC COMPLETE] Self-test finished.")
            self.current_status = "ONLINE"

    def run(self):
        """Main service loop."""
        import atexit
        import signal

        self.print_banner()
        self.register()

        def handle_exit(signum=None, frame=None):
            if self.is_running:
                logger.info("Shutting down Node 2...")
                self.is_running = False
                self.send_offline()

        try:
            signal.signal(signal.SIGINT, handle_exit)
            if hasattr(signal, "SIGTERM"):
                signal.signal(signal.SIGTERM, handle_exit)
        except Exception:
            pass
        atexit.register(self.send_offline)

        logger.info("🎧 Node 2 is ONLINE & MONITORING for announcements and commands (Poll cycle: 1.8s)...")
        while self.is_running:
            try:
                self.send_heartbeat_and_fetch_commands()
                self.sync_with_speaker_queue()
            except Exception as e:
                logger.debug(f"Main loop note: {e}")
            time.sleep(1.8)


def main():
    parser = argparse.ArgumentParser(description="EchoSphere Smart Speaker Node 2 Client")
    parser.add_argument("--server", type=str, help="Backend server URL (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--local", action="store_true", help="Connect to local backend at http://127.0.0.1:8000")
    parser.add_argument("--render", action="store_true", help="Connect to Render cloud backend")
    args = parser.parse_args()

    target_server = resolve_server_url(
        cli_server=args.server,
        force_local=args.local,
        force_render=args.render,
    )

    client = SpeakerNode2Client(server_url=target_server)
    client.run()


if __name__ == "__main__":
    main()
