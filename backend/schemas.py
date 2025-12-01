# backend/schemas.py

from datetime import datetime
from typing import Optional

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
        orm_mode = True
