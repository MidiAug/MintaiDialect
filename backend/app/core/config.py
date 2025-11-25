"""
应用配置模块
"""

from pydantic_settings import BaseSettings
from typing import List, Dict, Any
import os
import json
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from urllib import request, error as urllib_error

def _load_services_config() -> Dict[str, Any]:
    """
    加载统一服务配置文件 config/services.json
    如果文件不存在或解析失败，返回空字典（使用默认值）
    """
    try:
        # 获取项目根目录（backend/app/core/config.py -> 项目根目录）
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        config_file = project_root / "config" / "services.json"
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logging.warning(f"统一配置文件不存在: {config_file}，使用默认配置")
            return {}
    except Exception as e:
        logging.warning(f"加载统一配置文件失败: {e}，使用默认配置")
        return {}

# 加载服务配置
_services_config = _load_services_config()


def _is_local_llm_available(host: str, port: int) -> bool:
    """探测本地 LLM 服务是否可用"""
    health_url = f"http://{host}:{port}/health"
    try:
        with request.urlopen(health_url, timeout=1.5) as resp:
            if resp.status != 200:
                return False
            payload = resp.read().decode("utf-8") or "{}"
            data = json.loads(payload)
            status = data.get("status")
            model_loaded = data.get("model_loaded", False)
            return status == "healthy" or model_loaded
    except (urllib_error.URLError, TimeoutError, ValueError) as exc:
        logging.debug(f"本地 LLM 健康检查失败: {exc}")
        return False
    except Exception as exc:
        logging.debug(f"本地 LLM 探测异常: {exc}")
        return False


def _get_llm_service_url() -> str:
    """
    获取 LLM 服务 URL：
    1. 读取 config/services.json 中 llm 的 host/port
    2. 探测本地服务可用则使用本地 vLLM
    3. 探测失败则使用云端 Provider
    """
    host = "127.0.0.1"
    port: int | str = 9020

    if _services_config and "services" in _services_config:
        services = _services_config["services"]
        llm_config = services.get("llm", {})
        host = llm_config.get("host", host)
        port = llm_config.get("port", port)

    try:
        port = int(port)
    except (TypeError, ValueError):
        logging.warning(f"LLM 端口配置非法: {port}，回退使用 9020")
        port = 9020

    if _is_local_llm_available(host, port):
        logging.warning(f"[LLM] 检测到本地服务，使用 http://{host}:{port}")
        return f"http://{host}:{port}"

    fallback_provider = os.getenv("PROVIDER_NAME", "qwen")
    logging.warning(f"[LLM] 未检测到本地服务，回退到云端 Provider ({fallback_provider})")
    return ""

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
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_dir: str = "uploads"
    allowed_audio_formats: List[str] = ["wav", "mp3", "flac", "m4a", "ogg", "webm"]
    
    # CORS配置（根据统一配置文件动态生成）
    # 优先级：环境变量 > 配置文件 > 默认值
    def _get_cors_origins() -> List[str]:
        """根据配置文件动态生成 CORS allowed_origins"""
        default_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174"
        ]
        
        # 如果配置文件存在，添加前端端口
        if _services_config and "frontend" in _services_config:
            frontend_config = _services_config["frontend"]
            frontend_port = frontend_config.get("port", 5173)
            frontend_host = frontend_config.get("host", "localhost")
            
            # 生成前端 URL
            origins = [
                f"http://{frontend_host}:{frontend_port}",
                f"http://127.0.0.1:{frontend_port}"
            ]
            
            # 如果 host 是 localhost，也添加 localhost 版本
            if frontend_host != "localhost":
                origins.append(f"http://localhost:{frontend_port}")
            
            # 合并默认值（去重）
            all_origins = list(set(origins + default_origins))
            return all_origins
        
        return default_origins
    
    allowed_origins: List[str] = _get_cors_origins()
    
    # 外部模型服务配置（通过HTTP调用本地独立服务或云厂商API网关）
    # 留空则使用内置的模拟返回，以保证开发阶段可用
    # 本地微服务默认端口（如未通过环境变量覆盖，则使用本地服务）
    # 端口规则：
    #   - 标准服务（多语言模型）：ASR=9010, LLM=9020, TTS=9030
    #   - 方言ASR服务：9011, 9012, ... (x从1开始)
    #   - 方言TTS服务：9031, 9032, ... (x从1开始)
    #   注意：LLM只有标准服务（9020），无方言服务
    # 优先级：环境变量 > 统一配置文件 > 默认值
    def _get_service_url(service_name: str, default_port: int) -> str:
        """根据服务名获取服务 URL（优先级：环境变量 > 配置文件 > 默认值）"""
        env_key = f"{service_name.upper()}_SERVICE_URL"
        env_url = os.getenv(env_key)
        if env_url:
            return env_url
        
        # 从统一配置文件读取
        if _services_config and "services" in _services_config:
            services = _services_config["services"]
            if service_name in services:
                service_config = services[service_name]
                host = service_config.get("host", "127.0.0.1")
                port = service_config.get("port", default_port)
                return f"http://{host}:{port}"
        
        # 默认值
        return f"http://127.0.0.1:{default_port}"
    
    asr_service_url: str = _get_service_url("asr_minnan", 9011)
    tts_service_url: str = _get_service_url("tts", 9030)
    tts_minnan_service_url: str = _get_service_url("tts", 9030)  # 使用标准 TTS 服务
    tts_cjg_service_url: str = _get_service_url("tts_cjg", 9031)
    speech_translation_service_url: str = os.getenv("SPEECH_TRANSLATION_SERVICE_URL", "")
    voice_interaction_service_url: str = os.getenv("VOICE_INTERACTION_SERVICE_URL", "")
    voice_cloning_service_url: str = os.getenv("VOICE_CLONING_SERVICE_URL", "")
    llm_service_url: str = ""
    
    
    # 统一的请求配置
    model_request_timeout: int = 60  # 秒
    
    # LLM厂商配置
    
    # provider_name: str = os.getenv("PROVIDER_NAME", "gemini")
    # provider_api_key: str = os.getenv("PROVIDER_API_KEY", "AIzaSyBC8nX8_VrPMI5d5YEdad8oulx_XPsEX5s,AIzaSyBm1MMLkgmJhBcZVyhEp58IdXXI-tsCZFs")
    # llm_model_name: str = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
    
    # provider_name: str = os.getenv("PROVIDER_NAME", "deepseek")
    # llm_model_name: str = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
    # provider_api_key: str = os.getenv("PROVIDER_API_KEY", "sk-f20295f5bd454c8fbb40409865669884")

    provider_name: str = os.getenv("PROVIDER_NAME", "qwen")
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "qwen-max")
    provider_api_key: str = os.getenv("PROVIDER_API_KEY", "sk-75c80f6957ca4655a2033fc5cda4bb3c")


    # 数字嘉庚相关：检索内容文件路径（默认硬编码到仓库内）
    jiageng_stories_path: str = "data/jiageng_stories.txt"
    minnan_examples_path: str = "data/minnan_examples.json"
    minnan_lexicon_path: str = "data/minnan_lexicon.json"
    
    # 音频处理配置
    audio_sample_rate: int = 16000
    audio_max_duration: int = 300  # 5分钟
    
    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1小时
    
    # 日志配置
    log_level: str = "DEBUG"
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
    
    # 支持通过环境变量覆盖服务 URL（优先级最高）
    if os.getenv("ASR_SERVICE_URL"):
        s.asr_service_url = os.getenv("ASR_SERVICE_URL")
    if os.getenv("TTS_MINNAN_SERVICE_URL"):
        s.tts_minnan_service_url = os.getenv("TTS_MINNAN_SERVICE_URL")
    if os.getenv("TTS_CJG_SERVICE_URL"):
        s.tts_cjg_service_url = os.getenv("TTS_CJG_SERVICE_URL")
    
    return s

