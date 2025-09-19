import io
import logging
import shutil
import subprocess
import uuid
import wave
from pathlib import Path

from app.core.config import settings

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

logger = logging.getLogger(__name__)


def get_duration_seconds(filename: str, contents: bytes) -> float | None:
    """
    获取音频时长（秒）。
    - 优先用标准库解析 WAV
    - 其他格式若系统存在 ffprobe 则调用解析
    - 失败返回 None
    """
    try:
        ext = (filename.rsplit('.', 1)[-1] if '.' in filename else '').lower()
        if ext == 'wav':
            try:
                with wave.open(io.BytesIO(contents), 'rb') as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    return float(frames) / float(rate) if rate else None
            except Exception as e:
                logger.debug("[audio_utils] parse wav failed: %s", e)

        if shutil.which('ffprobe'):
            tmp_dir = Path(settings.upload_dir)
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = tmp_dir / f"_probe_{uuid.uuid4().hex}.{ext or 'bin'}"
            try:
                tmp_path.write_bytes(contents)
                result = subprocess.run(
                    [
                        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1', str(tmp_path)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    val = result.stdout.strip()
                    return float(val) if val else None
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as e:
        logger.debug("[audio_utils] get_duration_seconds error: %s", e)
        return None
    return None


def convert_format(raw_audio: bytes, source_format: str | None, target_format: str | None) -> bytes:
    """
    音频格式转换
    - source_format: 原始音频格式（如 'wav', 'mp3', 'flac'）
    - target_format: 目标音频格式（如 'wav', 'mp3', 'flac'）
    返回 bytes 类型的音频数据
    """
    sf = (source_format or "").lower()
    tf = (target_format or "").lower()

    # 无音频数据直接返回
    if not raw_audio:
        return raw_audio

    # 目标格式为空或与源格式相同，直接返回
    if not tf or tf == sf:
        return raw_audio

    # 使用 pydub 进行转码
    if AudioSegment is None:
        logger.warning("[audio_utils] pydub 未安装，无法进行音频格式转换：%s -> %s", sf or "unknown", tf)
        return raw_audio

    try:
        audio = AudioSegment.from_file(io.BytesIO(raw_audio), format=sf or None)

        out_io = io.BytesIO()
        audio.export(out_io, format=tf)
        logger.info("[audio_utils] 音频格式转换完成：%s -> %s", sf or "unknown", tf)

        return out_io.getvalue()

    except Exception as e:
        logger.warning("[audio_utils] 音频格式转换失败：%s -> %s, 错误: %s", sf or "unknown", tf, e)
        # 转换失败则返回原始音频
        return raw_audio

