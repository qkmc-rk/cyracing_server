from typing import Optional
from pydantic import BaseModel


class DriverRaceItem(BaseModel):

    race_id: int

    date: str

    session_type: str

    track_name: str

    car_model: str

    position: Optional[int] = None

    best_lap_ms: Optional[int] = None

    total_time_ms: Optional[int] = None

    laps_completed: Optional[int] = None