#!/bin/bash

echo "🛑 停止闽台方言大模型服务"
echo "================================"

# 停止本地服务
if [ -f "logs/backend.pid" ]; then
    echo "🔄 停止后端服务..."
    kill $(cat logs/backend.pid) 2>/dev/null
    rm -f logs/backend.pid
fi

if [ -f "logs/frontend.pid" ]; then
    echo "🔄 停止前端服务..."
    kill $(cat logs/frontend.pid) 2>/dev/null
    rm -f logs/frontend.pid
fi

# 停止Docker服务
if command -v docker-compose &> /dev/null; then
    echo "🔄 停止Docker服务..."
    docker-compose down 2>/dev/null
fi

echo "✅ 所有服务已停止"
