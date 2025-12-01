# routes/browser_events.py

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.models import BrowserEvent
from backend.schemas import BrowserEventCreate, BrowserEventRead
from routes.deps import get_db

router = APIRouter(
    prefix="/browser-events",
    tags=["browser"]
)


@router.post("/", response_model=dict, status_code=201)
def create_browser_event(
    event: BrowserEventCreate,
    db: Session = Depends(get_db),
):
    db_event = BrowserEvent(
        timestamp=event.timestamp,
        url=event.url,
        title=event.title,
        event_type=event.event_type,
        element_tag=event.element_tag,
        element_type=event.element_type,
        element_id=event.element_id,
        element_name=event.element_name,
        element_label=event.element_label,
        value_preview=event.value_preview,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return {"id": db_event.id}


@router.get("/", response_model=List[BrowserEventRead])
def list_browser_events(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Liefert die letzten Browser-Events (standardmäßig 100, absteigend nach Zeit).
    """
    q = (
        db.query(BrowserEvent)
        .order_by(BrowserEvent.timestamp.desc())
        .limit(limit)
    )
    return q.all()
