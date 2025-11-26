"""
数字嘉庚业务服务
职责：
- 预加载陈嘉庚相关语料
- 负责 LLM 提示词构建与响应解析
- 编排 ASR → LLM → TTS 完整业务流程
"""
from typing import Tuple, List, Dict, Optional, Any, Callable, AsyncGenerator
import logging
from pathlib import Path
import time
import json
import re
import uuid
import asyncio
from functools import lru_cache

from app.core.config import settings
from app.models.schemas import DigitalJiagengSubtitle, LanguageType
from app.services import asr_service, llm_service, tts_service, mock_service
from app.services import conversation_service
from app.services.subtitle_service import segment_text_to_subtitles
from app.services.audio_utils import get_duration_seconds, process_audio_file
from app.core.exceptions import LLMServiceError, TTSServiceError, ASRServiceError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_jiageng_data() -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    预加载陈嘉庚相关数据（避免每次请求读盘）
    使用 lru_cache 确保只加载一次，且线程安全
    
    Returns:
        Tuple[str, List[Dict], Dict]: (jiageng_stories, minnan_examples, minnan_lexicon)
    """
    jiageng_stories = ""
    minnan_examples: List[Dict[str, Any]] = []
    minnan_lexicon: Dict[str, Any] = {}

    try:
        jiageng_stories = Path(settings.jiageng_stories_path).read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"[JGS] 加载陈嘉庚故事失败: {e}")
        jiageng_stories = ""

    try:
        minnan_lexicon = json.loads(Path(settings.minnan_lexicon_path).read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[JGS] 加载闽南语词典失败: {e}")
        minnan_lexicon = {}

    try:
        _examples_raw = json.loads(Path(settings.minnan_examples_path).read_text(encoding="utf-8"))
        if isinstance(_examples_raw, list):
            minnan_examples = _examples_raw
        else:
            minnan_examples = []
    except Exception as e:
        logger.warning(f"[JGS] 加载闽南语示例失败: {e}")
        minnan_examples = []

    return jiageng_stories, minnan_examples, minnan_lexicon


# 预加载数据（初始化时调用一次）
_jiageng_stories, _minnan_examples, _minnan_lexicon = _load_jiageng_data()


def build_jiageng_poj_structured_prompt() -> str:
    """
    构建带有结构化要求的陈嘉庚提示词（保留旧模板，供特殊场景复用）

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


def _build_role_play_prompt(extra_instruction: Optional[str] = None) -> str:
    """
    构建通用的陈嘉庚角色提示词，并允许附加额外的格式要求。
    """
    stories = _jiageng_stories.strip() or "（暂无陈嘉庚资料，可用常识概述生平与贡献。）"
    base_instructions = [
        "你是陈嘉庚先生，所有回答必须使用第一人称，语气温和、真诚且充满家国情怀。",
        "回答时要结合陈嘉庚的真实经历、教育理念和嘉庚精神，必要时引用以下资料中的故事佐证观点。",
        "当用户提问与陈嘉庚无关时，也要保持角色身份，礼貌地把话题引导回“嘉庚精神、教育、家国情怀”等领域。",
        "回答需控制在 50 字以内，确保凝练有力；若内容不足以完整表达，可以先回应重点，再邀请用户继续追问。",
        "以下是陈嘉庚相关资料：",
        stories,
    ]
    if extra_instruction:
        base_instructions.append(extra_instruction)
    return "\n".join([item for item in base_instructions if item]).strip()


def build_jiageng_prompt_normal() -> Optional[str]:
    """
    返回常规提示词，包含嘉庚故事与角色扮演要求。
    """
    return _build_role_play_prompt()


def build_jiageng_pause_prompt() -> str:
    """
    构建带有句子停顿格式要求的提示词，指导模型在停顿间插入“｜”字符。
    """
    pause_instruction = (
        "请在回答前先规划好语句的自然停顿，输出时按照口语节奏切分，每个片段不要超过15个字。"
        "每个停顿片段之间使用“｜”字符连接，且不要出现英文竖线“｜”以外的额外分隔符。"
        "除了停顿要求之外，仍需保持陈嘉庚身份与叙事风格。"
        "示例1：'天气变冷啊｜主要是因为冷空气南下｜温度被迅速拉低｜你感受到的寒意｜就是这样来的'。"
        "示例2：'我今天很开心｜因为和朋友们一起出去玩｜玩得很开心｜还吃了好吃的｜心情特别愉快'。"
    )
    return _build_role_play_prompt(pause_instruction)


