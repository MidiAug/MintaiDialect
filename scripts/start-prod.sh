#!/bin/bash

# 闽台方言大模型系统 - 生产环境启动脚本

echo "🎤 闽台方言大模型系统 - 生产环境部署"
echo "========================================"

# 检查Docker环境
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✅ Docker环境检查通过"

# 创建必要的目录
echo "创建必要目录..."
mkdir -p backend/uploads backend/logs backend/models
mkdir -p logs ssl

# 构建并启动服务
echo ""
echo "🚀 构建并启动生产环境..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 30

# 检查服务状态
echo ""
echo "📊 检查服务状态..."
docker-compose ps

# 检查后端健康状态
echo ""
echo "🔍 检查服务健康状态..."
if curl -f http://localhost:8000/api/health &>/dev/null; then
    echo "✅ 后端API服务正常"
else
    echo "❌ 后端API服务异常"
    echo "查看日志: docker-compose logs backend"
fi

if curl -f http://localhost:3000 &>/dev/null; then
    echo "✅ 前端服务正常"
else
    echo "❌ 前端服务异常"
    echo "查看日志: docker-compose logs frontend"
fi

echo ""
echo "🎉 生产环境启动完成！"
echo "========================================"
echo "🌐 应用访问地址: http://localhost:3000"
echo "🔌 API服务地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo ""
echo "📝 查看日志:"
echo "   所有服务: docker-compose logs"
echo "   后端日志: docker-compose logs backend"
echo "   前端日志: docker-compose logs frontend"
echo ""
echo "⏹️  停止服务: docker-compose down"
echo "🔄 重启服务: docker-compose restart"
echo "========================================" 