from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.database import SessionLocal
from app.models import Driver, DriverProfile, RaceResult, Event
from app.schemas.driver_profile import (
    DriverProfileResponse, DriverProfileListItem, RefreshResult,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- 辅助函数 ----------

def _calc_license_level(ladder_score: int) -> str:
    """根据天梯分计算驾照等级"""
    if ladder_score >= 2000:
        return 'A'
    elif ladder_score >= 1900:
        return 'B'
    elif ladder_score >= 1700:
        return 'C'
    elif ladder_score >= 1500:
        return 'D'
    else:
        return 'N'


def _clamp_safety(score: float) -> float:
    """安全分限制在 [0, 10]"""
    return max(0.0, min(10.0, score))


def refresh_single_driver_profile(driver_id: int, db: Session):
    """
    重新计算并刷新某个车手的画像数据。
    返回更新后的 DriverProfile 对象。
    """
    # 1. 统计比赛数据（仅限真实参赛：至少完成1圈）
    stats = (
        db.query(
            func.count(RaceResult.result_id).label('total_races'),
            func.coalesce(func.sum(RaceResult.laps_completed), 0).label('total_laps'),
            func.coalesce(func.sum(RaceResult.total_time_ms), 0).label('total_drive_time_ms'),
        )
        .filter(RaceResult.driver_id == driver_id, RaceResult.laps_completed > 0)
        .first()
    )

    total_races = stats.total_races or 0
    total_laps = stats.total_laps or 0
    total_drive_time_ms = stats.total_drive_time_ms or 0

    # 2. 统计事故数量（仅限真实参赛的比赛）
    incidents_count = (
        db.query(func.count(Event.event_id))
        .join(
            RaceResult,
            (RaceResult.race_id == Event.race_id) & (RaceResult.driver_id == Event.driver_id)
        )
        .filter(
            Event.driver_id == driver_id,
            RaceResult.laps_completed > 0,
        )
        .scalar()
    ) or 0

    # 3. 计算安全分: 初始 3.0 + 完成比赛数*0.4 - 事故数*0.1
    safety_score = _clamp_safety(3.0 + total_races * 0.4 - incidents_count * 0.1)

    # 4. 计算天梯分: 初始 1350，每场按排名 +30 或 -30
    # 需要每场比赛的参赛人数和该车手的排名
    race_results = (
        db.query(RaceResult.race_id, RaceResult.position)
        .filter(RaceResult.driver_id == driver_id, RaceResult.laps_completed > 0)
        .all()
    )

    ladder_score = 1350
    for race_id, position in race_results:
        if position is None:
            continue
        # 统计该场比赛的真实参赛人数
        total_entrants = (
            db.query(func.count(RaceResult.result_id))
            .filter(RaceResult.race_id == race_id, RaceResult.laps_completed > 0)
            .scalar()
        ) or 0
        if total_entrants == 0:
            continue
        half = total_entrants / 2.0
        if position <= half:
            ladder_score += 30
        else:
            ladder_score -= 30

    # 5. 驾照等级
    license_level = _calc_license_level(ladder_score)

    # 6. 更新或创建 profile
    profile = db.query(DriverProfile).filter(
        DriverProfile.driver_id == driver_id
    ).first()

    if not profile:
        profile = DriverProfile(driver_id=driver_id)
        db.add(profile)

    profile.total_races = total_races
    profile.total_laps = total_laps
    profile.total_drive_time_ms = total_drive_time_ms
    profile.safety_score = safety_score
    profile.ladder_score = ladder_score
    profile.license_level = license_level

    db.flush()

    # 7. 更新全服排名（按天梯分降序）
    db.query(DriverProfile).update({'rank_overall': None}, synchronize_session=False)
    db.execute(
        text("""
        UPDATE driver_profiles AS dp
        JOIN (
            SELECT profile_id,
                   RANK() OVER (ORDER BY ladder_score DESC) AS rn
            FROM driver_profiles
        ) AS ranked ON dp.profile_id = ranked.profile_id
        SET dp.rank_overall = ranked.rn
        """)
    )

    return profile


# ---------- 接口 ----------

@router.get("/profiles", response_model=List[DriverProfileListItem])
def list_driver_profiles(
    order_by: str = "ladder_score",
    db: Session = Depends(get_db),
):
    """
    获取所有车手画像列表。

    order_by: ladder_score（天梯分降序）| total_races（总比赛降序）| safety_score（安全分降序）
    """
    order_map = {
        "ladder_score": DriverProfile.ladder_score.desc(),
        "total_races": DriverProfile.total_races.desc(),
        "safety_score": DriverProfile.safety_score.desc(),
    }
    order_col = order_map.get(order_by, DriverProfile.ladder_score.desc())

    profiles = (
        db.query(DriverProfile)
        .order_by(order_col)
        .all()
    )

    result = []
    for p in profiles:
        driver = p.driver
        result.append(
            DriverProfileListItem(
                driver_id=p.driver_id,
                driver_name=driver.driver_name if driver else "",
                team_name=driver.team_name or "" if driver else "",
                total_races=p.total_races,
                total_laps=p.total_laps,
                ladder_score=p.ladder_score,
                license_level=p.license_level,
                rank_overall=p.rank_overall,
            )
        )
    return result


@router.get("/profiles/{driver_id}", response_model=DriverProfileResponse)
def get_driver_profile(driver_id: int, db: Session = Depends(get_db)):
    """
    获取指定车手的画像详情。
    包含总比赛场次、总驾驶时间、总圈数、安全分、天梯分、驾照等级、全服排名。
    """
    profile = (
        db.query(DriverProfile)
        .filter(DriverProfile.driver_id == driver_id)
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="车手画像不存在，请先刷新数据")

    driver = profile.driver
    if not driver:
        raise HTTPException(status_code=404, detail="车手信息不存在")

    return DriverProfileResponse(
        driver_id=profile.driver_id,
        driver_name=driver.driver_name,
        team_name=driver.team_name or "",
        nation=driver.nation or "",
        total_races=profile.total_races,
        total_laps=profile.total_laps,
        total_drive_time_ms=profile.total_drive_time_ms,
        safety_score=float(profile.safety_score),
        ladder_score=profile.ladder_score,
        license_level=profile.license_level,
        rank_overall=profile.rank_overall,
    )


@router.post("/profiles/refresh", response_model=RefreshResult)
def refresh_all_profiles(db: Session = Depends(get_db)):
    """
    刷新所有车手的画像数据。
    遍历所有有比赛记录的车手，重新计算安全分、天梯分、驾照等级、排名等。
    """
    # 获取所有真实参赛过的车手 ID
    driver_ids = (
        db.query(RaceResult.driver_id)
        .filter(RaceResult.laps_completed > 0)
        .distinct()
        .all()
    )
    driver_ids = [d[0] for d in driver_ids]

    for did in driver_ids:
        refresh_single_driver_profile(did, db)

    db.commit()

    return RefreshResult(
        message="所有车手画像刷新完成",
        updated_count=len(driver_ids),
    )


@router.post("/profiles/{driver_id}/refresh", response_model=RefreshResult)
def refresh_one_profile(driver_id: int, db: Session = Depends(get_db)):
    """
    刷新指定车手的画像数据。
    """
    # 检查车手是否存在
    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="车手不存在")

    refresh_single_driver_profile(driver_id, db)
    db.commit()

    return RefreshResult(
        message=f"车手 {driver.driver_name} 画像刷新完成",
        updated_count=1,
    )