PromptBuilder = Callable[[], Optional[str]]
PROMPT_BUILDERS: Dict[str, PromptBuilder] = {
    "normal": build_jiageng_prompt_normal,
    "pause_format": build_jiageng_pause_prompt,
    "structured": build_jiageng_poj_structured_prompt,
}


# ================== 内部：LLM / TTS 各自职责 ==================
# 说明：
# - _generate_jiageng_text：只关心“文本生成”这一件事，不碰音频
# - _synthesize_jiageng_audio：只关心“语音合成 + 字幕”这一件事，不关心 LLM 细节

async def _generate_jiageng_text(
    user_input: str,
    session_id: str,
    input_language: LanguageType,
    prompt_style: str = "normal",
) -> Dict[str, str]:
    """
    只负责：构建消息 → 调用 LLM → 返回文本结果。

    Args:
        user_input: 用户原始文本
        session_id: 会话唯一 ID
        input_language: 用户输入语言
        prompt_style: 提示词构建风格（normal/pause_format/structured）

    Returns:
        {
            "text": str  # LLM 返回的文本内容
        }
    """
    # 1. 构建消息列表
    prompt_builder = PROMPT_BUILDERS.get(prompt_style, build_jiageng_prompt_normal)
    system_prompt = prompt_builder()
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    logger.info("[JGS] 使用提示词格式: %s", prompt_style)

    # 添加历史对话（最多保留最近 20 条消息）
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
        response_text = llm_out.get("text", "").strip()
    except Exception as e:
        logger.exception("[JGS] LLM 调用失败: %s", e)
        raise LLMServiceError(f"LLM 服务调用失败: {str(e)}")

    # 3. 验证响应
    if not response_text:
        raise LLMServiceError("生成回复失败，请重试")

    logger.info("[JGS] LLM 生成成功: text=%s...", response_text[:50])

    return {
        "text": response_text,
    }


