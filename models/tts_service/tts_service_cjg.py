#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from indextts.infer import IndexTTS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ------------------------------
# 读取环境变量
# ------------------------------
MODEL_DIR = os.environ.get("MODEL_DIR", "/home/yyz/ckpts/runs/infer-cjg-ckpt")
CFG_PATH = os.path.join(MODEL_DIR, "config.yaml")
SPEAKER_INFO_PATH = os.path.join(MODEL_DIR, "speaker_info.json")
OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------
# 默认参考音频路径（必填）
# ------------------------------
AUDIO_PROMPT = os.environ.get(
    "AUDIO_PROMPT", "/home/yyz/infer-code/tests/陈嘉庚.wav"
)
if not os.path.isfile(AUDIO_PROMPT):
    raise FileNotFoundError(f"[TTS-CJG] 找不到默认参考音频: {AUDIO_PROMPT}")

# ------------------------------
# 初始化 TTS 模型
# ------------------------------
try:
    tts = IndexTTS(
        model_dir=MODEL_DIR,
        cfg_path=CFG_PATH,
        speaker_info_path=SPEAKER_INFO_PATH
    )
except Exception as e:
    raise RuntimeError(f"[TTS-CJG] 模型加载失败，请检查 MODEL_DIR 是否正确: {MODEL_DIR}\n错误信息: {e}")

# 获取可用说话人
speaker_info = getattr(tts, "speaker_info", None)
available_speakers = list(speaker_info.keys()) if speaker_info else ["cjg"]
logger.info(f"Multi-speaker support enabled with {len(available_speakers)} speakers: {available_speakers}")
logger.info(f"Model directory: {MODEL_DIR}")
logger.info(f"Audio prompt file: {AUDIO_PROMPT}")
logger.info(f"Output directory: {OUTPUT_DIR}")

# ------------------------------
# FastAPI 实例
# ------------------------------
app = FastAPI(title="陈嘉庚TTS服务", version="1.0")

# ------------------------------
# 请求体定义
# ------------------------------
class TTSRequest(BaseModel):
    text: str
    speaker: str = "cjg"  # 默认使用 cjg
    do_sample: Optional[bool] = True
    top_p: Optional[float] = 0.8
    top_k: Optional[int] = 30
    temperature: Optional[float] = 0.6
    length_penalty: Optional[float] = 0.0
    num_beams: Optional[int] = 3
    repetition_penalty: Optional[float] = 10.0
    max_mel_tokens: Optional[int] = 600
    max_text_tokens_per_sentence: Optional[int] = 120
    sentences_bucket_max_size: Optional[int] = 4
    infer_mode: Optional[str] = "普通推理"  # 可选: 普通推理 / 批次推理

# ------------------------------
# 接口：文本转语音
# ------------------------------
@app.post("/tts")
async def synthesize(req: TTSRequest, request: Request):
    """
    文本转语音接口
    请求示例:
    {
        "text": "你好",
        "speaker": "cjg"
    }
    """
    # 记录请求信息
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"[TTS-CJG] 收到请求 - IP: {client_ip}, URL: {request.url}")
    logger.info(f"[TTS-CJG] 请求参数: text_len={len(req.text)}, speaker={req.speaker}, "
                f"do_sample={req.do_sample}, top_p={req.top_p}, top_k={req.top_k}, "
                f"temperature={req.temperature}, infer_mode={req.infer_mode}")
    logger.info(f"[TTS-CJG] 请求文本预览: {req.text[:50]}{'...' if len(req.text) > 50 else ''}")
    
    if req.speaker not in available_speakers:
        logger.error(f"[TTS-CJG] 无效的说话人: {req.speaker}, 可用说话人: {available_speakers}")
        return {"error": f"speaker {req.speaker} not found. Available: {available_speakers}"}

    output_path = os.path.join(OUTPUT_DIR, f"{req.speaker}_{int(time.time())}.wav")
    logger.info(f"[TTS-CJG] 输出文件路径: {output_path}")

    kwargs = {
        "do_sample": bool(req.do_sample),
        "top_p": float(req.top_p),
        "top_k": int(req.top_k) if req.top_k > 0 else None,
        "temperature": float(req.temperature),
        "length_penalty": float(req.length_penalty),
        "num_beams": int(req.num_beams),
        "repetition_penalty": float(req.repetition_penalty),
        "max_mel_tokens": int(req.max_mel_tokens),
    }
    
    logger.info(f"[TTS-CJG] 推理参数: {kwargs}")
    logger.info(f"[TTS-CJG] 使用推理模式: {req.infer_mode}")

    # 开始推理计时
    start_time = time.time()
    
    try:
        if req.infer_mode == "普通推理":
            logger.info(f"[TTS-CJG] 开始普通推理...")
            tts.infer(
                audio_prompt=AUDIO_PROMPT,  # 必传参考音频
                text=req.text,
                output_path=output_path,
                speaker_id=req.speaker,
                max_text_tokens_per_sentence=int(req.max_text_tokens_per_sentence),
                **kwargs
            )
        else:
            # 批次推理
            logger.info(f"[TTS-CJG] 开始批次推理...")
            tts.infer_fast(
                audio_prompt=AUDIO_PROMPT,  # 必传参考音频
                text=req.text,
                output_path=output_path,
                speaker_id=req.speaker,
                max_text_tokens_per_sentence=int(req.max_text_tokens_per_sentence),
                sentences_bucket_max_size=int(req.sentences_bucket_max_size),
                **kwargs
            )
        
        # 推理完成
        inference_time = time.time() - start_time
        logger.info(f"[TTS-CJG] 推理完成，耗时: {inference_time:.2f}秒")
        
        # 检查输出文件
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"[TTS-CJG] 输出文件生成成功: {output_path}, 大小: {file_size} bytes")
        else:
            logger.error(f"[TTS-CJG] 输出文件未生成: {output_path}")
            return {"error": "TTS推理失败，输出文件未生成"}

    except Exception as e:
        inference_time = time.time() - start_time
        logger.error(f"[TTS-CJG] 推理失败，耗时: {inference_time:.2f}秒, 错误: {str(e)}")
        return {"error": f"TTS推理失败: {str(e)}"}

    return FileResponse(output_path, media_type="audio/wav")

# =============================
# 开发时直接运行
# =============================
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 9002))
    log_level = os.getenv("LOG_LEVEL", "info")
    
    logger.info(f"[TTS-CJG] 启动陈嘉庚TTS服务...")
    logger.info(f"[TTS-CJG] 服务地址: http://{host}:{port}")
    logger.info(f"[TTS-CJG] TTS接口: http://{host}:{port}/tts")
    logger.info(f"[TTS-CJG] 日志级别: {log_level}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        reload=True,
        reload_dirs=[os.path.dirname(__file__)]
    )
