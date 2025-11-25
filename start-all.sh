#!/bin/bash
# 统一启动 ASR / TTS / Backend / Frontend / LLM / VPN 服务
# 日志会写到 ~/MintaiDialect/mintai-logs 目录

set -euo pipefail

# --- 环境变量配置 ---
LOG_DIR=${LOG_DIR:-~/MintaiDialect/mintai-logs}
CONDA_ENV=${CONDA_ENV:-mintai}

# 创建日志目录
mkdir -p "$LOG_DIR"

# 激活 conda 环境
if command -v conda >/dev/null 2>&1; then
    # 临时禁用严格模式以避免conda激活脚本的变量问题
    set +u
    source ~/anaconda3/etc/profile.d/conda.sh
    conda activate "$CONDA_ENV"
    set -u
    echo "✅ Conda环境 '$CONDA_ENV' 已激活"
else
    echo "⚠️  未找到conda，跳过环境激活"
fi

echo "🚀 开始启动所有服务..."
echo "📁 日志目录: $LOG_DIR"
echo "---"

# 1. 启动 ASR 服务
echo "🎤 启动ASR服务..."
nohup bash ./scripts/start-asr.sh > "$LOG_DIR/asr.log" 2>&1 &
ASR_PID=$!
echo "   ASR 服务已启动 (PID: $ASR_PID, 日志: $LOG_DIR/asr.log)"

# 2. 启动 TTS 服务
echo "🔊 启动TTS服务..."
nohup bash ./scripts/start-tts.sh > "$LOG_DIR/tts.log" 2>&1 &
TTS_PID=$!
echo "   TTS 服务已启动 (PID: $TTS_PID, 日志: $LOG_DIR/tts.log)"

# 3. 启动 LLM 服务
# echo "🧠 启动LLM服务..."
# nohup bash ./scripts/start-llm.sh > "$LOG_DIR/llm.log" 2>&1 &
# LLM_PID=$!
# echo "   LLM 服务已启动 (PID: $LLM_PID, 日志: $LOG_DIR/llm.log)"

# 4. 启动后端服务
echo "🔧 启动后端服务..."
nohup bash ./scripts/start-backend.sh > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   后端服务已启动 (PID: $BACKEND_PID, 日志: $LOG_DIR/backend.log)"

# 5. 启动前端服务
echo "🌐 启动前端服务..."
nohup bash ./scripts/start-frontend.sh > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   前端服务已启动 (PID: $FRONTEND_PID, 日志: $LOG_DIR/frontend.log)"

# 6. 启动 VPN (clash)
echo "🔒 启动VPN服务..."
if [ -d ~/.config/mihomo ] && [ -f ~/.config/mihomo/clash-linux ]; then
    cd ~/.config/mihomo
    nohup ./clash-linux > "$LOG_DIR/vpn.log" 2>&1 &
    VPN_PID=$!
    echo "   VPN 服务已启动 (PID: $VPN_PID, 日志: $LOG_DIR/vpn.log)"
else
    echo "   ⚠️  未找到VPN配置文件，跳过VPN启动"
fi

echo "---"
echo "✅ 所有服务启动完成!"
echo "📊 服务状态:"
echo "   ASR:     http://localhost:9010"
echo "   TTS:     http://localhost:9030"
# echo "   LLM:     http://localhost:9020"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "📁 查看日志: tail -f $LOG_DIR/*.log"
echo "🛑 停止服务: ./stop-all.sh"
