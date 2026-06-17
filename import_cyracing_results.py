#!/usr/bin/env python3
"""
将 Assetto Corsa 服务器导出的比赛 JSON 导入 cyracing MySQL 数据库。

支持表：tracks, cars, drivers, races, race_results, laps, events

races 表已增加 source_file 字段，用于按 JSON 文件名防止重复导入。

支持两种数据源：
  1. 本地 JSON 文件（原有方式）
  2. 远程服务器（通过 SSH 从远程目录拉取 JSON 文件）
"""
import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import paramiko
import pymysql
from dotenv import load_dotenv
from pymysql.connections import Connection

load_dotenv()

VALID_TYRES = {"HR", "MR", "SR", "WET", "INTER"}
TYRE_MAP = {"H": "HR", "M": "MR", "S": "SR", "HR": "HR", "MR": "MR", "SR": "SR", "W": "WET", "WET": "WET", "I": "INTER", "INTER": "INTER"}


def parse_race_date_from_filename(path: Path) -> datetime:
    m = re.search(r"(\d{4})_(\d{1,2})_(\d{1,2})_(\d{1,2})_(\d{1,2})", path.name)
    if not m:
        return datetime.now()
    y, mo, d, h, mi = map(int, m.groups())
    return datetime(y, mo, d, h, mi, 0)


def normalize_best_lap(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return None
    return None if ivalue >= 999_999_999 else ivalue


def normalize_tyre(value: Any) -> Optional[str]:
    if value is None:
        return None
    mapped = TYRE_MAP.get(str(value).strip().upper())
    return mapped if mapped in VALID_TYRES else None


def execute_scalar(conn: Connection, sql: str, params: tuple = ()) -> Any:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return None if row is None else row[0]


def upsert_track(conn: Connection, track_name: str, track_config: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tracks (track_name, track_config)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE track_id = LAST_INSERT_ID(track_id)
            """,
            (track_name, track_config or ""),
        )
        return int(cur.lastrowid)


def upsert_car(conn: Connection, car_model: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cars (car_model)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE car_id = LAST_INSERT_ID(car_id)
            """,
            (car_model,),
        )
        return int(cur.lastrowid)


def upsert_driver(conn: Connection, steam_guid: str, driver_name: str, team_name: str = "", nation: str = "") -> Optional[int]:
    if not steam_guid:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO drivers (steam_guid, driver_name, team_name, nation)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                driver_id = LAST_INSERT_ID(driver_id),
                driver_name = VALUES(driver_name),
                team_name = VALUES(team_name),
                nation = VALUES(nation)
            """,
            (steam_guid, driver_name or steam_guid, team_name or "", nation or ""),
        )
        return int(cur.lastrowid)


def find_or_create_race(
    conn: Connection,
    track_id: int,
    race_type: str,
    duration_secs: int,
    race_laps: int,
    race_date: datetime,
    server_name: Optional[str],
    source_file: str,
) -> int:
    # 按 JSON 文件名判断是否已经导入过
    existing = execute_scalar(
        conn,
        "SELECT race_id FROM races WHERE source_file=%s LIMIT 1",
        (source_file,),
    )
    if existing:
        return int(existing)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO races (track_id, race_type, duration_secs, race_laps, race_date, server_name, source_file)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (track_id, race_type, duration_secs or 0, race_laps or 0, race_date, server_name, source_file),
        )
        return int(cur.lastrowid)


def build_car_info(data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {int(c.get("CarId")): c for c in data.get("Cars", []) if c.get("CarId") is not None}


def import_events(conn, race_id, events, driver_pk_by_guid, car_pk_by_model, car_info_by_json_id):
    stats = defaultdict(int)
    with conn.cursor() as cur:
        for event in (events or []):
            event_type = event.get("Type")
            driver = event.get("Driver") or {}
            guid = driver.get("Guid") or ""
            driver_id = driver_pk_by_guid.get(guid)
            json_car = car_info_by_json_id.get(int(event.get("CarId") or -1), {})
            car_model = json_car.get("Model") or ""
            car_id = car_pk_by_model.get(car_model)
            if not driver_id or not car_id:
                stats["events_skipped"] += 1
                continue
            other_driver = event.get("OtherDriver") or {}
            other_guid = other_driver.get("Guid") or ""
            other_driver_id = driver_pk_by_guid.get(other_guid)
            other_json_car = car_info_by_json_id.get(int(event.get("OtherCarId") or -1), {})
            other_car_model = other_json_car.get("Model") or ""
            other_car_id = car_pk_by_model.get(other_car_model)
            wp = event.get("WorldPosition") or {}
            rp = event.get("RelPosition") or {}
            cur.execute(
                """
                INSERT INTO events (
                    race_id,event_type,driver_id,car_id,session_car_id,
                    other_driver_id,other_car_id,impact_speed,
                    world_pos_x,world_pos_y,world_pos_z,
                    rel_pos_x,rel_pos_y,rel_pos_z,extra_data
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    race_id,event_type,driver_id,car_id,event.get("CarId"),
                    other_driver_id,other_car_id,event.get("ImpactSpeed"),
                    wp.get("X"),wp.get("Y"),wp.get("Z"),
                    rp.get("X"),rp.get("Y"),rp.get("Z"),
                    json.dumps(event, ensure_ascii=False),
                )
            )
            stats["events_imported"] += 1
    return stats


