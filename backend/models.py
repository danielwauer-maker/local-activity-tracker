# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    source = Column(String, index=True)
    type = Column(String, index=True)
    payload = Column(JSON)

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

class BrowserEvent(Base):
    __tablename__ = "browser_events"

    id = Column(Integer, primary_key=True, index=True)

    # Wann ist das Event passiert?
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Kontext
    url = Column(Text, index=True, nullable=False)
    title = Column(Text, nullable=True)

    # Was ist passiert?
    event_type = Column(String(50), index=True, nullable=False)  # z.B. click, input, submit

    # Welches Element war betroffen?
    element_tag = Column(String(50), nullable=True)   # BUTTON, INPUT, A, ...
    element_type = Column(String(50), nullable=True)  # type="text", "email", ...
    element_id = Column(String(255), nullable=True)
    element_name = Column(String(255), nullable=True)

    # Lesbarer Kontext
    element_label = Column(Text, nullable=True)       # Label-Text / Button-Beschriftung
    value_preview = Column(Text, nullable=True)       # Anonymisierte/gekürzte Eingabewerte
