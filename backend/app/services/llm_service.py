from __future__ import annotations
from typing import Any, Dict, List, Callable, Awaitable, AsyncGenerator
import time
import logging
import httpx
import itertools
import os
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.exceptions import LLMServiceError

logger = logging.getLogger(__name__)

# ======================================================
# 工具函数
# ======================================================
def safe_extract(js: dict, *path, default: str = "") -> str:
    try:
        val = js
        for p in path:
            val = val[p]
        return val or default
    except Exception:
        return default


# 复用 httpx 客户端
_shared_client: httpx.AsyncClient | None = None

async def get_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(timeout=settings.model_request_timeout)
    return _shared_client


# ======================================================
# Provider 注册
# ======================================================
ProviderHandler = Callable[[List[Dict[str, str]], str | None], Awaitable[Dict[str, Any]]]
_registry: dict[str, ProviderHandler] = {}

def register_provider(name: str):
    def decorator(func: ProviderHandler):
        _registry[name.lower()] = func
        return func
    return decorator


# ======================================================
# Provider Key 管理
# ======================================================
def _parse_provider_keys(raw: str | None) -> List[str]:
    """解析 provider_api_key 字符串，支持逗号分隔多 Key"""
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


_PROVIDER_KEYS = _parse_provider_keys(settings.provider_api_key)
_PROVIDER_KEY_POOL = list(enumerate(_PROVIDER_KEYS, start=1))
_provider_key_cycle = itertools.cycle(_PROVIDER_KEY_POOL) if _PROVIDER_KEY_POOL else None


def _acquire_provider_key() -> tuple[int, str]:
    """
    轮询获取下一把 Provider Key。
    所有依赖云端/HTTP Provider 的调用都应统一走这里，以便多 Key 均匀使用。
    """
    if _provider_key_cycle is None:
        raise LLMServiceError("未配置 PROVIDER_API_KEY，请至少提供一把 Key")
    return next(_provider_key_cycle)


def _has_provider_key() -> bool:
    return bool(_PROVIDER_KEYS)


# ======================================================
# Gemini Provider
# ======================================================
@register_provider("gemini")
async def call_gemini(messages: List[Dict[str, str]], model_hint: str | None):
    model = model_hint or settings.llm_model_name or "gemini-2.5-flash"
    prompt = "\n".join([m.get("content", "") for m in messages])

    api_index, api_key = _acquire_provider_key()

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}},
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    client = await get_client()
    start = time.monotonic()

    try:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        dur = (time.monotonic() - start) * 1000
        body = e.response.text[:300] if e.response is not None else ""
        logger.error(
            "[Gemini] HTTP错误 (API#%s) status=%s url=%s body=%s (%.1fms)",
            api_index,
            e.response.status_code if e.response else "unknown",
            url,
            body,
            dur,
        )
        return {
            "text": "",
            "raw": {
                "error": str(e),
                "status": e.response.status_code if e.response else None,
                "body": body,
            },
        }
    except Exception as e:
        dur = (time.monotonic() - start) * 1000
        logger.exception(f"[Gemini] 调用失败 (API#{api_index}) ({dur:.1f}ms)")
        return {"text": "", "raw": str(e)}

    js = resp.json()
    text = safe_extract(js, "candidates", 0, "content", "parts", 0, "text", default="")

    dur = (time.monotonic() - start) * 1000
    logger.info(f"[Gemini] 成功 (API#{api_index}) {dur:.1f}ms text: {text[:50]}")

    return {"text": text, "raw": js}


