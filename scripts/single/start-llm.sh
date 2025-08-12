#!/bin/bash

echo "🧠 启动LLM模型服务 (端口: 9001)"
cd models/llm_service
python3 llm_service.py
