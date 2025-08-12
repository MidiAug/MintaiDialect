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

# 停止模型服务
if [ -f "logs/asr_service.pid" ]; then
    echo "🔄 停止ASR模型服务..."
    kill $(cat logs/asr_service.pid) 2>/dev/null
    rm -f logs/asr_service.pid
fi

if [ -f "logs/tts_service.pid" ]; then
    echo "🔄 停止TTS模型服务..."
    kill $(cat logs/tts_service.pid) 2>/dev/null
    rm -f logs/tts_service.pid
fi

if [ -f "logs/llm_service.pid" ]; then
    echo "🔄 停止LLM模型服务..."
    kill $(cat logs/llm_service.pid) 2>/dev/null
    rm -f logs/llm_service.pid
fi

# 停止Docker服务
if command -v docker-compose &> /dev/null; then
    echo "🔄 停止Docker服务..."
    docker-compose down 2>/dev/null
fi

echo "✅ 所有服务已停止"
