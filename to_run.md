# 终端1 - ASR服务
cd MintaiDialect
conda activate mintai
bash ./scripts/single/start-asr.sh

# 终端2 - LLM服务  
cd MintaiDialect
conda activate mintai
bash ./scripts/single/start-llm.sh

# 终端3 - TTS服务
cd MintaiDialect
conda activate mintai
bash ./scripts/single/start-tts.sh

# 终端4 - 后端服务
cd MintaiDialect
conda activate mintai
./scripts/single/start-backend.sh

# 终端5 - 前端服务
cd MintaiDialect
conda activate mintai
./scripts/single/start-frontend.sh