# ======================================================
# Qwen Provider (DashScope 兼容模式)
# ======================================================
@register_provider("qwen")
async def call_qwen(messages: List[Dict[str, str]], model_hint: str | None):
    model = model_hint or settings.llm_model_name or "qwen-plus"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    url = f"{base_url}/chat/completions"

    api_index, api_key = _acquire_provider_key()

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    client = await get_client()
    start = time.monotonic()

    try:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        dur = (time.monotonic() - start) * 1000
        body = e.response.text[:300] if e.response is not None else ""
        logger.error(
            "[Qwen] HTTP错误 (API#%s) status=%s url=%s body=%s (%.1fms)",
            api_index,
            e.response.status_code if e.response else "unknown",
            url,
            body,
            dur,
        )
        return {
            "text": "",
            "raw": {
                "error": str(e),
                "status": e.response.status_code if e.response else None,
                "body": body,
            },
        }
    except Exception as e:
        dur = (time.monotonic() - start) * 1000
        logger.exception(f"[Qwen] 调用失败 (API#{api_index}) ({dur:.1f}ms)")
        return {"text": "", "raw": str(e)}

    js = resp.json()
    text = safe_extract(js, "choices", 0, "message", "content", default="")

    dur = (time.monotonic() - start) * 1000
    logger.info(f"[Qwen] 成功 (API#{api_index}) {dur:.1f}ms text: {text[:50]}")

    return {"text": text, "raw": js}


