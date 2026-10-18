"""
EchoSphere Firebase Cloud Messaging (FCM) Push Notification Test Suite
=====================================================================
Tests live dispatch of 100% free, unlimited FCM push notifications:
1. Firebase Admin SDK credential loading & authentication
2. Campus-wide topic broadcast ('all_campus')
3. High-priority emergency siren push broadcast ('emergency_broadcasts')
4. Departmental topic routing ('dept_cse')
5. Verification of Google FCM message ID responses
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.firebase_push_service import firebase_push_service, get_firebase_admin_app


def run_tests():
    print("=" * 70)
    print("🔥 EchoSphere Firebase Cloud Messaging (FCM) Push Test Suite")
    print("=" * 70)

    # 1. Verify Firebase Admin Authentication
    print("\n--- [1/4] Verifying Firebase Admin SDK Authentication ---")
    app = get_firebase_admin_app()
    assert app is not None, "Failed to initialize Firebase Admin SDK"
    print(f"  [PASS] Firebase Admin App initialized! Project ID: {app.project_id}")
    assert app.project_id == "echosphere-3bcc0"

    # 2. Test Campus-Wide Topic Push Dispatch
    print("\n--- [2/4] Testing Campus-Wide Topic Push Dispatch ('all_campus') ---")
    res1 = firebase_push_service.send_topic_notification(
        topic="all_campus",
        title="EchoSphere System Test",
        body="This is a live test broadcast to verified campus devices.",
        data={"test": "true", "timestamp": "2026-10-19"},
    )
    assert res1.get("status") == "sent", f"FCM send failed: {res1}"
    assert "projects/echosphere-3bcc0/messages/" in res1.get("message_id", "")
    print(f"  [PASS] Broadcast sent successfully! Message ID: {res1['message_id']}")

    # 3. Test High-Priority Emergency Push Dispatch
    print("\n--- [3/4] Testing High-Priority Emergency Siren Push ('emergency_broadcasts') ---")
    res2 = firebase_push_service.send_topic_notification(
        topic="emergency_broadcasts",
        title="EMERGENCY ADVISORY: Flash Storm Alert",
        body="All students and faculty are advised to remain indoors.",
        data={"is_emergency": "true", "priority": "CRITICAL"},
        is_emergency=True,
    )
    assert res2.get("status") == "sent", f"FCM emergency send failed: {res2}"
    print(f"  [PASS] Emergency push dispatched! Message ID: {res2['message_id']}")

    # 4. Test Announcement Service Push Router
    print("\n--- [4/4] Testing Announcement Push Dispatch with Departmental Routing ---")
    res3_list = firebase_push_service.send_announcement_push(
        announcement_id=101,
        title="Mid-Term Examination Timetable",
        description="The autumn 2026 examination schedule has been officially published.",
        target_audience="CSE",
        department_code="CSE",
        category="Academics",
        priority="NORMAL",
    )
    assert len(res3_list) > 0
    for r in res3_list:
        assert r.get("status") == "sent"
        print(f"  [PASS] Announcement routed to topic '{r['topic']}'. Message ID: {r['message_id']}")

    print("\n" + "=" * 70)
    print("🏆 ALL 4/4 FCM PUSH NOTIFICATION TESTS PASSED (100% SUCCESS)")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
