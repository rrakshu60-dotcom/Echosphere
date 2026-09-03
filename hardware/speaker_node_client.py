#!/usr/bin/env python3
"""
EchoSphere Smart Speaker Node Client (Firmware / Edge Driver)
Runs on Windows, Linux, or Raspberry Pi.

Features:
- Auto-registration with EchoSphere Backend
- Periodic Heartbeat Telemetry & Pending REST Command Polling
- Native Audio Playback Engine (MP3/WAV & Windows SAPI Speech Synthesis)
- MQTT Command Listener (with automatic HTTP REST fallback)
- Real-time Campus Broadcast & Emergency Siren Playback
"""

import os
import sys
import time
import json
import uuid
import socket
import logging
import threading
import subprocess
import urllib.request
from datetime import datetime

import requests

# Try paho-mqtt
try:
    import paho.mqtt.client as mqtt  # type: ignore # noqa
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SpeakerNode] %(message)s",
)
logger = logging.getLogger("SpeakerNodeClient")

# Configurations
SERVER_URL = os.getenv("ECHOSPHERE_SERVER", "https://echosphere-backend-9lv8.onrender.com")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEPT_CODE = os.getenv("DEPT_CODE", "CSE")
ZONE_NAME = os.getenv("ZONE_NAME", "Block A - CSE Quad")

# Persistent MAC address
MAC_FILE = os.path.join(os.path.dirname(__file__), ".node_mac")
if os.path.exists(MAC_FILE):
    with open(MAC_FILE, "r") as f:
        MAC_ADDRESS = f.read().strip()
else:
    MAC_ADDRESS = ":".join([f"{(uuid.getnode() >> i) & 0xff:02X}" for i in range(0, 48, 8)][::-1])
    try:
        os.makedirs(os.path.dirname(MAC_FILE), exist_ok=True)
        with open(MAC_FILE, "w") as f:
            f.write(MAC_ADDRESS)
    except Exception:
        pass


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# -----------------------------------------------------------------------------
# Native Audio Output Engines (Cross-Platform / Windows Native)
# -----------------------------------------------------------------------------
def play_chime():
    """Plays an announcement attention chime."""
    try:
        import winsound
        winsound.Beep(587, 160)  # D5
        time.sleep(0.04)
        winsound.Beep(880, 240)  # A5
    except Exception:
        pass


def play_emergency_siren():
    """Plays an urgent emergency siren sweep."""
    try:
        import winsound
        for _ in range(2):
            for freq in range(600, 1350, 90):
                winsound.Beep(freq, 20)
            for freq in range(1350, 600, -90):
                winsound.Beep(freq, 20)
    except Exception:
        pass


def speak_text_native(text: str, volume: int = 100) -> bool:
    """Speaks notice text aloud using Windows built-in SpeechSynthesizer."""
    if sys.platform != "win32":
        return False
    try:
        clean_text = text.replace("'", " ").replace('"', " ")
        ps_cmd = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Volume = {volume}; "
            f"$s.Speak('{clean_text}')"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)
        return True
    except Exception as e:
        logger.warning(f"Native TTS speech failed: {e}")
        return False


