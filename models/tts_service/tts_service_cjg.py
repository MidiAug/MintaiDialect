#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
import io
import asyncio
import uuid
import tempfile
import torch
import torchaudio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Union

from indextts.infer import IndexTTS

# ------------------------------
# Worker 标识（用于区分不同的 worker 进程）
# ------------------------------
# 获取进程 ID 作为 worker 标识
_process_id = os.getpid()
# 尝试从环境变量获取 worker 编号（uvicorn 可能设置）
_worker_id = os.environ.get("UVICORN_WORKER_ID") or os.environ.get("WORKER_ID")
if _worker_id:
    _worker_prefix = f"Worker-{_worker_id}"
else:
    # 如果没有环境变量，使用 PID 的后4位作为标识
    _worker_prefix = f"Worker-{str(_process_id)[-4:]}"

# 配置日志（添加 Worker 信息，时间精确到毫秒，不显示日期）
logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s.%(msecs)03d [{_worker_prefix}] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.info(f"[TTS-CJG] Worker 进程启动: PID={_process_id}, Worker={_worker_prefix}")

# ------------------------------
# 读取环境变量
# ------------------------------
MODEL_DIR = os.environ.get("MODEL_DIR", "/root/data/MintaiDialect/models/tts_service/ckpt/cjg")
CFG_PATH = os.path.join(MODEL_DIR, "config.yaml")
SPEAKER_INFO_PATH = os.path.join(MODEL_DIR, "speaker_info.json")
OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------
# 临时文件目录配置（I/O 优化：优先使用 /dev/shm）
# ------------------------------
# 如果是 Linux 系统，优先使用 /dev/shm（内存映射目录），速度极快
TEMP_DIR = "/dev/shm" if os.path.exists("/dev/shm") else tempfile.gettempdir()
logger.info(f"[TTS-CJG] 临时文件目录: {TEMP_DIR} ({'内存映射' if TEMP_DIR == '/dev/shm' else '普通临时目录'})")

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
# 本地版本的 IndexTTS 使用 speaker_list（列表），而不是 speaker_info（字典）
speaker_list = getattr(tts, "speaker_list", None)
available_speakers = speaker_list if speaker_list else ["cjg"]
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
    合并多个音频文件为一个完整的音频文件（已优化：使用 torchaudio）
    
    Args:
        audio_files: 音频文件路径列表
    
    Returns:
        str: 合并后的音频文件路径
    
    Raises:
        ValueError: 当音频文件列表为空或合并失败时
    """
    if not audio_files:
        raise ValueError("音频文件列表不能为空")
    
    if len(audio_files) == 1:
        return audio_files[0]
    
    try:
        # 使用 torchaudio 合并（性能更优）
        merged_bytes = merge_audio_tensors(audio_files)
        
        # 保存到输出目录
        merged_path = os.path.join(OUTPUT_DIR, f"merged_{int(time.time())}.wav")
        with open(merged_path, 'wb') as f:
            f.write(merged_bytes)
        
        logger.info(
            "[TTS-CJG] 音频合并完成（torchaudio）: %d 个片段 -> %s",
            len(audio_files),
            merged_path,
        )
        return merged_path
    
    except Exception as e:
        logger.error("[TTS-CJG] 音频合并失败: %s", e)
        raise ValueError(f"音频合并失败: {str(e)}")


def merge_audio_tensors(audio_paths_or_bytes: List[Union[str, bytes]]) -> bytes:
    """
    使用 torchaudio 合并多个音频片段（性能优化：移除 pydub 依赖）
    
    支持混合输入：可以是文件路径（str）或内存中的 bytes 数据
    
    Args:
        audio_paths_or_bytes: 音频片段列表，每个元素为 str（文件路径）或 bytes（内存数据）
    
    Returns:
        bytes: 合并后的 WAV 音频数据
    
    Raises:
        ValueError: 当音频片段列表为空或合并失败时
    """
    if not audio_paths_or_bytes:
        raise ValueError("音频片段列表不能为空")
    
    if len(audio_paths_or_bytes) == 1:
        item = audio_paths_or_bytes[0]
        if isinstance(item, bytes):
            return item
        else:
            # 如果是文件路径，读取并返回
            with open(item, 'rb') as f:
                return f.read()
    
    wavs = []
    sample_rate = None
    
    try:
        for item in audio_paths_or_bytes:
            # 如果是内存中的 bytes
            if isinstance(item, bytes):
                # torchaudio.load 支持类文件对象
                wav_tensor, sr = torchaudio.load(io.BytesIO(item))
            else:
                # 如果是文件路径
                wav_tensor, sr = torchaudio.load(item)
            
            # 记录第一个片段的采样率作为基准
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                # 如果采样率不一致，进行重采样（保持与第一个片段一致）
                logger.warning(
                    "[TTS-CJG] 采样率不一致 (%d vs %d)，进行重采样",
                    sr, sample_rate
                )
                resampler = torchaudio.transforms.Resample(sr, sample_rate)
                wav_tensor = resampler(wav_tensor)
            
            wavs.append(wav_tensor)
        
        if not wavs:
            raise ValueError("没有有效的音频数据")
        
        # 在时间维度(dim=1)上拼接所有音频张量
        combined_tensor = torch.cat(wavs, dim=1)
        
        # 导出到内存
        # 注意：torchcodec backend 不支持直接保存到 BytesIO，需要先保存到临时文件
        temp_file = os.path.join(TEMP_DIR, f"merged_{uuid.uuid4().hex}.wav")
        
        try:
            # 保存到临时文件（使用 /dev/shm 以提升性能）
            torchaudio.save(temp_file, combined_tensor, sample_rate, format="wav")
            # 读取到内存
            with open(temp_file, 'rb') as f:
                result = f.read()
        finally:
            # 清理临时文件
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        
        logger.info(
            "[TTS-CJG] 音频合并完成（torchaudio）: %d 个片段 -> %d bytes, 采样率: %d Hz",
            len(audio_paths_or_bytes),
            len(result),
            sample_rate,
        )
        return result
    
    except Exception as e:
        logger.error("[TTS-CJG] 音频合并失败（torchaudio）: %s", e)
        raise ValueError(f"音频合并失败: {str(e)}")


def concatenate_audio_bytes(audio_bytes_list: List[bytes]) -> bytes:
    """
    在内存中合并多个音频片段为一个完整的音频文件（已优化：使用 torchaudio）
    
    Args:
        audio_bytes_list: 音频片段列表，每个元素为 bytes 类型的 WAV 音频数据
    
    Returns:
        bytes: 合并后的 WAV 音频数据
    
    Raises:
        ValueError: 当音频片段列表为空或合并失败时
    """
    return merge_audio_tensors(audio_bytes_list)


def _synthesize_segment_sync(
    segment_text: str,
    speaker: str,
    kwargs: dict,
    max_text_tokens_per_sentence: int,
    infer_mode: str,
    segment_index: int,
) -> str:
    """
    同步合成单个文本片段的音频（在线程池中执行）- 返回文件路径（保留用于向后兼容）
    
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
        
        logger.info("[TTS-CJG] 片段 %d 合成成功: text='%s', %s", 
                   segment_index, segment_text[:50] + ('...' if len(segment_text) > 50 else ''), segment_output_path)
        return segment_output_path
    
    except Exception as e:
        logger.error("[TTS-CJG] 片段 %d 合成失败: %s, 错误: %s", segment_index, segment_text[:30], e)
        raise


