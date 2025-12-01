# collectors/screenshot_collector.py
#!/usr/bin/env python3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import shutil

import requests
from mss import mss
from PIL import Image, ImageChops, ImageStat


# === Konfiguration ===
BACKEND_URL = "http://127.0.0.1:8000"

INTERVAL_SECONDS = 10          # alle 10 Sekunden prüfen
BASE_DIR = Path.home() / ".tracker" / "screenshots"

# Bildoptimierung
SCALE_FACTOR = 0.4             # 40 % der Originalgröße
WEBP_QUALITY = 75              # 60–85 = meist ideal

# Delta-Screenshots (nur speichern, wenn sich Bild sichtbar ändert)
ENABLE_DELTA = True
DELTA_THRESHOLD = 3.0          # je höher, desto „sensibler“ (1–5 ist ok)

# Cleanup-Job (Screenshots älter als retention_days löschen)
ENABLE_CLEANUP = True
CLEANUP_INTERVAL_SECONDS = 3600  # 1x pro Stunde aufräumen

# Fallback, falls /settings nicht erreichbar ist
DEFAULT_RETENTION_DAYS = 7


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def fetch_retention_days() -> int:
    """Liest screenshot_retention_days aus dem Backend (/settings)."""
    try:
        resp = requests.get(f"{BACKEND_URL}/settings", timeout=2)
        if resp.ok:
            data = resp.json()
            days = int(data.get("screenshot_retention_days", DEFAULT_RETENTION_DAYS))
            if days < 1:
                days = 1
            return days
    except Exception as e:
        print(f"[WARN] Konnte Settings nicht laden: {e}")
    return DEFAULT_RETENTION_DAYS


def cleanup_old_screenshots(retention_days: int):
    """Löscht Tagesordner unter BASE_DIR, die älter als retention_days sind."""
    if not BASE_DIR.exists():
        return

    now_date = datetime.now().date()
    for sub in BASE_DIR.iterdir():
        if not sub.is_dir():
            continue
        try:
            # Ordnername ist YYYY-MM-DD
            folder_date = datetime.strptime(sub.name, "%Y-%m-%d").date()
        except ValueError:
            continue

        age_days = (now_date - folder_date).days
        if age_days > retention_days:
            try:
                print(f"[INFO] Lösche alten Screenshot-Ordner: {sub} (Alter: {age_days} Tage)")
                shutil.rmtree(sub, ignore_errors=True)
            except Exception as e:
                print(f"[WARN] Konnte Ordner {sub} nicht löschen: {e}")


def rms_diff(img1: Image.Image, img2: Image.Image) -> float:
    """Berechnet RMS-Differenz zwischen zwei Bildern (gleiche Größe)."""
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)

    diff = ImageChops.difference(img1, img2)
    stat = ImageStat.Stat(diff)
    # stat.mean ist eine Liste pro Kanal (R, G, B)
    mean = stat.mean
    # einfache RMS über die Kanäle
    rms = sum((m ** 2 for m in mean)) ** 0.5
    return rms


def main():
    ensure_dir(BASE_DIR)

    # letzte verkleinerte Screenshots pro Monitor für Delta-Vergleich
    last_images = {}  # monitor_index -> PIL.Image

    # Settings & Cleanup-Steuerung
    retention_days = fetch_retention_days()
    last_settings_fetch = time.time()
    last_cleanup_run = 0.0

    print(f"[INFO] Screenshot-Collector gestartet. BASE_DIR={BASE_DIR}")
    print(f"[INFO] Retention (Start): {retention_days} Tage")
    print(f"[INFO] Delta-Screenshots: {ENABLE_DELTA}, Cleanup: {ENABLE_CLEANUP}")

    while True:
        now = datetime.now(timezone.utc)
        timestamp_iso = now.isoformat()

        # Alle X Sekunden Settings neu laden (z.B. alle 5 min)
        if time.time() - last_settings_fetch > 300:
            new_days = fetch_retention_days()
            if new_days != retention_days:
                print(f"[INFO] Retention-Tage geändert: {retention_days} -> {new_days}")
                retention_days = new_days
            last_settings_fetch = time.time()

        # Cleanup-Job
        if ENABLE_CLEANUP and (time.time() - last_cleanup_run > CLEANUP_INTERVAL_SECONDS):
            cleanup_old_screenshots(retention_days)
            last_cleanup_run = time.time()

        # Tagesordner
        date_str = now.strftime("%Y-%m-%d")
        day_dir = BASE_DIR / date_str
        ensure_dir(day_dir)

        try:
            with mss() as sct:
                # monitors[1:] = physische Monitore
                for i, monitor in enumerate(sct.monitors[1:], start=0):
                    raw = sct.grab(monitor)

                    # In PIL-Image umwandeln
                    img = Image.frombytes("RGB", (raw.width, raw.height), raw.rgb)

                    # Downscaling
                    if SCALE_FACTOR != 1.0:
                        img = img.resize(
                            (
                                max(1, int(img.width * SCALE_FACTOR)),
                                max(1, int(img.height * SCALE_FACTOR)),
                            ),
                            Image.Resampling.LANCZOS,
                        )

                    # Delta-Check
                    if ENABLE_DELTA and i in last_images:
                        diff_val = rms_diff(last_images[i], img)
                        if diff_val < DELTA_THRESHOLD:
                            # Bild hat sich nicht „genug“ geändert, wir sparen uns den Screenshot
                            # (Optional: Debug-Ausgabe)
                            # print(f"[DEBUG] Monitor {i}: diff={diff_val:.2f} < {DELTA_THRESHOLD}, überspringe.")
                            continue

                    # Wenn wir hier sind, speichern wir den Screenshot
                    last_images[i] = img

                    filename = f"{i}_{now.strftime('%Y%m%d_%H%M%S_%f')}.webp"
                    save_path = day_dir / filename

                    img.save(
                        save_path,
                        format="WEBP",
                        quality=WEBP_QUALITY,
                        method=6,  # beste Kompression
                    )

                    # Event ins Backend
                    payload = {
                        "timestamp": timestamp_iso,
                        "source": "screenshot",
                        "type": "screenshot_taken",
                        "payload": {
                            "screen_index": i,
                            "path": str(save_path),
                            "width": img.width,
                            "height": img.height,
                        },
                    }

                    try:
                        requests.post(
                            f"{BACKEND_URL}/events",
                            json=payload,
                            timeout=2,
                        )
                    except Exception as e:
                        print(f"[ERROR] Backend nicht erreichbar: {e}")

        except Exception as e:
            print(f"[ERROR] Fehler im Screenshot-Loop: {e}")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
