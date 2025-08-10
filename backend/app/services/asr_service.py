from typing import Any, Dict
import httpx
from app.core.config import settings


async def transcribe(audio_filename: str, audio_bytes: bytes, *, source_language: str,
                     enable_timestamps: bool = False, enable_word_level: bool = False) -> Dict[str, Any]:
    """
    调用外部 ASR 服务将音频转文字。

    返回值约定：尽量兼容不同服务，优先读取 'text'，否则尝试 data.text。
    """
    if not settings.asr_service_url:
        raise RuntimeError("ASR 服务未配置 (asr_service_url 为空)")

    # 简单重试 3 次
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
                # 兼容两种字段名：大多数服务用 "file"，也有后端使用 "audio_file"
                files = {
                    "file": (audio_filename, audio_bytes),
                    "audio_file": (audio_filename, audio_bytes),
                }
                data = {
                    "source_language": source_language,
                    "enable_timestamps": str(enable_timestamps).lower(),
                    "enable_word_level": str(enable_word_level).lower(),
                }
                resp = await client.post(
                    f"{settings.asr_service_url}/asr",
                    files=files,
                    data=data,
                    headers={
                        "Authorization": f"Bearer {settings.provider_api_key}" if settings.provider_api_key else ""
                    },
                )
                resp.raise_for_status()
                js = resp.json()
                return {
                    "text": js.get("text") or (js.get("data") or {}).get("text"),
                    "raw": js,
                }
        except Exception as e:
            last_exc = e
    raise httpx.HTTPError(f"ASR service failed after retries: {last_exc}")


