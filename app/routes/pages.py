from pathlib import Path
from typing import List
import json

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import SessionLocal
from app.models import Driver, User, Track, Race, Announcement, DriverProfile

router = APIRouter()

STATIC_ROOT = Path(__file__).parent.parent.parent / "static"
MOD_DIR = STATIC_ROOT / "mod"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _list_mod_files() -> List[dict]:
    """扫描 static/mod/ 目录，返回文件列表。"""
    files = []
    if MOD_DIR.is_dir():
        for f in sorted(MOD_DIR.iterdir()):
            if f.is_file() and f.name not in (".gitkeep", ".gitignore"):
                st = f.stat()
                files.append({
                    "name": f.name,
                    "size_bytes": st.st_size,
                    "size": _fmt_size(st.st_size),
                    "url": f"/static/mod/{f.name}",
                })
    return files


def _fmt_size(size_bytes: int) -> str:
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.2f} GB"
    if size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.2f} MB"
    if size_bytes >= 1_000:
        return f"{size_bytes / 1_000:.2f} KB"
    return f"{size_bytes} B"

# ---------- 首页 ----------

@router.get("/", response_class=HTMLResponse)
async def home(db: Session = Depends(get_db)):
    # 数据统计
    driver_count = db.query(func.count(Driver.driver_id)).scalar() or 0
    user_count = db.query(func.count(User.user_id)).scalar() or 0
    track_count = db.query(func.count(Track.track_id)).scalar() or 0
    race_count = db.query(func.count(Race.race_id)).filter(Race.race_type == "RACE").scalar() or 0

    # 公告列表（置顶在前，按发布时间倒序，取最新 5 条）
    announcements = (
        db.query(Announcement)
        .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
        .limit(5)
        .all()
    )

    # 构建公告数据 JSON（供弹窗使用）
    announce_data = []
    for a in announcements:
        # 从 Quill Delta 中提取纯文本
        content_text = ""
        if isinstance(a.content, dict) and "ops" in a.content:
            parts = []
            for op in a.content["ops"]:
                if isinstance(op.get("insert"), str):
                    parts.append(op["insert"])
            content_text = "".join(parts)
        elif isinstance(a.content, str):
            content_text = a.content
        else:
            content_text = json.dumps(a.content, ensure_ascii=False)

        announce_data.append({
            "id": a.announcement_id,
            "title": a.title,
            "summary": a.summary or "",
            "content": content_text,
            "is_pinned": bool(a.is_pinned),
        })

    # 构建公告列表 HTML
    announce_rows = ""
    if announcements:
        for idx, a in enumerate(announcements):
            pin_badge = '<span class="ml-2 px-1.5 py-0.5 bg-red-600 text-white text-xs rounded">置顶</span>' if a.is_pinned else ""
            announce_rows += f"""
            <div onclick="openAnnounce({idx})"
                 class="block px-4 py-3 border-b border-gray-800 hover:bg-gray-900 transition cursor-pointer last:border-b-0">
              <div class="flex items-center gap-2">
                <span class="text-sm text-white font-medium hover:text-red-400">{a.title}</span>{pin_badge}
              </div>
              <p class="text-xs text-gray-500 mt-1">{a.summary or ""}</p>
            </div>"""
    else:
        announce_rows = """<div class="px-4 py-6 text-center text-gray-500 text-sm">暂无公告</div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CYRacing</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen flex flex-col">
  <header class="border-b border-gray-800 px-6 py-4 flex items-center justify-between z-10 relative">
    <h1 class="text-xl font-bold tracking-wide text-red-500">CYRacing</h1>
    <nav class="flex gap-6 text-sm text-gray-400">
      <a href="/mods" class="hover:text-white transition">Mod 下载</a>
      <a href="/leaderboard" class="hover:text-white transition">排行榜</a>
      <a href="/docs" class="hover:text-white transition">API 文档</a>
    </nav>
  </header>

  <!-- 视频 Banner -->
  <div class="relative w-full" style="max-height:480px; overflow:hidden;">
    <video autoplay muted loop playsinline
           class="w-full object-cover" style="max-height:480px;">
      <source src="/static/banner_video.mp4" type="video/mp4" />
    </video>
    <!-- 径向蒙版：中心透明，四周白色半透明 -->
    <div class="absolute inset-0 flex items-center justify-center"
         style="background: radial-gradient(ellipse at center, transparent 20%, rgba(0,0,0,0.7) 60%, rgba(0,0,0,0.9) 100%);">
      <div class="text-center">
        <h2 class="text-5xl md:text-6xl font-extrabold drop-shadow-lg">
          <span class="text-white">CY</span><span class="text-red-500">Racing</span>
        </h2>
        <p class="text-gray-300 text-lg mt-3 drop-shadow">
          Assetto Corsa 赛车数据平台 &middot; 比赛结果 &middot; 车手画像 &middot; 圈速分析
        </p>
      </div>
    </div>
  </div>

  <main class="flex-1 max-w-5xl mx-auto w-full px-6 py-10 space-y-10">
    <!-- 数据统计卡片 -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
        <p class="text-3xl font-bold text-red-500">{driver_count}</p>
        <p class="text-gray-500 text-sm mt-1">参赛车手</p>
      </div>
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
        <p class="text-3xl font-bold text-blue-400">{user_count}</p>
        <p class="text-gray-500 text-sm mt-1">小程序用户</p>
      </div>
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
        <p class="text-3xl font-bold text-green-400">{track_count}</p>
        <p class="text-gray-500 text-sm mt-1">赛道点亮</p>
      </div>
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
        <p class="text-3xl font-bold text-yellow-400">{race_count}</p>
        <p class="text-gray-500 text-sm mt-1">正赛场次</p>
      </div>
    </div>

    <!-- 公告区域 -->
    <div>
      <h3 class="text-lg font-semibold mb-3">📢 公告</h3>
      <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {announce_rows}
      </div>
    </div>

    <!-- 按钮 + 微信小程序扫码 -->
    <div class="flex flex-col items-center gap-6">
      <div class="flex gap-4">
        <a href="/mods"
           class="px-6 py-3 bg-red-600 hover:bg-red-700 rounded-lg font-semibold transition">
          Mod 下载
        </a>
        <a href="/leaderboard"
           class="px-6 py-3 bg-yellow-600 hover:bg-yellow-700 rounded-lg font-semibold transition">
          排行榜
        </a>
        <a href="/docs"
           class="px-6 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg font-semibold transition">
          API 文档
        </a>
      </div>
      <div class="bg-gray-900 border border-gray-800 rounded-2xl p-6 text-center">
        <h3 class="font-semibold mb-2">扫码进入微信小程序</h3>
        <p class="text-gray-400 text-xs mb-4">比赛记录 · 个人画像 · 圈速分析</p>
        <img src="/static/miniapp.jpg" alt="微信小程序扫码"
             class="w-36 h-36 mx-auto rounded-xl border border-gray-700" />
        <p class="text-gray-500 text-xs mt-3">微信扫一扫</p>
      </div>
    </div>
  </main>

  <footer class="border-t border-gray-800 py-4 text-center text-gray-600 text-xs">
    CYRacing &copy; 2026 &nbsp;|&nbsp; 蜀ICP备18006071号
  </footer>

  <!-- 公告弹窗 -->
  <div id="announce-modal" class="fixed inset-0 z-50 hidden items-center justify-center bg-black/70"
       onclick="closeAnnounce(event)">
    <div class="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg mx-4 p-6 relative max-h-[80vh] overflow-y-auto"
         onclick="event.stopPropagation()">
      <button onclick="document.getElementById('announce-modal').classList.add('hidden')"
              class="absolute top-3 right-4 text-gray-500 hover:text-white text-xl leading-none">&times;</button>
      <h3 id="modal-title" class="text-xl font-bold mb-3 text-red-400"></h3>
      <div id="modal-content" class="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap"></div>
    </div>
  </div>

  <script>
    const announceData = {json.dumps(announce_data, ensure_ascii=False)};

    function openAnnounce(idx) {{
      const a = announceData[idx];
      if (!a) return;
      document.getElementById('modal-title').textContent = a.title;
      document.getElementById('modal-content').textContent = a.content || a.summary || '(暂无内容)';
      document.getElementById('announce-modal').classList.remove('hidden');
      document.getElementById('announce-modal').classList.add('flex');
    }}

    function closeAnnounce(e) {{
      if (e.target === document.getElementById('announce-modal')) {{
        document.getElementById('announce-modal').classList.add('hidden');
        document.getElementById('announce-modal').classList.remove('flex');
      }}
    }}
  </script>
</body>
</html>"""

    return html


