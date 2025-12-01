# collectors/window_collector.py
import time
from datetime import datetime, timezone

import requests
import win32gui
import win32process
import psutil


BACKEND_URL = "http://127.0.0.1:8000"
INTERVAL_SECONDS = 1  # jede Sekunde prüfen


def get_active_window_info():
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None, None, None

        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        app = None
        try:
            proc = psutil.Process(pid)
            app = proc.name()
        except Exception:
            pass

        return app, title, pid
    except Exception:
        return None, None, None


def main():
    last_state = None

    while True:
        now = datetime.now(timezone.utc)
        timestamp_iso = now.isoformat()

        app, title, pid = get_active_window_info()
        state = (app, title, pid)

        # Nur bei Änderung ein Event senden
        if state != last_state and any(state):
            payload = {
                "timestamp": timestamp_iso,
                "source": "window",
                "type": "window_focus",
                "payload": {
                    "app": app,
                    "title": title,
                    "pid": pid,
                },
            }

            try:
                requests.post(f"{BACKEND_URL}/events", json=payload, timeout=2)
                last_state = state
            except Exception as e:
                print(f"[ERROR] Backend nicht erreichbar: {e}")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
