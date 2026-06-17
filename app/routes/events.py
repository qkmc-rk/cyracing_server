from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/race/{race_id}")
def events_by_race(race_id: int, db: Session = Depends(get_db)):
    events = db.query(models.Event).filter(models.Event.race_id == race_id).all()
    return events