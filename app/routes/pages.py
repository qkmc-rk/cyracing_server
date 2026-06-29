from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

STATIC_ROOT = Path(__file__).parent.parent.parent / "static"
MOD_DIR = STATIC_ROOT / "mod"

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

  <main class="flex-1 flex flex-col items-center justify-center text-center px-6">
    <h2 class="text-5xl font-extrabold mb-4">
      <span class="text-white">CY</span><span class="text-red-500">Racing</span>
    </h2>
    <p class="text-gray-400 text-lg max-w-xl mb-10">
      Assetto Corsa 赛车数据平台 &middot; 比赛结果 &middot; 车手画像 &middot; 圈速分析
    </p>
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
    CYRacing &copy; 2026
  </footer>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def home():
    return INDEX_HTML


# ---------- Mod 下载页 ----------

def _fmt_size(size_bytes: int) -> str:
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.2f} GB"
    if size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.2f} MB"
    if size_bytes >= 1_000:
        return f"{size_bytes / 1_000:.2f} KB"
    return f"{size_bytes} B"


@router.get("/mods", response_class=HTMLResponse)
async def mod_list():
    files = []
    if MOD_DIR.is_dir():
        for f in sorted(MOD_DIR.iterdir()):
            if f.is_file() and f.name != ".gitkeep":
                files.append({
                    "name": f.name,
                    "size": _fmt_size(f.stat().st_size),
                    "url": f"/static/mod/{f.name}",
                })

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

    <p class="mt-8 text-gray-600 text-sm">
      将 .zip / .7z 文件放入服务器 <code class="bg-gray-800 px-1 rounded">static/mod/</code> 目录即可在此展示。
    </p>
  </main>

  <footer class="border-t border-gray-800 py-4 text-center text-gray-600 text-xs">
    CYRacing &copy; 2026
  </footer>
</body>
</html>"""

    return html
