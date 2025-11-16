"""
数字嘉庚业务服务
职责：
- 预加载陈嘉庚相关语料
- 负责 LLM 提示词构建与响应解析
- 编排 ASR → LLM → TTS 完整业务流程
"""
from typing import Tuple, List, Dict, Optional, Any
import logging
from pathlib import Path
import time
import json
import re
import uuid

from app.core.config import settings
from app.models.schemas import DigitalJiagengSubtitle, LanguageType
from app.services import asr_service, llm_service, tts_service, mock_service
from app.services import conversation_service
from app.services.subtitle_service import segment_text_to_subtitles
from app.services.audio_utils import get_duration_seconds, process_audio_file
from app.core.exceptions import LLMServiceError, TTSServiceError, ASRServiceError

logger = logging.getLogger(__name__)

# 预加载数据
_jiageng_stories = ""
_minnan_examples: List[Dict[str, Any]] = []
_minnan_lexicon: Dict[str, Any] = {}


def _load_jiageng_data() -> None:
    """预加载陈嘉庚相关数据（避免每次请求读盘）"""
    global _jiageng_stories, _minnan_examples, _minnan_lexicon

    # 只加载一次
    if _jiageng_stories or _minnan_lexicon:
        return

    try:
        _jiageng_stories = Path(settings.jiageng_stories_path).read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"[JGS] 加载陈嘉庚故事失败: {e}")
        _jiageng_stories = ""

    try:
        _minnan_lexicon = json.loads(Path(settings.minnan_lexicon_path).read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[JGS] 加载闽南语词典失败: {e}")
        _minnan_lexicon = {}

    try:
        _examples_raw = json.loads(Path(settings.minnan_examples_path).read_text(encoding="utf-8"))
        if isinstance(_examples_raw, list):
            _minnan_examples = _examples_raw
        else:
            _minnan_examples = []
    except Exception as e:
        logger.warning(f"[JGS] 加载闽南语示例失败: {e}")
        _minnan_examples = []


# 初始化时加载数据
_load_jiageng_data()


def build_jiageng_prompt() -> str:
    """
    构建数字嘉庚的 LLM 提示词

    Returns:
        完整的系统提示词
    """
    # 构建格式提示
    format_hint_json = {
        "zh": "中文普通话回答（带有一点闽南语特色）",
        "POJ": "对应的POJ白话文注音（不含标点符号）",
    }
    format_hint = f"严格以 JSON 返回：{json.dumps(format_hint_json, ensure_ascii=False)}"

    # 构建示例文本
    example_text = "\n".join(
        [f'示例{i+1}：\nzh：{e.get("zh","")}\nPOJ：{e.get("POJ","")}' for i, e in enumerate(_minnan_examples)]
    )

    # 组装完整提示词
    sys_prompt = (
        "你是陈嘉庚，回答问题要代入角色。\n"
        "下面陈嘉庚资料：\n"
        f"{_jiageng_stories}\n"
        "注意最大回复字数不要超过40字。\n"
        "如果用户输入的问题不像一个合理的问题，则回答："
        "“这个问题我不太明白，请重新提问。”\n"
        f"{format_hint}\n"
        "POJ 中将原逗号替换为空格，原空格替换为 '-'，不要输出除 JSON 之外的内容。\n"
        "下面是参考示例：\n"
        f"{example_text}"
    )

    return sys_prompt


# ================== LLM 响应解析 ==================

def _normalize_jsonish(raw: str) -> str:
    """清理并规范化类似 JSON 的字符串，尽量纠正轻微格式错误。"""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.replace("“", '"').replace("”", '"').replace("：", ":")
    cleaned = re.sub(r"'([A-Za-z_]+)'\s*:\s*", r'"\1": ', cleaned)  # 键名
    cleaned = re.sub(r":\s*'([^']*)'", r': "\1"', cleaned)  # 值
    return re.sub(r",\s*([}\]])", r"\1", cleaned)


def _extract_from_json(raw: str) -> Tuple[str, str]:
    """从 JSON 字符串提取 zh 和 POJ 字段。"""
    data = json.loads(raw)
    if isinstance(data, dict):
        return str(data.get("zh", "")), str(data.get("POJ", ""))
    raise ValueError


def _regex_extract(raw: str) -> Tuple[str, str]:
    """使用正则表达式兜底提取 zh / POJ 字段。"""
    zh = re.search(r'"zh"\s*:\s*"([^"]+)"', raw)
    poj = re.search(r'"POJ"\s*:\s*"([^"]+)"', raw)
    return (zh.group(1) if zh else ""), (poj.group(1) if poj else "")


def parse_llm_response(raw: str) -> Tuple[str, str]:
    """
    解析 LLM 响应，返回 (zh_text, POJ_text)。
    优先走严格 JSON 解析，其次尝试“近似 JSON”修复，最后用正则兜底。
    """
    try:
        return _extract_from_json(raw)
    except Exception:
        pass
    try:
        return _extract_from_json(_normalize_jsonish(raw))
    except Exception:
        pass
    return _regex_extract(raw)


# ================== 内部：LLM / TTS 各自职责 ==================
# 说明：
# - _generate_jiageng_text：只关心“文本生成”这一件事，不碰音频
# - _synthesize_jiageng_audio：只关心“语音合成 + 字幕”这一件事，不关心 LLM 细节

async def _generate_jiageng_text(
    user_input: str,
    session_id: str,
    input_language: LanguageType,
) -> Dict[str, str]:
    """
    只负责：构建消息 → 调用 LLM → 解析 JSON → 返回文本结果。

    Returns:
        {
            "text": str,    # LLM 原始 JSON 文本
            "zh_text": str, # 中文回答
            "poj_text": str # POJ 注音
        }
    """
    # 1. 构建消息列表
    messages = [{"role": "system", "content": build_jiageng_prompt()}]

    # 添加历史对话（最多保留最近 10 轮对话）
    history = conversation_service.get_conversation_history(session_id)
    if history:
        recent_history = history[-20:] if len(history) > 20 else history
        messages.extend(recent_history)
        logger.info("[JGS] 添加历史对话: %d 条消息", len(recent_history))

    # 添加当前用户输入
    user_prompt = f"用户问题：{user_input}"
    messages.append({"role": "user", "content": user_prompt})

    # 2. 调用 LLM
    try:
        llm_out = await llm_service.chat_messages(messages)
        response_text = llm_out.get("text", "")
    except Exception as e:
        logger.exception("[JGS] LLM 调用失败: %s", e)
        raise LLMServiceError(f"LLM 服务调用失败: {str(e)}")

    # 3. 解析 LLM 响应
    zh_text, poj_text = parse_llm_response(response_text)
    if not zh_text:
        raise LLMServiceError("生成回复失败，请重试")

    logger.info("[JGS] LLM 生成成功: zh=%s...", zh_text[:30])

    return {
        "text": response_text,
        "zh_text": zh_text,
        "poj_text": poj_text,
    }


async def _synthesize_jiageng_audio(
    zh_text: str,
    speaking_speed: float,
    show_subtitles: bool,
) -> Dict[str, Any]:
    """
    只负责：调用 TTS 合成音频 + 按文本生成字幕。

    Returns:
        {
            "audio_url": str,
            "audio_duration": float | None,
            "subtitles": List[DigitalJiagengSubtitle]
        }
    """
    if not settings.tts_service_url and not settings.tts_cjg_service_url:
        raise TTSServiceError("未配置 TTS 服务")

    audio_url: Optional[str] = None
    audio_duration: Optional[float] = None

    try:
        # 数字嘉庚默认使用 cjg 模式，传入中文文本
        tts_res = await tts_service.synthesize(
            text=zh_text,
            target_language="cjg",
            speaking_rate=speaking_speed,
        )

        if not tts_res.get("binary"):
            raise TTSServiceError("TTS 服务未返回音频数据")

        uploads_dir = Path(settings.upload_dir)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        out_path = uploads_dir / f"jiageng_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.wav"
        out_path.write_bytes(tts_res["binary"])

        audio_duration = get_duration_seconds(out_path.name, tts_res["binary"])
        audio_url = f"/uploads/{out_path.name}"

        logger.info("[JGS] TTS 成功: file=%s, size=%d", out_path, len(tts_res["binary"]))
    except Exception as e:
        logger.exception("[JGS] TTS 生成失败 text_preview=%s: %s", zh_text[:50], e)
        raise TTSServiceError(f"TTS 服务调用失败: {str(e)}")

    # 生成字幕（仅在 show_subtitles 为 True 时处理）
    subtitles: List[DigitalJiagengSubtitle] = []
    if show_subtitles and zh_text:
        base_text = zh_text.strip()
        est_total = (len(base_text) or 1) * 0.08
        total_dur = audio_duration if (audio_duration and audio_duration > 0) else est_total

        sliced = segment_text_to_subtitles(base_text, total_dur)
        subtitles = [DigitalJiagengSubtitle(**s) for s in sliced]

        if subtitles:
            try:
                preview = subtitles[:2]
                logger.info(
                    "[JGS] subtitles preview: %s",
                    [(s.text, s.start_time, s.end_time) for s in preview],
                )
            except Exception:
                pass

    return {
        "audio_url": audio_url,
        "audio_duration": audio_duration,
        "subtitles": subtitles,
    }


# ================== 对外：从音频请求到完整结果 ==================

async def chat_with_audio(
    audio_filename: str,
    audio_bytes: bytes,
    session_id: str,
    input_language: LanguageType,
    speaking_speed: float,
    show_subtitles: bool,
) -> Dict[str, Any]:
    """
    从原始音频到最终数字嘉庚回复的完整流程：
    - 统一音频预处理
    - 调用 ASR 获得用户文本
    - 调用 LLM 得到回答文本
    - 调用 TTS 合成音频并生成字幕
    - 记录会话历史
    """
    # 1) 音频预处理（大小/格式校验及必要转换）
    processed_audio_bytes, processed_filename = process_audio_file_like(audio_filename, audio_bytes)

    # 2) ASR：音频 → 用户文本
    try:
        asr_res = await asr_service.transcribe(
            processed_filename or "recording.wav",
            processed_audio_bytes,
            source_language=input_language.value,
        )
        user_input = asr_res.get("text", "") or ""
        logger.info("[JGS] ASR 完成: %s", user_input[:50])
    except Exception as e:
        logger.exception("[JGS] ASR 服务调用失败: %s", e)
        raise ASRServiceError(f"ASR 服务调用失败: {str(e)}")

    # 3) LLM：根据用户文本生成嘉庚回答
    text_result = await _generate_jiageng_text(
        user_input=user_input,
        session_id=session_id,
        input_language=input_language,
    )

    # 4) TTS：把中文回答转换为音频 + 字幕
    tts_result = await _synthesize_jiageng_audio(
        zh_text=text_result["zh_text"],
        speaking_speed=speaking_speed,
        show_subtitles=show_subtitles,
    )

    # 5) 记录对话历史（只记录文本轮次）
    conversation_service.add_to_conversation_history(session_id, user_input, text_result.get("text", ""))

    # 6) 汇总结果
    return {
        "text": text_result.get("text", ""),
        "zh_text": text_result.get("zh_text", ""),
        "poj_text": text_result.get("poj_text", ""),
        "audio_url": tts_result.get("audio_url"),
        "audio_duration": tts_result.get("audio_duration"),
        "subtitles": tts_result.get("subtitles") or [],
    }


def process_audio_file_like(filename: str, contents: bytes) -> tuple[bytes, str]:
    """
    适配路由层传入的 (filename, bytes)，复用现有的 process_audio_file 逻辑。
    路由层不再关心音频格式/大小等业务细节。
    """
    class DummyUpload:
        def __init__(self, name: str):
            self.filename = name

    dummy = DummyUpload(filename or "recording.wav")
    processed_audio_bytes, processed_filename = process_audio_file(dummy, contents)
    return processed_audio_bytes, processed_filename


async def mock_chat(
    session_id: str,
    show_subtitles: bool,
) -> Dict[str, Any]:
    """
    使用固定文本 + 固定音频的“模拟数字嘉庚”流程。
    目前主要用于前端联调和体验验证。
    """
    fixed_text = "记得，你问我为什么创办厦门大学"

    mock = await mock_service.mock_digital_jiageng(
        fixed_text=fixed_text,
        audio_filename="4.wav",
        text_delay_seconds=1.2,
        total_latency_seconds=3.0,
    )

    base_text = (mock.text or "").strip()

    # 生成字幕
    subtitles: List[DigitalJiagengSubtitle] = []
    if show_subtitles and base_text:
        est_total = (len(base_text) or 1) * 0.08
        total_dur = mock.audio_duration if (mock.audio_duration and mock.audio_duration > 0) else est_total
        sliced = segment_text_to_subtitles(base_text, total_dur)
        subtitles = [DigitalJiagengSubtitle(**s) for s in sliced]

    # 保存对话历史
    conversation_service.add_to_conversation_history(session_id, "", base_text)

    return {
        "text": base_text,
        "zh_text": base_text,
        "poj_text": "",
        "audio_url": mock.audio_url,
        "audio_duration": mock.audio_duration,
        "subtitles": subtitles,
    }