def import_one_json(conn: Connection, path: Path, server_name: Optional[str] = None) -> Dict[str, int]:
    """从本地 Path 导入一个 JSON 文件。"""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    race_date = parse_race_date_from_filename(path)
    track_id = upsert_track(conn, data.get("TrackName", ""), data.get("TrackConfig", ""))
    race_id = find_or_create_race(
        conn=conn,
        track_id=track_id,
        race_type=data.get("Type", "RACE"),
        duration_secs=int(data.get("DurationSecs") or 0),
        race_laps=int(data.get("RaceLaps") or 0),
        race_date=race_date,
        server_name=server_name,
        source_file=path.name,  # 传入文件名用于去重
    )

    car_pk_by_model: Dict[str, int] = {}
    driver_pk_by_guid: Dict[str, int] = {}
    car_info_by_json_id = build_car_info(data)
    stats = defaultdict(int)
    stats["race_id"] = race_id

    # 1) Cars + Drivers
    for car in data.get("Cars", []):
        model = car.get("Model") or ""
        if model:
            car_pk_by_model[model] = upsert_car(conn, model)
            stats["cars_seen"] += 1
        driver = car.get("Driver") or {}
        guid = driver.get("Guid") or ""
        if guid:
            driver_id = upsert_driver(conn, steam_guid=guid,
                                      driver_name=driver.get("Name") or guid,
                                      team_name=driver.get("Team") or "",
                                      nation=driver.get("Nation") or "")
            if driver_id:
                driver_pk_by_guid[guid] = driver_id
                stats["drivers_seen"] += 1

    # 2) Result/Laps 补充 Cars/Drivers
    for item in list(data.get("Result", [])) + list(data.get("Laps", [])):
        model = item.get("CarModel") or ""
        if model and model not in car_pk_by_model:
            car_pk_by_model[model] = upsert_car(conn, model)
        guid = item.get("DriverGuid") or ""
        if guid and guid not in driver_pk_by_guid:
            driver_id = upsert_driver(conn, guid, item.get("DriverName") or guid)
            if driver_id:
                driver_pk_by_guid[guid] = driver_id

    # 3) race_results
    with conn.cursor() as cur:
        for pos, result in enumerate(data.get("Result", []), start=1):
            guid = result.get("DriverGuid") or ""
            model = result.get("CarModel") or ""
            driver_id = driver_pk_by_guid.get(guid)
            car_id = car_pk_by_model.get(model)
            if not driver_id or not car_id:
                stats["results_skipped_no_driver_or_car"] += 1
                continue
            json_car = car_info_by_json_id.get(int(result.get("CarId") or -1), {})
            laps_completed = sum(1 for lap in data.get("Laps", []) if (lap.get("DriverGuid") or "") == guid)
            cur.execute(
                """
                INSERT INTO race_results
                    (race_id,driver_id,car_id,car_skin,ballast_kg,restrictor,
                     best_lap_ms,total_time_ms,position,laps_completed)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    car_id=VALUES(car_id),
                    car_skin=VALUES(car_skin),
                    ballast_kg=VALUES(ballast_kg),
                    restrictor=VALUES(restrictor),
                    best_lap_ms=VALUES(best_lap_ms),
                    total_time_ms=VALUES(total_time_ms),
                    position=VALUES(position),
                    laps_completed=VALUES(laps_completed)
                """,
                (
                    race_id,driver_id,car_id,json_car.get("Skin") or "",
                    int(result.get("BallastKG") or 0),int(result.get("Restrictor") or 0),
                    normalize_best_lap(result.get("BestLap")),int(result.get("TotalTime") or 0),
                    pos,laps_completed,
                )
            )
            stats["results_imported"] += 1

    # 4) laps
    laps_by_guid: Dict[str, list] = defaultdict(list)
    for lap in data.get("Laps", []):
        if lap.get("DriverGuid"):
            laps_by_guid[lap["DriverGuid"]].append(lap)
    with conn.cursor() as cur:
        for guid, laps in laps_by_guid.items():
            laps.sort(key=lambda x: int(x.get("Timestamp") or 0))
            for lap_no, lap in enumerate(laps, start=1):
                driver_id = driver_pk_by_guid.get(guid)
                car_id = car_pk_by_model.get(lap.get("CarModel") or "")
                if not driver_id or not car_id:
                    stats["laps_skipped_no_driver_or_car"] += 1
                    continue
                sectors = list(lap.get("Sectors") or []) + [None, None, None]
                cuts = int(lap.get("Cuts") or 0)
                cur.execute(
                    """
                    INSERT INTO laps
                        (race_id,driver_id,car_id,lap_number,lap_time_ms,timestamp_ms,
                         sector1_ms,sector2_ms,sector3_ms,cuts,tyre_type,
                         ballast_kg,restrictor,is_valid)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        car_id=VALUES(car_id),
                        lap_time_ms=VALUES(lap_time_ms),
                        timestamp_ms=VALUES(timestamp_ms),
                        sector1_ms=VALUES(sector1_ms),
                        sector2_ms=VALUES(sector2_ms),
                        sector3_ms=VALUES(sector3_ms),
                        cuts=VALUES(cuts),
                        tyre_type=VALUES(tyre_type),
                        ballast_kg=VALUES(ballast_kg),
                        restrictor=VALUES(restrictor),
                        is_valid=VALUES(is_valid)
                    """,
                    (
                        race_id,driver_id,car_id,lap_no,int(lap.get("LapTime") or 0),
                        int(lap.get("Timestamp") or 0),
                        sectors[0],sectors[1],sectors[2],cuts,
                        normalize_tyre(lap.get("Tyre")),
                        int(lap.get("BallastKG") or 0),
                        int(lap.get("Restrictor") or 0),
                        1 if cuts == 0 else 0,
                    )
                )
                stats["laps_imported"] += 1

    # 5) events
    event_stats = import_events(
        conn=conn,
        race_id=race_id,
        events=data.get("Events") or [],
        driver_pk_by_guid=driver_pk_by_guid,
        car_pk_by_model=car_pk_by_model,
        car_info_by_json_id=car_info_by_json_id,
    )
    stats.update(event_stats)

    return dict(stats)


