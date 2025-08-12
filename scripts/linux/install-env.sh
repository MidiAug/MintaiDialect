#!/bin/bash

echo "🔧 闽台方言大模型环境安装脚本"
echo "================================"

# 检查conda是否可用
if ! command -v conda &> /dev/null; then
    echo "❌ 未找到conda命令，请先安装Anaconda或Miniconda"
    exit 1
fi

echo "📁 创建项目目录结构..."
# 创建必要的目录
mkdir -p logs
mkdir -p backend/uploads
mkdir -p backend/logs
mkdir -p backend/models
mkdir -p backend/data
mkdir -p frontend/dist
mkdir -p frontend/build

echo "✅ 目录结构创建完成"

echo "📦 创建conda环境: Mintai (Python 3.11)"
conda create -n Mintai python=3.11 -y

echo "🔄 激活环境并安装依赖..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate Mintai

echo "📥 安装Python依赖..."
cd backend
pip install -r requirements.txt
cd ..

echo "📥 安装Node.js依赖..."
cd frontend
npm install
cd ..

echo "🔧 设置文件权限..."
chmod +x scripts/*.sh

echo "✅ 环境安装完成！"
echo ""
echo "📁 已创建的目录："
echo "  - logs/           # 服务日志"
echo "  - backend/uploads/ # 后端上传文件"
echo "  - backend/logs/    # 后端日志"
echo "  - backend/models/  # AI模型文件"
echo "  - backend/data/    # 数据文件"
echo "  - frontend/dist/   # 前端构建文件"
echo "  - frontend/build/  # 前端构建缓存"
echo ""
echo "💡 使用方法："
echo "1. 激活环境: conda activate Mintai"
echo "2. 启动服务: ./scripts/start-dev.sh"
echo ""
echo "🎯 当前环境: $(conda info --envs | grep '*' | awk '{print $1}')"
