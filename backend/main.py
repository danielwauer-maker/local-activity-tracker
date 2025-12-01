# backend/main.py
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from .db import SessionLocal, init_db
from .models import Event as EventModel, Setting as SettingModel
from pathlib import Path
from routes import export as export_routes
from routes import browser_events

from backend.db import get_db
from backend import models
from backend.schemas import BrowserCollectorStatus, BrowserEventOut

app = FastAPI(title="Local Activity Tracker")
BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "templates" / "index.html"

DEFAULT_RETENTION_DAYS = 7

app.include_router(export_routes.router)
app.include_router(browser_events.router)


# =========================
# Pydantic-Modelle
# =========================

class EventIn(BaseModel):
    timestamp: datetime
    source: str
    type: str
    payload: dict


class EventOut(EventIn):
    id: int


class TopWindowOut(BaseModel):
    app: Optional[str]
    title: Optional[str]
    total_seconds: float
    total_minutes: float
    total_hours: float


class RoutineOut(BaseModel):
    sequence: List[Dict[str, Optional[str]]]  # Liste von {app, title}
    count: int
    total_seconds: float
    total_minutes: float
    total_hours: float


class AutomationCandidateOut(BaseModel):
    app: Optional[str]
    title: Optional[str]
    avg_minutes_per_day: float
    yearly_hours: float
    hourly_rate: float
    yearly_cost: float
    automation_factor: float
    potential_savings_per_year: float


class SettingsIn(BaseModel):
    screenshot_retention_days: int = DEFAULT_RETENTION_DAYS


class SettingsOut(SettingsIn):
    pass


