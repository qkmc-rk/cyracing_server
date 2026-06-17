import asyncio
import importlib.util
import logging
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import races, events
from app.routes import drivers
from app.routes import users
from app.routes import announcements
from app.routes import driver_profiles

load_dotenv()

# --- 动态导入 import_cyracing_results（文件名含横线，无法直接 import） ---
_script_path = Path(__file__).parent.parent / "import_cyracing_results.py"
_spec = importlib.util.spec_from_file_location("import_cyracing_results", _script_path)
_import_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_import_mod)
import_one_json = _import_mod.import_one_json

logger = logging.getLogger("scanner")

# --- 配置 ---
JSON_DIR = os.getenv("JSON_DIR", "./json_results")
SERVER_NAME = os.getenv("CYRACING_SERVER_NAME") or os.getenv("SERVER_NAME")
STATIC_DIR = os.getenv("STATIC_DIR", "static")

SCAN_INTERVAL = 60   # 目录扫描间隔（秒）
FILE_STABLE_WAIT = 3  # 等待文件写入完成的时间（秒）

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "cyracing")


def _get_pymysql_conn():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4", autocommit=False,
    )


async def _scan_and_import():
    """后台定时任务：每 60 秒扫描 JSON_DIR，发现新文件自动导入。"""
    json_dir = Path(JSON_DIR)
    if not json_dir.is_dir():
        logger.warning(f"JSON_DIR 不存在: {json_dir}，扫描任务已跳过")
        return

    seen_files = set(f.name for f in json_dir.glob("*.json"))
    logger.info(f"目录扫描已启动: {json_dir}，已有 {len(seen_files)} 个文件 (间隔 {SCAN_INTERVAL}s)")

    loop = asyncio.get_running_loop()

    while True:
        try:
            current_files = set(f.name for f in json_dir.glob("*.json"))
            new_files = current_files - seen_files

            for fname in sorted(new_files):
                fpath = json_dir / fname
                logger.info(f"发现新文件: {fname}，等待 {FILE_STABLE_WAIT}s 确保写入完成...")
                await asyncio.sleep(FILE_STABLE_WAIT)

                def _import():
                    conn = _get_pymysql_conn()
                    try:
                        stats = import_one_json(conn, fpath, server_name=SERVER_NAME)
                        conn.commit()
                        return stats
                    except Exception:
                        conn.rollback()
                        raise
                    finally:
                        conn.close()

                try:
                    stats = await loop.run_in_executor(None, _import)
                    logger.info(f"导入完成: {fname} -> race_id={stats.get('race_id')}")
                except Exception as e:
                    logger.error(f"导入失败: {fname} -> {e}")

                seen_files.add(fname)

        except Exception as e:
            logger.error(f"扫描异常: {e}")

        await asyncio.sleep(SCAN_INTERVAL)


_scan_task = None  # asyncio.Task


app = FastAPI(title="CYRacing API", version="1.0")


@app.on_event("startup")
async def startup():
    global _scan_task
    _scan_task = asyncio.create_task(_scan_and_import())


@app.on_event("shutdown")
async def shutdown():
    global _scan_task
    if _scan_task:
        _scan_task.cancel()
        try:
            await _scan_task
        except asyncio.CancelledError:
            pass


app.include_router(races.router, prefix="/races", tags=["races"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(drivers.router, prefix="/drivers", tags=["drivers"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
app.include_router(driver_profiles.router, prefix="/driver_profiles", tags=["driver_profiles"])

# 静态资源目录（挂载在 /static 路径）
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), STATIC_DIR)
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")