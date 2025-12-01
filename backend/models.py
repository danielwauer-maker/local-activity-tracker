# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON
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
