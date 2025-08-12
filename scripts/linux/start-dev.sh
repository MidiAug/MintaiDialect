#!/bin/bash

echo "🚀 闽台方言大模型启动脚本"
echo "================================"

# 本地启动函数
start_local() {
    echo "使用本地环境启动服务..."
    
    # 启动ASR模型服务
    echo "🎤 启动ASR模型服务..."
    cd models/asr_service
    nohup python asr_service.py > ../../logs/asr_service.log 2>&1 &
    echo $! > ../../logs/asr_service.pid
    cd ../..
    
    # 启动TTS模型服务
    echo "🔊 启动TTS模型服务..."
    cd models/tts_service
    nohup python tts_service.py > ../../logs/tts_service.log 2>&1 &
    echo $! > ../../logs/tts_service.pid
    cd ../..
    
    
    # 等待模型服务启动
    echo "⏳ 等待模型服务启动..."
    sleep 5
    
    # 启动后端
    echo "🚀 启动后端服务..."
    cd backend
    
    # 后台启动后端
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
    echo $! > ../logs/backend.pid
    
    cd ..
    
    # 等待后端启动
    sleep 3
    
    # 启动前端
    echo "🚀 启动前端服务..."
    cd frontend
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    echo $! > ../logs/frontend.pid
    
    cd ..
    
    echo "✅ 本地服务启动完成！"
    echo "🎤 ASR模型服务: http://localhost:9000"
    echo "🧠 LLM模型服务: http://localhost:9001"
    echo "🔊 TTS模型服务: http://localhost:9002"
    echo "🌐 前端: http://localhost:5173"
    echo "🔧 后端: http://localhost:8000"
}

# Docker启动函数
start_docker() {
    echo "🐳 使用Docker启动服务..."
    docker-compose build
    docker-compose up -d
    
    echo "✅ Docker服务启动完成！"
    echo "🌐 前端: http://localhost:3000"
    echo "🔧 后端: http://localhost:8000"
}

# 主菜单
echo "请选择启动方式："
echo "1. 本地启动（开发环境）"
echo "2. Docker启动（生产环境）"
echo "3. 退出"
echo ""

read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        start_local
        ;;
    2)
        start_docker
        ;;
    3)
        echo "👋 再见！"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac
