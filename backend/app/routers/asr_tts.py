"""
语音文本互转API路由器 - ASR/TTS功能
"""

from fastapi import APIRouter, File, UploadFile, Form, Request
from typing import Optional
import uuid
import os
import time
import logging
from app.models.schemas import (
    ASRRequest, ASRResponse, TTSRequest, TTSResponse,
    BaseResponse, ErrorResponse, LanguageType, AudioFormat
)
from app.core.config import settings
from app.core.exceptions import ValidationError, LLMServiceError, TTSServiceError, ASRServiceError
from app.services import asr_service, tts_service, llm_service
import json
import re
from pathlib import Path
from app.services.audio_utils import get_duration_seconds, convert_format

router = APIRouter(tags=["语音文本互转"])
logger = logging.getLogger(__name__)

# 预加载示例，避免每次请求读盘
try:
    _EXAMPLES = json.loads(Path(settings.example_text_path).read_text(encoding="utf-8"))
except Exception:
    _EXAMPLES = []


# ============ 工具：解析真实音频时长 ============
def _get_audio_duration_seconds(filename: str, contents: bytes) -> float | None:
    return get_duration_seconds(filename, contents)


# ============ 语音识别 (ASR) 接口 ============
@router.post(
    "/asr",
    response_model=BaseResponse,
    summary="语音转文字",
    description="上传音频文件并指定语种，调用 ASR 服务进行语音识别，返回识别文本与时长"
)
async def speech_to_text(
    audio_file: UploadFile = File(..., description="上传音频文件（支持 wav/mp3/flac/m4a/ogg 格式）"),
    source_language: str = Form(..., description="语音识别语种（例如 zh, en, minnan）")
):
    logger.info(f"[ASR] 收到文件: {audio_file.filename}, 语种: {source_language}")
    contents = await audio_file.read()
    logger.debug(f"[ASR] 文件大小: {len(contents)} bytes")
    
    # 音频格式校验
    if not audio_file.filename:
        raise ValidationError("文件名不能为空")
    
    # 获取文件扩展名
    file_extension = audio_file.filename.lower().split('.')[-1] if '.' in audio_file.filename else ''
    
    # 检查是否为支持的音频格式
    supported_formats = [fmt.value for fmt in AudioFormat]
    if file_extension not in supported_formats:
        raise ValidationError(f"不支持的音频格式: {file_extension}。支持的格式: {', '.join(supported_formats)}")
    
    # 文件大小校验：限制为10MB
    max_size = settings.max_file_size
    if len(contents) > max_size:
        raise ValidationError(f"文件大小不能超过10MB，当前文件大小为 {len(contents) / 1024 / 1024:.2f}MB")

    # 音频格式转换：将非WAV格式转换为WAV
    processed_audio_bytes = contents
    processed_filename = audio_file.filename
    
    if file_extension != 'wav':
        logger.info(f"[ASR] 检测到非WAV格式 ({file_extension})，开始转换为WAV格式")
        converted_audio = convert_format(contents, file_extension, 'wav')
        if converted_audio == contents:
            raise ValidationError(f"音频格式转换失败，无法将 {file_extension} 格式转换为WAV格式")
        
        processed_audio_bytes = converted_audio
        processed_filename = audio_file.filename.rsplit('.', 1)[0] + '.wav'
        logger.info(f"[ASR] 音频格式转换成功: {file_extension} -> wav, 大小: {len(processed_audio_bytes)} bytes")
    else:
        logger.debug(f"[ASR] 音频已是WAV格式，无需转换")

    # 调用 ASR 服务
    try:
        result = await asr_service.transcribe(
            audio_bytes=processed_audio_bytes,
            audio_filename=processed_filename,
            source_language=source_language
        )
        logger.debug(f"[ASR] 服务返回: {result}")
    except Exception as e:
        logger.exception(f"[ASR] 服务调用失败: {str(e)}")
        raise ASRServiceError(f"ASR 服务调用失败: {str(e)}")

    # 验证返回结果
    if not result or "text" not in result:
        logger.error(f"[ASR] 返回结果不完整: {result}")
        raise ASRServiceError("ASR 服务返回结果无效")

    duration = _get_audio_duration_seconds(processed_filename, processed_audio_bytes)
    preview = (result["text"] or "")[:60]
    logger.info(f"[ASR] 完成: text='{preview}'... duration={duration}")
    
    return BaseResponse(
        success=True,
        message="语音识别完成",
        data={
            "text": result["text"],
            "duration": duration
        }
    )


# ============ 文本转语音 (TTS) 接口 ============

