#!/bin/bash
# 生产环境启动脚本（uvicorn）

cd "$(dirname "$0")"
PYTHON=/usr/local/python310/bin/python3.10

# 后台启动 API 服务（4 个 worker 进程）
nohup $PYTHON -m uvicorn app.main:app \
    --workers 4 \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    > server.log 2>&1 &

echo "server 已启动 (PID: $!)，查看日志: tail -f server.log"
