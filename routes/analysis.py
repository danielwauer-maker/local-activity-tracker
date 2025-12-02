from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.analysis_local import get_dashboard_summary

router = APIRouter(prefix="/analysis")

@router.get("/dashboard/summary")
def dashboard_summary(from_: str = None, to: str = None, db: Session = Depends(get_db)):
    return get_dashboard_summary(db, from_, to)
