#!/bin/bash

# 统一配置加载脚本
# 支持通过 jq 或 Python 解析 JSON 配置文件
# 优先级：环境变量 > 配置文件 > 默认值

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
CONFIG_FILE="${ROOT_DIR}/config/services.json"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
  echo "⚠️  警告: 配置文件 $CONFIG_FILE 不存在，使用环境变量或默认值"
  return 0 2>/dev/null || exit 0
fi

# 尝试使用 jq 解析 JSON
if command -v jq &> /dev/null; then
  # 使用 jq 解析
  export FRONTEND_PORT=${FRONTEND_PORT:-$(jq -r '.frontend.port' "$CONFIG_FILE")}
  export FRONTEND_HOST=${FRONTEND_HOST:-$(jq -r '.frontend.host' "$CONFIG_FILE")}
  
  export BACKEND_PORT=${BACKEND_PORT:-$(jq -r '.backend.port' "$CONFIG_FILE")}
  export BACKEND_HOST=${BACKEND_HOST:-$(jq -r '.backend.host' "$CONFIG_FILE")}
  
  export ASR_PORT=${ASR_PORT:-$(jq -r '.services.asr_minnan.port' "$CONFIG_FILE")}
  export ASR_HOST=${ASR_HOST:-$(jq -r '.services.asr_minnan.host' "$CONFIG_FILE")}
  
  export LLM_PORT=${LLM_PORT:-$(jq -r '.services.llm.port' "$CONFIG_FILE")}
  export LLM_HOST=${LLM_HOST:-$(jq -r '.services.llm.host' "$CONFIG_FILE")}
  
  export TTS_PORT=${TTS_PORT:-$(jq -r '.services.tts.port' "$CONFIG_FILE")}
  export TTS_HOST=${TTS_HOST:-$(jq -r '.services.tts.host' "$CONFIG_FILE")}
  
  export TTS_CJG_PORT=${TTS_CJG_PORT:-$(jq -r '.services.tts_cjg.port' "$CONFIG_FILE")}
  export TTS_CJG_HOST=${TTS_CJG_HOST:-$(jq -r '.services.tts_cjg.host' "$CONFIG_FILE")}
  
# 如果没有 jq，使用 Python 解析
elif command -v python3 &> /dev/null || command -v python &> /dev/null; then
  PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
  
  # 使用 Python 解析 JSON
  eval "$($PYTHON_CMD << 'PYTHON_EOF'
import json
import os
import sys

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    
    # 前端配置
    frontend_port = os.getenv('FRONTEND_PORT', str(cfg['frontend']['port']))
    frontend_host = os.getenv('FRONTEND_HOST', cfg['frontend']['host'])
    
    # 后端配置
    backend_port = os.getenv('BACKEND_PORT', str(cfg['backend']['port']))
    backend_host = os.getenv('BACKEND_HOST', cfg['backend']['host'])
    
    # 服务配置
    asr_port = os.getenv('ASR_PORT', str(cfg['services']['asr_minnan']['port']))
    asr_host = os.getenv('ASR_HOST', cfg['services']['asr_minnan']['host'])
    
    llm_port = os.getenv('LLM_PORT', str(cfg['services']['llm']['port']))
    llm_host = os.getenv('LLM_HOST', cfg['services']['llm']['host'])
    
    tts_port = os.getenv('TTS_PORT', str(cfg['services']['tts']['port']))
    tts_host = os.getenv('TTS_HOST', cfg['services']['tts']['host'])
    
    tts_cjg_port = os.getenv('TTS_CJG_PORT', str(cfg['services']['tts_cjg']['port']))
    tts_cjg_host = os.getenv('TTS_CJG_HOST', cfg['services']['tts_cjg']['host'])
    
    # 输出 export 语句
    print(f'export FRONTEND_PORT={frontend_port}')
    print(f'export FRONTEND_HOST={frontend_host}')
    print(f'export BACKEND_PORT={backend_port}')
    print(f'export BACKEND_HOST={backend_host}')
    print(f'export ASR_PORT={asr_port}')
    print(f'export ASR_HOST={asr_host}')
    print(f'export LLM_PORT={llm_port}')
    print(f'export LLM_HOST={llm_host}')
    print(f'export TTS_PORT={tts_port}')
    print(f'export TTS_HOST={tts_host}')
    print(f'export TTS_CJG_PORT={tts_cjg_port}')
    print(f'export TTS_CJG_HOST={tts_cjg_host}')
except Exception as e:
    print(f'# 错误: 无法解析配置文件: {e}', file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
  "$CONFIG_FILE")"
  
else
  echo "⚠️  警告: 未找到 jq 或 Python，无法解析配置文件，使用环境变量或默认值"
fi

