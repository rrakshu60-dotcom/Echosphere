"""
EchoSphere Firebase Cloud Messaging (FCM) Push Service
======================================================
Provides 100% free, unlimited, real-time push notifications
to Android, iOS, and Web clients via Google Firebase Admin SDK.
Supports topic-based fan-out (department, role, campus-wide, emergency).
"""

import os
import re
import glob
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("echosphere.firebase_push")

_firebase_app = None


def get_firebase_admin_app():
    """Initializes or returns the singleton Firebase Admin App."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Check existing apps
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app

        # 0. The key as base64 of the JSON (one line in .env and in Render's settings)
        raw_b64 = (os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON_B64") or "").strip()
        if raw_b64:
            import base64
            cred = credentials.Certificate(json.loads(base64.b64decode(raw_b64)))
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info(f"🔥 [Firebase FCM] Initialized from FIREBASE_SERVICE_ACCOUNT_JSON_B64 (Project: {_firebase_app.project_id})")
            return _firebase_app

        # 1. Check FIREBASE_SERVICE_ACCOUNT_KEY env var
        key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")

        # 2. Candidate paths
        candidates = [
            key_path,
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "serviceAccountKey.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", "serviceAccountKey.json"),
            "serviceAccountKey.json",
            "backend/serviceAccountKey.json",
        ]

        # 3. Search glob for firebase-adminsdk*.json in backend
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        glob_matches = glob.glob(os.path.join(backend_dir, "*firebase-adminsdk*.json"))
        candidates.extend(glob_matches)

        chosen_key = None
        for c in candidates:
            if c and os.path.exists(c) and os.path.getsize(c) > 100:
                chosen_key = c
                break

        if chosen_key:
            cred = credentials.Certificate(chosen_key)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info(f"🔥 [Firebase FCM] Initialized successfully with key: {chosen_key} (Project: {_firebase_app.project_id})")
            return _firebase_app

        # 4. Check inline JSON string
        raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if raw_json and raw_json.strip().startswith("{"):
            cred_dict = json.loads(raw_json)
            cred = credentials.Certificate(cred_dict)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info(f"🔥 [Firebase FCM] Initialized from FIREBASE_SERVICE_ACCOUNT_JSON (Project: {_firebase_app.project_id})")
            return _firebase_app

        logger.warning("⚠️ [Firebase FCM] No service account key found; push notifications are not sent.")
    except Exception as e:
        logger.warning(f"⚠️ [Firebase FCM] Initialization warning: {e}")

    return None


class FirebasePushService:
    """Manages FCM push notifications for campus announcements and emergency alerts."""

    @staticmethod
    def send_topic_notification(
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        is_emergency: bool = False,
    ) -> Dict[str, Any]:
        """
        Broadcasts a push notification to an FCM topic.
        Topics: 'all_campus', 'dept_cse', 'role_faculty', 'emergency_broadcasts', etc.
        """
        clean_topic = topic.strip().replace(" ", "_").replace("/", "_").lower()
        # Clean data dict: all values must be strings for FCM
        payload_data = {}
        if data:
            for k, v in data.items():
                payload_data[str(k)] = str(v) if v is not None else ""

        app = get_firebase_admin_app()
        if app is None:
            logger.info(
                f"[FCM MOCK DISPATCH] Topic='{clean_topic}', Title='{title}', Body='{body[:80]}...', Emergency={is_emergency}"
            )
            return {"status": "not_configured", "topic": clean_topic}

        try:
            from firebase_admin import messaging

            android_config = messaging.AndroidConfig(
                priority="high" if is_emergency else "normal",
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    channel_id="emergency_alerts" if is_emergency else "campus_announcements",
                    sound="default",
                    default_sound=True,
                    default_vibrate_timings=True,
                ),
            )

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=payload_data,
                topic=clean_topic,
                android=android_config,
            )

            response = messaging.send(message)
            logger.info(f"🚀 [FCM PUSH SENT] Broadcast to topic '{clean_topic}' successful! Message ID: {response}")
            return {"status": "sent", "topic": clean_topic, "message_id": response}
        except Exception as e:
            logger.error(f"❌ [FCM PUSH ERROR] Failed to send topic notification: {e}")
            return {"status": "error", "topic": clean_topic, "error": str(e)}

    @staticmethod
    def send_announcement_push(
        announcement_id: int,
        title: str,
        description: str,
        target_audience: Optional[str] = None,
        department_code: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = "NORMAL",
        audio_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Dispatches push notifications for a newly approved/published announcement.
        Dispatches to college-wide or specific departmental topic channels.
        """
        is_emergency = str(priority).upper() in ("URGENT", "EMERGENCY", "HIGH")
        body_text = description[:160] + ("..." if len(description) > 160 else "")

        data_payload = {
            "announcement_id": str(announcement_id),
            "title": title,
            "category": category or "General",
            "priority": str(priority),
            "audio_url": audio_url or "",
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
        }

        results = []
        target_str = (target_audience or "").strip().lower()

        # 1. Emergency notices always push to emergency_broadcasts and all_campus
        if is_emergency:
            res_emerg = FirebasePushService.send_topic_notification(
                topic="emergency_broadcasts",
                title=f"🚨 EMERGENCY: {title}",
                body=body_text,
                data=data_payload,
                is_emergency=True,
            )
            results.append(res_emerg)

        # 2. The topic follows the notice's audience (not the creator's department): "CSE Department" -> dept_cse;
        #    year groups, faculty and the whole college -> all_campus (in-app alerts do the finer targeting)
        dept_match = re.fullmatch(r"\s*([a-z0-9]+)\s+department\s*", target_str or "")
        topic = f"dept_{dept_match.group(1)}" if dept_match else "all_campus"

        res = FirebasePushService.send_topic_notification(
            topic=topic,
            title=f"📢 {title}",
            body=body_text,
            data=data_payload,
            is_emergency=is_emergency,
        )
        results.append(res)

        return results


firebase_push_service = FirebasePushService()


def device_topics(user) -> list:
    """Topics a signed-in device is subscribed to, worked out from the account (never from the client)."""
    topics = ["all_campus", "emergency_broadcasts"]
    dept = getattr(user, "department", None)
    code = (getattr(dept, "code", None) or "").strip().lower() if dept else ""
    if code and code.isalnum():
        topics.append(f"dept_{code}")
    return topics


def subscribe_device(token: str, topics: list) -> list:
    """Subscribes one device token to the topics; returns the topics that succeeded."""
    app = get_firebase_admin_app()
    if app is None:
        return []
    from firebase_admin import messaging
    done = []
    for topic in topics:
        try:
            res = messaging.subscribe_to_topic([token], topic, app=app)
            if res.success_count:
                done.append(topic)
        except Exception as e:
            logger.warning(f"[FCM] subscribe to {topic} failed: {type(e).__name__}")
    return done
