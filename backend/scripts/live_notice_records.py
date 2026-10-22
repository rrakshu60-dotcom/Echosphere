"""
Live check of permanent notice records on production + the ESP32 (.agents/rules/testing.md §4-5).

1. A quiet test notice plays on the ESP32 and is deleted: its record must show CREATED, PUBLISHED,
   SPEAKER_STARTED, SPEAKER_FINISHED, DELETED (after broadcast) and AUDIO_DELETED, and keep its content.
2. A test notice scheduled for next year is deleted before it airs: "deleted before broadcast".

Records are permanent by design, so the two [ES-TEST] records stay in the audit log; the notices
themselves are deleted.

    python backend/scripts/live_notice_records.py      (close any other serial monitor on COM7 first)
"""
import sys

from live_support import ESP32_NODE_ID, Esp32Serial, LiveNotices, LiveSession, speaker_busy, wait_until


def record(session, nid) -> dict:
    return session.get(f"/audit/notices/{nid}")


def events(rec) -> list:
    return [e["event"] for e in rec["events"]]


def main() -> None:
    session = LiveSession.login()
    busy = speaker_busy(session.get("/hardware/queue"))
    assert not busy, f"speaker is busy ({len(busy)} item(s) playing or due soon); not interrupting real notices"

    with Esp32Serial() as esp, LiveNotices(session) as notices:
        mark = esp.mark()
        played = notices.create("Record check played", "Short speaker test for the notice record.", speaker_node_id=ESP32_NODE_ID)
        later = notices.create("Record check scheduled", "Scheduled test notice, deleted before it airs.",
                               speaker_node_id=ESP32_NODE_ID, scheduled_at="2027-06-01T04:30:00")
        p, s = played["id"], later["id"]
        print(f"published #{p} and scheduled #{s} {notices.tag}")

        _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=60, since=mark)
        print(f"PASS #{p} played on the ESP32 ({t:.1f}s)")
        wait_until(lambda: "SPEAKER_FINISHED" in events(record(session, p)), timeout=15, what="SPEAKER_FINISHED in the record")

        rec = record(session, p)["record"]
        assert rec["creator_role"] == "Dev Admin" and rec["creator_name"], f"creator missing: {rec}"
        assert rec["content"].startswith("Short speaker test"), "content not recorded"
        assert "Speaker" in rec["channels"] and rec["speaker_play_count"] >= 1 and rec["first_delivered_at"]
        print(f"PASS record of #{p}: creator {rec['creator_name']}, channels {rec['channels']}, plays {rec['speaker_play_count']}")

    # LiveNotices has deleted both notices; their records must remain, marked deleted
    def deleted_with_audio(nid):
        r = record(session, nid)
        return r if (r["record"]["deleted"] and "AUDIO_DELETED" in events(r)) else None

    r_played, t = wait_until(lambda: deleted_with_audio(p), timeout=60, interval=1, what=f"#{p} deleted + audio deleted")
    ev = events(r_played)
    for needed in ("CREATED", "PUBLISHED", "SPEAKER_STARTED", "SPEAKER_FINISHED", "DELETED", "AUDIO_DELETED"):
        assert needed in ev, f"#{p} timeline missing {needed}: {ev}"
    assert ev.index("DELETED") < ev.index("AUDIO_DELETED"), "audio was deleted before the deletion was recorded"
    rp = r_played["record"]
    assert rp["deleted_before_broadcast"] is False and rp["deleted_by_role"] == "Dev Admin"
    assert rp["content"].startswith("Short speaker test"), "content lost after deletion"
    audio_note = [e["detail"] for e in r_played["events"] if e["event"] == "AUDIO_DELETED"][0]
    print(f"PASS #{p}: record kept after deletion, deleted after broadcast; {audio_note}")

    r_later, _ = wait_until(lambda: deleted_with_audio(s), timeout=60, interval=1, what=f"#{s} deleted + audio deleted")
    assert r_later["record"]["deleted_before_broadcast"] is True, f"#{s} not marked deleted before broadcast"
    assert r_later["record"]["scheduled_at"], "scheduled time not recorded"
    print(f"PASS #{s}: deleted before broadcast, scheduled time kept ({r_later['record']['scheduled_at']})")

    found = session.get(f"/audit/notices?q={notices.tag}&state=deleted")
    assert {i["announcement_id"] for i in found["items"]} >= {p, s}, "search did not find the deleted test notices"
    print("PASS search finds both deleted notices by their tag")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
