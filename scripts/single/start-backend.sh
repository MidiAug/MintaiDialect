#!/bin/bash

echo "🔧 启动后端API服务 (端口: 8000)"
cd backend
# 固定 Python 模块查找路径为当前 backend 目录，避免误加载其它路径同名模块
export PYTHONPATH="$(pwd)"
# 明确指定热重载监控目录为当前 backend 目录，并提升日志级别为 debug
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir "$(pwd)" --log-level debug
