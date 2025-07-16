"""
应用配置模块
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    app_name: str = "闽台方言大模型API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # API配置
    api_v1_str: str = "/api"
    
    # 数据库配置
    database_url: str = "sqlite:///./dialect_ai.db"
    
    # 文件上传配置
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "uploads"
    allowed_audio_formats: List[str] = ["wav", "mp3", "flac", "m4a", "ogg"]
    
    # CORS配置
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # AI模型配置 (预留)
    # ASR模型配置
    asr_model_path: str = ""
    asr_model_name: str = "whisper-base"
    
    # TTS模型配置
    tts_model_path: str = ""
    tts_model_name: str = "tts-model"
    
    # 语音翻译模型配置
    translation_model_path: str = ""
    translation_model_name: str = "speech-translation-model"
    
    # 对话模型配置
    dialogue_model_path: str = ""
    dialogue_model_name: str = "dialogue-model"
    
    # 音色克隆模型配置
    voice_cloning_model_path: str = ""
    voice_cloning_model_name: str = "voice-cloning-model"
    
    # 音频处理配置
    audio_sample_rate: int = 16000
    audio_max_duration: int = 300  # 5分钟
    
    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1小时
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # 安全配置
    secret_key: str = "your-secret-key-here"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 创建全局配置实例
settings = Settings()

# 确保必要的目录存在
def ensure_directories():
    """确保必要的目录存在"""
    import os
    from pathlib import Path
    
    directories = [
        settings.upload_dir,
        "logs",
        "cache",
        "models"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# 初始化目录
ensure_directories() 