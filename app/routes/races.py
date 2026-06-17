from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas.race import RaceListItem
from app.models import Race, RaceResult, Driver, Car, Event, Lap, Track
from app.schemas.race import (
    RaceSummary, RaceSummaryEntrant,
    DriverLapDetail, DriverLapDetailResponse,
    DriverCollisionEvent, DriverCollisionResponse,
    CollisionPosition,
)
from sqlalchemy import func
router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[RaceListItem])
def get_races(db: Session = Depends(get_db)):

    races = (
        db.query(Race)
        .order_by(Race.race_date.desc())
        .all()
    )

    result = []

    for race in races:

        track = (
            db.query(Track)
            .filter(Track.track_id == race.track_id)
            .first()
        )

        entrants_query = (
            db.query(Driver.driver_name)
            .join(
                RaceResult,
                RaceResult.driver_id == Driver.driver_id
            )
            .filter(
                RaceResult.race_id == race.race_id,
                RaceResult.laps_completed > 0,
            )
            .all()
        )

        entrants = [e[0] for e in entrants_query]

        result.append(
            RaceListItem(
                race_id=race.race_id,
                date=str(race.race_date),
                session_type=race.race_type,
                track_name=track.track_name if track else "",
                entrants=entrants,
            )
        )

    return result


@router.get("/summaries", response_model=List[RaceSummary])
def get_all_race_summaries(db: Session = Depends(get_db)):
    """批量返回所有比赛的摘要数据，仅需一次请求。"""

    races = db.query(Race).order_by(Race.race_date.desc()).all()
    if not races:
        return []

    race_ids = [r.race_id for r in races]
    track_ids = [r.track_id for r in races]

    # 批量加载赛道
    tracks_map = {}
    if track_ids:
        tracks = db.query(Track).filter(Track.track_id.in_(track_ids)).all()
        tracks_map = {t.track_id: t for t in tracks}

    # 批量加载所有比赛结果（仅限真实参赛者：laps_completed > 0）
    results = (
        db.query(RaceResult)
        .filter(RaceResult.race_id.in_(race_ids), RaceResult.laps_completed > 0)
        .all()
    )

    # 批量加载车手和赛车
    driver_ids = list(set(r.driver_id for r in results))
    car_ids = list(set(r.car_id for r in results))

    drivers_map = {}
    if driver_ids:
        drivers = db.query(Driver).filter(Driver.driver_id.in_(driver_ids)).all()
        drivers_map = {d.driver_id: d for d in drivers}

    cars_map = {}
    if car_ids:
        cars = db.query(Car).filter(Car.car_id.in_(car_ids)).all()
        cars_map = {c.car_id: c for c in cars}

    # 批量加载事故计数
    incidents = (
        db.query(Event.race_id, Event.driver_id, func.count(Event.event_id))
        .filter(Event.race_id.in_(race_ids))
        .group_by(Event.race_id, Event.driver_id)
        .all()
    )
    incidents_map = {(r, d): c for r, d, c in incidents}

    # 批量加载所有圈速数据
    laps = db.query(Lap).filter(Lap.race_id.in_(race_ids)).all()
    laps_by_key: Dict[Tuple[int, int], List[Lap]] = defaultdict(list)
    for lap in laps:
        laps_by_key[(lap.race_id, lap.driver_id)].append(lap)

    # 按 race_id 分组比赛结果
    results_by_race: Dict[int, List[RaceResult]] = defaultdict(list)
    for r in results:
        results_by_race[r.race_id].append(r)

    # 组装汇总数据
    summaries: List[RaceSummary] = []
    for race in races:
        track = tracks_map.get(race.track_id)
        entrants: List[RaceSummaryEntrant] = []

        for r in results_by_race.get(race.race_id, []):
            driver = drivers_map.get(r.driver_id)
            car = cars_map.get(r.car_id)

            incident_count = incidents_map.get((race.race_id, r.driver_id), 0)

            driver_laps = laps_by_key.get((race.race_id, r.driver_id), [])
            clean_times = [
                lap.lap_time_ms for lap in driver_laps
                if lap.lap_time_ms and lap.cuts == 0
            ]
            avg_clean = float(sum(clean_times) / len(clean_times)) if clean_times else 0.0
            total_cuts = sum(lap.cuts or 0 for lap in driver_laps)
            tyre_type = driver_laps[0].tyre_type if driver_laps else None
            best_lap = min(clean_times) if clean_times else None

            entrants.append(RaceSummaryEntrant(
                driver_id=r.driver_id,
                driver_name=driver.driver_name if driver else "",
                car_model=car.car_model if car else "",
                total_time_ms=r.total_time_ms or 0,
                laps_completed=r.laps_completed or 0,
                incidents_count=incident_count,
                best_lap_ms=best_lap,
                avg_clean_lap_ms=avg_clean,
                total_cuts=total_cuts,
                tyre_type=tyre_type,
            ))

        summaries.append(RaceSummary(
            race_id=race.race_id,
            track_name=track.track_name if track else "",
            session_type=race.race_type,
            date=str(race.race_date),
            entrants=entrants,
        ))

    return summaries


