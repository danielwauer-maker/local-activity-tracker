# backend/schemas.py

from datetime import datetime
from typing import Optional, Literal, Any

from pydantic import BaseModel


class BrowserEventBase(BaseModel):
    timestamp: Optional[datetime] = None
    url: str
    title: Optional[str] = None
    event_type: str

    element_tag: Optional[str] = None
    element_type: Optional[str] = None
    element_id: Optional[str] = None
    element_name: Optional[str] = None

    element_label: Optional[str] = None
    value_preview: Optional[str] = None


class BrowserEventCreate(BrowserEventBase):
    """Payload, das die Extension schickt."""
    pass


class BrowserEventRead(BrowserEventBase):
    id: int

    class Config:
        from_attributes = True  # falls du SQLAlchemy benutzt (Pydantic v2)

class BrowserCollectorStatus(BaseModel):
    last_event: Optional[datetime]
    seconds_since_last_event: Optional[float]
    status: Literal["ok", "warn", "offline"]

class BrowserEventOut(BaseModel):
    id: int
    timestamp: datetime
    type: str
    payload: dict[str, Any]

    class Config:
        from_attributes = True  # falls du SQLAlchemy benutzt (Pydantic v2)
