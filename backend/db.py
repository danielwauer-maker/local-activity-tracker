# backend/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

DATABASE_URL = "sqlite:///./tracker.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # nur für SQLite nötig
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Einmalig beim Start aufrufen, um die Tabellen zu erstellen."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI-Dependency für DB-Sessions.

    Nutzung:
        @app.get("/irgendwas")
        def foo(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
