from pydantic import BaseModel
from typing import Optional, List


class RaceListItem(BaseModel):
    race_id: int
    date: str
    session_type: str
    track_name: str
    entrants: List[str]

class RaceSummaryEntrant(BaseModel):
    driver_id: int
    driver_name: str
    car_model: str
    total_time_ms: int
    laps_completed: int
    incidents_count: int
    best_lap_ms: Optional[int] = None
    avg_clean_lap_ms: Optional[float] = None
    total_cuts: int
    tyre_type: Optional[str] = None

class RaceSummary(BaseModel):
    race_id: int
    track_name: str
    session_type: str
    date: str
    entrants: List[RaceSummaryEntrant]


class DriverLapDetail(BaseModel):
    """单圈详细数据"""
    lap_number: int
    lap_time_ms: int
    sector1_ms: Optional[int] = None
    sector2_ms: Optional[int] = None
    sector3_ms: Optional[int] = None
    cuts: int
    tyre_type: Optional[str] = None
    is_valid: bool

    class Config:
        from_attributes = True


class DriverLapDetailResponse(BaseModel):
    """车手单场比赛圈速详情"""
    race_id: int
    driver_id: int
    driver_name: str
    car_model: str
    final_position: Optional[int] = None
    total_time_ms: Optional[int] = None
    laps_completed: int
    laps: List[DriverLapDetail]


class CollisionPosition(BaseModel):
    """碰撞坐标"""
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None


class DriverCollisionEvent(BaseModel):
    """单条碰撞事件"""
    driver: str
    other_driver: Optional[str] = None
    type: str
    impact_speed: Optional[float] = None
    relative_position: Optional[CollisionPosition] = None
    world_position: Optional[CollisionPosition] = None


class DriverCollisionResponse(BaseModel):
    """车手单场比赛碰撞事件"""
    race_id: int
    driver_id: int
    driver_name: str
    total_events: int
    collisions: List[DriverCollisionEvent]