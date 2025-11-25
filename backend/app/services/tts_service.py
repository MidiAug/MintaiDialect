from typing import Any, Dict, List
import time
import logging
import asyncio
import httpx
from app.core.config import settings
from app.core.exceptions import TTSServiceError
from app.services.audio_utils import convert_format, concatenate_audio_segments

logger = logging.getLogger(__name__)

def _maybe_convert_audio(raw_audio: bytes, source_format: str, target_format: str) -> bytes:
    """
    占位：根据目标格式进行音频转封装/转码。
    - 目前项目仅使用 wav，因此默认直接返回原始数据。
    - 将来如需支持 mp3/ogg/flac，可在此实现实际转换逻辑（如依赖 ffmpeg）。
    """
    if not raw_audio:
        return raw_audio
    sf = (source_format or "").lower()
    tf = (target_format or "").lower()
    if tf in ("", "wav") or tf == sf:
        return raw_audio
    logger.info("[TTS] 占位转换：%s -> %s（当前为直返占位，不做实际转换）", sf or "unknown", tf)
    return raw_audio

async def synthesize_minnan(
    text: str,
    target_language: str,
    speaking_rate: float | None = 1.0,
    audio_format: str = "wav"
) -> Dict[str, Any]:
    """
    调用闽南语TTS服务将文本转为语音。
    返回值：{"binary": bytes, "content_type": "audio/wav"}
    """
    if not settings.tts_minnan_service_url:
        raise TTSServiceError("闽南语TTS服务未配置 (tts_minnan_service_url 为空)")

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            start_ts = time.monotonic()
            async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
                payload = {
                    "text": text,
                    "target_language": target_language,
                    "speaking_rate": speaking_rate,
                    "audio_format": audio_format,
                }
                logger.debug("[TTS-MINNAN] 请求: url=%s payload={len(text)=%d, target_language=%s, speaking_rate=%s, audio_format=%s}",
                             f"{settings.tts_minnan_service_url}/tts", len(text or ""), target_language, str(speaking_rate), audio_format)
                resp = await client.post(
                    f"{settings.tts_minnan_service_url}/tts",
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.provider_api_key}"} if settings.provider_api_key else {},
                )
                resp.raise_for_status()

                logger.debug("[TTS-MINNAN] 响应: status=%s content-type=%s length=%d", resp.status_code, resp.headers.get("content-type"), len(resp.content or b""))
                if resp.headers.get("content-type", "").startswith("audio/"):
                    dur = (time.monotonic() - start_ts) * 1000
                    logger.info("[TTS-MINNAN] attempt=%d success: %d bytes in %.1fms", attempt, len(resp.content), dur)
                    # 假设服务默认返回 wav，如需其他格式则转换
                    if audio_format and audio_format.lower() != "wav":
                        out_bytes = convert_format(resp.content, "wav", audio_format)
                        # 检查转换是否成功（通过字节数变化判断）
                        if len(out_bytes) != len(resp.content):
                            logger.info("[TTS-MINNAN] 格式转换成功: wav -> %s", audio_format)
                            return {"binary": out_bytes, "content_type": f"audio/{audio_format}"}
                        else:
                            logger.warning("[TTS-MINNAN] 格式转换失败，返回原始 wav 格式")
                            return {"binary": resp.content, "content_type": "audio/wav"}
                    else:
                        return {"binary": resp.content, "content_type": "audio/wav"}

                logger.warning("[TTS-MINNAN] attempt=%d unexpected response: %s", attempt, resp.headers.get("content-type"))
                return {"raw": resp.text}

        except Exception as e:
            last_exc = e
            logger.warning("[TTS-MINNAN] attempt=%d failed: %s", attempt, e)

    raise TTSServiceError(f"闽南语TTS服务重试失败: {last_exc}")


