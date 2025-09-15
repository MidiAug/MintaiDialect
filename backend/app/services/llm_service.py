from typing import Any, Dict, List
import time
import logging
import httpx
from app.core.config import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def chat_to_taibun(input_text: str, *, history: List[dict] | None = None) -> Dict[str, Any]:
    """
    调用外部 LLM 服务，输出台罗拼音（Taibun / TLPA）。

    约定：服务端支持 output_format=tlp，返回 JSON 包含 text（或 data.text）。
    """
    if not settings.llm_service_url:
        raise RuntimeError("LLM 服务未配置 (llm_service_url 为空)")

    # 优先使用外部自建 llm_service
    if settings.llm_service_url:
        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                start_ts = time.monotonic()
                async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
                    # 先尝试我们当前简单的 GET /chat?message= 接口
                    try:
                        logger.debug("[LLM] attempt=%d GET %s/chat msg_len=%d", attempt, settings.llm_service_url, len(input_text or ""))
                        resp = await client.get(
                            f"{settings.llm_service_url}/chat",
                            params={"message": input_text},
                            headers={
                                "Authorization": f"Bearer {settings.provider_api_key}" if settings.provider_api_key else ""
                            },
                        )
                        resp.raise_for_status()
                        js = resp.json()
                        dur = (time.monotonic() - start_ts) * 1000
                        logger.info("[LLM] GET status=%d time=%.1fms keys=%s", resp.status_code, dur, list(js.keys()))
                        return {"text": js.get("response") or js.get("text") or "", "raw": js}
                    except Exception:
                        # 回退到 JSON POST 协议
                        payload = {
                            "input": input_text,
                            "history": history or [],
                            "output_format": "tlp",
                        }
                        logger.debug("[LLM] attempt=%d POST %s/chat-messages", attempt, settings.llm_service_url)
                        resp = await client.post(
                            f"{settings.llm_service_url}/chat",
                            json=payload,
                            headers={
                                "Authorization": f"Bearer {settings.provider_api_key}" if settings.provider_api_key else ""
                            },
                        )
                        resp.raise_for_status()
                        js = resp.json()
                        dur = (time.monotonic() - start_ts) * 1000
                        logger.info("[LLM] POST status=%d time=%.1fms keys=%s", resp.status_code, dur, list(js.keys()))
                        return {
                            "text": js.get("text") or (js.get("data") or {}).get("text"),
                            "raw": js,
                        }
            except Exception as e:
                last_exc = e
                logger.warning("[LLM] attempt failed: %s", e)
        raise httpx.HTTPError(f"LLM service failed after retries: {last_exc}")

    # 云厂商：DeepSeek Chat Completions（按你的 curl 示例）
    if settings.provider_name.lower() == "deepseek" and settings.provider_api_key:
        endpoint = f"{settings.deepseek_api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.provider_api_key}",
        }
        system_prompt = "請將使用者輸入轉換成臺羅拼音（教典／TLPA），只輸出臺羅文字，不要解釋。"
        payload = {
            "model": settings.llm_model_name or "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            start_ts = time.monotonic()
            logger.debug("[LLM] DeepSeek POST %s", endpoint)
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            js = resp.json()
            dur = (time.monotonic() - start_ts) * 1000
            logger.info("[LLM] DeepSeek status=%d time=%.1fms", resp.status_code, dur)
            text = None
            try:
                text = js["choices"][0]["message"]["content"]
            except Exception:
                text = None
            return {"text": text or "", "raw": js}

    # 阿里云 DashScope（Qwen）OpenAI 兼容 Chat Completions
    if settings.provider_name.lower() in ("dashscope", "qwen", "aliyun") and settings.provider_api_key:
        dashscope_base = getattr(settings, "dashscope_api_base", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        endpoint = f"{dashscope_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.provider_api_key}",
        }
        system_prompt = "請將使用者輸入轉換成臺羅拼音（教典／TLPA），只輸出臺羅文字，不要解釋。"
        payload = {
            "model": settings.llm_model_name or "qwen-plus",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            start_ts = time.monotonic()
            logger.debug("[LLM] DashScope POST %s", endpoint)
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            js = resp.json()
            dur = (time.monotonic() - start_ts) * 1000
            logger.info("[LLM] DashScope status=%d time=%.1fms", resp.status_code, dur)
            text = None
            try:
                text = js["choices"][0]["message"]["content"]
            except Exception:
                text = None
            return {"text": text or "", "raw": js}

    # 其次支持直接调用 Google Gemini API（无需自建 llm_service）
    if settings.provider_name.lower() == "gemini" and settings.provider_api_key:
        # 按你提供的 curl 方式改写：
        # curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
        #   -H "x-goog-api-key: $GEMINI_API_KEY" -H 'Content-Type: application/json' -X POST -d '{"contents": [{"parts": [{"text": "..."}]}]}'
        endpoint = f"{settings.gemini_api_base}/models/{settings.llm_model_name}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.provider_api_key,
        }
        # 期望输出为台罗拼音：在提示中明确要求格式，仅输出台罗。
        prompt = (
            "請將使用者輸入轉換成臺羅拼音（教典／TLPA），只輸出臺羅文字，不要解釋。\n"
            f"使用者輸入：{input_text}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            start_ts = time.monotonic()
            logger.debug("[LLM] Gemini POST %s", endpoint)
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            js = resp.json()
            dur = (time.monotonic() - start_ts) * 1000
            logger.info("[LLM] Gemini status=%d time=%.1fms", resp.status_code, dur)
            # Gemini 的返回结构：candidates[0].content.parts[0].text
            text = None
            try:
                text = js["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                text = None
            return {"text": text or "", "raw": js}

    raise RuntimeError("LLM 未配置：请设置 llm_service_url 或 provider_name=gemini 与 provider_api_key")


async def chat_messages(messages: List[Dict[str, str]], *, model_hint: str | None = None) -> Dict[str, Any]:
    """
    通用聊天接口：接受 OpenAI 兼容的 messages 列表。
    优先调用自建 llm_service（/chat-messages），否则按 provider 调用：
    - provider_name=gemini: 转为 generateContent 的 prompt（拼接 messages 内容）
    - 未来可扩展 openai/azure 等
    返回：{"text": str, "raw": any}
    """
    # 1) 自建 llm_service 优先
    if settings.llm_service_url:
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            resp = await client.post(
                f"{settings.llm_service_url}/chat-messages",
                json={"messages": messages, "model": model_hint},
                headers={"Authorization": f"Bearer {settings.provider_api_key}" if settings.provider_api_key else ""},
            )
            resp.raise_for_status()
            js = resp.json()
            return {"text": js.get("text") or (js.get("data") or {}).get("text", ""), "raw": js}

    # 2) DeepSeek Chat Completions（直接转发 OpenAI 兼容的 messages）
    if settings.provider_name.lower() == "deepseek" and settings.provider_api_key:
        endpoint = f"{settings.deepseek_api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.provider_api_key}",
        }
        payload = {
            "model": model_hint or settings.llm_model_name or "deepseek-chat",
            "messages": messages,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            start_ts = time.monotonic()
            logger.debug("[LLM] DeepSeek chat.completions POST %s", endpoint)
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            js = resp.json()
            dur = (time.monotonic() - start_ts) * 1000
            logger.info("[LLM] DeepSeek status=%d time=%.1fms", resp.status_code, dur)
            try:
                text = js["choices"][0]["message"]["content"]
            except Exception:
                text = ""
            return {"text": text, "raw": js}

    # 2.5) 阿里云 DashScope（Qwen）OpenAI 兼容 Chat Completions
    if settings.provider_name.lower() in ("dashscope", "qwen", "aliyun") and settings.provider_api_key:
        # 创建官方 SDK 异步客户端（AsyncOpenAI）
        client = AsyncOpenAI(
            api_key=settings.provider_api_key,
            base_url=getattr(settings, "dashscope_api_base", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )

        start_ts = time.monotonic()
        logger.debug("[LLM] DashScope (SDK) chat.completions.create called")

        try:
            # 异步调用 chat completions（使用 AsyncOpenAI + await create）
            completion = await client.chat.completions.create(
                model=model_hint or settings.llm_model_name or "qwen-max",
                messages=messages,
                extra_body={"enable_thinking": False},  # 非流式必须加
            )
        except Exception as e:
            dur = (time.monotonic() - start_ts) * 1000
            logger.error("[LLM] DashScope 请求失败: %s (耗时 %.1fms)", e, dur)
            return {"text": "", "raw": str(e)}

        dur = (time.monotonic() - start_ts) * 1000
        logger.info("[LLM] DashScope 返回成功 time=%.1fms", dur)

        # 提取文本
        try:
            text = completion.choices[0].message.content
        except (KeyError, IndexError, TypeError):
            text = ""

        return {"text": text, "raw": completion.model_dump()}

    # 3) Google Gemini 直连（拼接 messages 为 prompt）
    if settings.provider_name.lower() == "gemini" and settings.provider_api_key:
        prompt = "\n".join([m.get("content", "") for m in messages])
        endpoint = f"{settings.gemini_api_base}/models/{model_hint or settings.llm_model_name}:generateContent"
        headers = {"Content-Type": "application/json", "X-goog-api-key": settings.provider_api_key}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            js = resp.json()
            try:
                text = js["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                text = ""
            return {"text": text, "raw": js}

    raise RuntimeError("LLM 未配置：请设置 llm_service_url 或 provider_name 与 api_key")


