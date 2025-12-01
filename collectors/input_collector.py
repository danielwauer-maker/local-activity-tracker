# collectors/input_collector.py
#!/usr/bin/env python3
import time
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Set

import requests
from pynput import mouse, keyboard
import win32gui
import win32process
import psutil


BACKEND_URL = "http://127.0.0.1:8000"
SEND_INTERVAL = 1.0    # alle 1 Sekunde Buffer senden
BUFFER_MAX = 200       # ab so vielen Events sofort senden


buffer: List[Dict[str, Any]] = []
lock = threading.Lock()

# Set aller aktuell gedrückten Tasten für Shortcut-Erkennung
pressed_keys: Set[str] = set()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_active_window():
    """Gibt (app, title, pid) des aktiven Fensters zurück."""
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


def add_event(event_type: str, payload: Dict[str, Any]):
    """Schreibt ein Input-Event in den lokalen Buffer (mit Fenster-Bezug)."""
    app, title, pid = get_active_window()

    event = {
        "timestamp": now_iso(),
        "source": "input",
        "type": event_type,
        "payload": {
            "app": app,
            "title": title,
            "pid": pid,
            **payload
        }
    }

    with lock:
        buffer.append(event)
        if len(buffer) >= BUFFER_MAX:
            flush_buffer_locked()


def flush_buffer_locked():
    """Buffer senden – nur aufrufen, wenn lock bereits gehalten wird."""
    global buffer
    if not buffer:
        return

    to_send = buffer
    buffer = []

    try:
        requests.post(
            f"{BACKEND_URL}/events/batch",
            json={"events": to_send},
            timeout=2
        )
    except Exception as e:
        print(f"[ERROR] Backend unreachable while sending batch: {e}")


def sender_loop():
    """Hintergrund-Thread, der den Buffer alle X Sekunden sendet."""
    while True:
        time.sleep(SEND_INTERVAL)
        with lock:
            flush_buffer_locked()


# === Maus-Callbacks ===

def on_move(x, y):
    # Optional: Wenn dir alle Bewegungen zu viel sind, kannst du das kommentieren
    add_event("mouse_move", {"x": x, "y": y})


def on_click(x, y, button, pressed):
    event_type = "mouse_click_down" if pressed else "mouse_click_up"
    add_event(event_type, {
        "x": x,
        "y": y,
        "button": str(button)
    })


def on_scroll(x, y, dx, dy):
    add_event("mouse_scroll", {
        "x": x,
        "y": y,
        "dx": dx,
        "dy": dy
    })


# === Tastatur-Helper ===

def normalize_key(key) -> str:
    """
    Liefert einen lesbaren Namen für die Taste:
    - normale Tasten: 'a', 'b', '1', ...
    - Sondertasten: 'ctrl_l', 'shift', 'alt', ...
    """
    # Versuche, das Zeichen direkt zu bekommen (z. B. 'a', 's', '1')
    try:
        if hasattr(key, "char") and key.char is not None:
            return key.char
    except Exception:
        pass

    # Fallback für Sondertasten
    name = str(key)  # z. B. 'Key.ctrl_l'
    if name.startswith("Key."):
        name = name[4:]
    return name


def get_combo_string() -> str:
    """Gibt die aktuelle Tastenkombination als sortierte, + getrennte Zeichenkette zurück."""
    if not pressed_keys:
        return ""
    return "+".join(sorted(pressed_keys))


# === Tastatur-Callbacks ===

def on_key_press(key):
    key_name = normalize_key(key)
    pressed_keys.add(key_name)

    add_event("key_down", {
        "key": key_name,
        "combo": get_combo_string()
    })


def on_key_release(key):
    key_name = normalize_key(key)
    if key_name in pressed_keys:
        pressed_keys.remove(key_name)

    add_event("key_up", {
        "key": key_name,
        "combo": get_combo_string()
    })


def main():
    # Hinweis: Nur auf deinem eigenen Rechner verwenden, nicht zum „Spionieren“ bei anderen.
    threading.Thread(target=sender_loop, daemon=True).start()

    with mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll
    ) as ml, keyboard.Listener(
        on_press=on_key_press,
        on_release=on_key_release
    ) as kl:

        print("Input-Collector läuft… (Strg+C zum Beenden)")
        ml.join()
        kl.join()


if __name__ == "__main__":
    main()
