"""
服务层入口：封装与外部推理服务（ASR/LLM/TTS 等）的交互。

约定：
- 统一使用 httpx.AsyncClient 发起请求
- 从 app.core.config.settings 读取服务地址、超时与 API Key
- 返回尽量规范化的结构，具体字段由调用方（路由）再封装为响应模型
"""

__all__ = [
    "asr_service",
    "tts_service",
    "llm_service",
    "subtitle_service",
    "mock_service",
    "conversation_service",
    "jiageng_service",
]