def _synthesize_segment_to_bytes_sync(
    segment_text: str,
    speaker: str,
    kwargs: dict,
    max_text_tokens_per_sentence: int,
    infer_mode: str,
    segment_index: int,
) -> bytes:
    """
    同步合成单个文本片段的音频（在线程池中执行）- 返回音频bytes
    优化：使用 /dev/shm 内存文件系统，大幅提升 I/O 性能
    
    Returns:
        bytes: 生成的音频数据（WAV格式）
    """
    try:
        # 使用 /dev/shm 内存文件系统（Linux）或普通临时目录
        # 在 /dev/shm 中读写，实际上是在内存中操作，速度极快
        temp_filename = f"tts_{speaker}_seg{segment_index}_{uuid.uuid4().hex}.wav"
        temp_file_path = os.path.join(TEMP_DIR, temp_filename)
        
        try:
            if infer_mode == "普通推理":
                tts.infer(
                    audio_prompt=AUDIO_PROMPT,
                    text=segment_text,
                    output_path=temp_file_path,
                    speaker_id=speaker,
                    max_text_tokens_per_sentence=max_text_tokens_per_sentence,
                    **kwargs
                )
            else:
                tts.infer_fast(
                    audio_prompt=AUDIO_PROMPT,
                    text=segment_text,
                    output_path=temp_file_path,
                    speaker_id=speaker,
                    max_text_tokens_per_sentence=max_text_tokens_per_sentence,
                    sentences_bucket_max_size=kwargs.get("sentences_bucket_max_size", 4),
                    **kwargs
                )
            
            # 读取文件内容到内存（即使在 /dev/shm，读取也是极快的）
            with open(temp_file_path, 'rb') as f:
                audio_bytes = f.read()
            
            logger.info("[TTS-CJG] 片段 %d 合成成功: text='%s', %d bytes", 
                       segment_index, segment_text[:50] + ('...' if len(segment_text) > 50 else ''), len(audio_bytes))
            return audio_bytes
        
        finally:
            # 立即删除临时文件
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception as cleanup_error:
                logger.warning("[TTS-CJG] 清理临时文件失败: %s, 错误: %s", temp_file_path, cleanup_error)
    
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


