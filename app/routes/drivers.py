from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Driver, RaceResult, Race, Track, Car
from app.schemas.driver import DriverRaceItem

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{steam_guid}/races", response_model=List[DriverRaceItem])
def get_driver_races(
    steam_guid: str,
    db: Session = Depends(get_db)
):

    driver = (
        db.query(Driver)
        .filter(Driver.steam_guid == steam_guid)
        .first()
    )

    if not driver:
        raise HTTPException(
            status_code=404,
            detail="Driver not found"
        )

    results = (
        db.query(RaceResult, Race, Track, Car)
        .join(
            Race,
            Race.race_id == RaceResult.race_id
        )
        .join(
            Track,
            Track.track_id == Race.track_id
        )
        .join(
            Car,
            Car.car_id == RaceResult.car_id
        )
        .filter(
            RaceResult.driver_id == driver.driver_id,
            RaceResult.laps_completed > 0,
        )
        .order_by(Race.race_date.desc())
        .all()
    )

    response = []

    for rr, race, track, car in results:

        response.append(
            DriverRaceItem(
                race_id=race.race_id,
                date=str(race.race_date),
                session_type=race.race_type,
                track_name=track.track_name,
                car_model=car.car_model,
                position=rr.position,
                best_lap_ms=rr.best_lap_ms,
                total_time_ms=rr.total_time_ms,
                laps_completed=rr.laps_completed,
            )
        )

    return response