async def synthesize(
    text: str,
    target_language: str = "cjg",
    speaking_rate: float | None = 1.0,
    audio_format: str = "wav",
    **kwargs
) -> Dict[str, Any]:
    """
    根据语言类型调用相应的TTS服务将文本转为语音。
    返回值：{"binary": bytes, "content_type": "audio/wav"}
    
    Args:
        text: 要合成的文本
        target_language: 目标语言，默认为"cjg"（陈嘉庚），支持"minnan"（闽南语）
        speaking_rate: 语速
        audio_format: 音频格式
        **kwargs: 其他参数，传递给具体的TTS服务
    """
    logger.info("[TTS] 开始合成语音: language=%s, text_len=%d", target_language, len(text or ""))
    
    # 根据语言类型选择相应的TTS服务
    if target_language.lower() == "minnan":
        logger.info("[TTS] 使用闽南语TTS服务")
        return await synthesize_minnan(text, target_language, speaking_rate, audio_format)
    else:
        # 默认为陈嘉庚TTS服务
        logger.info("[TTS] 使用陈嘉庚TTS服务")
        return await synthesize_cjg(text, speaker=target_language, speaking_rate=speaking_rate, audio_format=audio_format, **kwargs)


async def synthesize_cjg(
    text: str,
    speaker: str = "cjg",
    speaking_rate: float | None = 1.0,
    audio_format: str = "wav",
    **kwargs
) -> Dict[str, Any]:
    """
    调用陈嘉庚TTS服务将文本转为语音。
    返回值：{"binary": bytes, "content_type": "audio/wav"}
    """
    if not settings.tts_cjg_service_url:
        raise TTSServiceError("陈嘉庚TTS服务未配置 (tts_cjg_service_url 为空)")

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            start_ts = time.monotonic()
            async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
                payload = {
                    "text": text,
                    "speaker": speaker,
                    "do_sample": kwargs.get("do_sample", True),
                    "top_p": kwargs.get("top_p", 0.8),
                    "top_k": kwargs.get("top_k", 30),
                    "temperature": kwargs.get("temperature", 1.0),
                    "length_penalty": kwargs.get("length_penalty", 0.0),
                    "num_beams": kwargs.get("num_beams", 3),
                    "repetition_penalty": kwargs.get("repetition_penalty", 10.0),
                    "max_mel_tokens": kwargs.get("max_mel_tokens", 600),
                    "max_text_tokens_per_sentence": kwargs.get("max_text_tokens_per_sentence", 120),
                    "sentences_bucket_max_size": kwargs.get("sentences_bucket_max_size", 4),
                    "infer_mode": kwargs.get("infer_mode", "普通推理"),
                }
                logger.debug("[TTS-CJG] 请求: url=%s payload={len(text)=%d, speaker=%s, speaking_rate=%s, audio_format=%s}",
                             f"{settings.tts_cjg_service_url}/tts", len(text or ""), speaker, str(speaking_rate), audio_format)
                resp = await client.post(
                    f"{settings.tts_cjg_service_url}/tts",
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.provider_api_key}"} if settings.provider_api_key else {},
                )
                resp.raise_for_status()

                logger.debug("[TTS-CJG] 响应: status=%s content-type=%s length=%d", resp.status_code, resp.headers.get("content-type"), len(resp.content or b""))
                if resp.headers.get("content-type", "").startswith("audio/"):
                    dur = (time.monotonic() - start_ts) * 1000
                    logger.info("[TTS-CJG] attempt=%d success: %d bytes in %.1fms", attempt, len(resp.content), dur)
                    # 假设服务默认返回 wav，如需其他格式则转换
                    if audio_format and audio_format.lower() != "wav":
                        out_bytes = convert_format(resp.content, "wav", audio_format)
                        # 检查转换是否成功（通过字节数变化判断）
                        if len(out_bytes) != len(resp.content):
                            logger.info("[TTS-CJG] 格式转换成功: wav -> %s", audio_format)
                            return {"binary": out_bytes, "content_type": f"audio/{audio_format}"}
                        else:
                            logger.warning("[TTS-CJG] 格式转换失败，返回原始 wav 格式")
                            return {"binary": resp.content, "content_type": "audio/wav"}
                    else:
                        return {"binary": resp.content, "content_type": "audio/wav"}

                logger.warning("[TTS-CJG] attempt=%d unexpected response: %s", attempt, resp.headers.get("content-type"))
                return {"raw": resp.text}

        except Exception as e:
            last_exc = e
            logger.warning("[TTS-CJG] attempt=%d failed: %s", attempt, e)

    raise TTSServiceError(f"陈嘉庚TTS服务重试失败: {last_exc}")


