#!/bin/bash

# 闽台方言大模型系统 - 开发环境启动脚本

echo "🎤 闽台方言大模型系统 - 开发环境启动"
echo "========================================"

# 检查Node.js和Python环境
echo "检查环境依赖..."

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js 16+"
    exit 1
fi

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装 Python 3.8+"
    exit 1
fi

echo "✅ 环境检查通过"

# 启动后端服务
echo ""
echo "🚀 启动后端服务..."
cd backend

# 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# 安装依赖
echo "安装Python依赖..."
pip install -r requirements.txt

# 创建必要目录
mkdir -p uploads logs cache models

# 复制环境变量文件
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请根据需要修改配置"
fi

# 启动后端服务 (后台运行)
echo "启动FastAPI后端服务..."
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"

cd ..

# 启动前端服务
echo ""
echo "🎨 启动前端服务..."
cd frontend

# 安装依赖
echo "安装Node.js依赖..."
npm install

# 启动前端服务
echo "启动React开发服务器..."
npm run dev &
FRONTEND_PID=$!
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"

cd ..

echo ""
echo "🎉 启动完成！"
echo "========================================"
echo "📖 前端应用: http://localhost:5173"
echo "🔌 后端API: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo ""
echo "📝 日志文件:"
echo "   后端日志: logs/backend.log"
echo "   前端日志: 查看终端输出"
echo ""
echo "⏹️  停止服务: Ctrl+C 或运行 scripts/stop-dev.sh"
echo "========================================"

# 保存PID到文件
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

# 等待用户中断
wait 