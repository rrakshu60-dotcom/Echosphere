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
        db,
        announcement_id: int,
        title: str,
        description: str,
        target_audience: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = "NORMAL",
        audio_url: Optional[str] = None,
        is_emergency: bool = False,
    ) -> List[Dict[str, Any]]:
        """Pushes a published notice to the signed-in devices of its audience (all devices for an emergency)."""
        audience = "all_campus" if is_emergency else audience_topic(target_audience or "")
        if audience is None:
            logger.info(f"[FCM] No push audience for '{target_audience}'; push skipped.")
            return [{"status": "no_audience", "topic": target_audience}]
        app = get_firebase_admin_app()
        if app is None:
            return [{"status": "not_configured", "topic": audience}]

        from firebase_admin import messaging
        from app.models.push_device import PushDevice
        from app.models.user import User

        devices = [d for d, u in db.query(PushDevice, User).join(User, User.id == PushDevice.user_id)
                   .filter(User.is_active == True).all() if user_in_audience(u, audience)]
        if not devices:
            return [{"status": "no_devices", "topic": audience}]

        notice_url = f"https://echosphere-2jf.pages.dev/announcement?id={announcement_id}"
        data = {"announcement_id": str(announcement_id), "title": title, "category": category or "General",
                "priority": str(priority), "audio_url": audio_url or "", "click_action": "FLUTTER_NOTIFICATION_CLICK"}
        shown_title = f"🚨 EMERGENCY: {title}" if is_emergency else f"📢 {title}"
        body = description[:160] + ("..." if len(description) > 160 else "")
        sent, dead = 0, []
        for start in range(0, len(devices), 500):
            batch = devices[start:start + 500]
            message = messaging.MulticastMessage(
                tokens=[d.token for d in batch],
                notification=messaging.Notification(title=shown_title, body=body),
                data=data,
                android=messaging.AndroidConfig(priority="high", notification=messaging.AndroidNotification(
                    channel_id="emergency_alerts" if is_emergency else "campus_announcements", sound="default")),
                webpush=messaging.WebpushConfig(fcm_options=messaging.WebpushFCMOptions(link=notice_url)),
            )
            try:
                result = messaging.send_each_for_multicast(message, app=app)
            except Exception as e:
                logger.error(f"[FCM] push failed: {type(e).__name__}")
                return [{"status": "error", "topic": audience, "error": type(e).__name__}]
            sent += result.success_count
            for device, r in zip(batch, result.responses):
                if not r.success and isinstance(r.exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
                    dead.append(device.id)
        if dead:
            db.query(PushDevice).filter(PushDevice.id.in_(dead)).delete(synchronize_session=False)
            db.commit()
        status = "sent" if sent else "error"
        return [{"status": status, "topic": f"{sent} device(s) ({audience})", "error": None if sent else "no device accepted it"}]


firebase_push_service = FirebasePushService()


STAFF_ROLES = {"dev admin", "developer", "college admin", "principal", "hod", "teacher"}


def audience_topic(audience: str) -> Optional[str]:
    """The push topic of a notice audience. Restricted audiences have their own topic; None = no push."""
    a = (audience or "").strip().lower()
    if a in ("", "entire college", "all", "college-wide", "all students and staff"):
        return "all_campus"
    m = re.fullmatch(r"([a-z0-9]+)\s+department", a)
    if m:
        return f"dept_{m.group(1)}"
    if a in ("faculty members", "faculty", "staff"):
        return "faculty"
    m = re.fullmatch(r"([1-4])(?:st|nd|rd|th)\s+year\s+students", a)
    if m:
        return f"year_{m.group(1)}"
    if a in ("students", "all students"):
        return "students"
    return None


def user_in_audience(user, audience: str) -> bool:
    """Whether a user belongs to a push audience from audience_topic()."""
    if audience == "all_campus":
        return True
    role = (getattr(getattr(user, "role", None), "name", "") or "").strip().lower()
    staff = role in STAFF_ROLES
    if audience == "faculty":
        return staff
    if audience == "students":
        return not staff
    if audience.startswith("year_"):
        semester = getattr(user, "semester", None)
        return not staff and bool(semester) and str(min(4, (int(semester) + 1) // 2)) == audience[5:]
    if audience.startswith("dept_"):
        dept = getattr(user, "department", None)
        return bool(dept) and (getattr(dept, "code", "") or "").strip().lower() == audience[5:]
    return False


def register_device(db, user, token: str, platform: Optional[str]) -> None:
    """Stores (or moves to this user) a device's push token."""
    from app.models.push_device import PushDevice
    device = db.query(PushDevice).filter(PushDevice.token == token).first()
    if device is None:
        db.add(PushDevice(token=token, user_id=user.id, platform=platform))
    else:
        device.user_id, device.platform = user.id, platform
    db.commit()