# =========================
# DB-Dependency & Helper
# =========================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_utc(dt: datetime) -> datetime:
    """Sorgt dafür, dass alle Datumswerte als UTC-aware vorliegen."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_settings(db: Session) -> SettingsOut:
    row = db.query(SettingModel).filter(SettingModel.key == "screenshot_retention_days").first()
    if row is None:
        return SettingsOut(screenshot_retention_days=DEFAULT_RETENTION_DAYS)
    try:
        days = int(row.value)
    except ValueError:
        days = DEFAULT_RETENTION_DAYS
    if days < 1:
        days = 1
    return SettingsOut(screenshot_retention_days=days)


def save_settings(db: Session, settings: SettingsIn) -> SettingsOut:
    days = settings.screenshot_retention_days
    if days < 1:
        days = 1
    s = db.query(SettingModel).filter(SettingModel.key == "screenshot_retention_days").first()
    if s is None:
        s = SettingModel(key="screenshot_retention_days", value=str(days))
        db.add(s)
    else:
        s.value = str(days)
    db.commit()
    return SettingsOut(screenshot_retention_days=days)


# =========================
# Startup
# =========================

@app.on_event("startup")
def startup():
    init_db()


# =========================
# Root: Dashboard-HTML
# =========================

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(INDEX_PATH.read_text(encoding="utf-8"))


# =========================
# Settings-API
# =========================

@app.get("/settings", response_model=SettingsOut)
def api_get_settings(db: Session = Depends(get_db)):
    return get_settings(db)


@app.post("/settings", response_model=SettingsOut)
def api_set_settings(settings: SettingsIn, db: Session = Depends(get_db)):
    return save_settings(db, settings)


# =========================
# Event-API
# =========================

@app.post("/events", response_model=EventOut)
def create_event(event: EventIn, db: Session = Depends(get_db)):
    db_event = EventModel(
        timestamp=event.timestamp,
        source=event.source,
        type=event.type,
        payload=event.payload,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return EventOut(
        id=db_event.id,
        timestamp=db_event.timestamp,
        source=db_event.source,
        type=db_event.type,
        payload=db_event.payload,
    )


@app.post("/events/batch")
def create_events_batch(data: Dict[str, Any], db: Session = Depends(get_db)):
    events = data.get("events", [])
    created = 0

    for e in events:
        ts = e["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

        db_event = EventModel(
            timestamp=ts,
            source=e["source"],
            type=e["type"],
            payload=e["payload"],
        )
        db.add(db_event)
        created += 1

    db.commit()
    return {"inserted": created}


@app.get("/events", response_model=List[EventOut])
def list_events(
    source: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(EventModel).order_by(EventModel.timestamp.desc())
    if source:
        q = q.filter(EventModel.source == source)
    rows = q.limit(limit).all()
    return [
        EventOut(
            id=r.id,
            timestamp=r.timestamp,
            source=r.source,
            type=r.type,
            payload=r.payload,
        )
        for r in rows
    ]


# =========================
# Analyse-APIs
# =========================

@app.get("/analysis/timeline", response_model=List[EventOut])
def analysis_timeline(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    source: Optional[str] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """
    Liefert Events, standardmäßig mit den NEUESTEN zuerst (desc).
    Wird für Timeline, Input- und Dokument-Anzeige genutzt.
    """
    q = db.query(EventModel)

    if start:
        q = q.filter(EventModel.timestamp >= start)
    if end:
        q = q.filter(EventModel.timestamp <= end)
    if source:
        q = q.filter(EventModel.source == source)

    # Wichtig: neueste zuerst
    rows = q.order_by(EventModel.timestamp.desc()).limit(limit).all()

    return [
        EventOut(
            id=r.id,
            timestamp=r.timestamp,
            source=r.source,
            type=r.type,
            payload=r.payload,
        )
        for r in rows
    ]


@app.get("/analysis/top-windows", response_model=List[TopWindowOut])
def analysis_top_windows(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(EventModel).filter(EventModel.source == "window")

    if start:
        q = q.filter(EventModel.timestamp >= start)
    if end:
        q = q.filter(EventModel.timestamp <= end)

    rows = q.order_by(EventModel.timestamp.asc()).all()

    if not rows:
        return []

    durations: Dict[tuple, float] = {}

    for idx, row in enumerate(rows):
        this_ts = _to_utc(row.timestamp)
        payload = row.payload or {}
        app = payload.get("app")
        title = payload.get("title")

        if idx < len(rows) - 1:
            next_ts = _to_utc(rows[idx + 1].timestamp)
        else:
            next_ts = _to_utc(end) if end else datetime.now(timezone.utc)

        delta = (next_ts - this_ts).total_seconds()
        if delta <= 0:
            continue

        key = (app, title)
        durations[key] = durations.get(key, 0.0) + delta

    result: List[TopWindowOut] = []
    for (app, title), secs in durations.items():
        result.append(
            TopWindowOut(
                app=app,
                title=title,
                total_seconds=secs,
                total_minutes=secs / 60.0,
                total_hours=secs / 3600.0,
            )
        )

    result.sort(key=lambda x: x.total_seconds, reverse=True)
    return result[:limit]


@app.get("/analysis/routines", response_model=List[RoutineOut])
def analysis_routines(
    n: int = 3,
    min_count: int = 3,
    days: int = 3,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    if n < 2:
        n = 2

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    q = (
        db.query(EventModel)
        .filter(EventModel.source == "window")
        .filter(EventModel.timestamp >= start)
        .filter(EventModel.timestamp <= end)
        .order_by(EventModel.timestamp.asc())
    )
    rows = q.all()
    if not rows:
        return []

    events = []
    for r in rows:
        ts = _to_utc(r.timestamp)
        payload = r.payload or {}
        app = payload.get("app")
        title = payload.get("title")
        events.append((app, title, ts))

    if len(events) < n:
        return []

    durations = []
    for i, (_, _, ts) in enumerate(events):
        if i < len(events) - 1:
            next_ts = events[i + 1][2]
        else:
            next_ts = end
        delta = (next_ts - ts).total_seconds()
        if delta < 0:
            delta = 0
        durations.append(delta)

    from collections import defaultdict
    seq_stats = defaultdict(lambda: {"count": 0, "total_seconds": 0.0})

    for i in range(len(events) - n + 1):
        seq = tuple((events[i + j][0], events[i + j][1]) for j in range(n))
        seq_dur = sum(durations[i : i + n])
        stats = seq_stats[seq]
        stats["count"] += 1
        stats["total_seconds"] += seq_dur

    filtered = [
        (seq, stats)
        for seq, stats in seq_stats.items()
        if stats["count"] >= min_count
    ]

    filtered.sort(key=lambda x: x[1]["total_seconds"], reverse=True)

    result: List[RoutineOut] = []
    for seq, stats in filtered[:limit]:
        total_sec = stats["total_seconds"]
        result.append(
            RoutineOut(
                sequence=[{"app": a, "title": t} for (a, t) in seq],
                count=stats["count"],
                total_seconds=total_sec,
                total_minutes=total_sec / 60.0,
                total_hours=total_sec / 3600.0,
            )
        )

    return result


@app.get("/analysis/automation-candidates", response_model=List[AutomationCandidateOut])
def analysis_automation_candidates(
    days: int = 7,
    limit: int = 20,
    hourly_rate: float = 60.0,
    automation_factor: float = 0.7,
    working_days_per_year: int = 220,
    min_minutes_per_day: float = 5.0,
    db: Session = Depends(get_db),
):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    q = (
        db.query(EventModel)
        .filter(EventModel.source == "window")
        .filter(EventModel.timestamp >= start)
        .filter(EventModel.timestamp <= end)
        .order_by(EventModel.timestamp.asc())
    )
    rows = q.all()
    if not rows:
        return []

    durations: Dict[tuple, float] = {}

    for idx, row in enumerate(rows):
        this_ts = _to_utc(row.timestamp)
        payload = row.payload or {}
        app = payload.get("app")
        title = payload.get("title")

        if idx < len(rows) - 1:
            next_ts = _to_utc(rows[idx + 1].timestamp)
        else:
            next_ts = end

        delta = (next_ts - this_ts).total_seconds()
        if delta <= 0:
            continue

        key = (app, title)
        durations[key] = durations.get(key, 0.0) + delta

    if not durations:
        return []

    result: List[AutomationCandidateOut] = []
    days_factor = max(days, 1)

    for (app, title), secs in durations.items():
        minutes_total = secs / 60.0
        avg_min_per_day = minutes_total / days_factor

        if avg_min_per_day < min_minutes_per_day:
            continue

        hours_per_year = (avg_min_per_day / 60.0) * working_days_per_year
        yearly_cost = hours_per_year * hourly_rate
        potential_savings = yearly_cost * automation_factor

        result.append(
            AutomationCandidateOut(
                app=app,
                title=title,
                avg_minutes_per_day=avg_min_per_day,
                yearly_hours=hours_per_year,
                hourly_rate=hourly_rate,
                yearly_cost=yearly_cost,
                automation_factor=automation_factor,
                potential_savings_per_year=potential_savings,
            )
        )

    result.sort(key=lambda x: x.potential_savings_per_year, reverse=True)

    return result[:limit]

@app.get("/browser")
def get_browser_timeline(limit: int = 200, db: Session = Depends(get_db)):
    """
    Liefert die letzten Browser-Events (source='browser'),
    neueste zuerst, für die Browser-Timeline im Dashboard.
    """
    rows = (
        db.query(EventModel)
        .filter(EventModel.source == "browser")
        .order_by(EventModel.timestamp.desc())
        .limit(limit)
        .all()
    )

    result = []
    for e in rows:
        payload = e.payload or {}
        result.append(
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "title": payload.get("title"),
                "url": payload.get("url"),
                "event_type": e.type,
            }
        )
    return result

@app.get("/collectors/browser/status", response_model=BrowserCollectorStatus)
def get_browser_status(db: Session = Depends(get_db)):
    # letztes Event der Quelle "browser" holen
    last_event = (
        db.query(models.Event)
        .filter(models.Event.source == "browser")
        .order_by(models.Event.timestamp.desc())
        .first()
    )

    if not last_event:
        return BrowserCollectorStatus(
            last_event=None,
            seconds_since_last_event=None,
            status="offline",
        )

    now = datetime.now(timezone.utc)
    # sicherstellen, dass last_event.timestamp timezone-aware ist
    last_ts = (
        last_event.timestamp
        if last_event.timestamp.tzinfo
        else last_event.timestamp.replace(tzinfo=timezone.utc)
    )
    diff = (now - last_ts).total_seconds()

    if diff <= 60:
        status = "ok"
    elif diff <= 300:
        status = "warn"
    else:
        status = "offline"

    return BrowserCollectorStatus(
        last_event=last_ts,
        seconds_since_last_event=diff,
        status=status,
    )

@app.get("/events/browser/recent", response_model=list[BrowserEventOut])
def get_recent_browser_events(limit: int = 100, db: Session = Depends(get_db)):
    events = (
        db.query(models.Event)
        .filter(models.Event.source == "browser")
        .order_by(models.Event.timestamp.desc())
        .limit(limit)
        .all()
    )
    return events