def import_one_json_from_bytes(conn: Connection, raw_bytes: bytes, file_name: str, server_name: Optional[str] = None) -> Dict[str, int]:
    """从内存中的 JSON 字节内容导入一场比赛（用于远程下载后直接导入，无需落地）。"""
    data = json.loads(raw_bytes.decode("utf-8-sig"))
    # 构造一个虚拟 Path，仅用于解析文件名中的日期
    virtual_path = Path(file_name)
    race_date = parse_race_date_from_filename(virtual_path)
    track_id = upsert_track(conn, data.get("TrackName", ""), data.get("TrackConfig", ""))
    race_id = find_or_create_race(
        conn=conn,
        track_id=track_id,
        race_type=data.get("Type", "RACE"),
        duration_secs=int(data.get("DurationSecs") or 0),
        race_laps=int(data.get("RaceLaps") or 0),
        race_date=race_date,
        server_name=server_name,
        source_file=file_name,
    )

    car_pk_by_model: Dict[str, int] = {}
    driver_pk_by_guid: Dict[str, int] = {}
    car_info_by_json_id = build_car_info(data)
    stats = defaultdict(int)
    stats["race_id"] = race_id

    # 1) Cars + Drivers
    for car in data.get("Cars", []):
        model = car.get("Model") or ""
        if model:
            car_pk_by_model[model] = upsert_car(conn, model)
            stats["cars_seen"] += 1
        driver = car.get("Driver") or {}
        guid = driver.get("Guid") or ""
        if guid:
            driver_id = upsert_driver(conn, steam_guid=guid,
                                      driver_name=driver.get("Name") or guid,
                                      team_name=driver.get("Team") or "",
                                      nation=driver.get("Nation") or "")
            if driver_id:
                driver_pk_by_guid[guid] = driver_id
                stats["drivers_seen"] += 1

    # 2) Result/Laps 补充 Cars/Drivers
    for item in list(data.get("Result", [])) + list(data.get("Laps", [])):
        model = item.get("CarModel") or ""
        if model and model not in car_pk_by_model:
            car_pk_by_model[model] = upsert_car(conn, model)
        guid = item.get("DriverGuid") or ""
        if guid and guid not in driver_pk_by_guid:
            driver_id = upsert_driver(conn, guid, item.get("DriverName") or guid)
            if driver_id:
                driver_pk_by_guid[guid] = driver_id

    # 3) race_results
    with conn.cursor() as cur:
        for pos, result in enumerate(data.get("Result", []), start=1):
            guid = result.get("DriverGuid") or ""
            model = result.get("CarModel") or ""
            driver_id = driver_pk_by_guid.get(guid)
            car_id = car_pk_by_model.get(model)
            if not driver_id or not car_id:
                stats["results_skipped_no_driver_or_car"] += 1
                continue
            json_car = car_info_by_json_id.get(int(result.get("CarId") or -1), {})
            laps_completed = sum(1 for lap in data.get("Laps", []) if (lap.get("DriverGuid") or "") == guid)
            cur.execute(
                """
                INSERT INTO race_results
                    (race_id,driver_id,car_id,car_skin,ballast_kg,restrictor,
                     best_lap_ms,total_time_ms,position,laps_completed)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    car_id=VALUES(car_id),
                    car_skin=VALUES(car_skin),
                    ballast_kg=VALUES(ballast_kg),
                    restrictor=VALUES(restrictor),
                    best_lap_ms=VALUES(best_lap_ms),
                    total_time_ms=VALUES(total_time_ms),
                    position=VALUES(position),
                    laps_completed=VALUES(laps_completed)
                """,
                (
                    race_id,driver_id,car_id,json_car.get("Skin") or "",
                    int(result.get("BallastKG") or 0),int(result.get("Restrictor") or 0),
                    normalize_best_lap(result.get("BestLap")),int(result.get("TotalTime") or 0),
                    pos,laps_completed,
                )
            )
            stats["results_imported"] += 1

    # 4) laps
    laps_by_guid: Dict[str, list] = defaultdict(list)
    for lap in data.get("Laps", []):
        if lap.get("DriverGuid"):
            laps_by_guid[lap["DriverGuid"]].append(lap)
    with conn.cursor() as cur:
        for guid, laps in laps_by_guid.items():
            laps.sort(key=lambda x: int(x.get("Timestamp") or 0))
            for lap_no, lap in enumerate(laps, start=1):
                driver_id = driver_pk_by_guid.get(guid)
                car_id = car_pk_by_model.get(lap.get("CarModel") or "")
                if not driver_id or not car_id:
                    stats["laps_skipped_no_driver_or_car"] += 1
                    continue
                sectors = list(lap.get("Sectors") or []) + [None, None, None]
                cuts = int(lap.get("Cuts") or 0)
                cur.execute(
                    """
                    INSERT INTO laps
                        (race_id,driver_id,car_id,lap_number,lap_time_ms,timestamp_ms,
                         sector1_ms,sector2_ms,sector3_ms,cuts,tyre_type,
                         ballast_kg,restrictor,is_valid)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        car_id=VALUES(car_id),
                        lap_time_ms=VALUES(lap_time_ms),
                        timestamp_ms=VALUES(timestamp_ms),
                        sector1_ms=VALUES(sector1_ms),
                        sector2_ms=VALUES(sector2_ms),
                        sector3_ms=VALUES(sector3_ms),
                        cuts=VALUES(cuts),
                        tyre_type=VALUES(tyre_type),
                        ballast_kg=VALUES(ballast_kg),
                        restrictor=VALUES(restrictor),
                        is_valid=VALUES(is_valid)
                    """,
                    (
                        race_id,driver_id,car_id,lap_no,int(lap.get("LapTime") or 0),
                        int(lap.get("Timestamp") or 0),
                        sectors[0],sectors[1],sectors[2],cuts,
                        normalize_tyre(lap.get("Tyre")),
                        int(lap.get("BallastKG") or 0),
                        int(lap.get("Restrictor") or 0),
                        1 if cuts == 0 else 0,
                    )
                )
                stats["laps_imported"] += 1

    # 5) events
    event_stats = import_events(
        conn=conn,
        race_id=race_id,
        events=data.get("Events") or [],
        driver_pk_by_guid=driver_pk_by_guid,
        car_pk_by_model=car_pk_by_model,
        car_info_by_json_id=car_info_by_json_id,
    )
    stats.update(event_stats)

    return dict(stats)