@router.post(
    "/tts",
    response_model=BaseResponse,
    summary="文本转语音",
    description="将文本转换为目标方言语音，返回可播放的音频 URL 及时长估算。",
    responses={
        200: {
            "description": "合成成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "文本转语音完成",
                        "data": {
                            "poj_text": "Li2-ho2 se3-kai1",
                            "audio_url": "/uploads/tts_xxx.wav",
                            "audio_duration": 1.68,
                            "file_size": 123456,
                        }
                    }
                }
            }
        },
        400: {"description": "参数不合法"},
        500: {"description": "服务内部错误"}
    }
)
async def text_to_speech(
    request: Request,
    text: str = Form(..., description="要合成的文本"),
    target_language: str = Form(..., description="目标语言，如 minnan"),
    speed: float = Form(1.0, description="语速，默认 1.0"),
    audio_format: str = Form(..., description="输出音频格式，如 wav, mp3, flac, m4a, ogg"),
):
    """
    将文本转换为语音
    
    - **text**: 要转换的文本内容
    - **target_language**: 目标语言/方言
    - **speed**: 语音速度 (0.5-2.0)
    - **audio_format**: 输出音频格式
    """
    logger.info(f"[TTS] 收到请求，文本长度={len(text)}, 目标语言={target_language}, speed={speed}, audio_format={audio_format}")

    # 参数验证
    if len(text) > 1000:
        raise ValidationError("文本长度不能超过1000个字符")

    # 1) LLM 转换 POJ
    example_text = "\n".join(
        [f'示例{i+1}：\nzh：{e.get("zh","")}\nPOJ：{e.get("POJ","")}' for i, e in enumerate(_EXAMPLES)]
    )
    sys_prompt = (
        "你是方言罗马字助手，请将输入文本转换为闽南语 POJ 白话字注音。"
        "严格只输出 JSON，格式如下：{\"POJ\":\"用户文本对应的POJ白话文注音（不含标点）\"}。"
        "不要输出 JSON 以外的任何字符。POJ 中需要将用户原文本的中的标点符号替换为空格以实现句子的分割,句子内使用'-'连接。"
        f"示例：{example_text}"
    )
    user_prompt = f"用户文本：{text}"

    def _parse_llm(raw: str) -> str:
        try:
            data = json.loads(raw)
            poj = data.get("POJ", "")
            logger.debug(f"[TTS][_parse_llm] JSON解析成功, POJ='{poj}'")
            return poj
        except Exception as e:
            logger.warning(f"[TTS][_parse_llm] JSON解析失败: {str(e)}，退化解析原始文本")
            return " "  # 避免空串导致 TTS 报错

    try:
        llm_out = await llm_service.chat_messages([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ])
        resp_text = llm_out.get("text", "")
        logger.info(f"[TTS] LLM 返回文本长度={len(resp_text)}")
    except Exception as e:
        logger.exception(f"[TTS] LLM 服务调用失败: {str(e)}")
        raise LLMServiceError(f"LLM 服务调用失败: {str(e)}")

    poj_text = _parse_llm(resp_text) if resp_text else text
    if not poj_text.strip():
        logger.warning("[TTS] LLM 未返回 POJ，退化为原文")
        poj_text = text

    # 2) 调用 TTS 服务
    if not settings.tts_service_url:
        raise TTSServiceError("未配置 TTS 服务")

    try:
        tts_res = await tts_service.synthesize(
            text=poj_text,
            target_language=target_language,
            speaking_rate=speed,
            audio_format=(audio_format or "wav").lower(),
        )
    except Exception as e:
        logger.exception(f"[TTS] TTS 服务调用失败: {str(e)}")
        raise TTSServiceError(f"TTS 服务调用失败: {str(e)}")

    if not tts_res.get("binary"):
        raise TTSServiceError("TTS 服务未返回音频数据")

    # 3) 根据实际返回格式准备文件路径
    uploads_dir = Path(settings.upload_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    # 从 TTS 服务返回的 content_type 中提取实际格式
    content_type = tts_res.get("content_type", "audio/wav")
    actual_format = content_type.split("/")[-1] if "/" in content_type else "wav"
    audio_filename = f"{file_id}.{actual_format}"
    audio_path = uploads_dir / audio_filename
    logger.info(f"[TTS] 输出音频路径: {audio_path} (实际格式: {actual_format})")

    # 4) 保存音频文件
    audio_path.write_bytes(tts_res["binary"])
    logger.info(f"[TTS] 音频生成成功, 大小={audio_path.stat().st_size} bytes")

    if not audio_path.exists():
        raise TTSServiceError("TTS 音频文件未生成")

    # 5) 构建响应
    file_size = os.path.getsize(audio_path)
    estimated_duration = max(0.5, len(poj_text) * 0.08)
    try:
        audio_url = str(request.url_for("uploads", path=audio_filename))
    except Exception:
        audio_url = f"/uploads/{audio_filename}"

    # 确保以枚举返回真实格式（以保存文件的后缀为准）
    real_ext = (Path(audio_path).suffix or '').lstrip('.').lower() or audio_fmt or 'wav'
    audio_format_enum = AudioFormat(real_ext)

    resp = TTSResponse(
        audio_url=audio_url,
        audio_duration=estimated_duration,
        file_size=file_size,
        poj_text=poj_text,
        audio_format=audio_format_enum,
    )

    logger.info(f"[TTS] 文本转语音完成, 文件大小={file_size}, 预计时长={estimated_duration:.2f}s, url={audio_url}")
    return BaseResponse(success=True, message="文本转语音完成", data=resp)