class TTSBatchRequest(BaseModel):
    """批处理请求体（优先级1优化）"""
    segments: List[str]  # 文本片段列表
    speaker: str = "cjg"
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


# ------------------------------
# 接口：批处理文本转语音（优先级1优化）
# ------------------------------
@app.post("/tts/batch")
async def synthesize_batch(req: TTSBatchRequest, request: Request):
    """
    批处理文本转语音接口（优先级1优化）
    接收片段列表，内部并发处理，内存中合并返回
    请求示例:
    {
        "segments": ["片段1", "片段2", "片段3", "片段4"],
        "speaker": "cjg"
    }
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"[TTS-CJG-BATCH] 收到批处理请求 - IP: {client_ip}, 片段数: {len(req.segments)}")
    
    # 验证说话人
    if req.speaker not in available_speakers:
        logger.error(f"[TTS-CJG-BATCH] 无效的说话人: {req.speaker}, 可用说话人: {available_speakers}")
        return {"error": f"speaker {req.speaker} not found. Available: {available_speakers}"}
    
    # 验证片段列表
    if not req.segments:
        return {"error": "片段列表不能为空"}
    
    # 过滤空片段
    text_segments = [seg.strip() for seg in req.segments if seg.strip()]
    if not text_segments:
        return {"error": "没有有效的文本片段"}
    
    # 如果只有一个片段，直接调用单次接口
    if len(text_segments) == 1:
        logger.info("[TTS-CJG-BATCH] 只有一个片段，使用单次接口")
        single_req = TTSRequest(
            text=text_segments[0],
            speaker=req.speaker,
            do_sample=req.do_sample,
            top_p=req.top_p,
            top_k=req.top_k,
            temperature=req.temperature,
            length_penalty=req.length_penalty,
            num_beams=req.num_beams,
            repetition_penalty=req.repetition_penalty,
            max_mel_tokens=req.max_mel_tokens,
            max_text_tokens_per_sentence=req.max_text_tokens_per_sentence,
            sentences_bucket_max_size=req.sentences_bucket_max_size,
            infer_mode=req.infer_mode,
        )
        return await synthesize(single_req, request)
    
    # 准备推理参数
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
    
    start_time = time.time()
    logger.info(f"[TTS-CJG-BATCH] 开始批处理合成: {len(text_segments)} 个片段")
    
    try:
        # 准备并发任务（使用线程池执行器，返回bytes）
        loop = asyncio.get_event_loop()
        futures = []
        for idx, segment_text in enumerate(text_segments):
            future = loop.run_in_executor(
                executor,
                _synthesize_segment_to_bytes_sync,
                segment_text,
                req.speaker,
                kwargs,
                int(req.max_text_tokens_per_sentence),
                req.infer_mode,
                idx,
            )
            futures.append(future)
        
        # 等待所有片段合成完成（返回bytes列表）
        try:
            audio_bytes_list = await asyncio.gather(*futures)
            logger.info(f"[TTS-CJG-BATCH] 所有片段合成完成，开始合并音频")
        except Exception as e:
            logger.error(f"[TTS-CJG-BATCH] 并发合成过程中出错: {e}")
            return {"error": f"并发合成失败: {str(e)}"}
        
        # 在内存中合并所有音频片段（优先级2优化）
        try:
            final_audio_bytes = concatenate_audio_bytes(audio_bytes_list)
            inference_time = time.time() - start_time
            logger.info(
                f"[TTS-CJG-BATCH] 批处理完成: {len(audio_bytes_list)} 个片段 -> {len(final_audio_bytes)} bytes, 耗时: {inference_time:.2f}秒"
            )
        except Exception as e:
            logger.exception(f"[TTS-CJG-BATCH] 音频合并失败: {e}")
            return {"error": f"音频合并失败: {str(e)}"}
        
        # 直接返回音频bytes（不经过文件系统）
        return Response(
            content=final_audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=tts_batch_{int(time.time())}.wav"
            }
        )
    
    except Exception as e:
        inference_time = time.time() - start_time
        logger.error(f"[TTS-CJG-BATCH] 批处理失败，耗时: {inference_time:.2f}秒, 错误: {str(e)}")
        return {"error": f"批处理失败: {str(e)}"}