# ---------- 排行榜 ----------

@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(db: Session = Depends(get_db)):
    rows_query = (
        db.query(
            Driver.driver_name,
            Driver.nation,
            func.coalesce(DriverProfile.total_races, 0).label("total_races"),
        )
        .select_from(User)
        .join(Driver, User.driver_id == Driver.driver_id)
        .outerjoin(DriverProfile, Driver.driver_id == DriverProfile.driver_id)
        .filter(User.driver_id.isnot(None))
        .order_by(desc("total_races"))
        .all()
    )

    rows_html = ""
    for idx, (name, nation, total_races) in enumerate(rows_query):
        nation_str = nation or "-"
        rows_html += f"""
            <tr class="border-b border-gray-800 hover:bg-gray-900 transition">
              <td class="py-3 px-4 text-gray-500 text-center">{idx + 1}</td>
              <td class="py-3 px-4 text-blue-400 font-medium">{name}</td>
              <td class="py-3 px-4 text-gray-400 text-center">{nation_str}</td>
              <td class="py-3 px-4 text-yellow-400 font-bold text-center">{total_races}</td>
            </tr>"""

    if not rows_query:
        rows_html = """<tr><td colspan="4" class="py-8 text-center text-gray-500">暂无排行数据</td></tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>排行榜 - CYRacing</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen flex flex-col">
  <header class="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
    <a href="/" class="text-xl font-bold tracking-wide text-red-500">CYRacing</a>
    <nav class="flex gap-6 text-sm text-gray-400">
      <a href="/mods" class="hover:text-white transition">Mod 下载</a>
      <a href="/leaderboard" class="text-white font-semibold">排行榜</a>
      <a href="/docs" class="hover:text-white transition">API 文档</a>
    </nav>
  </header>

  <main class="flex-1 max-w-5xl mx-auto w-full px-6 py-10">
    <h2 class="text-2xl font-bold mb-6">排行榜</h2>

    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b border-gray-700 text-gray-400 text-sm">
            <th class="py-3 px-4 font-medium text-center">排名</th>
            <th class="py-3 px-4 font-medium">车手姓名</th>
            <th class="py-3 px-4 font-medium text-center">国籍</th>
            <th class="py-3 px-4 font-medium text-center">积分数</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    <p class="mt-4 text-gray-500 text-xs">仅统计已绑定微信小程序的用户</p>
  </main>

  <footer class="border-t border-gray-800 py-4 text-center text-gray-600 text-xs">
    CYRacing &copy; 2026 &nbsp;|&nbsp; 蜀ICP备18006071号
  </footer>
</body>
</html>"""

    return html