async def synthesize_cjg_batch(
    text_segments: List[str],
    speaker: str = "cjg",
    speaking_rate: float | None = 1.0,
    audio_format: str = "wav",
    **kwargs
) -> Dict[str, Any]:
    """
    批处理调用陈嘉庚TTS服务，并发处理多个文本片段，然后合并音频。
    用于 pause_format 模式，可以真正利用多 GPU/多 Worker 进行并行处理。
    
    返回值：{"binary": bytes, "content_type": "audio/wav"}
    
    Args:
        text_segments: 文本片段列表（已按 '｜' 分隔符切分）
        speaker: 说话人
        speaking_rate: 语速
        audio_format: 音频格式
        **kwargs: 其他参数，传递给具体的TTS服务
    
    Returns:
        {"binary": bytes, "content_type": "audio/wav"} 合并后的完整音频
    """
    if not settings.tts_cjg_service_url:
        raise TTSServiceError("陈嘉庚TTS服务未配置 (tts_cjg_service_url 为空)")
    
    if not text_segments:
        raise TTSServiceError("文本片段列表不能为空")
    
    # 如果只有一个片段，直接调用单次接口
    if len(text_segments) == 1:
        logger.info("[TTS-CJG-BATCH] 只有一个片段，使用单次接口")
        return await synthesize_cjg(
            text=text_segments[0],
            speaker=speaker,
            speaking_rate=speaking_rate,
            audio_format=audio_format,
            **kwargs
        )
    
    logger.info("[TTS-CJG-BATCH] 开始批处理合成: %d 个片段", len(text_segments))
    start_time = time.monotonic()
    
    async def synthesize_segment(segment_text: str, segment_index: int) -> bytes:
        """并发合成单个文本片段的音频"""
        try:
            result = await synthesize_cjg(
                text=segment_text,
                speaker=speaker,
                speaking_rate=speaking_rate,
                audio_format=audio_format,
                **kwargs
            )
            if not result.get("binary"):
                raise TTSServiceError(f"TTS 服务未返回音频数据（片段 {segment_index}: {segment_text[:20]}...）")
            logger.info("[TTS-CJG-BATCH] 片段 %d/%d 合成成功: %d bytes", 
                       segment_index + 1, len(text_segments), len(result["binary"]))
            return result["binary"]
        except Exception as e:
            logger.error("[TTS-CJG-BATCH] 片段 %d 合成失败: %s, 错误: %s", 
                        segment_index, segment_text[:30], e)
            raise
    
    # 并发调用 TTS 服务合成所有片段
    try:
        audio_segments = await asyncio.gather(*[
            synthesize_segment(seg, idx) 
            for idx, seg in enumerate(text_segments)
        ])
        
        # 合并所有音频片段
        try:
            final_audio_bytes = concatenate_audio_segments(audio_segments)
            elapsed_time = (time.monotonic() - start_time) * 1000
            logger.info(
                "[TTS-CJG-BATCH] 批处理完成: %d 个片段 -> %d bytes, 耗时: %.1fms",
                len(audio_segments),
                len(final_audio_bytes),
                elapsed_time,
            )
            return {"binary": final_audio_bytes, "content_type": "audio/wav"}
        except Exception as e:
            logger.exception("[TTS-CJG-BATCH] 音频合并失败: %s", e)
            raise TTSServiceError(f"音频合并失败: {str(e)}")
    
    except Exception as e:
        logger.exception("[TTS-CJG-BATCH] 批处理失败: %s", e)
        raise TTSServiceError(f"批处理TTS服务调用失败: {str(e)}")