async def _generate_jiageng_text_stream(
    user_input: str,
    session_id: str,
    input_language: LanguageType,
    prompt_style: str = "pause_format",
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    流式生成文本，每次检测到 "｜" 时 yield 一个片段。
    
    Args:
        user_input: 用户原始文本
        session_id: 会话唯一 ID
        input_language: 用户输入语言
        prompt_style: 提示词构建风格（normal/pause_format/structured）
    
    Yields:
        每个片段或完整文本的字典：
        - "segment": str - 文本片段（检测到 "｜" 时）
        - "text": str - 累积的完整文本
        - "is_complete": bool - 是否完成
    """
    # 1. 构建消息列表（与非流式版本相同）
    prompt_builder = PROMPT_BUILDERS.get(prompt_style, build_jiageng_prompt_normal)
    system_prompt = prompt_builder()
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    logger.info("[JGS-Stream] 使用提示词格式: %s", prompt_style)

    # 添加历史对话（最多保留最近 20 条消息）
    history = conversation_service.get_conversation_history(session_id)
    if history:
        recent_history = history[-20:] if len(history) > 20 else history
        messages.extend(recent_history)
        logger.info("[JGS-Stream] 添加历史对话: %d 条消息", len(recent_history))

    # 添加当前用户输入
    user_prompt = f"用户问题：{user_input}"
    messages.append({"role": "user", "content": user_prompt})

    # 2. 流式调用 LLM
    accumulated_text = ""
    pending_text = ""  # 待处理的文本（可能包含不完整的片段）
    
    try:
        async for chunk in llm_service.chat_messages_stream(messages):
            chunk_text = chunk.get("text", "")
            if not chunk_text:
                continue
            
            accumulated_text += chunk_text
            pending_text += chunk_text
            
            # 检测到 "｜" 分隔符时，提取已完成的片段
            if "｜" in pending_text:
                parts = pending_text.split("｜", 1)
                completed_segment = parts[0].strip()
                pending_text = parts[1] if len(parts) > 1 else ""
                
                if completed_segment:
                    logger.info("[JGS-Stream] 检测到片段: %s", completed_segment[:50])
                    yield {
                        "segment": completed_segment,
                        "text": accumulated_text,
                        "is_complete": False,
                    }
            
            # 检查是否完成
            if chunk.get("done", False):
                # 处理剩余的文本（最后一个片段，可能没有 "｜" 结尾）
                if pending_text.strip():
                    logger.info("[JGS-Stream] 最后片段: %s", pending_text.strip()[:50])
                    yield {
                        "segment": pending_text.strip(),
                        "text": accumulated_text,
                        "is_complete": False,
                    }
                
                # 返回完整文本
                logger.info("[JGS-Stream] LLM 生成完成: text=%s...", accumulated_text[:50])
                yield {
                    "segment": None,
                    "text": accumulated_text.strip(),
                    "is_complete": True,
                }
                break
                
    except Exception as e:
        logger.exception("[JGS-Stream] LLM 流式调用失败: %s", e)
        # 如果流式失败，尝试回退到非流式
        try:
            logger.warning("[JGS-Stream] 回退到非流式调用")
            result = await _generate_jiageng_text(
                user_input=user_input,
                session_id=session_id,
                input_language=input_language,
                prompt_style=prompt_style,
            )
            full_text = result.get("text", "")
            yield {
                "segment": None,
                "text": full_text,
                "is_complete": True,
            }
        except Exception as fallback_error:
            logger.exception("[JGS-Stream] 非流式回退也失败: %s", fallback_error)
            raise LLMServiceError(f"LLM 服务调用失败: {str(e)}")


async def _synthesize_segment_stream(
    text_segment: str,
    segment_index: int,
    speaking_speed: float,
    show_subtitles: bool,
) -> Dict[str, Any]:
    """
    单个片段的 TTS 合成（立即返回，不等待其他片段）。
    
    Args:
        text_segment: 文本片段
        segment_index: 片段索引（用于排序）
        speaking_speed: 语速
        show_subtitles: 是否生成字幕
    
    Returns:
        {
            "audio_url": str,
            "audio_duration": float | None,
            "subtitles": List[DigitalJiagengSubtitle],
            "segment_index": int
        }
    """
    if not settings.tts_service_url and not settings.tts_cjg_service_url:
        raise TTSServiceError("未配置 TTS 服务")
    
    if not text_segment.strip():
        return {
            "audio_url": None,
            "audio_duration": 0.0,
            "subtitles": [],
            "segment_index": segment_index,
        }
    
    audio_url: Optional[str] = None
    audio_duration: Optional[float] = None
    
    try:
        # 调用单个片段的 TTS
        tts_res = await tts_service.synthesize(
            text=text_segment,
            target_language="cjg",
            speaking_rate=speaking_speed,
        )
        
        if not tts_res.get("binary"):
            raise TTSServiceError("TTS 服务未返回音频数据")
        
        # 保存音频文件
        uploads_dir = Path(settings.upload_dir)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        out_path = uploads_dir / f"jiageng_seg_{segment_index}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.wav"
        
        # 使用 asyncio.to_thread 将阻塞式文件写入操作放入线程池
        await asyncio.to_thread(out_path.write_bytes, tts_res["binary"])
        
        audio_duration = get_duration_seconds(out_path.name, tts_res["binary"])
        audio_url = f"/uploads/{out_path.name}"
        
        logger.info("[JGS-Stream] 片段 %d TTS 成功: file=%s, size=%d, duration=%.2f", 
                   segment_index, out_path, len(tts_res["binary"]), audio_duration or 0.0)
    except Exception as e:
        logger.exception("[JGS-Stream] 片段 %d TTS 生成失败: %s", segment_index, e)
        raise TTSServiceError(f"TTS 服务调用失败: {str(e)}")
    
    # 生成字幕（仅在 show_subtitles 为 True 时处理）
    subtitles: List[DigitalJiagengSubtitle] = []
    if show_subtitles and text_segment:
        base_text = text_segment.strip()
        # 如果 audio_duration 为 None 或 <= 0，使用估算值
        if audio_duration is None or audio_duration <= 0:
            est_total = (len(base_text) or 1) * 0.08
            total_dur = est_total
            logger.warning(
                "[JGS-Stream] 片段 %d TTS 返回的音频时长为空或无效 (duration=%s)，使用估算值: %.2f 秒",
                segment_index, audio_duration, total_dur,
            )
        else:
            total_dur = audio_duration
        
        sliced = segment_text_to_subtitles(base_text, total_dur)
        subtitles = [DigitalJiagengSubtitle(**s) for s in sliced]
    
    return {
        "audio_url": audio_url,
        "audio_duration": audio_duration,
        "subtitles": subtitles,
        "segment_index": segment_index,
    }


async def _synthesize_jiageng_audio(
    text: str,
    speaking_speed: float,
    show_subtitles: bool,
    is_pause_format: bool = False,
) -> Dict[str, Any]:
    """
    只负责：调用 TTS 合成音频 + 按文本生成字幕。
    
    如果 is_pause_format 为 True 或文本包含 '｜' 分隔符，使用批处理接口并发请求，
    可以真正利用多 GPU/多 Worker 进行并行处理。

    Args:
        text: LLM 生成的文本内容（可能包含 '｜' 分隔符）
        speaking_speed: 语速
        show_subtitles: 是否生成字幕
        is_pause_format: 是否为 pause_format 模式（使用 '｜' 分隔符）

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
        # 检测是否使用 pause_format 模式（文本中包含 '｜' 分隔符）
        tts_start_time = None
        if is_pause_format or "｜" in text:
            
            # 按 '｜' 分割文本，过滤空片段
            logger.info("[JGS] 使用批处理 TTS 接口")
            tts_start_time = time.monotonic()
            # 使用批处理接口并发请求，真正利用多 GPU/多 Worker
            tts_res = await tts_service.synthesize_cjg_batch_client(
                text=text,
                speaker="cjg",
                speaking_rate=speaking_speed,
            )
        else:
            # 普通模式，使用正常接口
            logger.info("[JGS] 使用正常 TTS 接口（普通模式）")
            tts_res = await tts_service.synthesize(
                text=text,
                target_language="cjg",
                speaking_rate=speaking_speed,
            )

        if not tts_res.get("binary"):
            raise TTSServiceError("TTS 服务未返回音频数据")

        # 保存音频文件
        uploads_dir = Path(settings.upload_dir)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        out_path = uploads_dir / f"jiageng_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.wav"
        
        # 使用 asyncio.to_thread 将阻塞式文件写入操作放入线程池，避免阻塞事件循环
        await asyncio.to_thread(out_path.write_bytes, tts_res["binary"])

        audio_duration = get_duration_seconds(out_path.name, tts_res["binary"])
        audio_url = f"/uploads/{out_path.name}"

        # 如果使用了批处理接口，记录从开始批处理到 TTS 成功的总耗时
        if tts_start_time is not None:
            total_elapsed = (time.monotonic() - tts_start_time) * 1000
            logger.info("[JGS] TTS 成功: file=%s, size=%d, 总耗时: %.1fms", out_path, len(tts_res["binary"]), total_elapsed)
        else:
            logger.info("[JGS] TTS 成功: file=%s, size=%d", out_path, len(tts_res["binary"]))
    except Exception as e:
        logger.exception("[JGS] TTS 生成失败 text_preview=%s: %s", text[:50], e)
        raise TTSServiceError(f"TTS 服务调用失败: {str(e)}")

    # 生成字幕（仅在 show_subtitles 为 True 时处理）
    subtitles: List[DigitalJiagengSubtitle] = []
    if show_subtitles and text:
        base_text = text.strip()
        # 优化字幕切分逻辑：增加对 TTS 返回时长的空值校验
        # 如果 audio_duration 为 None 或 <= 0，使用估算值
        if audio_duration is None or audio_duration <= 0:
            est_total = (len(base_text) or 1) * 0.08
            total_dur = est_total
            logger.warning(
                "[JGS] TTS 返回的音频时长为空或无效 (duration=%s)，使用估算值: %.2f 秒",
                audio_duration,
                total_dur,
            )
        else:
            total_dur = audio_duration

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
    prompt_style: str = "pause_format",
) -> Dict[str, Any]:
    """
    从原始音频到最终数字嘉庚回复的完整流程：
    - 统一音频预处理
    - 调用 ASR 获得用户文本
    - 调用 LLM 得到回答文本
    - 调用 TTS 合成音频并生成字幕
    - 记录会话历史
    
    Args:
        audio_filename: 音频文件名
        audio_bytes: 音频文件内容
        session_id: 会话ID
        input_language: 输入语言
        speaking_speed: 语速
        show_subtitles: 是否显示字幕
        prompt_style: 提示词风格，默认为 "pause_format"（使用 '｜' 分隔符支持并发TTS处理）
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
    
    # user_input = "详细介绍一下你的生平"
    prompt_style = "pause_format"
    
    # 3) LLM：根据用户文本生成嘉庚回答
    text_result = await _generate_jiageng_text(
        user_input=user_input,
        session_id=session_id,
        input_language=input_language,
        prompt_style=prompt_style,
    )

    response_text = text_result.get("text", "")

    # 4) TTS：把回答转换为音频 + 字幕
    # 如果使用 pause_format，使用批处理接口并发请求以利用多 GPU/多 Worker
    is_pause_format = prompt_style == "pause_format"
    tts_result = await _synthesize_jiageng_audio(
        text=response_text,
        speaking_speed=speaking_speed,
        show_subtitles=show_subtitles,
        is_pause_format=is_pause_format,
    )

    # 5) 记录对话历史（只记录文本轮次）
    conversation_service.add_to_conversation_history(session_id, user_input, response_text)

    # 6) 汇总结果
    return {
        "text": response_text,
        "audio_url": tts_result.get("audio_url"),
        "audio_duration": tts_result.get("audio_duration"),
        "subtitles": tts_result.get("subtitles") or [],
    }


async def chat_with_audio_stream(
    audio_filename: str,
    audio_bytes: bytes,
    session_id: str,
    input_language: LanguageType,
    speaking_speed: float,
    show_subtitles: bool,
    prompt_style: str = "pause_format",
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    流式处理完整流程：
    1. 音频预处理
    2. ASR 识别用户输入
    3. 流式调用 LLM，检测到 "｜" 时立即触发 TTS
    4. 每次 yield 一个片段的结果
    5. 最后 yield 完整结果
    
    Args:
        audio_filename: 音频文件名
        audio_bytes: 音频文件内容
        session_id: 会话ID
        input_language: 输入语言
        speaking_speed: 语速
        show_subtitles: 是否显示字幕
        prompt_style: 提示词风格，默认为 "pause_format"
    
    Yields:
        每个片段的结果字典：
        - "type": "segment" | "complete"
        - "segment_index": int (仅 segment 类型)
        - "text": str - 片段文本或完整文本
        - "audio_url": str - 音频 URL
        - "audio_duration": float - 音频时长
        - "subtitles": List[DigitalJiagengSubtitle] - 字幕列表
        - "all_segments": List[Dict] (仅 complete 类型) - 所有片段信息
    """
    segment_results: List[Dict[str, Any]] = []
    full_text = ""
    history_saved = False
    
    try:
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
            logger.info("[JGS-Stream] ASR 完成: %s", user_input[:50])
        except Exception as e:
            logger.exception("[JGS-Stream] ASR 服务调用失败: %s", e)
            raise ASRServiceError(f"ASR 服务调用失败: {str(e)}")
        
        # 临时硬编码（用于测试）
        # user_input = "详细介绍一下你的生平"
        prompt_style = "pause_format"
        
        # 3) 流式 LLM：根据用户文本生成嘉庚回答
        segment_index = 0
        async for segment_data in _generate_jiageng_text_stream(
            user_input=user_input,
            session_id=session_id,
            input_language=input_language,
            prompt_style=prompt_style,
        ):
            segment_text = segment_data.get("segment")
            is_complete = segment_data.get("is_complete", False)
            
            # 更新完整文本
            if segment_data.get("text"):
                full_text = segment_data.get("text", "")
            
            # 如果检测到片段，立即触发 TTS
            if segment_text and not is_complete:
                try:
                    tts_result = await _synthesize_segment_stream(
                        text_segment=segment_text,
                        segment_index=segment_index,
                        speaking_speed=speaking_speed,
                        show_subtitles=show_subtitles,
                    )
                    
                    segment_result = {
                        "type": "segment",
                        "segment_index": segment_index,
                        "text": segment_text,
                        "audio_url": tts_result.get("audio_url"),
                        "audio_duration": tts_result.get("audio_duration"),
                        "subtitles": tts_result.get("subtitles") or [],
                    }
                    
                    segment_results.append(segment_result)
                    segment_index += 1
                    
                    # 立即 yield 片段结果
                    yield segment_result
                    
                except Exception as e:
                    logger.exception("[JGS-Stream] 片段 %d TTS 失败: %s", segment_index, e)
                    # 即使 TTS 失败，也继续处理后续片段
                    yield {
                        "type": "segment",
                        "segment_index": segment_index,
                        "text": segment_text,
                        "audio_url": None,
                        "audio_duration": 0.0,
                        "subtitles": [],
                        "error": str(e),
                    }
                    segment_index += 1
            
            # 如果完成，处理最后一个片段（可能没有 "｜" 结尾）
            if is_complete:
                logger.info("[JGS-Stream] LLM 流式完成，开始处理最后片段和完成消息")
                # 检查是否还有未处理的文本（最后一个片段）
                if full_text and segment_results:
                    # 检查最后一个片段是否覆盖了完整文本
                    last_segment_text = "".join([seg.get("text", "") for seg in segment_results])
                    remaining_text = full_text[len(last_segment_text):].strip()
                    
                    if remaining_text:
                        logger.info("[JGS-Stream] 发现剩余文本片段: %s", remaining_text[:50])
                        try:
                            tts_result = await _synthesize_segment_stream(
                                text_segment=remaining_text,
                                segment_index=segment_index,
                                speaking_speed=speaking_speed,
                                show_subtitles=show_subtitles,
                            )
                            
                            segment_result = {
                                "type": "segment",
                                "segment_index": segment_index,
                                "text": remaining_text,
                                "audio_url": tts_result.get("audio_url"),
                                "audio_duration": tts_result.get("audio_duration"),
                                "subtitles": tts_result.get("subtitles") or [],
                            }
                            
                            segment_results.append(segment_result)
                            yield segment_result
                            
                        except Exception as e:
                            logger.exception("[JGS-Stream] 最后片段 TTS 失败: %s", e)
                
                # 记录对话历史
                try:
                    conversation_service.add_to_conversation_history(session_id, user_input, full_text)
                    history_saved = True
                except Exception as conv_err:
                    logger.exception("[JGS-Stream] 会话历史保存失败: %s", conv_err)
                
                # 返回完整结果（确保一定会发送）
                complete_message = {
                    "type": "complete",
                    "text": full_text,
                    "all_segments": segment_results,
                }
                logger.info(
                    "[JGS-Stream] 发送完成消息: type=complete, text_len=%d, segments=%d",
                    len(full_text),
                    len(segment_results),
                )
                yield complete_message
                return
        
        # 补偿：若未收到完整标记但已有文本，仍需保存历史并返回 complete
        if not history_saved and full_text:
            logger.warning("[JGS-Stream] 未收到完整标记，使用补偿逻辑保存对话")
            try:
                conversation_service.add_to_conversation_history(session_id, user_input, full_text)
                history_saved = True
            except Exception as conv_err:
                logger.exception("[JGS-Stream] 补偿保存会话失败: %s", conv_err)
            
            fallback_complete = {
                "type": "complete",
                "text": full_text,
                "all_segments": segment_results,
            }
            yield fallback_complete
            return
    
    except Exception as e:
        logger.exception("[JGS-Stream] 流式处理失败: %s", e)
        # 失败时如果已生成文本也尝试保存
        if full_text and not history_saved:
            try:
                conversation_service.add_to_conversation_history(session_id, user_input, full_text)
            except Exception as conv_err:
                logger.exception("[JGS-Stream] 错误路径保存会话失败: %s", conv_err)
        # 返回错误信息
        yield {
            "type": "error",
            "error": str(e),
            "text": full_text,
            "all_segments": segment_results,
    }


