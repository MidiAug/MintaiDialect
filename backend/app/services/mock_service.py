import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.audio_utils import get_duration_seconds


@dataclass
class MockResult:
    text: str
    audio_url: str
    audio_duration: Optional[float]


async def mock_digital_jiageng(
    fixed_text: str,
    audio_filename: str,
    text_delay_seconds: float = 1.2,
    total_latency_seconds: float = 3.0,
) -> MockResult:
    """
    模拟 LLM + TTS：
    - text_delay_seconds 后返回文本
    - total_latency_seconds 内返回音频 URL
    - 若能读取到真实音频文件，返回其时长
    """
    start = time.time()
    await asyncio.sleep(max(0.0, text_delay_seconds))

    # 等待到总延迟
    remain = total_latency_seconds - (time.time() - start)
    await asyncio.sleep(max(0.0, remain))

    audio_url = f"/uploads/audio/{audio_filename}"
    audio_duration: Optional[float] = None
    try:
        wav_path = Path(settings.upload_dir) / "audio" / audio_filename
        if wav_path.exists():
            audio_duration = get_duration_seconds(audio_filename, wav_path.read_bytes()) or None
    except Exception:
        audio_duration = None

    return MockResult(text=fixed_text, audio_url=audio_url, audio_duration=audio_duration)


