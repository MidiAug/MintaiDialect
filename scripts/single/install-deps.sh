#!/bin/bash

echo "📦 安装模型服务依赖"
echo "================================"

# 检查conda环境
if [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "✅ 当前conda环境: $CONDA_DEFAULT_ENV"
else
    echo "⚠️  未检测到conda环境，请先激活环境"
    exit 1
fi

# 先卸载可能有冲突的包（从用户目录和conda环境）
echo "🔄 卸载可能有冲突的包..."
pip uninstall -y modelscope datasets transformers
pip uninstall -y modelscope datasets transformers --user

# 在conda环境中安装兼容版本
echo "📥 在conda环境中安装兼容版本的依赖..."

echo "🎤 安装ASR服务依赖..."
cd models/asr_service
pip install -r requirements.txt
cd ../..

echo "🧠 安装LLM服务依赖..."
cd models/llm_service
pip install -r requirements.txt
cd ../..

echo "🔊 安装TTS服务依赖..."
cd models/tts_service
pip install -r requirements.txt
cd ../..

echo "✅ 依赖安装完成！"
echo "💡 现在可以尝试启动服务了"
