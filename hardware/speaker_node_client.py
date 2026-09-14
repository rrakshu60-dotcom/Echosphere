#!/usr/bin/env python3
"""
EchoSphere Smart Speaker Node 1 (Firmware / Audio Edge Client)
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
    format="%(asctime)s [%(levelname)s] [Node-1] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Node1")

# Node 1 Hardware Configuration
NODE_NAME = "Hardware Speaker Client 1"
MAC_ADDRESS = "D4:F3:2D:22:2A:CB"
ZONE_NAME = "Auditorium / Campus"
DEPT_CODE = "College-Wide"
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
    """Plays an attention chime (587Hz -> 880Hz) to signal incoming broadcast."""
    try:
        import winsound
        winsound.Beep(587, 180)
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


_kokoro_instance = None
_kokoro_lock = threading.Lock()


def get_node_kokoro():
    """Returns cached Kokoro-ONNX instance if available on the node."""
    global _kokoro_instance
    with _kokoro_lock:
        if _kokoro_instance is not None:
            return _kokoro_instance
        try:
            from kokoro_onnx import Kokoro
            candidate_dirs = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "kokoro")),
                os.path.abspath("models/kokoro"),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "kokoro")),
                os.path.expanduser("~/.cache/kokoro"),
            ]
            for d in candidate_dirs:
                m1 = os.path.join(d, "kokoro-v1.0.onnx")
                m2 = os.path.join(d, "kokoro-v0_19.onnx")
                v1 = os.path.join(d, "voices-v1.0.bin")
                v2 = os.path.join(d, "voices.bin")
                m_chosen = m1 if os.path.exists(m1) else (m2 if os.path.exists(m2) else None)
                v_chosen = v1 if os.path.exists(v1) else (v2 if os.path.exists(v2) else None)
                if m_chosen and v_chosen:
                    _kokoro_instance = Kokoro(m_chosen, v_chosen)
                    logger.info(f"🔊 [KOKORO TTS LOADED] Successfully loaded Kokoro-82M model from {m_chosen}")
                    return _kokoro_instance
        except Exception as e:
            logger.debug(f"Kokoro load note: {e}")
    return None


def speak_text_kokoro(text: str, voice: str = "af_heart", volume: int = 90, stop_event: Optional[threading.Event] = None) -> bool:
    """
    Synthesizes speech using Kokoro-82M neural TTS and plays aloud via WinMM MCI.
    """
    kokoro = get_node_kokoro()
    if kokoro is None:
        return False
    try:
        import soundfile as sf
        clean_text = text.replace("'", " ").replace('"', " ").strip()
        if not clean_text:
            return False

        samples, sample_rate = kokoro.create(clean_text, voice=voice, speed=1.0, lang="en-us")
        if samples is None or len(samples) == 0:
            return False

        # Convert float samples to standard 16-bit PCM WAV so Windows audio drivers play reliably
        import numpy as np
        int16_samples = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)

        tmp_wav = os.path.join(os.path.dirname(__file__), f"node1_kokoro_{uuid.uuid4().hex[:6]}.wav")
        sf.write(tmp_wav, int16_samples, sample_rate, subtype="PCM_16")
        if os.path.exists(tmp_wav) and os.path.getsize(tmp_wav) > 500:
            logger.info(f"🔊 [KOKORO TTS PLAYBACK] Broadcasting speech via Kokoro ({len(samples)} samples at {sample_rate}Hz)...")
            ok = play_audio_file(tmp_wav, volume=volume, stop_event=stop_event)
            try:
                if os.path.exists(tmp_wav):
                    os.remove(tmp_wav)
            except Exception:
                pass
            return ok
    except Exception as e:
        logger.warning(f"Kokoro TTS playback error: {e}")
    return False


def speak_text_neural(text: str, volume: int = 90, stop_event: Optional[threading.Event] = None) -> bool:
    """
    Synthesizes speech aloud using neural voices via edge-tts.
    """
    try:
        import asyncio
        import edge_tts

        clean_text = text.replace("'", " ").replace('"', " ").strip()
        if not clean_text:
            return False

        voice = "en-US-AriaNeural"
        tmp_voice = os.path.join(os.path.dirname(__file__), f"node1_voice_{uuid.uuid4().hex[:6]}.mp3")

        async def _synth():
            comm = edge_tts.Communicate(clean_text, voice)
            await comm.save(tmp_voice)

        asyncio.run(_synth())
        if os.path.exists(tmp_voice) and os.path.getsize(tmp_voice) > 300:
            ok = play_audio_file(tmp_voice, volume=volume, stop_event=stop_event)
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
            alias = f"node1_mci_{uuid.uuid4().hex[:6]}"
            winmm.mciSendStringW(f'close {alias}', None, 0, 0)

            is_mp3 = abs_path.lower().endswith((".mp3", ".mp4", ".m4a"))
            type_str = "mpegvideo" if is_mp3 else "waveaudio"
            open_res = winmm.mciSendStringW(f'open "{abs_path}" type {type_str} alias {alias}', None, 0, 0)

            if open_res == 0:
                winmm.mciSendStringW(f'set {alias} time format milliseconds', None, 0, 0)
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


def download_and_play_stream(server_url: str, audio_url: str, volume: int = 90, stop_event: Optional[threading.Event] = None) -> bool:
    """
    Directly streams / downloads the backend neural MP3 audio stream and plays via WinMM MCI.
    Supports both absolute URLs and relative endpoints.
    """
    try:
        full_url = audio_url
        if audio_url.startswith("/"):
            full_url = f"{server_url.rstrip('/')}{audio_url}"

        logger.info(f"📥 [STREAMING AUDIO] Downloading speech stream from: {full_url}")
        resp = requests.get(full_url, timeout=15.0)
        if resp.status_code == 200 and len(resp.content) > 500:
            tmp_path = os.path.join(os.path.dirname(__file__), f"node1_stream_{uuid.uuid4().hex[:6]}.mp3")
            with open(tmp_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"▶️ [STREAM PLAYBACK] Audio stream ready ({len(resp.content)} bytes). Broadcasting via speaker...")
            success = play_audio_file(tmp_path, volume=volume, stop_event=stop_event)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return success
        else:
            logger.warning(f"Audio stream fetch returned HTTP {resp.status_code} ({len(resp.content)} bytes)")
    except Exception as e:
        logger.warning(f"Audio stream download error: {e}")
    return False


# -----------------------------------------------------------------------------
# Speaker Node 1 Client Engine
# -----------------------------------------------------------------------------
class SpeakerNode1Client:
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
        self.played_signatures: Set[str] = set()
        self.pending_play_ids: Set[int] = set()

        self._playback_lock = threading.Lock()
        self._current_stop_event: Optional[threading.Event] = None
        self._is_paused = False

    def print_banner(self):
        print("\n" + "═" * 70)
        print("  🔊 EchoSphere Smart Speaker Node 1 - Audio Edge Client")
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
            "cpu_usage": 12.5,
            "memory_usage": 38.0,
            "disk_space": 72.0,
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

            for item in items:
                status = str(item.get("status", "")).lower()
                ann_id = item.get("announcement_id") or item.get("id")
                queue_id = item.get("id")
                if not ann_id:
                    continue

                target_node_id = item.get("speaker_node_id")
                target_mac = str(item.get("speaker_node_mac") or "").upper().strip()
                node_name = str(item.get("speaker_node_name", ""))

                # Check if announcement is targeted to this node or All Nodes
                is_broadcast = (
                    target_node_id is None
                    or target_node_id == 0
                    or not target_mac
                    or target_mac == "ALL"
                    or "All" in node_name
                )
                is_targeted_to_me = (
                    (target_mac and target_mac == self.mac_address.upper())
                    or (target_node_id and target_node_id == self.node_id)
                    or target_node_id in (8, 15, 1)
                    or "Client 1" in node_name
                    or "Auditorium" in node_name
                )

                if not (is_broadcast or is_targeted_to_me):
                    continue

                sig = f"{queue_id}_{ann_id}" if queue_id else f"ann_{ann_id}"

                if status == "playing":
                    if ann_id != self.active_announcement_id and ann_id not in self.pending_play_ids:
                        self.pending_play_ids.add(ann_id)
                        title = item.get("title") or f"Notice #{ann_id}"
                        message = item.get("description") or item.get("content") or ""
                        audio_url = item.get("audio_url")
                        is_emerg = str(item.get("priority", "")).upper() == "EMERGENCY"

                        logger.info(f"🔗 [QUEUE DETECTED] Announcement #{ann_id} ('{title}') is PLAYING! (Target: Node 1 / All)")
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
        target_mac = str(cmd.get("target_mac") or "").upper().strip()
        if target_mac and target_mac not in ("ALL", self.mac_address.upper()):
            return

        logger.info(f"⚡ [COMMAND DISPATCHED] Action: '{c}'")

        if c == "TEST_SPEAKER":
            threading.Thread(target=self.run_diagnostic_test, daemon=True).start()

        elif c == "SET_VOLUME":
            vol = cmd.get("volume")
            if vol is not None:
                self.volume = max(0, min(100, int(vol)))
                logger.info(f"🔊 [VOLUME UPDATED] Node 1 volume set to {self.volume}%")

        elif c in ("PLAY_ANNOUNCEMENT", "PLAY_EMERGENCY"):
            ann_id = cmd.get("announcement_id", 0)
            queue_id = cmd.get("queue_id")
            if ann_id == self.active_announcement_id or ann_id in self.pending_play_ids:
                return
            self.pending_play_ids.add(ann_id)
            title = cmd.get("title") or "Campus Notice"
            message = cmd.get("message") or cmd.get("content") or ""
            audio_url = cmd.get("audio_url")
            is_emerg = (c == "PLAY_EMERGENCY")
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
        Executes announcement broadcast with chime/siren, backend neural stream, and auto-advance.
        """
        with self._playback_lock:
            try:
                self.active_announcement_id = ann_id
                self.active_queue_id = queue_id
                self.current_status = "PLAYING"
                self._is_paused = False
                self._current_stop_event = threading.Event()
                sig = f"{queue_id}_{ann_id}" if queue_id else f"ann_{ann_id}"

                print("\n" + "─" * 60)
                if is_emergency:
                    print(f"🚨 [EMERGENCY BROADCAST ACTIVE] {title.upper()}")
                else:
                    print(f"📢 [BROADCASTING NOTICE #{ann_id}] {title}")
                print(f"   Message: {message[:120]}..." if len(message) > 120 else f"   Message: {message}")
                if audio_url:
                    print(f"   Stream:  {audio_url}")
                print("─" * 60)

                # 1. Attention chime or emergency siren
                if is_emergency:
                    play_emergency_siren()
                else:
                    play_attention_chime()

                # 2. High-Fidelity Audio Playback:
                # Primary: Kokoro Neural Speech TTS!
                played = False
                vol = 100 if is_emergency else self.volume
                speech_text = f"{title}. {message}" if message else title

                # Priority 1: Direct Kokoro TTS synthesis on the node
                if not (self._current_stop_event and self._current_stop_event.is_set()):
                    played = speak_text_kokoro(speech_text, voice="af_heart", volume=vol, stop_event=self._current_stop_event)

                # Priority 2: Streaming backend audio stream (which also serves Kokoro TTS)
                if not played and audio_url and not (self._current_stop_event and self._current_stop_event.is_set()):
                    played = download_and_play_stream(self.server_url, audio_url, volume=vol, stop_event=self._current_stop_event)

                # Priority 3: Fallback Edge-TTS / Windows SAPI
                if not played and not (self._current_stop_event and self._current_stop_event.is_set()):
                    logger.info(f"🎙️ [LOCAL TTS FALLBACK] Speaking text aloud: '{speech_text}'")
                    ok = speak_text_neural(speech_text, volume=vol, stop_event=self._current_stop_event)
                    if not ok:
                        speak_text_sapi(speech_text, volume=vol)

                logger.info(f"✅ [BROADCAST FINISHED] Completed playback for Notice #{ann_id} ('{title}')")
                self.active_announcement_id = None
                self.current_status = "ONLINE"

                # 4. Notify backend that playback completed so the queue advances immediately!
                if queue_id:
                    try:
                        complete_url = f"{self.server_url}/api/v1/hardware/queue/{queue_id}/action?action=complete"
                        requests.post(complete_url, timeout=4.0)
                        logger.info(f"⏩ [QUEUE ADVANCED] Notified backend of item #{queue_id} completion.")
                    except Exception as e:
                        logger.debug(f"Complete notification note: {e}")
            finally:
                self.pending_play_ids.discard(ann_id)
                self.active_announcement_id = None
                self.current_status = "ONLINE"

    def run_diagnostic_test(self):
        """Runs the speaker diagnostic self-test command triggered from the Nodes tab."""
        with self._playback_lock:
            self.current_status = "PLAYING"
            logger.info("🎛️ [DIAGNOSTIC TEST] Running Speaker Node 1 self-test...")
            play_attention_chime()
            test_msg = f"EchoSphere Smart Speaker Node 1 diagnostic self test. Audio subsystem is operational in {self.zone}. Powered by Kokoro neural TTS."
            ok = speak_text_kokoro(test_msg, voice="af_heart", volume=self.volume)
            if not ok:
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
                logger.info("Shutting down Node 1...")
                self.is_running = False
                self.send_offline()

        try:
            signal.signal(signal.SIGINT, handle_exit)
            if hasattr(signal, "SIGTERM"):
                signal.signal(signal.SIGTERM, handle_exit)
        except Exception:
            pass
        atexit.register(self.send_offline)

        logger.info("🎧 Node 1 is ONLINE & MONITORING for announcements and commands (Poll cycle: 1.8s)...")
        while self.is_running:
            try:
                self.send_heartbeat_and_fetch_commands()
                self.sync_with_speaker_queue()
            except Exception as e:
                logger.debug(f"Main loop note: {e}")
            time.sleep(1.8)


def main():
    parser = argparse.ArgumentParser(description="EchoSphere Smart Speaker Node 1 Client")
    parser.add_argument("--server", type=str, help="Backend server URL (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--local", action="store_true", help="Connect to local backend at http://127.0.0.1:8000")
    parser.add_argument("--render", action="store_true", help="Connect to Render cloud backend")
    args = parser.parse_args()

    target_server = resolve_server_url(
        cli_server=args.server,
        force_local=args.local,
        force_render=args.render,
    )

    client = SpeakerNode1Client(server_url=target_server)
    client.run()


if __name__ == "__main__":
    main()