# ---------- Mod 下载页 ----------

@router.get("/mods", response_class=HTMLResponse)
async def mod_page():
    files = _list_mod_files()

    rows = ""
    if files:
        for f in files:
            rows += f"""
            <tr class="border-b border-gray-800 hover:bg-gray-900 transition">
              <td class="py-3 px-4 text-blue-400">
                <a href="{f['url']}" download class="hover:underline">{f['name']}</a>
              </td>
              <td class="py-3 px-4 text-gray-500 text-sm text-right">{f['size']}</td>
              <td class="py-3 px-4 text-center">
                <a href="{f['url']}" download
                   class="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-xs font-semibold transition">
                  下载
                </a>
              </td>
            </tr>"""
    else:
        rows = """<tr><td colspan="3" class="py-8 text-center text-gray-500">暂无 Mod 文件</td></tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mod 下载 - CYRacing</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen flex flex-col">
  <header class="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
    <a href="/" class="text-xl font-bold tracking-wide text-red-500">CYRacing</a>
    <nav class="flex gap-6 text-sm text-gray-400">
      <a href="/mods" class="text-white font-semibold">Mod 下载</a>
      <a href="/docs" class="hover:text-white transition">API 文档</a>
    </nav>
  </header>

  <main class="flex-1 max-w-4xl mx-auto w-full px-6 py-10">
    <h2 class="text-2xl font-bold mb-6">Mod 下载</h2>

    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b border-gray-700 text-gray-400 text-sm">
            <th class="py-3 px-4 font-medium">文件名</th>
            <th class="py-3 px-4 font-medium text-right">大小</th>
            <th class="py-3 px-4 font-medium text-center">操作</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>

    <!-- 安装说明 -->
    <div class="mt-10 bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h3 class="text-lg font-semibold mb-3">Mod 安装方法</h3>
      <ol class="text-gray-400 text-sm space-y-2 list-decimal list-inside">
        <li>下载上方压缩包文件</li>
        <li>打开 <span class="text-white font-medium">Content Manager</span>（Assetto Corsa 内容管理器）</li>
        <li>将压缩包<span class="text-white">直接拖入</span> Content Manager 窗口</li>
        <li>点击右上角 <span class="text-white font-bold">三</span>（菜单按钮），即可自动安装</li>
      </ol>
    </div>
  </main>

  <footer class="border-t border-gray-800 py-4 text-center text-gray-600 text-xs">
    CYRacing &copy; 2026 &nbsp;|&nbsp; 蜀ICP备18006071号
  </footer>
</body>
</html>"""

    return html


@router.get("/api/mods")
async def mod_list_json():
    """返回 mod 文件列表 JSON。"""
    return _list_mod_files()
