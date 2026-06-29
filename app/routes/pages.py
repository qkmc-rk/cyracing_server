from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

STATIC_ROOT = Path(__file__).parent.parent.parent / "static"
MOD_DIR = STATIC_ROOT / "mod"


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

INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CYRacing</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen flex flex-col">
  <header class="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
    <h1 class="text-xl font-bold tracking-wide text-red-500">CYRacing</h1>
    <nav class="flex gap-6 text-sm text-gray-400">
      <a href="/mods" class="hover:text-white transition">Mod 下载</a>
      <a href="/docs" class="hover:text-white transition">API 文档</a>
    </nav>
  </header>

  <main class="flex-1 flex flex-col items-center justify-center text-center px-6 py-12">
    <h2 class="text-5xl font-extrabold mb-4">
      <span class="text-white">CY</span><span class="text-red-500">Racing</span>
    </h2>
    <p class="text-gray-400 text-lg max-w-xl mb-8">
      Assetto Corsa 赛车数据平台 &middot; 比赛结果 &middot; 车手画像 &middot; 圈速分析
    </p>

    <!-- 微信小程序扫码 -->
    <div class="bg-gray-900 border border-gray-800 rounded-2xl p-8 mb-8 max-w-sm w-full">
      <h3 class="text-lg font-semibold mb-2">扫码进入微信小程序</h3>
      <p class="text-gray-400 text-sm mb-5">查询比赛记录、个人画像、圈速分析</p>
      <img src="/static/miniapp.jpg" alt="微信小程序扫码"
           class="w-48 h-48 mx-auto rounded-xl border border-gray-700" />
      <p class="text-gray-500 text-xs mt-4">微信扫一扫上方二维码</p>
    </div>

    <div class="flex gap-4">
      <a href="/mods"
         class="px-6 py-3 bg-red-600 hover:bg-red-700 rounded-lg font-semibold transition">
        Mod 下载
      </a>
      <a href="/docs"
         class="px-6 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg font-semibold transition">
        API 文档
      </a>
    </div>
  </main>

  <footer class="border-t border-gray-800 py-4 text-center text-gray-600 text-xs">
    CYRacing &copy; 2026 &nbsp;|&nbsp; 蜀ICP备18006071号
  </footer>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def home():
    return INDEX_HTML


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
