#!/bin/bash
# 启动 CYRacing 服务（后台运行，内置文件扫描定时任务）

cd "$(dirname "$0")"

nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
echo "server 已启动 (PID: $!)，查看日志: tail -f server.log"
