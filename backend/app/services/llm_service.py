from typing import Any, Dict, List
import httpx
from app.core.config import settings


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
        for _ in range(3):
            try:
                async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
                    payload = {
                        "input": input_text,
                        "history": history or [],
                        "output_format": "tlp",
                    }
                    resp = await client.post(
                        f"{settings.llm_service_url}/chat",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {settings.provider_api_key}" if settings.provider_api_key else ""
                        },
                    )
                    resp.raise_for_status()
                    js = resp.json()
                    return {
                        "text": js.get("text") or (js.get("data") or {}).get("text"),
                        "raw": js,
                    }
            except Exception as e:
                last_exc = e
        raise httpx.HTTPError(f"LLM service failed after retries: {last_exc}")

    # 其次支持直接调用 Google Gemini API（无需自建 llm_service）
    if settings.provider_name.lower() == "gemini" and settings.provider_api_key:
        endpoint = f"{settings.gemini_api_base}/models/{settings.llm_model_name}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": settings.provider_api_key,
        }
        # 你期望输出为台罗拼音：在提示中明确要求格式
        prompt = (
            "請將使用者輸入轉換成臺羅拼音（教典／TLPA），只輸出臺羅文字，不要解釋。\n"
            f"使用者輸入：{input_text}"
        )
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            js = resp.json()
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

    # 2) Google Gemini 直连（拼接 messages 为 prompt）
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


