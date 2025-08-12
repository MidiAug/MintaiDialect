#!/bin/bash

echo "🎤 启动ASR模型服务 (端口: 9000)"
cd models/asr_service
python3 asr_service.py
