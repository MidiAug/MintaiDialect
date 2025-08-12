from typing import Any, Dict
import time
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def synthesize(text: str, *, target_language: str, voice_style: str = "default", audio_format: str = "wav") -> Dict[str, Any]:
    """
    调用外部 TTS 服务将文本(台罗拼音)转为语音。

    返回值约定：优先读取 audio_url；若直接返回音频二进制，由上层负责保存。
    """
    if not settings.tts_service_url:
        raise RuntimeError("TTS 服务未配置 (tts_service_url 为空)")

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            start_ts = time.monotonic()
            async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
                # 兼容我们当前 tts_service 的 GET /tts?text= 形式
                try:
                    logger.debug("[TTS] attempt=%d GET %s/tts text_len=%d", attempt, settings.tts_service_url, len(text or ""))
                    resp = await client.get(
                        f"{settings.tts_service_url}/tts",
                        params={"text": text},
                        headers={
                            "Authorization": f"Bearer {settings.provider_api_key}" if settings.provider_api_key else ""
                        },
                    )
                    resp.raise_for_status()
                    # 当前 tts_service 直接返回音频文件
                    if resp.headers.get("content-type", "").startswith("audio/"):
                        dur = (time.monotonic() - start_ts) * 1000
                        logger.info("[TTS] status=%d time=%.1fms content_type=%s size=%d",
                                    resp.status_code, dur, resp.headers.get("content-type"), len(resp.content))
                        return {"binary": resp.content, "content_type": resp.headers.get("content-type")}
                except Exception:
                    # 回退到 JSON POST 协议
                    logger.debug("[TTS] GET 失败，尝试 POST JSON 协议")
                    payload = {
                        "text": text,
                        "target_language": target_language,
                        "voice_style": voice_style,
                        "audio_format": audio_format,
                    }
                    resp = await client.post(
                        f"{settings.tts_service_url}/tts",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {settings.provider_api_key}" if settings.provider_api_key else ""
                        },
                    )
                    resp.raise_for_status()
                    if resp.headers.get("content-type", "").startswith("application/json"):
                        js = resp.json()
                        dur = (time.monotonic() - start_ts) * 1000
                        logger.info("[TTS] status=%d time=%.1fms json_keys=%s",
                                    resp.status_code, dur, list(js.keys()))
                        return {
                            "audio_url": js.get("audio_url") or (js.get("data") or {}).get("audio_url"),
                            "raw": js,
                        }
                    dur = (time.monotonic() - start_ts) * 1000
                    logger.info("[TTS] status=%d time=%.1fms content_type=%s size=%d",
                                resp.status_code, dur, resp.headers.get("content-type"), len(resp.content))
                    return {"binary": resp.content}
        except Exception as e:
            last_exc = e
            logger.warning("[TTS] attempt=%d failed: %s", attempt, e)
    raise httpx.HTTPError(f"TTS service failed after retries: {last_exc}")