# ---------- 远程 SSH 相关 ----------

def list_remote_json_files(
    host: str, port: int, user: str, password: str,
    remote_dir: str = "/opt/asm/server/results",
) -> List[str]:
    """通过 SSH 列出远程服务器目录下的 JSON 文件名（仅文件名，不含路径）。"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=password)
    try:
        sftp = ssh.open_sftp()
        try:
            all_files = sftp.listdir(remote_dir)
            json_files = sorted(f for f in all_files if f.endswith(".json"))
            return json_files
        finally:
            sftp.close()
    finally:
        ssh.close()


def download_remote_json(
    host: str, port: int, user: str, password: str,
    remote_path: str,
) -> bytes:
    """通过 SSH 下载远程服务器上的单个 JSON 文件，返回字节内容。"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=password)
    try:
        sftp = ssh.open_sftp()
        try:
            with sftp.open(remote_path, "rb") as f:
                return f.read()
        finally:
            sftp.close()
    finally:
        ssh.close()


def import_from_remote(
    conn: Connection,
    host: str, port: int, user: str, password: str,
    remote_dir: str = "/opt/asm/server/results",
    server_name: Optional[str] = None,
    files_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    从远程服务器拉取 JSON 文件并导入数据库。

    参数:
        files_filter: 可选，只导入指定文件名列表；为 None 则导入全部 JSON 文件。
    返回统计信息。
    """
    all_remote_files = list_remote_json_files(host, port, user, password, remote_dir)
    print(f"远程目录 {remote_dir} 下共发现 {len(all_remote_files)} 个 JSON 文件")

    if files_filter:
        to_import = [f for f in all_remote_files if f in set(files_filter)]
        skipped = [f for f in files_filter if f not in set(all_remote_files)]
        if skipped:
            print(f"警告：以下指定文件在远程目录中不存在: {skipped}")
    else:
        to_import = all_remote_files

    print(f"本次将导入 {len(to_import)} 个文件")
    overall_stats = {"files_total": len(to_import), "files_imported": 0, "files_skipped": 0, "per_file": []}

    for file_name in to_import:
        remote_path = f"{remote_dir.rstrip('/')}/{file_name}"
        print(f"  下载: {remote_path} ...", end=" ")
        raw = download_remote_json(host, port, user, password, remote_path)
        print(f"({len(raw)} bytes) ", end="")
        stats = import_one_json_from_bytes(conn, raw, file_name, server_name=server_name)
        overall_stats["files_imported"] += 1
        overall_stats["per_file"].append({"file": file_name, "stats": stats})
        print(f"完成 -> {stats}")

    return overall_stats


def expand_input_paths(paths):
    result = []
    for path in paths:
        p = Path(path)
        if p.is_dir():
            result.extend(sorted(p.glob("*.json")))
        else:
            result.append(p)
    return result


def connect(args: argparse.Namespace) -> Connection:
    return pymysql.connect(
        host=args.host,port=args.port,user=args.user,password=args.password,
        database=args.database,charset="utf8mb4",autocommit=False
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import cyracing JSON result files into MySQL.")
    parser.add_argument("json_files", nargs="*", type=str, help="比赛 JSON 文件路径（本地模式），远程模式下可省略")
    parser.add_argument("--host", default=os.getenv("CYRACING_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("CYRACING_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("CYRACING_USER", "root"))
    parser.add_argument("--password", default=os.getenv("CYRACING_PASSWORD", ""))
    parser.add_argument("--database", default=os.getenv("CYRACING_DATABASE", "cyracing"))
    parser.add_argument("--server-name", default=os.getenv("CYRACING_SERVER_NAME"), help="可选：写入 races.server_name")
    parser.add_argument("--dry-run", action="store_true", help="测试解析和事务，最后回滚，不真正写入")

    # 远程模式参数
    parser.add_argument("--remote", action="store_true", help="启用远程模式，从 SSH 服务器拉取 JSON")
    parser.add_argument("--remote-host", default=os.getenv("REMOTE_HOST", "www.ruankun.xyz"), help="远程服务器地址")
    parser.add_argument("--remote-port", type=int, default=int(os.getenv("REMOTE_PORT", "22")), help="SSH 端口")
    parser.add_argument("--remote-user", default=os.getenv("REMOTE_USER", "root"), help="SSH 用户名")
    parser.add_argument("--remote-password", default=os.getenv("REMOTE_PASSWORD", ""), help="SSH 密码")
    parser.add_argument("--remote-dir", default=os.getenv("REMOTE_DIR", "/opt/asm/server/results"), help="远程 JSON 文件目录")
    parser.add_argument("--remote-files", nargs="*", default=None, help="指定远程文件名（可选，不传则导入全部）")
    args = parser.parse_args()

    conn = connect(args)
    try:
        if args.remote:
            # ---------- 远程模式 ----------
            print(f"远程模式: {args.remote_user}@{args.remote_host}:{args.remote_port} -> {args.remote_dir}")
            stats = import_from_remote(
                conn=conn,
                host=args.remote_host,
                port=args.remote_port,
                user=args.remote_user,
                password=args.remote_password,
                remote_dir=args.remote_dir,
                server_name=args.server_name,
                files_filter=args.remote_files,
            )
            print(f"\n远程导入汇总: {stats['files_imported']}/{stats['files_total']} 个文件已导入")
        else:
            # ---------- 本地模式 ----------
            if not args.json_files:
                json_dir = os.getenv("JSON_DIR", "")
                if json_dir:
                    args.json_files = [json_dir]
                else:
                    parser.error("本地模式下必须提供 json_files 参数，或在 .env 中设置 JSON_DIR，或使用 --remote 启用远程模式")
            all_files = expand_input_paths(args.json_files)
            print(f"Found {len(all_files)} json files")
            for path in all_files:
                stats = import_one_json(conn, path, server_name=args.server_name)
                print(f"Imported {path}: {stats}")

        if args.dry_run:
            conn.rollback()
            print("dry-run finished: rolled back")
        else:
            conn.commit()
            print("commit ok")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()