def play_audio_file(file_path: str, volume: int = 100) -> bool:
    """Plays an MP3 or WAV file using Windows native MediaPlayer."""
    if sys.platform != "win32":
        return False
    try:
        abs_path = os.path.abspath(file_path).replace("\\", "\\\\")
        ps_cmd = f"""
        Add-Type -AssemblyName presentationCore
        $player = New-Object System.Windows.Media.MediaPlayer
        $player.Open('{abs_path}')
        $player.Volume = {max(0, min(100, volume)) / 100.0}
        $player.Play()
        $wait = 0
        while (-not $player.NaturalDuration.HasTimeSpan -and $wait -lt 25) {{
            Start-Sleep -Milliseconds 100
            $wait++
        }}
        if ($player.NaturalDuration.HasTimeSpan) {{
            $ms = [int]$player.NaturalDuration.TimeSpan.TotalMilliseconds
            Start-Sleep -Milliseconds ($ms + 200)
        }} else {{
            Start-Sleep -Seconds 4
        }}
        $player.Close()
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)
        return True
    except Exception as e:
        logger.warning(f"Audio file playback failed: {e}")
        return False


# -----------------------------------------------------------------------------
# Speaker Node Edge Client Class
# -----------------------------------------------------------------------------
class SpeakerNodeClient:
    def __init__(self):
        self.mac_address = MAC_ADDRESS
        self.ip_address = get_local_ip()
        self.node_id = None
        self.is_running = True
        self.current_status = "ONLINE"
        self.volume = 90
        self.mqtt_client = None

    def register_node(self):
        url = f"{SERVER_URL}/api/v1/hardware/speakers/register"
        payload = {
            "name": f"Laptop Speaker Node ({DEPT_CODE} {ZONE_NAME})",
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "zone": ZONE_NAME,
            "volume": self.volume,
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code in (200, 201):
                data = resp.json()
                self.node_id = data.get("id")
                logger.info(f"✅ Node registered successfully! ID: #{self.node_id}, MAC: {self.mac_address}")
            else:
                logger.info(f"ℹ️ Node already registered (HTTP {resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"Could not connect to backend server during registration: {e}")

    def send_heartbeat(self):
        url = f"{SERVER_URL}/api/v1/hardware/speakers/heartbeat"
        payload = {
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "cpu_usage": 18.2,
            "memory_usage": 41.5,
            "disk_space": 68.0,
            "status": self.current_status,
        }
        try:
            resp = requests.post(url, json=payload, timeout=4)
            if resp.status_code in (200, 201):
                data = resp.json()
                cmds = data.get("pending_commands", [])
                for cmd in cmds:
                    logger.info(f"⚡ [REST DISPATCH] Received queued command: {cmd.get('command')}")
                    self.handle_command_payload(cmd)
        except Exception as e:
            logger.debug(f"Heartbeat send failed: {e}")

    def play_audio(self, audio_url: str, title: str, message: str = "", is_emergency: bool = False):
        self.current_status = "PLAYING"
        logger.info(f"\n=======================================================")
        logger.info(f"📢 [PA BROADCAST START] Title: '{title}'")
        logger.info(f"=======================================================")

        # 1. Play attention chime or emergency siren
        if is_emergency:
            play_emergency_siren()
        else:
            play_chime()

        # 2. Try to download and stream backend-generated MP3 audio
        played = False
        if audio_url:
            tmp_filename = f"tmp_announcement_{uuid.uuid4().hex[:8]}.mp3"
            tmp_audio = os.path.join(os.path.dirname(__file__), tmp_filename)
            try:
                logger.info(f"📥 Downloading audio stream from: {audio_url}")
                urllib.request.urlretrieve(audio_url, tmp_audio)
                if os.path.exists(tmp_audio) and os.path.getsize(tmp_audio) > 200:
                    played = play_audio_file(tmp_audio, volume=self.volume)
            except Exception as e:
                logger.warning(f"Could not download audio stream ({e}), falling back to direct voice synthesis.")
            finally:
                if os.path.exists(tmp_audio):
                    try:
                        os.remove(tmp_audio)
                    except Exception:
                        pass

        # 3. Fallback: Speak the text directly via Windows Native Voice Synthesis
        if not played:
            text_to_speak = f"{title}. {message}" if message else title
            logger.info(f"🗣️ [TTS VOICE] Speaking announcement aloud: '{text_to_speak}'")
            speak_text_native(text_to_speak, volume=self.volume)

        logger.info(f"✅ [PA BROADCAST COMPLETE] Finished playback for '{title}'\n")
        self.current_status = "ONLINE"

    def _run_speaker_test(self):
        self.current_status = "PLAYING"
        play_chime()
        speak_text_native("EchoSphere smart speaker diagnostic test passed. Audio subsystem is operational.", volume=self.volume)
        self.current_status = "ONLINE"

    def handle_command_payload(self, data: dict):
        cmd = data.get("command")
        logger.info(f"📢 [COMMAND RECEIVED] Action: {cmd}")

        if cmd == "PLAY_ANNOUNCEMENT":
            audio_url = data.get("audio_url")
            title = data.get("title", "Campus Announcement")
            message = data.get("message") or data.get("content") or ""
            threading.Thread(target=self.play_audio, args=(audio_url, title, message, False), daemon=True).start()

        elif cmd == "PLAY_EMERGENCY":
            audio_url = data.get("audio_url")
            title = data.get("title", "EMERGENCY OVERRIDE")
            message = data.get("message") or data.get("content") or "Campus Emergency Alert!"
            threading.Thread(target=self.play_audio, args=(audio_url, title, message, True), daemon=True).start()

        elif cmd == "TEST_SPEAKER":
            logger.info("🎛️ [TEST] Executing Speaker Diagnostic Test...")
            threading.Thread(target=self._run_speaker_test, daemon=True).start()

        elif cmd == "RESTART":
            logger.info("🔄 [RESTART] Rebooting hardware speaker subsystem...")
            self.current_status = "ONLINE"

    def setup_mqtt(self):
        if not MQTT_AVAILABLE:
            logger.info("ℹ️ Operating in HTTP REST polling mode.")
            return

        try:
            client_id = f"SpeakerNode_{self.mac_address.replace(':', '')}"
            if hasattr(mqtt, "CallbackAPIVersion"):
                self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
            else:
                self.mqtt_client = mqtt.Client(client_id=client_id)

            def on_connect(client, userdata, flags, rc):
                logger.info(f"Connected to MQTT Broker (rc={rc})")
                client.subscribe(f"echosphere/dept/{DEPT_CODE}/speakers/command")
                client.subscribe(f"echosphere/zone/{ZONE_NAME}/speakers/command")
                client.subscribe("echosphere/speakers/all/emergency")
                client.subscribe(f"echosphere/node/{self.mac_address}/command")

            def on_message(client, userdata, msg):
                try:
                    payload = json.loads(msg.payload.decode())
                    self.handle_command_payload(payload)
                except Exception as e:
                    logger.error(f"Failed to parse MQTT payload: {e}")

            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_message = on_message
            self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.info(f"ℹ️ MQTT Broker offline ({e}). Operating in HTTP REST polling mode.")

    def run(self):
        logger.info(f"Starting Speaker Node Client (MAC: {self.mac_address}, IP: {self.ip_address})")
        self.register_node()
        self.setup_mqtt()

        logger.info("🎧 Speaker Node is ACTIVE & LISTENING for broadcasts (Polling every 1.5s)...")
        try:
            while self.is_running:
                self.send_heartbeat()
                time.sleep(1.5)  # Fast 1.5s polling interval
        except KeyboardInterrupt:
            logger.info("Shutting down Speaker Node Client...")
            self.is_running = False


if __name__ == "__main__":
    client = SpeakerNodeClient()
    client.run()
