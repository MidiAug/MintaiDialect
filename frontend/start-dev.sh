#!/bin/bash

# 启动开发服务器
echo "正在启动民台方言智能语音处理平台前端开发服务器..."

# 检查node_modules是否存在
if [ ! -d "node_modules" ]; then
    echo "安装依赖包..."
    npm install
fi

# 启动开发服务器
echo "启动开发服务器..."
npm run dev
