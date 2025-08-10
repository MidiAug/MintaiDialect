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
    
    # 外部模型服务配置（通过HTTP调用本地独立服务或云厂商API网关）
    # 留空则使用内置的模拟返回，以保证开发阶段可用
    asr_service_url: str = ""
    tts_service_url: str = ""
    speech_translation_service_url: str = ""
    voice_interaction_service_url: str = ""
    voice_cloning_service_url: str = ""
    llm_service_url: str = ""  # 专用于文本→台罗拼音的模型服务

    # 统一的请求配置
    model_request_timeout: int = 60  # 秒
    provider_name: str = ""         # 可选：如 openai, azure, volcengine 等
    provider_api_key: str = ""      # 可选：云厂商API密钥
    # LLM厂商配置（示例：Google Gemini）
    llm_model_name: str = "gemini-2.0-flash"  # 当 provider_name=gemini 时使用
    gemini_api_base: str = "https://generativelanguage.googleapis.com/v1beta"

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