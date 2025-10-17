"""
数据模型定义
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
from enum import Enum

# 基础响应模型
class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    message: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# 语言和方言枚举
class LanguageType(str, Enum):
    """语言类型枚举"""
    MANDARIN = "mandarin"      # 普通话
    MINNAN = "minnan"          # 闽南话
    HAKKA = "hakka"            # 客家话
    TAIWANESE = "taiwanese"     # 台湾话

class AudioFormat(str, Enum):
    """音频格式枚举"""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    M4A = "m4a"
    OGG = "ogg"

# ============ ASR/TTS 相关模型 ============

class ASRRequest(BaseModel):
    """语音识别请求模型"""
    audio_file: str = Field(..., description="音频文件路径或base64编码")
    source_language: LanguageType = Field(default=LanguageType.MINNAN, description="源语言")

class ASRResponse(BaseModel):
    """语音识别响应模型"""
    text: str = Field(..., description="识别出的文本")
    duration: float = Field(..., description="音频时长(秒)")


class TTSRequest(BaseModel):
    """文本转语音请求模型"""
    text: str = Field(..., description="要转换的文本", min_length=1)
    target_language: LanguageType = Field(default=LanguageType.MINNAN, description="目标语言")
    speed: float = Field(default=1.0, description="语音速度", ge=0.5, le=2.0)
    audio_format: AudioFormat = Field(default=AudioFormat.WAV, description="输出音频格式")

class TTSResponse(BaseModel):
    """文本转语音响应模型"""
    audio_url: str = Field(..., description="生成的音频文件URL")
    audio_duration: float = Field(..., description="音频时长(秒)")
    file_size: int = Field(..., description="文件大小(字节)")
    poj_text: Optional[str] = Field(None, description="用于合成的POJ文本")
    audio_format: AudioFormat = Field(default=AudioFormat.WAV, description="实际音频格式")

# ============ 语音翻译相关模型 ============

# ============ 数字嘉庚相关模型 ============

class DigitalJiagengSubtitle(BaseModel):
    text: str = Field(..., description="字幕文本")
    start_time: float = Field(..., description="开始时间(秒)")
    end_time: float = Field(..., description="结束时间(秒)")

class DigitalJiagengResponse(BaseModel):
    session_id: Optional[str] = Field(None, description="会话ID")
    response_audio_url: Optional[str] = Field(None, description="回复音频URL")
    subtitles: List[DigitalJiagengSubtitle] = Field(default_factory=list, description="字幕列表")

class DigitalJiagengChatRequest(BaseModel):
    """数字嘉庚对话请求模型"""
    text_input: Optional[str] = Field(None, description="文本输入")
    session_id: Optional[str] = Field(None, description="会话ID，用于多轮对话")
    input_language: LanguageType = Field(default=LanguageType.MINNAN, description="输入语言")
    output_language: LanguageType = Field(default=LanguageType.MINNAN, description="输出语言")
    speaking_speed: float = Field(default=1.0, description="语音速度", ge=0.5, le=2.0)
    show_subtitles: bool = Field(default=False, description="是否显示字幕")

class SpeechTranslationRequest(BaseModel):
    """语音翻译请求模型"""
    audio_file: str = Field(..., description="音频文件路径或base64编码")
    source_language: LanguageType = Field(..., description="源语言")
    target_language: LanguageType = Field(..., description="目标语言")
    return_audio: bool = Field(default=True, description="是否返回翻译后的语音")
    return_text: bool = Field(default=True, description="是否返回翻译后的文本")

class SpeechTranslationResponse(BaseModel):
    """语音翻译响应模型"""
    source_text: str = Field(..., description="识别出的源文本")
    target_text: str = Field(..., description="翻译后的目标文本")
    target_audio_url: Optional[str] = Field(None, description="翻译后的音频文件URL")
    confidence: float = Field(..., description="翻译置信度", ge=0, le=1)
    source_language: LanguageType = Field(..., description="源语言")
    target_language: LanguageType = Field(..., description="目标语言")

# ============ 语音交互相关模型 ============

class VoiceInteractionRequest(BaseModel):
    """语音交互请求模型"""
    audio_file: Optional[str] = Field(None, description="音频文件路径或base64编码")
    text_input: Optional[str] = Field(None, description="文本输入")
    conversation_id: Optional[str] = Field(None, description="对话ID，用于多轮对话")
    user_language: LanguageType = Field(default=LanguageType.MINNAN, description="用户语言")
    response_language: LanguageType = Field(default=LanguageType.MINNAN, description="回复语言")
    response_mode: str = Field(default="both", description="回复模式: text, audio, both")

class VoiceInteractionResponse(BaseModel):
    """语音交互响应模型"""
    conversation_id: str = Field(..., description="对话ID")
    user_input: str = Field(..., description="用户输入内容")
    response_text: str = Field(..., description="系统回复文本")
    response_audio_url: Optional[str] = Field(None, description="系统回复音频URL")
    emotion: Optional[str] = Field(None, description="检测到的情感")
    intent: Optional[str] = Field(None, description="检测到的意图")
    entities: Optional[List[Dict[str, Any]]] = Field(None, description="提取的实体")

# ============ 音色克隆相关模型 ============

class VoiceCloningRequest(BaseModel):
    """音色克隆请求模型"""
    reference_audio: str = Field(..., description="参考音频文件路径或base64编码")
    target_text: Optional[str] = Field(None, description="目标文本 (文本驱动模式)")
    target_audio: Optional[str] = Field(None, description="目标音频 (音频驱动模式)")
    cloning_mode: str = Field(default="text_driven", description="克隆模式: text_driven, audio_driven")
    quality: str = Field(default="high", description="生成质量: low, medium, high")
    preserve_emotion: bool = Field(default=True, description="是否保持情感")

class VoiceCloningResponse(BaseModel):
    """音色克隆响应模型"""
    cloned_audio_url: str = Field(..., description="克隆音频文件URL")
    similarity_score: float = Field(..., description="相似度评分", ge=0, le=1)
    quality_score: float = Field(..., description="质量评分", ge=0, le=1)
    processing_time: float = Field(..., description="处理时间(秒)")
    audio_duration: float = Field(..., description="音频时长(秒)")

# ============ 文件上传相关模型 ============

class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    file_url: str = Field(..., description="文件访问URL")
    file_size: int = Field(..., description="文件大小(字节)")
    file_format: str = Field(..., description="文件格式")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")

# ============ 任务状态相关模型 ============

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 等待中
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 失败

class TaskResponse(BaseModel):
    """异步任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(default=0.0, description="进度百分比", ge=0, le=100)
    result: Optional[Any] = Field(None, description="任务结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

# ============ 系统信息相关模型 ============

class SystemInfoResponse(BaseModel):
    """系统信息响应模型"""
    name: str = Field(..., description="系统名称")
    version: str = Field(..., description="版本号")
    status: str = Field(..., description="系统状态")
    uptime: float = Field(..., description="运行时间(秒)")
    supported_languages: List[LanguageType] = Field(..., description="支持的语言")
    supported_formats: List[AudioFormat] = Field(..., description="支持的音频格式")
    max_file_size: int = Field(..., description="最大文件大小(字节)")
    features: List[str] = Field(..., description="支持的功能列表") 