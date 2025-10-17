import io
import logging
import shutil
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Tuple

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.models.schemas import AudioFormat

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
    - target_format: 目标音频格式（如 'wav', 'mp3', 'flac', 'm4a'）
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

        # ✅ 修正 m4a 特殊处理
        export_format = tf
        export_codec = None
        export_params = {}

        if tf == "m4a":
            export_format = "mp4"       # ffmpeg 使用 mp4 容器
            export_codec = "aac"        # 使用 AAC 编码
            export_params = {"bitrate": "192k"}

        if export_codec:
            audio.export(out_io, format=export_format, codec=export_codec, **export_params)
        else:
            audio.export(out_io, format=export_format)

        logger.info("[audio_utils] 音频格式转换完成：%s -> %s", sf or "unknown", tf)
        return out_io.getvalue()

    except Exception as e:
        logger.warning("[audio_utils] 音频格式转换失败：%s -> %s, 错误: %s", sf or "unknown", tf, e)
        # 转换失败则返回原始音频
        return raw_audio



def process_audio_file(file, contents: bytes) -> Tuple[bytes, str]:
    """
    统一的音频文件处理函数
    包含格式校验、大小校验和格式转换
    
    Args:
        file: 文件对象，需要有 filename 属性
        contents: 音频文件内容（bytes）
    
    Returns:
        Tuple[bytes, str]: (处理后的音频数据, 处理后的文件名)
    
    Raises:
        ValidationError: 当文件格式不支持、文件过大或转换失败时
    """
    logger = logging.getLogger(__name__)
    
    # 1. 基础校验
    if not hasattr(file, 'filename') or not file.filename:
        raise ValidationError("文件名不能为空")
    
    # 2. 获取文件扩展名
    file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    
    # 3. 检查是否为支持的音频格式
    supported_formats = [fmt.value for fmt in AudioFormat]
    if file_extension not in supported_formats:
        raise ValidationError(f"不支持的音频格式: {file_extension}。支持的格式: {', '.join(supported_formats)}")
    
    # 4. 文件大小校验
    max_size = settings.max_file_size
    if len(contents) > max_size:
        max_size_mb = max_size / 1024 / 1024
        current_size_mb = len(contents) / 1024 / 1024
        raise ValidationError(f"音频文件过大，请上传小于{max_size_mb:.0f}MB的文件，当前文件大小为 {current_size_mb:.2f}MB")
    
    # 5. 音频格式转换
    processed_audio_bytes = contents
    processed_filename = file.filename
    
    if file_extension != 'wav':
        logger.info(f"[AudioProcessor] 检测到非WAV格式 ({file_extension})，开始转换为WAV格式")
        converted_audio = convert_format(contents, file_extension, 'wav')
        if converted_audio == contents:
            raise ValidationError(f"音频格式转换失败，无法将 {file_extension} 格式转换为WAV格式")
        
        processed_audio_bytes = converted_audio
        processed_filename = file.filename.rsplit('.', 1)[0] + '.wav'
        logger.info(f"[AudioProcessor] 音频格式转换成功: {file_extension} -> wav, 大小: {len(processed_audio_bytes)} bytes")
    else:
        logger.debug(f"[AudioProcessor] 音频已是WAV格式，无需转换")
    
    return processed_audio_bytes, processed_filename

