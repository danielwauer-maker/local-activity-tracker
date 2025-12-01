from typing import Generator
from sqlalchemy.orm import Session

from backend.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI-Dependency für eine DB-Session.
    Nutzung in Routern z.B.:

        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...

    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