# 将 DummyUpload 类移到函数外部，避免每次调用都重新定义类
class DummyUpload:
    """用于适配 process_audio_file 的虚拟文件对象"""
    def __init__(self, name: str):
        self.filename = name


def process_audio_file_like(filename: str, contents: bytes) -> tuple[bytes, str]:
    """
    适配路由层传入的 (filename, bytes)，复用现有的 process_audio_file 逻辑。
    路由层不再关心音频格式/大小等业务细节。
    """
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
        # 优化字幕切分逻辑：增加对音频时长的空值校验
        if mock.audio_duration is None or mock.audio_duration <= 0:
            est_total = (len(base_text) or 1) * 0.08
            total_dur = est_total
            logger.warning(
                "[JGS] Mock 音频时长为空或无效 (duration=%s)，使用估算值: %.2f 秒",
                mock.audio_duration,
                total_dur,
            )
        else:
            total_dur = mock.audio_duration
        sliced = segment_text_to_subtitles(base_text, total_dur)
        subtitles = [DigitalJiagengSubtitle(**s) for s in sliced]

    # 保存对话历史
    conversation_service.add_to_conversation_history(session_id, "", base_text)

    return {
        "text": base_text,
        "audio_url": mock.audio_url,
        "audio_duration": mock.audio_duration,
        "subtitles": subtitles,
    }