@router.get("/races/{race_id}/summary", response_model=RaceSummary)
def get_race_summary(race_id: int, db: Session = Depends(get_db)):

    race = db.query(Race).filter(Race.race_id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    track = db.query(Track).filter(Track.track_id == race.track_id).first()

    # 查询所有真实参赛结果（仅限完成至少1圈的选手）
    results = (
        db.query(RaceResult)
        .filter(RaceResult.race_id == race_id, RaceResult.laps_completed > 0)
        .all()
    )
    entrants = []

    for r in results:
        driver = db.query(Driver).filter(Driver.driver_id == r.driver_id).first()
        car = db.query(Car).filter(Car.car_id == r.car_id).first()

        # 事故个数
        incidents_count = db.query(func.count(Event.event_id)).filter(
            Event.race_id == race_id,
            Event.driver_id == r.driver_id
        ).scalar() or 0

        # 圈速信息
        laps = db.query(Lap).filter(
            Lap.race_id == race_id,
            Lap.driver_id == r.driver_id
        ).all()

        lap_times = [lap.lap_time_ms for lap in laps if lap.lap_time_ms and lap.cuts == 0]
        avg_clean_lap = float(sum(lap_times) / len(lap_times)) if lap_times else 0
        total_cuts = sum(lap.cuts for lap in laps)
        tyre_type = laps[0].tyre_type if laps else ""

        best_lap = min(lap_times) if lap_times else None

        entrants.append(
            RaceSummaryEntrant(
                driver_id=r.driver_id,
                driver_name=driver.driver_name if driver else "",
                car_model=car.car_model if car else "",
                total_time_ms=r.total_time_ms,
                laps_completed=r.laps_completed,
                incidents_count=incidents_count,
                best_lap_ms=best_lap,
                avg_clean_lap_ms=avg_clean_lap,
                total_cuts=total_cuts,
                tyre_type=tyre_type
            )
        )

    return RaceSummary(
        race_id=race.race_id,
        track_name=track.track_name if track else "",
        session_type=race.race_type,
        date=str(race.race_date),
        entrants=entrants
    )




@router.get("/races/{race_id}/laps", response_model=List[DriverLapDetailResponse])
def get_race_all_laps(race_id: int, db: Session = Depends(get_db)):
    """返回该场比赛所有有效参赛者的单圈数据。"""

    race = db.query(Race).filter(Race.race_id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    # 查询所有有效参赛者
    results = (
        db.query(RaceResult)
        .filter(RaceResult.race_id == race_id, RaceResult.laps_completed > 0)
        .all()
    )

    if not results:
        return []

    driver_ids = [r.driver_id for r in results]
    car_ids = [r.car_id for r in results]

    # 批量加载车手和赛车
    drivers_map = {}
    if driver_ids:
        drivers = db.query(Driver).filter(Driver.driver_id.in_(driver_ids)).all()
        drivers_map = {d.driver_id: d for d in drivers}

    cars_map = {}
    if car_ids:
        cars = db.query(Car).filter(Car.car_id.in_(car_ids)).all()
        cars_map = {c.car_id: c for c in cars}

    # 批量加载所有圈速数据
    all_laps = (
        db.query(Lap)
        .filter(Lap.race_id == race_id, Lap.driver_id.in_(driver_ids))
        .order_by(Lap.driver_id, Lap.lap_number.asc())
        .all()
    )

    # 按 driver_id 分组圈速
    laps_by_driver: Dict[int, List[Lap]] = defaultdict(list)
    for lap in all_laps:
        laps_by_driver[lap.driver_id].append(lap)

    # 组装响应
    response: List[DriverLapDetailResponse] = []
    for rr in results:
        driver = drivers_map.get(rr.driver_id)
        car = cars_map.get(rr.car_id)
        driver_laps = laps_by_driver.get(rr.driver_id, [])

        response.append(DriverLapDetailResponse(
            race_id=race.race_id,
            driver_id=rr.driver_id,
            driver_name=driver.driver_name if driver else "",
            car_model=car.car_model if car else "",
            final_position=rr.position,
            total_time_ms=rr.total_time_ms,
            laps_completed=rr.laps_completed or 0,
            laps=[
                DriverLapDetail(
                    lap_number=lap.lap_number,
                    lap_time_ms=lap.lap_time_ms,
                    sector1_ms=lap.sector1_ms,
                    sector2_ms=lap.sector2_ms,
                    sector3_ms=lap.sector3_ms,
                    cuts=lap.cuts or 0,
                    tyre_type=lap.tyre_type,
                    is_valid=bool(lap.is_valid) if lap.is_valid is not None else True,
                )
                for lap in driver_laps
            ],
        ))

    return response


@router.get("/races/{race_id}/driver/{driver_id}/laps", response_model=DriverLapDetailResponse)
def get_driver_laps(race_id: int, driver_id: int, db: Session = Depends(get_db)):
    """
    获取某车手在某场比赛中的圈速详细数据。
    包含：圈数(Lap#)、单圈时间、Sector 1/2/3、切弯次数(Cuts)、轮胎类型(Tyre)
    """

    race = db.query(Race).filter(Race.race_id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # 获取比赛结果（最终排名和总时间）
    race_result = (
        db.query(RaceResult)
        .filter(RaceResult.race_id == race_id, RaceResult.driver_id == driver_id)
        .first()
    )

    if not race_result:
        raise HTTPException(status_code=404, detail="Driver did not participate in this race")

    if (race_result.laps_completed or 0) == 0:
        raise HTTPException(status_code=404, detail="Driver did not complete any laps in this race")

    car = db.query(Car).filter(Car.car_id == race_result.car_id).first()

    # 获取所有圈速数据，按圈数排序
    laps = (
        db.query(Lap)
        .filter(Lap.race_id == race_id, Lap.driver_id == driver_id)
        .order_by(Lap.lap_number.asc())
        .all()
    )

    lap_details = [
        DriverLapDetail(
            lap_number=lap.lap_number,
            lap_time_ms=lap.lap_time_ms,
            sector1_ms=lap.sector1_ms,
            sector2_ms=lap.sector2_ms,
            sector3_ms=lap.sector3_ms,
            cuts=lap.cuts or 0,
            tyre_type=lap.tyre_type,
            is_valid=bool(lap.is_valid) if lap.is_valid is not None else True,
        )
        for lap in laps
    ]

    return DriverLapDetailResponse(
        race_id=race.race_id,
        driver_id=driver.driver_id,
        driver_name=driver.driver_name,
        car_model=car.car_model if car else "",
        final_position=race_result.position,
        total_time_ms=race_result.total_time_ms,
        laps_completed=race_result.laps_completed or 0,
        laps=lap_details,
    )


@router.get("/races/{race_id}/driver/{driver_id}/collisions", response_model=DriverCollisionResponse)
def get_driver_collisions(race_id: int, driver_id: int, db: Session = Depends(get_db)):
    """
    获取某车手在某场比赛中的碰撞事件。
    包含：Driver、Other Driver、Type、Impact Speed、Relative Position、World Position
    """

    race = db.query(Race).filter(Race.race_id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # 获取该车手在该场比赛中的成绩
    race_result = (
        db.query(RaceResult)
        .filter(RaceResult.race_id == race_id, RaceResult.driver_id == driver_id)
        .first()
    )

    if not race_result:
        raise HTTPException(status_code=404, detail="Driver did not participate in this race")

    if (race_result.laps_completed or 0) == 0:
        raise HTTPException(status_code=404, detail="Driver did not complete any laps in this race")

    # 获取该车手在比赛中的所有事件（含碰撞）
    events = (
        db.query(Event)
        .filter(Event.race_id == race_id, Event.driver_id == driver_id)
        .all()
    )

    # 批量获取所有 other_driver 的名字
    other_driver_ids = [e.other_driver_id for e in events if e.other_driver_id]
    other_drivers_map = {}
    if other_driver_ids:
        other_drivers = (
            db.query(Driver)
            .filter(Driver.driver_id.in_(list(set(other_driver_ids))))
            .all()
        )
        other_drivers_map = {d.driver_id: d.driver_name for d in other_drivers}

    collisions = [
        DriverCollisionEvent(
            driver=driver.driver_name,
            other_driver=other_drivers_map.get(e.other_driver_id),
            type=e.event_type,
            impact_speed=float(e.impact_speed) if e.impact_speed is not None else None,
            relative_position=CollisionPosition(
                x=float(e.rel_pos_x) if e.rel_pos_x is not None else None,
                y=float(e.rel_pos_y) if e.rel_pos_y is not None else None,
                z=float(e.rel_pos_z) if e.rel_pos_z is not None else None,
            ),
            world_position=CollisionPosition(
                x=float(e.world_pos_x) if e.world_pos_x is not None else None,
                y=float(e.world_pos_y) if e.world_pos_y is not None else None,
                z=float(e.world_pos_z) if e.world_pos_z is not None else None,
            ),
        )
        for e in events
    ]

    return DriverCollisionResponse(
        race_id=race.race_id,
        driver_id=driver.driver_id,
        driver_name=driver.driver_name,
        total_events=len(collisions),
        collisions=collisions,
    )