settings = _load_settings()


def refresh_llm_service_url() -> str:
    """
    重新探测并刷新 LLM 服务地址。
    在 FastAPI startup 事件中调用，确保日志系统已初始化。
    """
    url = _get_llm_service_url()
    settings.llm_service_url = url
    return url

# 确保必要的目录存在
def ensure_directories():
    """确保必要的目录存在"""
    import os
    from pathlib import Path
    
    directories = [
        settings.upload_dir,
        "logs",
        "cache"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# 初始化目录
ensure_directories() 


# 自定义日志格式化器（去除app前缀，添加毫秒）
class CustomFormatter(logging.Formatter):
    """自定义格式化器，去除logger name中的app.前缀，并添加毫秒精度"""
    def formatTime(self, record, datefmt=None):
        """重写formatTime方法，添加毫秒精度"""
        import time
        ct = time.localtime(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime("%H:%M:%S", ct)
        # 添加毫秒
        s = s + f".{int(record.msecs):03d}"
        return s
    
    def format(self, record):
        # 去除name中的app.前缀
        if record.name.startswith('app.'):
            record.name = record.name[4:]  # 移除'app.'前缀
        
        return super().format(record)

# 日志统一初始化（集中式）
def configure_logging():
    """
    依据 Settings 中的 log_level 与 log_file 统一配置日志：
    - 设置 root logger 等级
    - 标准输出与文件（可轮转）双通道输出
    - 第三方库降噪
    可重复调用，具备幂等性（会复用已有 handler 并更新其等级与格式）。
    """
    level_name = (settings.log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = CustomFormatter(
        fmt="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 控制台输出（存在则更新，没有则添加）
    stream_handler = None
    for h in root_logger.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            stream_handler = h
            break
    if stream_handler is None:
        stream_handler = logging.StreamHandler()
        root_logger.addHandler(stream_handler)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    # 文件输出（轮转），存在则更新，没有则添加
    log_file_path = settings.log_file or "logs/app.log"
    try:
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    except Exception:
        pass

    file_handler = None
    for h in root_logger.handlers:
        if isinstance(h, logging.FileHandler):
            file_handler = h
            break
    if file_handler is None:
        file_handler = RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        root_logger.addHandler(file_handler)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # 第三方库降噪
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
