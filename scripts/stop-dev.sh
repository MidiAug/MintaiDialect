#!/bin/bash

# 闽台方言大模型系统 - 开发环境停止脚本

echo "⏹️  停止闽台方言大模型系统开发服务..."

# 停止后端服务
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "停止后端服务 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        rm .backend.pid
        echo "✅ 后端服务已停止"
    else
        echo "⚠️  后端服务已停止"
        rm .backend.pid
    fi
else
    echo "⚠️  未找到后端服务PID文件"
fi

# 停止前端服务
if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "停止前端服务 (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        rm .frontend.pid
        echo "✅ 前端服务已停止"
    else
        echo "⚠️  前端服务已停止"
        rm .frontend.pid
    fi
else
    echo "⚠️  未找到前端服务PID文件"
fi

# 清理其他可能的进程
echo "清理相关进程..."
pkill -f "uvicorn.*app.main:app" 2>/dev/null
pkill -f "vite.*dev" 2>/dev/null

echo "🎉 所有服务已停止" 