import io
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
import wave
import torch
import torchaudio
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


def _concatenate_audio_segments_torchaudio(audio_segments: list[bytes]) -> bytes:
    """
    使用 torchaudio 合并多个音频片段
    
    Args:
        audio_segments: 音频片段列表，每个元素为 bytes 类型的 WAV 音频数据
    
    Returns:
        bytes: 合并后的 WAV 音频数据
    
    Raises:
        ValueError: 当音频片段列表为空或合并失败时
    """
    wavs = []
    sample_rate = None
    
    try:
        # 使用 torchaudio 加载所有音频片段
        for segment_bytes in audio_segments:
            # torchaudio.load 支持类文件对象
            wav_tensor, sr = torchaudio.load(io.BytesIO(segment_bytes))
            
            # 记录第一个片段的采样率作为基准
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                # 如果采样率不一致，进行重采样（保持与第一个片段一致）
                logger.warning(
                    "[audio_utils] 采样率不一致 (%d vs %d)，进行重采样",
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
        temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"merged_torchaudio_{uuid.uuid4().hex}.wav")
        
        try:
            # 保存到临时文件
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
            "[audio_utils] 音频合并完成（torchaudio）: %d 个片段 -> %d bytes, 采样率: %d Hz",
            len(audio_segments),
            len(result),
            sample_rate,
        )
        return result
    
    except Exception as e:
        logger.error("[audio_utils] 音频合并失败（torchaudio）: %s", e)
        raise ValueError(f"音频合并失败（torchaudio）: {str(e)}")


def _concatenate_audio_segments_ffmpeg(audio_segments: list[bytes]) -> bytes:
    """
    使用 ffmpeg 合并多个音频片段
    
    Args:
        audio_segments: 音频片段列表，每个元素为 bytes 类型的 WAV 音频数据
    
    Returns:
        bytes: 合并后的 WAV 音频数据
    
    Raises:
        ValueError: 当音频片段列表为空、ffmpeg 不可用或合并失败时
    """
    # 检查 ffmpeg 是否可用
    if not shutil.which('ffmpeg'):
        raise ValueError("ffmpeg 未安装或不在 PATH 中，无法使用 ffmpeg 合并音频")
    
    temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else tempfile.gettempdir()
    temp_files = []
    concat_list_file = None
    output_file = None
    
    try:
        # 1. 将所有音频片段写入临时文件
        for idx, segment_bytes in enumerate(audio_segments):
            temp_file = os.path.join(temp_dir, f"segment_{idx}_{uuid.uuid4().hex}.wav")
            with open(temp_file, 'wb') as f:
                f.write(segment_bytes)
            temp_files.append(temp_file)
        
        # 2. 创建 concat 列表文件（ffmpeg concat demuxer 格式）
        concat_list_file = os.path.join(temp_dir, f"concat_list_{uuid.uuid4().hex}.txt")
        with open(concat_list_file, 'w') as f:
            for temp_file in temp_files:
                # 使用绝对路径，避免相对路径问题
                abs_path = os.path.abspath(temp_file)
                f.write(f"file '{abs_path}'\n")
        
        # 3. 使用 ffmpeg 合并音频
        output_file = os.path.join(temp_dir, f"merged_ffmpeg_{uuid.uuid4().hex}.wav")
        
        # ffmpeg 命令：使用 concat demuxer（适用于相同编码格式的音频）
        cmd = [
            'ffmpeg',
            '-f', 'concat',           # 使用 concat demuxer
            '-safe', '0',             # 允许不安全的文件名
            '-i', concat_list_file,   # 输入列表文件
            '-c', 'copy',             # 直接复制流，不重新编码（快速）
            '-y',                     # 覆盖输出文件
            output_file
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # 60秒超时
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "未知错误"
            raise RuntimeError(f"ffmpeg 合并失败: {error_msg}")
        
        # 4. 读取合并后的音频
        if not os.path.exists(output_file):
            raise RuntimeError("ffmpeg 输出文件未生成")
        
        with open(output_file, 'rb') as f:
            result_bytes = f.read()
        
        logger.info(
            "[audio_utils] 音频合并完成（ffmpeg）: %d 个片段 -> %d bytes",
            len(audio_segments),
            len(result_bytes),
        )
        return result_bytes
    
    except subprocess.TimeoutExpired:
        logger.error("[audio_utils] ffmpeg 合并超时（60秒）")
        raise ValueError("音频合并失败（ffmpeg）: 处理超时")
    except Exception as e:
        logger.error("[audio_utils] 音频合并失败（ffmpeg）: %s", e)
        raise ValueError(f"音频合并失败（ffmpeg）: {str(e)}")
    
    finally:
        # 清理所有临时文件
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        
        if concat_list_file and os.path.exists(concat_list_file):
            try:
                os.remove(concat_list_file)
            except Exception:
                pass
        
        if output_file and os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception:
                pass


def concatenate_audio_segments(
    audio_segments: list[bytes],
    backend: str = "ffmpeg"
) -> bytes:
    """
    合并多个音频片段为一个完整的音频文件（统一入口）
    
    Args:
        audio_segments: 音频片段列表，每个元素为 bytes 类型的 WAV 音频数据
        backend: 合并方式，可选 "torchaudio" 或 "ffmpeg"，默认为 "torchaudio"
    
    Returns:
        bytes: 合并后的 WAV 音频数据
    
    Raises:
        ValueError: 当音频片段列表为空、backend 参数无效或合并失败时
    """
    if not audio_segments:
        raise ValueError("音频片段列表不能为空")
    
    if len(audio_segments) == 1:
        return audio_segments[0]
    
    backend = backend.lower()
    
    if backend == "torchaudio":
        return _concatenate_audio_segments_torchaudio(audio_segments)
    elif backend == "ffmpeg":
        return _concatenate_audio_segments_ffmpeg(audio_segments)
    else:
        raise ValueError(f"不支持的 backend: {backend}，支持的值: 'torchaudio', 'ffmpeg'")

