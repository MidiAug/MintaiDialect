#!/bin/bash

echo "📦 使用conda安装模型服务依赖"
echo "================================"

# 检查conda环境
if [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "✅ 当前conda环境: $CONDA_DEFAULT_ENV"
    echo "📍 环境路径: $CONDA_PREFIX"
else
    echo "⚠️  未检测到conda环境，请先激活环境"
    exit 1
fi

# 检查pip和python路径
echo "🔍 检查环境信息..."
echo "Python路径: $(which python)"
echo "Pip路径: $(which pip)"

# 使用conda安装核心依赖
echo "📥 使用conda安装核心依赖..."
conda install -c conda-forge -y modelscope transformers datasets

# 安装其他依赖
echo "📥 安装其他依赖..."
conda install -c conda-forge -y fastapi uvicorn torch torchaudio scipy

# 验证安装
echo "✅ 验证安装..."
python -c "import modelscope; print('✅ modelscope安装成功')"
python -c "import transformers; print('✅ transformers安装成功')"
python -c "import datasets; print('✅ datasets安装成功')"

echo "🎉 所有依赖安装完成！"
