# analysis_local.py
#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
from backend.db import SessionLocal
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.models import Event, BrowserEvent


def summarize_top_windows(days: int = 1, limit: int = 20):
    """
    Konsolen-Auswertung: Top Fenster/Anwendungen in den letzten X Tagen.
    """
    db = SessionLocal()
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        q = (
            db.query(Event)
            .filter(Event.source == "window")
            .filter(Event.timestamp >= start)
            .filter(Event.timestamp <= end)
            .order_by(Event.timestamp.asc())
        )
        rows = q.all()
        if not rows:
            print("Keine window-Events im Zeitraum gefunden.")
            return

        durations = {}

        for idx, row in enumerate(rows):
            this_ts = row.timestamp
            payload = row.payload or {}
            app = payload.get("app")
            title = payload.get("title")

            if idx < len(rows) - 1:
                next_ts = rows[idx + 1].timestamp
            else:
                next_ts = end

            delta = (next_ts - this_ts).total_seconds()
            if delta < 0:
                continue

            key = (app, title)
            durations[key] = durations.get(key, 0.0) + delta

        # sortieren
        items = sorted(durations.items(), key=lambda kv: kv[1], reverse=True)[:limit]

        print(f"Top Fenster/Anwendungen (letzte {days} Tage):")
        print("-" * 80)
        for (app, title), secs in items:
            mins = secs / 60.0
            hours = secs / 3600.0
            print(f"{hours:5.2f} h  | {mins:6.1f} min  | {app or '???'}  | {title or ''}")
    finally:
        db.close()


def summarize_daily_usage(days: int = 7):
    """
    Zeigt grob, wie viele Stunden pro Tag aufgezeichnet wurden (Fensteraktivität).
    """
    db = SessionLocal()
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        q = (
            db.query(Event)
            .filter(Event.source == "window")
            .filter(Event.timestamp >= start)
            .filter(Event.timestamp <= end)
            .order_by(Event.timestamp.asc())
        )
        rows = q.all()
        if not rows:
            print("Keine window-Events im Zeitraum gefunden.")
            return

        # Pro Tag: earliest vs latest
        by_date = {}
        for row in rows:
            d = row.timestamp.astimezone(timezone.utc).date()
            if d not in by_date:
                by_date[d] = [row.timestamp, row.timestamp]
            else:
                if row.timestamp < by_date[d][0]:
                    by_date[d][0] = row.timestamp
                if row.timestamp > by_date[d][1]:
                    by_date[d][1] = row.timestamp

        print(f"Aktive Fensterzeiten (Fensterwechsel) pro Tag, letzte {days} Tage:")
        print("-" * 80)
        for d in sorted(by_date.keys()):
            start_ts, end_ts = by_date[d]
            span_hours = (end_ts - start_ts).total_seconds() / 3600.0
            print(f"{d} : ~{span_hours:5.2f} h zwischen erstem und letztem Fensterwechsel")
    finally:
        db.close()


def parse_range(from_, to):
    if not from_ or not to:
        return None, None
    try:
        start = datetime.fromisoformat(from_.replace("Z", ""))
        end = datetime.fromisoformat(to.replace("Z", ""))
        return start, end
    except:
        return None, None


def get_dashboard_summary(db: Session, from_, to):
    start, end = parse_range(from_, to)

    q = db.query(Event)
    if start and end:
        q = q.filter(Event.timestamp >= start, Event.timestamp <= end)

    # --- Fensteraktivität (source="window") ---
    window_events = q.filter(Event.source == "window").all()
    total_active_hours = 0.0
    if window_events:
        for ev in window_events:
            p = ev.payload or {}
            d = p.get("duration_seconds") or p.get("duration") or 0
            total_active_hours += d / 3600

    # --- Input ---
    input_q = q.filter(Event.source == "input")
    total_keystrokes = input_q.filter(Event.type == "key_down").count()
    total_clicks = input_q.filter(Event.type == "mouse_click").count()

    # --- Dokumente ---
    document_q = q.filter(Event.source == "document")
    document_events = document_q.count()

    # --- Browser ---
    browser_q = db.query(BrowserEvent)
    if start and end:
        browser_q = browser_q.filter(BrowserEvent.timestamp >= start,
                                     BrowserEvent.timestamp <= end)
    browser_events = browser_q.count()

    # --- Screenshots (falls du später Events/Tabellen dafür nutzt) ---
    screenshot_count = q.filter(Event.source == "screenshot").count()

    # Coverage rudimentär: Screenshots pro Stunde geschätzt
    coverage_percent = None
    if screenshot_count > 0 and start and end:
        duration_hours = (end - start).total_seconds() / 3600
        if duration_hours > 0:
            # Beispiel: 360 Screenshots in 6h → 1/min → ~100%
            shots_per_hour = screenshot_count / duration_hours
            coverage_percent = min(100, shots_per_hour / 60 * 100)  # 60/min = Perfekt

    return {
        "total_active_hours": round(total_active_hours, 2),
        "total_keystrokes": total_keystrokes,
        "total_clicks": total_clicks,
        "document_events": document_events,
        "browser_events": browser_events,
        "screenshot_count": screenshot_count,
        "coverage_percent": coverage_percent
    }


if __name__ == "__main__":
    # Beispiele:
    summarize_top_windows(days=1, limit=15)
    print()
    summarize_daily_usage(days=7)
