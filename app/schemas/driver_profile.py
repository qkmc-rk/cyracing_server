from typing import Optional
from pydantic import BaseModel


class DriverProfileResponse(BaseModel):
    """车手画像响应"""
    driver_id: int
    driver_name: str
    team_name: str
    nation: str
    total_races: int
    total_laps: int
    total_drive_time_ms: int
    safety_score: float
    ladder_score: int
    license_level: str
    rank_overall: Optional[int] = None

    class Config:
        from_attributes = True


class DriverProfileListItem(BaseModel):
    """车手画像列表项"""
    driver_id: int
    driver_name: str
    team_name: str
    total_races: int
    total_laps: int
    ladder_score: int
    license_level: str
    rank_overall: Optional[int] = None

    class Config:
        from_attributes = True


class RefreshResult(BaseModel):
    """刷新画像结果"""
    message: str
    updated_count: int
