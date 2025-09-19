# app/services/llm_service.py
from __future__ import annotations
from typing import Any, Dict, List, Callable, Awaitable
import time
import logging
import httpx
import itertools
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.exceptions import LLMServiceError


logger = logging.getLogger(__name__)

# ======================================================
# 工具函数
# ======================================================
def safe_extract(js: dict, *path, default: str = "") -> str:
    """安全取值，避免 KeyError/IndexError"""
    try:
        val = js
        for p in path:
            val = val[p]
        return val or default
    except Exception:
        return default

# 复用 httpx.AsyncClient
_shared_client: httpx.AsyncClient | None = None

async def get_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(timeout=settings.model_request_timeout)
    return _shared_client

# provider handler 类型
ProviderHandler = Callable[[List[Dict[str, str]], str | None], Awaitable[Dict[str, Any]]]
_registry: dict[str, ProviderHandler] = {}

def register_provider(name: str):
    def decorator(func: ProviderHandler):
        _registry[name.lower()] = func
        return func
    return decorator

# -------------------------------
# 轮流使用 API Key 列表
# -------------------------------
API_KEYS: List[str] = [k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip()]

if not API_KEYS:
    raise LLMServiceError("请至少在环境变量 GEMINI_API_KEYS 中设置一个有效的 key")

# 创建一个无限循环迭代器
api_key_cycle = itertools.cycle(API_KEYS)

# ======================================================
# Provider 实现
# ======================================================
@register_provider("gemini")
async def call_gemini(messages: List[Dict[str, str]], model_hint: str | None) -> Dict[str, Any]:
    model = model_hint or settings.llm_model_name or "gemini-2.5-flash"
    prompt = "\n".join([m.get("content", "") for m in messages])
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": settings.provider_api_key}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}},
    }

    client = await get_client()
    start = time.monotonic()
    try:
        resp = await client.post(endpoint, headers=headers, json=payload)
        dur = (time.monotonic() - start) * 1000
    except Exception as e:
        dur = (time.monotonic() - start) * 1000
        logger.error("[LLM] Gemini 请求异常: %s (耗时 %.1fms)", e, dur)
        return {"text": "", "raw": str(e)}

    # 处理非 200 状态码
    if resp.status_code != 200:
        logger.error(
            "[LLM] Gemini 请求失败 status=%d time=%.1fms\nHeaders: %s\nBody: %s",
            resp.status_code, dur, resp.headers, resp.text[:500]
        )
        return {"text": "", "raw": resp.text}

    # 成功响应，解析文本
    try:
        js = resp.json()
        text = safe_extract(js, "candidates", 0, "content", "parts", 0, "text")
        logger.info("[LLM] Gemini status=%d time=%.1fms text=%s",
                    resp.status_code, dur, text[:500])
        return {"text": text, "raw": js}
    except Exception as e:
        logger.error("[LLM] Gemini 解析响应失败: %s\n原始响应: %s", e, resp.text[:500])
        return {"text": "", "raw": resp.text}
    
# @register_provider("deepseek")
# async def call_deepseek(messages: List[Dict[str, str]], model_hint: str | None) -> Dict[str, Any]:
#     endpoint = "https://api.deepseek.com/chat/completions"
#     headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.provider_api_key}"}
#     payload = {
#         "model": model_hint or settings.llm_model_name or "deepseek-chat",
#         "messages": messages,
#         "stream": False,
#     }
#     client = await get_client()
#     start = time.monotonic()
#     resp = await client.post(endpoint, headers=headers, json=payload)
#     dur = (time.monotonic() - start) * 1000
#     logger.info("[LLM] DeepSeek status=%d time=%.1fms", resp.status_code, dur)
#     js = resp.json()
#     text = safe_extract(js, "choices", 0, "message", "content")
#     return {"text": text, "raw": js}


# @register_provider("dashscope")
# @register_provider("qwen")
# @register_provider("aliyun")
# async def call_dashscope(messages: List[Dict[str, str]], model_hint: str | None) -> Dict[str, Any]:
#     client = AsyncOpenAI(
#         api_key=settings.provider_api_key,
#         base_url=getattr(settings, "dashscope_api_base", "https://dashscope.aliyuncs.com/compatible-mode/v1")
#     )
#     start = time.monotonic()
#     try:
#         completion = await client.chat.completions.create(
#             model=model_hint or settings.llm_model_name or "qwen-max",
#             messages=messages,
#             extra_body={"enable_thinking": False},
#         )
#     except Exception as e:
#         dur = (time.monotonic() - start) * 1000
#         logger.error("[LLM] DashScope 请求失败: %s (耗时 %.1fms)", e, dur)
#         return {"text": "", "raw": str(e)}
#     dur = (time.monotonic() - start) * 1000
#     logger.info("[LLM] DashScope 返回成功 time=%.1fms", dur)
#     text = safe_extract(completion.model_dump(), "choices", 0, "message", "content")
#     return {"text": text, "raw": completion.model_dump()}


# ======================================================
# 主入口
# ======================================================
async def chat_messages(messages: List[Dict[str, str]], *, model_hint: str | None = None) -> Dict[str, Any]:
    """
    通用聊天接口：接受 OpenAI 兼容的 messages 列表。
    优先调用自建 llm_service，否则按 provider 调用。
    """
    # 1) 自建服务优先
    if settings.llm_service_url:
        client = await get_client()
        resp = await client.post(
            f"{settings.llm_service_url}/chat-messages",
            json={"messages": messages, "model": model_hint},
            headers={"Authorization": f"Bearer {settings.provider_api_key}" if settings.provider_api_key else ""},
        )
        js = resp.json()
        text = js.get("text") or safe_extract(js, "data", "text")
        return {"text": text, "raw": js}

    # 2) 调用注册的 provider
    provider = (settings.provider_name or "").lower()
    if provider in _registry:
        return await _registry[provider](messages, model_hint)

    # 3) 兜底
    raise LLMServiceError("LLM 未配置：请设置 llm_service_url 或 provider_name 与 api_key")
