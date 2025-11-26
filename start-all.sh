#!/bin/bash
# 统一启动 ASR / TTS / Backend / Frontend / LLM / VPN 服务
# 日志会写到 ~/MintaiDialect/logs 目录

set -euo pipefail

# --- 环境变量配置 ---
ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
LOG_DIR=${LOG_DIR:-$ROOT_DIR/logs}
CONDA_ENV=${CONDA_ENV:-mintai}
TTS_CONDA_ENV=${TTS_CONDA_ENV:-index-tts}
TTS_CJG_PORT_LABEL=${TTS_CJG_PORT:-9032}
CONDA_AVAILABLE=0
CONDA_SH=""

# 创建日志目录
mkdir -p "$LOG_DIR"

# 激活 conda 环境
if command -v conda >/dev/null 2>&1; then
    CONDA_BASE=$(conda info --base 2>/dev/null || echo "$HOME/anaconda3")
    CONDA_SH="$CONDA_BASE/etc/profile.d/conda.sh"
    if [ -f "$CONDA_SH" ]; then
        CONDA_AVAILABLE=1
        # 临时禁用严格模式以避免conda激活脚本的变量问题
        set +u
        # shellcheck disable=SC1090
        source "$CONDA_SH"
        conda activate "$CONDA_ENV"
        set -u
        echo "✅ Conda环境 '$CONDA_ENV' 已激活"
    else
        echo "⚠️  未找到conda激活脚本($CONDA_SH)，跳过环境激活"
    fi
else
    echo "⚠️  未找到conda，跳过环境激活"
fi

echo "🚀 开始启动所有服务..."
echo "📁 日志目录: $LOG_DIR"
echo "---"

# 1. 启动 ASR 服务
echo "🎤 启动ASR服务..."
nohup bash ./scripts/start-asr_minnan.sh > "$LOG_DIR/asr_minnan.log" 2>&1 &
ASR_PID=$!
echo "   ASR 服务已启动 (PID: $ASR_PID, 日志: $LOG_DIR/asr_minnan.log)"

# 2. 启动 TTS 服务（陈嘉庚版本）
echo "🔊 启动陈嘉庚TTS服务..."
TTS_ENV_LABEL="当前Shell"
if [ "$CONDA_AVAILABLE" -eq 1 ] && [ -f "$CONDA_SH" ]; then
    nohup bash -c "set -euo pipefail; source \"$CONDA_SH\"; conda activate \"$TTS_CONDA_ENV\"; bash ./scripts/start-tts_cjg.sh" > "$LOG_DIR/tts_cjg.log" 2>&1 &
    TTS_ENV_LABEL="conda:${TTS_CONDA_ENV}"
else
    echo "   ⚠️ 未检测到可用的 conda，使用当前环境启动陈嘉庚TTS服务"
    nohup bash ./scripts/start-tts_cjg.sh > "$LOG_DIR/tts_cjg.log" 2>&1 &
fi
TTS_PID=$!
echo "   陈嘉庚TTS 服务已启动 (PID: $TTS_PID, 日志: $LOG_DIR/tts_cjg.log, 环境: $TTS_ENV_LABEL)"

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
# echo "🔒 启动VPN服务..."
# if [ -d ~/.config/mihomo ] && [ -f ~/.config/mihomo/clash-linux ]; then
#     cd ~/.config/mihomo
#     nohup ./clash-linux > "$LOG_DIR/vpn.log" 2>&1 &
#     VPN_PID=$!
#     echo "   VPN 服务已启动 (PID: $VPN_PID, 日志: $LOG_DIR/vpn.log)"
# else
#     echo "   ⚠️  未找到VPN配置文件，跳过VPN启动"
# fi

echo "---"
echo "✅ 所有服务启动完成!"
echo "📊 服务状态:"
echo "   ASR:     http://localhost:9010"
echo "   TTS(CJG): http://localhost:${TTS_CJG_PORT_LABEL}"
# echo "   LLM:     http://localhost:9020"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "📁 查看日志: tail -f $LOG_DIR/*.log"
echo "🛑 停止服务: ./stop-all.sh"
