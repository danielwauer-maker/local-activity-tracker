# collectors/document_collector.py
#!/usr/bin/env python3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


BACKEND_URL = "http://127.0.0.1:8000"

# Welche Ordner sollen überwacht werden?
# Passe das an deine Umgebung an:
WATCH_DIRS: List[Path] = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    # ggf. weitere Projektordner:
    # Path("C:/dev"),
]

# Welche Dateitypen sind interessant?
INTERESTING_EXTENSIONS = {
    ".docx", ".doc",
    ".xlsx", ".xls",
    ".pptx", ".ppt",
    ".txt",
    ".md",
    ".py", ".cs", ".js", ".ts", ".ps1",
    ".csv",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def is_interesting(path: Path) -> bool:
    if not path.is_file():
        return False
    return path.suffix.lower() in INTERESTING_EXTENSIONS


def send_doc_event(event_type: str, path: Path):
    payload = {
        "timestamp": now_iso(),
        "source": "document",
        "type": event_type,
        "payload": {
            "path": str(path),
            "name": path.name,
            "suffix": path.suffix,
            # evtl. später: Dateigröße, Hash, etc.
        }
    }
    try:
        requests.post(f"{BACKEND_URL}/events", json=payload, timeout=2)
    except Exception as e:
        print(f"[ERROR] Backend unreachable in document_collector: {e}")


class DocEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if is_interesting(p):
            send_doc_event("doc_created", p)

    def on_modified(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if is_interesting(p):
            send_doc_event("doc_modified", p)

    # Optional: löschen / verschieben ebenfalls loggen
    def on_moved(self, event):
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        if is_interesting(dest):
            send_doc_event("doc_moved", dest)

    def on_deleted(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if is_interesting(p):
            send_doc_event("doc_deleted", p)


def main():
    observer = Observer()
    handler = DocEventHandler()

    for d in WATCH_DIRS:
        if d.exists():
            print(f"[INFO] Überwache Ordner: {d}")
            observer.schedule(handler, str(d), recursive=True)
        else:
            print(f"[WARN] Ordner existiert nicht: {d}")

    observer.start()
    print("Document-Collector läuft… (Strg+C zum Beenden)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
