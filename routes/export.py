# routes/export.py
from datetime import datetime
from typing import Optional, List

import io
import csv
import json

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .deps import get_db       # <- anpassen, falls dein Pfad anders ist
from .models import Event      # <- anpassen, falls dein Pfad anders ist

router = APIRouter(
    prefix="/export",
    tags=["export"],
)


@router.get("/events")
def export_events(
    source: str = Query(..., description="Collector/Quelle, z.B. input, window, screenshot, document"),
    fmt: str = Query("csv", regex="^(csv|json)$"),
    date_from: Optional[datetime] = Query(
        None,
        description="Startzeit (inklusive), ISO8601, z.B. 2025-12-01T00:00:00"
    ),
    date_to: Optional[datetime] = Query(
        None,
        description="Endzeit (inklusive), ISO8601, z.B. 2025-12-01T23:59:59"
    ),
    db: Session = Depends(get_db),
):
    """
    Exportiert Events eines Collectors als CSV oder JSON.
    Optional: Zeitraum filterbar über date_from / date_to.
    """
    q = db.query(Event).filter(Event.source == source)

    if date_from is not None:
        q = q.filter(Event.timestamp >= date_from)
    if date_to is not None:
        q = q.filter(Event.timestamp <= date_to)

    q = q.order_by(Event.timestamp.asc())
    events: List[Event] = q.all()

    if not events:
        raise HTTPException(status_code=404, detail="Keine Events für die Filter gefunden.")

    if fmt == "json":
        return _export_as_json(events, source)
    else:
        return _export_as_csv(events, source)


def _export_as_json(events: List[Event], source: str) -> StreamingResponse:
    """
    Export als JSON: Liste von Objekten mit id, timestamp, source, type, payload (voll).
    """
    data = []
    for ev in events:
        # falls payload kein dict ist (z.B. Text), hier ggf. json.loads(...)
        payload = ev.payload if isinstance(ev.payload, dict) else ev.payload

        data.append(
            {
                "id": ev.id,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "source": ev.source,
                "type": ev.type,
                "payload": payload,
            }
        )

    buf = io.StringIO()
    json.dump(data, buf, ensure_ascii=False, indent=2, default=str)
    buf.seek(0)

    filename = f"events_{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return StreamingResponse(
        buf,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


def _export_as_csv(events: List[Event], source: str) -> StreamingResponse:
    """
    CSV in übersichtlicher Form:

    Spalten:
    - id
    - timestamp
    - source
    - type
    - app (payload.app)
    - title (payload.title)
    - pid (payload.pid)
    - payload_rest (alles andere aus payload als JSON-String)

    So kannst du in Excel/PowerBI schnell filtern / gruppieren.
    """
    buf = io.StringIO()
    fieldnames = ["id", "timestamp", "source", "type", "app", "title", "pid", "payload_rest"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for ev in events:
        payload = ev.payload if isinstance(ev.payload, dict) else {}

        # Standard-Felder aus dem payload ziehen
        app = payload.pop("app", None)
        title = payload.pop("title", None)
        pid = payload.pop("pid", None)

        # Rest als kompakter JSON-String
        payload_rest = json.dumps(payload, ensure_ascii=False) if payload else ""

        row = {
            "id": ev.id,
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            "source": ev.source,
            "type": ev.type,
            "app": app,
            "title": title,
            "pid": pid,
            "payload_rest": payload_rest,
        }
        writer.writerow(row)

        # wichtig: payload war evtl. ein dict-Objekt direkt aus dem ORM – wir sollten es
        # nicht dauerhaft verändert lassen:
        if isinstance(ev.payload, dict):
            # optional: zurücksetzen, falls du später im Code nochmal mit ev.payload arbeitest
            ev.payload.update({"app": app, "title": title, "pid": pid})

    buf.seek(0)

    filename = f"events_{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        buf,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
