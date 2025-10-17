start-all.sh

# 终端1 - ASR服务
cd MintaiDialect
conda activate mintai
bash ./scripts/start-asr.sh

# 终端2 - LLM服务  
cd MintaiDialect
conda activate mintai
bash ./scripts/start-llm.sh

# 终端3 - TTS服务
cd MintaiDialect
conda activate mintai
bash ./scripts/start-tts.sh

# 终端4 - 后端服务
cd MintaiDialect
conda activate mintai
./scripts/start-backend.sh

# 终端5 - 前端服务
cd MintaiDialect
conda activate mintai
./scripts/start-frontend.sh

# 终端6 - vpn
kill -9 $(lsof -t -i :7890)
cd ~/.config/mihomo
./clash-linux

wget -U "Mozilla/6.0" -O ~/.config/mihomo/config.yaml "https://v1.v2ai.top/link/OZUpESmIRbY3JxBPB9NMQJUdgJhxeXK2BUxl?clash=2"

# 终端7 - swagger
cd MintaiDialect
conda activate mintai
python3 -m http.server 3000