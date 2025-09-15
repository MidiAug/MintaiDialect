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
    allowed_audio_formats: List[str] = ["wav", "mp3", "flac", "m4a", "ogg", "webm"]
    
    # CORS配置
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ]
    
    # 外部模型服务配置（通过HTTP调用本地独立服务或云厂商API网关）
    # 留空则使用内置的模拟返回，以保证开发阶段可用
    # 本地微服务默认端口（如未通过环境变量覆盖，则使用本地服务）
    # 端口按用户要求：ASR=9000, TTS=9002
    asr_service_url: str = os.getenv("ASR_SERVICE_URL", "http://127.0.0.1:9000")
    tts_service_url: str = os.getenv("TTS_SERVICE_URL", "http://127.0.0.1:9002")
    speech_translation_service_url: str = os.getenv("SPEECH_TRANSLATION_SERVICE_URL", "")
    voice_interaction_service_url: str = os.getenv("VOICE_INTERACTION_SERVICE_URL", "")
    voice_cloning_service_url: str = os.getenv("VOICE_CLONING_SERVICE_URL", "")
    # LLM 默认走云厂商分支（DeepSeek），也可通过环境变量切换或指定本地 llm_service_url
    llm_service_url: str = os.getenv("LLM_SERVICE_URL", "")
    
    provider_name: str = os.getenv("PROVIDER_NAME", "deepseek")
    provider_api_key: str = os.getenv("PROVIDER_API_KEY", "sk-f20295f5bd454c8fbb40409865669884")

    # provider_name: str = os.getenv("PROVIDER_NAME", "qwen")
    # provider_api_key: str = os.getenv("PROVIDER_API_KEY", "sk-75c80f6957ca4655a2033fc5cda4bb3c")

    # 统一的请求配置
    model_request_timeout: int = 60  # 秒
    # LLM厂商配置
    # DeepSeek（默认）
    deepseek_api_base: str = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "")
    
    # Gemini（保留：当 provider_name=gemini 时使用）
    gemini_api_base: str = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")

    # 数字嘉庚相关：检索内容文件路径（默认硬编码到仓库内）
    jiageng_retrieval_path: str = "knowledge/digital_jiageng.txt"
    
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

    # 短信推送服务配置（例如 spug）
    # 示例： https://push.spug.cc/send/<TOKEN>
    # 硬编码默认值；可被环境变量覆盖
    sms_push_url: str = os.getenv("SMS_PUSH_URL", "https://push.spug.cc/send/X4PBx8EwBOjYAny5")
    sms_push_name: str = os.getenv("SMS_PUSH_NAME", "推送助手")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 创建全局配置实例
def _load_settings() -> Settings:
    s = Settings()
    # 支持通过 ALLOWED_ORIGINS=comma,separated,urls 覆盖默认
    env_val = os.getenv("ALLOWED_ORIGINS")
    if env_val:
        s.allowed_origins = [x.strip() for x in env_val.split(",") if x.strip()]
    return s

settings = _load_settings()

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