from typing import Any, Dict
import httpx
from app.core.config import settings


async def synthesize(text: str, *, target_language: str, voice_style: str = "default", audio_format: str = "wav") -> Dict[str, Any]:
    """
    调用外部 TTS 服务将文本(台罗拼音)转为语音。

    返回值约定：优先读取 audio_url；若直接返回音频二进制，由上层负责保存。
    """
    if not settings.tts_service_url:
        raise RuntimeError("TTS 服务未配置 (tts_service_url 为空)")

    last_exc: Exception | None = None
    for _ in range(3):
        try:
            async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
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
                    return {
                        "audio_url": js.get("audio_url") or (js.get("data") or {}).get("audio_url"),
                        "raw": js,
                    }
                return {"binary": resp.content}
        except Exception as e:
            last_exc = e
    raise httpx.HTTPError(f"TTS service failed after retries: {last_exc}")


