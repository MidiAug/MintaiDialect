#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List

from indextts.infer import IndexTTS

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

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
MODEL_DIR = os.environ.get("MODEL_DIR", "/root/data/MintaiDialect/models/tts_service/ckpt/cjg")
CFG_PATH = os.path.join(MODEL_DIR, "config.yaml")
SPEAKER_INFO_PATH = os.path.join(MODEL_DIR, "speaker_info.json")
OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------
# 默认参考音频路径（必填）
# ------------------------------
AUDIO_PROMPT = os.environ.get(
    "AUDIO_PROMPT", "/root/data/MintaiDialect/models/tts_service/infer-code/tests/陈嘉庚.wav"
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
# 线程池执行器（用于并发推理）
# ------------------------------
executor = ThreadPoolExecutor(max_workers=4)

# ------------------------------
# 音频合并工具函数
# ------------------------------
def concatenate_audio_files(audio_files: List[str]) -> str:
    """
    合并多个音频文件为一个完整的音频文件
    
    Args:
        audio_files: 音频文件路径列表
    
    Returns:
        str: 合并后的音频文件路径
    
    Raises:
        ValueError: 当 pydub 未安装或音频文件列表为空时
    """
    if AudioSegment is None:
        raise ValueError("pydub 未安装，无法合并音频片段。请安装: pip install pydub")
    
    if not audio_files:
        raise ValueError("音频文件列表不能为空")
    
    if len(audio_files) == 1:
        return audio_files[0]
    
    try:
        # 加载第一个音频文件作为基准
        combined = AudioSegment.from_wav(audio_files[0])
        
        # 依次合并其他文件
        for audio_file in audio_files[1:]:
            segment = AudioSegment.from_wav(audio_file)
            # 确保采样率和声道数一致（pydub 会自动处理）
            combined += segment
        
        # 生成合并后的文件路径
        merged_path = os.path.join(OUTPUT_DIR, f"merged_{int(time.time())}.wav")
        combined.export(merged_path, format="wav")
        
        logger.info(
            "[TTS-CJG] 音频合并完成: %d 个片段 -> %s",
            len(audio_files),
            merged_path,
        )
        return merged_path
    
    except Exception as e:
        logger.error("[TTS-CJG] 音频合并失败: %s", e)
        raise ValueError(f"音频合并失败: {str(e)}")


def _synthesize_segment_sync(
    segment_text: str,
    speaker: str,
    kwargs: dict,
    max_text_tokens_per_sentence: int,
    infer_mode: str,
    segment_index: int,
) -> str:
    """
    同步合成单个文本片段的音频（在线程池中执行）
    
    Returns:
        str: 生成的音频文件路径
    """
    segment_output_path = os.path.join(OUTPUT_DIR, f"{speaker}_seg{segment_index}_{int(time.time())}.wav")
    
    try:
        if infer_mode == "普通推理":
            tts.infer(
                audio_prompt=AUDIO_PROMPT,
                text=segment_text,
                output_path=segment_output_path,
                speaker_id=speaker,
                max_text_tokens_per_sentence=max_text_tokens_per_sentence,
                **kwargs
            )
        else:
            tts.infer_fast(
                audio_prompt=AUDIO_PROMPT,
                text=segment_text,
                output_path=segment_output_path,
                speaker_id=speaker,
                max_text_tokens_per_sentence=max_text_tokens_per_sentence,
                sentences_bucket_max_size=kwargs.get("sentences_bucket_max_size", 4),
                **kwargs
            )
        
        if not os.path.exists(segment_output_path):
            raise RuntimeError(f"片段音频文件未生成: {segment_output_path}")
        
        logger.info("[TTS-CJG] 片段 %d 合成成功: %s", segment_index, segment_output_path)
        return segment_output_path
    
    except Exception as e:
        logger.error("[TTS-CJG] 片段 %d 合成失败: %s, 错误: %s", segment_index, segment_text[:30], e)
        raise

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
        "sentences_bucket_max_size": int(req.sentences_bucket_max_size),
    }
    
    logger.info(f"[TTS-CJG] 推理参数: {kwargs}")
    logger.info(f"[TTS-CJG] 使用推理模式: {req.infer_mode}")

    # 开始推理计时
    start_time = time.time()
    
    try:
        # 检测文本中是否包含 '｜' 分隔符（pause_format 模式）
        text_segments: List[str] = []
        if "｜" in req.text:
            # 按 '｜' 分割文本，过滤空片段
            text_segments = [seg.strip() for seg in req.text.split("｜") if seg.strip()]
            logger.info(f"[TTS-CJG] 检测到 '｜' 分隔符，文本分割为 {len(text_segments)} 个片段")
        else:
            # 普通模式，整个文本作为一个片段
            text_segments = [req.text.strip()] if req.text.strip() else []

        if not text_segments:
            return {"error": "文本内容为空，无法合成音频"}

        # 如果只有一个片段，使用原有逻辑（避免不必要的并发开销）
        if len(text_segments) == 1:
            if req.infer_mode == "普通推理":
                logger.info(f"[TTS-CJG] 开始普通推理...")
                tts.infer(
                    audio_prompt=AUDIO_PROMPT,  # 必传参考音频
                    text=text_segments[0],
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
                    text=text_segments[0],
                    output_path=output_path,
                    speaker_id=req.speaker,
                    max_text_tokens_per_sentence=int(req.max_text_tokens_per_sentence),
                    sentences_bucket_max_size=int(req.sentences_bucket_max_size),
                    **kwargs
                )
        else:
            # 并发处理多个片段
            logger.info(f"[TTS-CJG] 开始并发合成 {len(text_segments)} 个音频片段...")
            
            # 准备并发任务（使用线程池执行器）
            loop = asyncio.get_event_loop()
            futures = []
            for idx, segment_text in enumerate(text_segments):
                future = loop.run_in_executor(
                    executor,
                    _synthesize_segment_sync,
                    segment_text,
                    req.speaker,
                    kwargs,
                    int(req.max_text_tokens_per_sentence),
                    req.infer_mode,
                    idx,
                )
                futures.append(future)
            
            # 等待所有片段合成完成
            try:
                segment_files = await asyncio.gather(*futures)
            except Exception as e:
                logger.error(f"[TTS-CJG] 并发合成过程中出错: {e}")
                raise
            
            # 合并所有音频片段
            try:
                output_path = concatenate_audio_files(segment_files)
                logger.info(f"[TTS-CJG] 并发合成完成，合并为: {output_path}")
                
                # 清理临时片段文件
                for seg_file in segment_files:
                    try:
                        if seg_file != output_path and os.path.exists(seg_file):
                            os.remove(seg_file)
                    except Exception as e:
                        logger.warning(f"[TTS-CJG] 清理临时文件失败: {seg_file}, 错误: {e}")
            except Exception as e:
                logger.exception(f"[TTS-CJG] 音频合并失败: {e}")
                return {"error": f"音频合并失败: {str(e)}"}
        
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