# ======================================================
# Qwen Provider 流式调用 (DashScope 兼容模式)
# ======================================================
async def call_qwen_stream(
    messages: List[Dict[str, str]], 
    model_hint: str | None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    流式调用 Qwen Provider (DashScope 兼容模式)
    
    Args:
        messages: 对话消息列表
        model_hint: 模型名称提示（可选）
    
    Yields:
        每个 chunk 的字典，包含：
        - "text": 增量文本内容
        - "raw": 原始 chunk 数据
        - "done": 是否完成（最后一个 chunk 为 True）
    """
    model = model_hint or settings.llm_model_name or "qwen-plus"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    api_index, api_key = _acquire_provider_key()
    
    # 创建 OpenAI 客户端（使用 DashScope 兼容模式）
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    start = time.monotonic()
    accumulated_text = ""
    
    try:
        # 发起流式请求
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True}
        )
        
        # 逐步返回每个 chunk
        async for chunk in completion:
            # 提取增量文本
            delta_text = ""
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    delta_text = delta.content
                    accumulated_text += delta_text
            
            # 转换为字典格式（兼容多种方式）
            try:
                if hasattr(chunk, 'model_dump'):
                    chunk_dict = chunk.model_dump()
                elif hasattr(chunk, 'dict'):
                    chunk_dict = chunk.dict()
                else:
                    # 手动构建字典
                    chunk_dict = {
                        "id": getattr(chunk, 'id', None),
                        "object": getattr(chunk, 'object', None),
                        "created": getattr(chunk, 'created', None),
                        "model": getattr(chunk, 'model', None),
                        "choices": [
                            {
                                "index": getattr(choice, 'index', None),
                                "delta": {
                                    "content": getattr(choice.delta, 'content', None) if hasattr(choice, 'delta') else None
                                } if hasattr(choice, 'delta') else {},
                                "finish_reason": getattr(choice, 'finish_reason', None)
                            }
                            for choice in (chunk.choices or [])
                        ]
                    }
            except Exception as e:
                logger.warning(f"[Qwen Stream] 转换 chunk 为字典失败: {e}")
                chunk_dict = {"error": f"转换失败: {str(e)}"}
            
            # 判断是否完成（检查 finish_reason）
            is_done = False
            if chunk.choices and len(chunk.choices) > 0:
                finish_reason = chunk.choices[0].finish_reason
                if finish_reason is not None:
                    is_done = True
            
            yield {
                "text": delta_text,
                "accumulated_text": accumulated_text,
                "raw": chunk_dict,
                "done": is_done
            }
        
        dur = (time.monotonic() - start) * 1000
        logger.info(f"[Qwen Stream] 成功 (API#{api_index}) {dur:.1f}ms 总长度: {len(accumulated_text)}")
        
    except Exception as e:
        dur = (time.monotonic() - start) * 1000
        logger.exception(f"[Qwen Stream] 调用失败 (API#{api_index}) ({dur:.1f}ms)")
        # 返回错误信息
        yield {
            "text": "",
            "accumulated_text": accumulated_text,
            "raw": {
                "error": str(e),
                "endpoint": base_url,
                "model": model,
            },
            "done": True
        }


# ======================================================
# 本地 LLM 调用
# ======================================================
async def _call_local_llm(messages: List[Dict[str, str]], model_hint: str | None) -> Dict[str, Any]:
    if not settings.llm_service_url:
        raise LLMServiceError("本地 LLM URL 未配置")

    client = await get_client()
    start = time.monotonic()

    # 判断本地 vLLM（9020端口）
    is_vllm = any(tag in settings.llm_service_url for tag in [
        "localhost:9020", "127.0.0.1:9020", ":9020"
    ])

    # 提取当前用户消息
    user_message = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            user_message = msg["content"]
            break
    if not user_message:
        raise LLMServiceError("未找到用户消息")

    # 构建上下文
    context = []
    for msg in messages[:-1]:
        r, c = msg["role"], msg["content"]
        prefix = "用户" if r == "user" else "助手"
        context.append(f"{prefix}: {c}")
    context_str = "\n".join(context)

    try:
        if is_vllm:
            # 本地 vLLM
            resp = await client.post(
                f"{settings.llm_service_url}/chat",
                json={
                    "message": user_message,
                    "context": context_str,
                    "max_length": 512,
                    "temperature": 0.7
                }
            )
        else:
            # 其他本地 LLM
            headers: Dict[str, str] = {}
            if _has_provider_key():
                _, bearer_key = _acquire_provider_key()
                headers["Authorization"] = f"Bearer {bearer_key}"

            resp = await client.post(
                f"{settings.llm_service_url}/chat-messages",
                json={"messages": messages, "model": model_hint},
                headers=headers
            )

        resp.raise_for_status()
    except Exception as e:
        logger.exception("[Local LLM] 调用失败")
        raise LLMServiceError(f"本地 LLM 调用失败: {e}")

    js = resp.json()
    text = js.get("response") or js.get("text") or safe_extract(js, "data", "text")

    return {"text": text, "raw": js}


# ======================================================
# 本地 LLM 流式调用（模拟流式）
# ======================================================
async def _call_local_llm_stream(
    messages: List[Dict[str, str]], 
    model_hint: str | None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    本地 LLM 流式调用（模拟流式）
    由于 vLLM 不支持真正的流式输出，这里采用定时分块返回的方式模拟流式
    """
    if not settings.llm_service_url:
        raise LLMServiceError("本地 LLM URL 未配置")
    
    # 先调用非流式接口获取完整响应
    try:
        full_result = await _call_local_llm(messages, model_hint)
        full_text = full_result.get("text", "")
    except Exception as e:
        logger.exception(f"[Local LLM Stream] 调用失败: {e}")
        yield {
            "text": "",
            "accumulated_text": "",
            "raw": {"error": str(e)},
            "done": True
        }
        return
    
    # 模拟流式：将完整文本分块返回
    # 按字符或按句子分割，每块延迟一小段时间
    import asyncio
    
    chunk_size = 3  # 每次返回 3 个字符（可根据需要调整）
    accumulated = ""
    
    for i in range(0, len(full_text), chunk_size):
        chunk = full_text[i:i + chunk_size]
        accumulated += chunk
        
        yield {
            "text": chunk,
            "accumulated_text": accumulated,
            "raw": {"chunk_index": i // chunk_size},
            "done": False
        }
        
        # 小延迟模拟流式效果（可根据需要调整）
        await asyncio.sleep(0.05)  # 50ms 延迟
    
    # 最后返回完成标记
    yield {
        "text": "",
        "accumulated_text": accumulated,
        "raw": {"done": True},
        "done": True
    }


# ======================================================
# Provider 流式注册表
# ======================================================
ProviderStreamHandler = Callable[[List[Dict[str, str]], str | None], AsyncGenerator[Dict[str, Any], None]]
_stream_registry: dict[str, ProviderStreamHandler] = {}


def register_provider_stream(name: str):
    """注册 Provider 流式处理器"""
    def decorator(func: ProviderStreamHandler):
        _stream_registry[name.lower()] = func
        return func
    return decorator


# 注册 Qwen 流式处理器
_stream_registry["qwen"] = call_qwen_stream


# ======================================================
# 🔥🔥 新增两个稳定入口（流式版本）
# ======================================================

async def chat_messages_local_stream(
    messages: List[Dict[str, str]], 
    *, 
    model_hint: str | None = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    永远走本地 LLM 流式，不看 provider 配置
    返回异步生成器，逐块返回文本
    """
    async for chunk in _call_local_llm_stream(messages, model_hint):
        yield chunk


async def chat_messages_api_stream(
    messages: List[Dict[str, str]], 
    *, 
    model_hint: str | None = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    永远走在线 Provider API 流式
    返回异步生成器，逐块返回文本
    """
    provider = (settings.provider_name or "").lower()
    
    if provider not in _stream_registry:
        # 如果 Provider 不支持流式，回退到非流式并模拟流式返回
        logger.warning(f"[LLM Stream] Provider '{provider}' 不支持流式，使用非流式接口并模拟流式返回")
        try:
            result = await chat_messages_api(messages, model_hint=model_hint)
            full_text = result.get("text", "")
            
            # 模拟流式返回
            import asyncio
            chunk_size = 3
            accumulated = ""
            
            for i in range(0, len(full_text), chunk_size):
                chunk = full_text[i:i + chunk_size]
                accumulated += chunk
                yield {
                    "text": chunk,
                    "accumulated_text": accumulated,
                    "raw": {"chunk_index": i // chunk_size},
                    "done": False
                }
                await asyncio.sleep(0.05)
            
            yield {
                "text": "",
                "accumulated_text": accumulated,
                "raw": {"done": True},
                "done": True
            }
        except Exception as e:
            logger.exception(f"[LLM Stream] 模拟流式失败: {e}")
            yield {
                "text": "",
                "accumulated_text": "",
                "raw": {"error": str(e)},
                "done": True
            }
        return
    
    # 使用注册的流式处理器
    handler = _stream_registry[provider]
    async for chunk in handler(messages, model_hint):
        yield chunk


async def chat_messages_stream(
    messages: List[Dict[str, str]], 
    *, 
    model_hint: str | None = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    智能选择 LLM 通道（流式版本）：
    - 若检测到本地 llm_service_url，优先走本地（低时延、可离线）
    - 否则回退到云端 Provider（依据 provider_name）
    
    返回异步生成器，逐块返回文本
    """
    if settings.llm_service_url:
        async for chunk in chat_messages_local_stream(messages, model_hint=model_hint):
            yield chunk
    else:
        async for chunk in chat_messages_api_stream(messages, model_hint=model_hint):
            yield chunk


# ======================================================
# 🔥🔥 新增两个稳定入口（非流式版本，保持不变）
# ======================================================

async def chat_messages_local(messages: List[Dict[str, str]], *, model_hint: str | None = None):
    """永远走本地 LLM，不看 provider 配置"""
    return await _call_local_llm(messages, model_hint)


async def chat_messages_api(messages: List[Dict[str, str]], *, model_hint: str | None = None):
    """永远走在线 Provider API"""
    provider = (settings.provider_name or "").lower()
    if provider not in _registry:
        raise LLMServiceError("未配置 provider_name 或该 provider 未注册")
    handler = _registry[provider]
    return await handler(messages, model_hint)


async def chat_messages(messages: List[Dict[str, str]], *, model_hint: str | None = None):
    """
    智能选择 LLM 通道：
    - 若检测到本地 llm_service_url，优先走本地（低时延、可离线）
    - 否则回退到云端 Provider（依据 provider_name）
    """
    if settings.llm_service_url:
        return await chat_messages_local(messages, model_hint=model_hint)
    return await chat_messages_api(messages, model_hint=model_hint)
