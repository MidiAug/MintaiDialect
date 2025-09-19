from typing import Any, Dict
import time
import logging
import httpx
from app.core.config import settings
from app.core.exceptions import ASRServiceError

logger = logging.getLogger(__name__)


async def transcribe(audio_filename: str, audio_bytes: bytes, *, source_language: str) -> Dict[str, Any]:
    """
    调用外部 ASR 服务将音频转文字。

    返回值约定：尽量兼容不同服务，优先读取 'text'，否则尝试 data.text。
    """
    if not settings.asr_service_url:
        raise ASRServiceError("ASR 服务未配置 (asr_service_url 为空)")

    # 简单重试 3 次
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            start_ts = time.monotonic()
            async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
                # 兼容两种字段名：大多数服务用 "file"，也有后端使用 "audio_file"
                files = {
                    "file": (audio_filename, audio_bytes),
                    "audio_file": (audio_filename, audio_bytes),
                }
                data = {
                    "source_language": source_language,
                }
                # 兼容我们当前 asr_service 的 FastAPI 端点（POST /asr，接收 multipart）
                logger.debug(
                    "[ASR] attempt=%d POST %s/asr, bytes=%d, data=%s",
                    attempt, settings.asr_service_url, len(audio_bytes or b""), {k: data[k] for k in data}
                )
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
                dur = (time.monotonic() - start_ts) * 1000
                logger.info("[ASR] status=%d time=%.1fms text_preview=%s",
                            resp.status_code, dur,
                            (js.get("text", "")[:80] + "...") if (js.get("text") and len(js.get("text")) > 80) else js.get("text"))
                return {
                    "text": js.get("text") or (js.get("data") or {}).get("text"),
                    "raw": js,
                }
        except Exception as e:
            last_exc = e
            logger.warning("[ASR] attempt=%d failed: %s", attempt, e)
    raise ASRServiceError(f"ASR 服务重试失败: {last_exc}")


