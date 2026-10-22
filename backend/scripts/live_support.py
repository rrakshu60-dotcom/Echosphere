"""
Shared helper for live checks against production and the physical ESP32 (.agents/rules/testing.md §4-5).

- LiveSession: logged-in calls to the live backend; any non-2xx answer fails the check.
- wait_until: poll a condition with a deadline instead of fixed sleeps; returns the measured time.
- Esp32Serial: owns the ESP32 serial port for the run and asserts on firmware log lines with deadlines.
- LiveNotices: creates tagged, quiet test notices and always deletes them, then fails on leftovers.

Typical use:

    with Esp32Serial() as esp, LiveNotices(LiveSession.login()) as notices:
        mark = esp.mark()
        ann = notices.create("Speaker check", "Short test notice.", speaker_node_id=13)
        esp.wait_for(rf"Play command received for notice #{ann['id']}", timeout=5, since=mark)
"""
import os
import re
import secrets
import threading
import time
from typing import Any, Callable, Optional, Tuple

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_API = "https://echosphere-backend-9lv8.onrender.com/api/v1"
ESP32_NODE_ID = 13  # "ESP32 Smart Speaker & Live Display" (D4:F3:2D:22:2A:CD)


def wait_until(check: Callable[[], Any], timeout: float, interval: float = 0.25, what: str = "condition") -> Tuple[Any, float]:
    """Call check() until it returns something truthy; return (value, seconds waited) or fail at the deadline."""
    start = time.monotonic()
    while True:
        value = check()
        elapsed = time.monotonic() - start
        if value:
            return value, elapsed
        if elapsed >= timeout:
            raise AssertionError(f"timed out waiting for {what} after {timeout:g}s")
        time.sleep(interval)


class LiveSession:
    """Calls to the live backend as a logged-in user."""

    def __init__(self, base_url: str, token: str):
        import requests

        self.base_url = base_url.rstrip("/")
        self._http = requests.Session()
        self._http.headers["Authorization"] = f"Bearer {token}"

    @classmethod
    def login(cls, identifier: str = "ESDEV01", base_url: Optional[str] = None) -> "LiveSession":
        import requests
        from dotenv import load_dotenv

        load_dotenv(os.path.join(BACKEND_DIR, ".env"))
        base_url = base_url or os.environ.get("ES_LIVE_API", DEFAULT_API)
        env_name = "ES_PASSWORD_" + re.sub(r"\W", "_", identifier.upper())
        res = requests.post(
            f"{base_url}/auth/login",
            json={"identifier": identifier, "password": os.environ[env_name]},
            timeout=30,
        )
        assert res.status_code == 200, f"login as {identifier} failed: HTTP {res.status_code}"
        return cls(base_url, res.json()["access_token"])

    def _call(self, method: str, path: str, **kwargs) -> Any:
        res = self._http.request(method, f"{self.base_url}{path}", timeout=30, **kwargs)
        assert 200 <= res.status_code < 300, f"{method} {path}: HTTP {res.status_code} {res.text[:200]}"
        return res.json() if res.content else None

    def get(self, path: str) -> Any:
        return self._call("GET", path)

    def post(self, path: str, json: Any = None) -> Any:
        return self._call("POST", path, json=json)

    def put(self, path: str, json: Any = None) -> Any:
        return self._call("PUT", path, json=json)

    def delete(self, path: str) -> Any:
        return self._call("DELETE", path)


