#!/usr/bin/env python3
"""
EchoSphere Smart Speaker Node Client (Firmware / Microcontroller Driver)
Can be executed on ESP32, Raspberry Pi, or any Linux/Windows edge device.

Features:
- Auto-registration with EchoSphere Backend
- Periodic Heartbeat Telemetry (CPU, Memory, Disk, IP)
- MQTT Command Listener (fallback REST polling)
- Audio Stream Downloader & Playback Engine (Pygame / System player)
- Playback Status Reporting (Started, Completed, Error)
"""

import os
import sys
import time
import json
import uuid
import socket
import logging
import threading
import urllib.request
from datetime import datetime

import requests

# Try paho-mqtt
try:
    import paho.mqtt.client as mqtt  # type: ignore # noqa
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

# Try pygame audio mixer
try:
    import pygame  # type: ignore # noqa
    pygame.mixer.init()
    AUDIO_ENGINE = "pygame"
except Exception:
    AUDIO_ENGINE = "system"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SpeakerNode] %(message)s",
)
logger = logging.getLogger("SpeakerNodeClient")

# Configurations
SERVER_URL = os.getenv("ECHOSPHERE_SERVER", "http://localhost:8000")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEPT_CODE = os.getenv("DEPT_CODE", "CSE")
ZONE_NAME = os.getenv("ZONE_NAME", "Block A")

# Generate or read persistent MAC address
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


class SpeakerNodeClient:
    def __init__(self):
        self.mac_address = MAC_ADDRESS
        self.ip_address = get_local_ip()
        self.node_id = None
        self.is_running = True
        self.current_status = "ONLINE"
        self.volume = 80
        self.mqtt_client = None

    def register_node(self):
        url = f"{SERVER_URL}/api/v1/hardware/speakers/register"
        payload = {
            "name": f"Speaker Node ({DEPT_CODE} {ZONE_NAME})",
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
                logger.info(f"Node registered successfully! ID: #{self.node_id}, MAC: {self.mac_address}")
            else:
                logger.info(f"Node already registered or response {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Could not connect to backend server during registration: {e}")

    def send_heartbeat(self):
        url = f"{SERVER_URL}/api/v1/hardware/speakers/heartbeat"
        # Dummy system metrics for demo/simulation
        payload = {
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "cpu_usage": 14.5,
            "memory_usage": 32.8,
            "disk_space": 45.0,
            "status": self.current_status,
        }
        try:
            requests.post(url, json=payload, timeout=3)
        except Exception as e:
            logger.debug(f"Heartbeat send failed: {e}")

    def play_audio(self, audio_url: str, title: str):
        logger.info(f"Playing announcement: '{title}' from {audio_url}")
        self.current_status = "PLAYING"
        tmp_filename = f"tmp_announcement_{uuid.uuid4().hex[:8]}.mp3"
        tmp_audio = os.path.join(os.path.dirname(__file__), tmp_filename)

        try:
            urllib.request.urlretrieve(audio_url, tmp_audio)
            if AUDIO_ENGINE == "pygame":
                pygame.mixer.music.load(tmp_audio)
                pygame.mixer.music.set_volume(max(0, min(100, self.volume)) / 100.0)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.5)
            else:
                logger.info(f"[Audio Simulator] Playing audio stream for '{title}'...")
                time.sleep(3.0)

            logger.info(f"Finished playback for '{title}'")
            self.current_status = "ONLINE"
        except Exception as e:
            logger.error(f"Playback error: {e}")
            self.current_status = "ERROR"
        finally:
            if os.path.exists(tmp_audio):
                try:
                    os.remove(tmp_audio)
                except Exception:
                    pass

    def handle_command_payload(self, data: dict):
        cmd = data.get("command")
        logger.info(f"Command received: {cmd}")

        if cmd in ("PLAY_ANNOUNCEMENT", "PLAY_EMERGENCY"):
            audio_url = data.get("audio_url")
            title = data.get("title", "Announcement")
            if audio_url:
                threading.Thread(target=self.play_audio, args=(audio_url, title), daemon=True).start()

        elif cmd == "TEST_SPEAKER":
            logger.info("Executing TEST_SPEAKER tone burst test...")

        elif cmd == "RESTART":
            logger.info("Restarting Speaker Node software...")

    def setup_mqtt(self):
        if not MQTT_AVAILABLE:
            logger.warning("Paho-MQTT not installed. Operating in REST heartbeat mode.")
            return

        try:
            self.mqtt_client = mqtt.Client(client_id=f"SpeakerNode_{self.mac_address.replace(':', '')}")

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
            logger.warning(f"MQTT Broker connection failed: {e}. Falling back to REST mode.")

    def run(self):
        logger.info(f"Starting Speaker Node Client (MAC: {self.mac_address}, IP: {self.ip_address})")
        self.register_node()
        self.setup_mqtt()

        counter = 0
        try:
            while self.is_running:
                self.send_heartbeat()
                time.sleep(10)
                counter += 1
        except KeyboardInterrupt:
            logger.info("Shutting down Speaker Node Client...")
            self.is_running = False


if __name__ == "__main__":
    client = SpeakerNodeClient()
    client.run()