class Esp32Serial:
    """Reads the ESP32 serial log in the background; wait_for() asserts a line appears before a deadline."""

    def __init__(self, port: Optional[str] = None, baud: int = 115200, port_factory: Optional[Callable[[], Any]] = None):
        self._port_name = port or os.environ.get("ES_ESP32_PORT", "COM7")
        self._baud = baud
        self._factory = port_factory
        self._port = None
        self._lines: list = []  # (monotonic time, text)
        self._cond = threading.Condition()
        self._stop = threading.Event()
        self._reader: Optional[threading.Thread] = None
        self._after_match = 0

    def __enter__(self) -> "Esp32Serial":
        if self._factory:
            self._port = self._factory()
        else:
            import serial

            # DTR/RTS drive the ESP32's EN/BOOT pins: keep them low so opening the port does not reboot it.
            port = serial.Serial()
            port.port = self._port_name
            port.baudrate = self._baud
            port.timeout = 0.2
            port.dtr = False
            port.rts = False
            try:
                port.open()
                self._port = port
            except serial.SerialException as exc:
                raise AssertionError(
                    f"cannot open {self._port_name}: {exc}. Close any other serial monitor (only one program can own the port)."
                ) from exc
        self._reader = threading.Thread(target=self._read_loop, daemon=True, name="Esp32SerialReader")
        self._reader.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        if self._reader:
            self._reader.join(timeout=2)
        if self._port is not None:
            self._port.close()

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self._port.readline()
            except Exception:
                break
            if not raw:
                continue
            text = raw.decode("utf-8", errors="replace").replace("�", "").strip()
            if text:
                with self._cond:
                    self._lines.append((time.monotonic(), text))
                    self._cond.notify_all()

    def mark(self) -> int:
        """Position in the log; pass it as since= to ignore everything printed before it."""
        with self._cond:
            return len(self._lines)

    def after_last_match(self) -> int:
        """Log position right after the line the last wait_for() matched."""
        return self._after_match

    def lines_since(self, since: int) -> list:
        with self._cond:
            return [t for _, t in self._lines[since:]]

    def wait_for(self, pattern: str, timeout: float, since: int = 0) -> Tuple[str, float]:
        """Return (line, seconds waited) for the first line after `since` matching the regex, or fail."""
        regex = re.compile(pattern)
        start = time.monotonic()
        deadline = start + timeout
        index = since
        with self._cond:
            while True:
                while index < len(self._lines):
                    _, text = self._lines[index]
                    index += 1
                    if regex.search(text):
                        self._after_match = index
                        return text, time.monotonic() - start
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    recent = "\n  ".join(t for _, t in self._lines[-8:]) or "(nothing received)"
                    # The firmware logs emoji; keep the message printable on any console (e.g. Windows cp1252).
                    recent = recent.encode("ascii", "ignore").decode()
                    raise AssertionError(
                        f"ESP32 did not log /{pattern}/ within {timeout:g}s. Last lines:\n  {recent}"
                    )
                self._cond.wait(remaining)


class LiveNotices:
    """Creates tagged test notices and always deletes them on exit, failing if any are left behind."""

    def __init__(self, session: Any):
        self.session = session
        self.run_id = secrets.token_hex(3)
        self.tag = f"[ES-TEST {self.run_id}]"
        self.created_ids: list = []

    def __enter__(self) -> "LiveNotices":
        return self

    def create(self, title: str, description: str, speaker_node_id: Optional[int] = None, **fields) -> dict:
        payload = {
            "title": f"{self.tag} {title}",
            "description": description,
            "category_id": 12,
            "priority": "Normal",
            # Keep test notices out of people's phones and feeds; only the target speaker plays them.
            "target_audience": "Faculty Members",
            "deliver_in_app": False,
            "deliver_push": False,
            "deliver_speaker": True,
            "speaker_node_id": speaker_node_id,
            **fields,
        }
        created = self.session.post("/announcements", json=payload)
        self.created_ids.append(created["id"])
        return created

    def leftovers(self) -> list:
        found = [a for a in self.session.get("/announcements") if self.tag in (a.get("title") or "")]
        found += [q for q in self.session.get("/hardware/queue") if self.tag in (q.get("title") or "")]
        return found

    def __exit__(self, *exc) -> None:
        for nid in self.created_ids:
            try:
                self.session.delete(f"/announcements/{nid}")
            except AssertionError:
                pass  # reported by the leftover check below
        left = self.leftovers()
        assert not left, f"cleanup failed, {self.tag} test data left behind: {[x.get('id') for x in left]}"
