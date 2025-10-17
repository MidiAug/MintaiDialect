from fastapi import APIRouter, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging, time, json, re
import asyncio
from pathlib import Path
import uuid
from datetime import datetime, timedelta

from ..models.schemas import BaseResponse, LanguageType, DigitalJiagengSubtitle, DigitalJiagengResponse, DigitalJiagengChatRequest
from app.core.config import settings
from app.core.exceptions import ValidationError, LLMServiceError, TTSServiceError, ASRServiceError
from app.services import asr_service, tts_service, llm_service
from app.services.audio_utils import get_duration_seconds, process_audio_file
from app.services.mock_service import mock_digital_jiageng
from app.services.subtitle_service import segment_text_to_subtitles

router = APIRouter(prefix="/api/digital-jiageng", tags=["数字嘉庚"])
logger = logging.getLogger(__name__)

# 对话历史缓存（生产环境建议使用Redis）
conversation_history: Dict[str, List[Dict[str, str]]] = {}
session_metadata: Dict[str, Dict[str, any]] = {}  # 存储会话元数据

# JSON文件存储路径
CONVERSATIONS_DIR = Path("conversations")
CONVERSATIONS_DIR.mkdir(exist_ok=True)

# 预加载数据文件,避免每次请求读盘
try:
    _JIAGENG_STORIES = Path(settings.jiageng_stories_path).read_text(encoding="utf-8")
except Exception:
    _JIAGENG_STORIES = ""

try:
    _MINNAN_LEXICON = json.loads(Path(settings.minnan_lexicon_path).read_text(encoding="utf-8"))
except Exception:
    _MINNAN_LEXICON = {}

try:
    _MINNAN_EXAMPLES = json.loads(Path(settings.minnan_examples_path).read_text(encoding="utf-8"))
except Exception:
    _MINNAN_EXAMPLES = []

# ================== 工具函数 ==================

def _generate_session_id() -> str:
    """生成新的会话ID"""
    return str(uuid.uuid4())

def _get_or_create_session(session_id: Optional[str]) -> str:
    """获取或创建会话ID"""
    if not session_id:
        session_id = _generate_session_id()
        conversation_history[session_id] = []
        session_metadata[session_id] = {
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0
        }
        # 保存到文件
        _save_conversation_to_file(session_id, [])
        _save_session_metadata_to_file(session_id, session_metadata[session_id])
    else:
        # 更新最后活动时间
        if session_id in session_metadata:
            session_metadata[session_id]["last_activity"] = datetime.now()
        else:
            # 如果会话ID不存在，尝试从文件加载
            loaded_history = _load_conversation_from_file(session_id)
            loaded_metadata = _load_session_metadata_from_file(session_id)
            
            if loaded_history or loaded_metadata:
                # 从文件恢复会话
                conversation_history[session_id] = loaded_history
                session_metadata[session_id] = loaded_metadata
                session_metadata[session_id]["last_activity"] = datetime.now()
                logger.info(f"[DJ] 从文件恢复会话: {session_id}")
            else:
                # 创建新会话
                conversation_history[session_id] = []
                session_metadata[session_id] = {
                    "created_at": datetime.now(),
                    "last_activity": datetime.now(),
                    "message_count": 0
                }
                _save_conversation_to_file(session_id, [])
                _save_session_metadata_to_file(session_id, session_metadata[session_id])
    return session_id

def _add_to_conversation_history(session_id: str, user_input: str, ai_response: str):
    """添加对话到历史记录"""
    if session_id not in conversation_history:
        conversation_history[session_id] = []
    
    conversation_history[session_id].append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    conversation_history[session_id].append({
        "role": "assistant", 
        "content": ai_response,
        "timestamp": datetime.now().isoformat()
    })
    
    # 更新会话元数据
    if session_id in session_metadata:
        session_metadata[session_id]["message_count"] += 1
        session_metadata[session_id]["last_activity"] = datetime.now()
    
    # 保存到文件
    _save_conversation_to_file(session_id, conversation_history[session_id])
    _save_session_metadata_to_file(session_id, session_metadata[session_id])

def _load_conversation_from_file(session_id: str) -> List[Dict[str, str]]:
    """从JSON文件加载会话历史"""
    file_path = CONVERSATIONS_DIR / f"{session_id}.json"
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[DJ] 加载会话文件失败 {session_id}: {e}")
    return []

def _save_conversation_to_file(session_id: str, history: List[Dict[str, str]]):
    """保存会话历史到JSON文件"""
    file_path = CONVERSATIONS_DIR / f"{session_id}.json"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[DJ] 保存会话文件失败 {session_id}: {e}")

def _load_session_metadata_from_file(session_id: str) -> Dict[str, any]:
    """从JSON文件加载会话元数据"""
    file_path = CONVERSATIONS_DIR / f"{session_id}_metadata.json"
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 转换时间字符串回datetime对象
                if 'created_at' in data and isinstance(data['created_at'], str):
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                if 'last_activity' in data and isinstance(data['last_activity'], str):
                    data['last_activity'] = datetime.fromisoformat(data['last_activity'])
                return data
        except Exception as e:
            logger.error(f"[DJ] 加载会话元数据失败 {session_id}: {e}")
    return {}

def _save_session_metadata_to_file(session_id: str, metadata: Dict[str, any]):
    """保存会话元数据到JSON文件"""
    file_path = CONVERSATIONS_DIR / f"{session_id}_metadata.json"
    try:
        # 转换datetime对象为字符串
        data = metadata.copy()
        if 'created_at' in data and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        if 'last_activity' in data and isinstance(data['last_activity'], datetime):
            data['last_activity'] = data['last_activity'].isoformat()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[DJ] 保存会话元数据失败 {session_id}: {e}")

def _cleanup_old_sessions():
    """清理超过24小时的旧会话"""
    cutoff_time = datetime.now() - timedelta(hours=24)
    sessions_to_remove = []
    
    for session_id, metadata in session_metadata.items():
        if metadata["last_activity"] < cutoff_time:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        conversation_history.pop(session_id, None)
        session_metadata.pop(session_id, None)
        # 删除对应的JSON文件
        try:
            (CONVERSATIONS_DIR / f"{session_id}.json").unlink(missing_ok=True)
            (CONVERSATIONS_DIR / f"{session_id}_metadata.json").unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"[DJ] 删除会话文件失败 {session_id}: {e}")
        logger.info(f"[DJ] 清理过期会话: {session_id}")

async def _mock_digital_jiageng_response(session_id: str, show_subtitles: bool) -> DigitalJiagengResponse:
    """临时模拟 LLM 与 TTS，返回固定文本与固定音频路径，并按原逻辑生成字幕。"""
    start_time = time.time()

    # 模拟 LLM（~1.2s）
    await asyncio.sleep(1.2)
    fixed_text = "记得，你问我为什么创办厦门大学"

    # 模拟 TTS（总耗时 ~3s 内）
    await asyncio.sleep(max(0.0, 3 - (time.time() - start_time)))
    audio_url = "/uploads/audio/4.wav"

    # 计算真实音频时长（若可用）
    audio_duration: float | None = None
    try:
        from pathlib import Path as _P
        wav_path = _P(settings.upload_dir) / "audio" / "4.wav"
        if wav_path.exists():
            wav_bytes = wav_path.read_bytes()
            audio_duration = get_duration_seconds("4.wav", wav_bytes) or None
    except Exception:
        audio_duration = None

    # 字幕（与原逻辑一致）
    subs: List[DigitalJiagengSubtitle] = []
    base_text = (fixed_text or "").strip()
    if show_subtitles and base_text:
        est_total = (len(base_text) or 1) * 0.08
        total_dur = audio_duration if (audio_duration and audio_duration > 0) else est_total
        punct = set("，,。.!！?？、；;：:（）()【】[]\"'…—-")
        segments: List[tuple[str,int]] = []
        buf_display: List[str] = []
        timed_len = 0
        for ch in base_text:
            timed_len += 1
            if not ch.isspace() and ch not in punct:
                buf_display.append(ch)
            if ch.isspace() or ch in punct:
                disp = ''.join(buf_display).strip()
                if disp or timed_len > 0:
                    segments.append((disp, timed_len))
                buf_display = []
                timed_len = 0
        if buf_display or timed_len > 0:
            disp = ''.join(buf_display).strip()
            segments.append((disp, timed_len))

        total_units = sum(max(1, tl) for (_, tl) in segments) or 1
        t = 0.0
        for disp, tl in segments:
            dur = total_dur * (max(1, tl) / total_units)
            start = t
            end = t + dur
            text_out = disp
            if text_out:
                subs.append(DigitalJiagengSubtitle(text=text_out, start_time=round(start, 3), end_time=round(end, 3)))
            t = end

    _add_to_conversation_history(session_id, "", base_text)

    return DigitalJiagengResponse(
        session_id=session_id,
        response_audio_url=audio_url,
        subtitles=subs,
    )

async def _run_asr(file: UploadFile, contents: bytes, lang: str) -> str:
    logger.debug("[ASR] 调用服务: %s", settings.asr_service_url)
    try:
        asr_res = await asr_service.transcribe(file.filename or "recording.wav", contents, source_language=lang)
        return asr_res.get("text", "")
    except Exception as e:
        logger.exception(f"[ASR] 服务调用失败: {str(e)}")
        raise ASRServiceError(f"ASR 服务调用失败: {str(e)}")

def _normalize_jsonish(raw: str) -> str:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.replace("“", '"').replace("”", '"').replace("：", ":")
    cleaned = re.sub(r"'([A-Za-z_]+)'\s*:\s*", r'"\1": ', cleaned)  # 键名
    cleaned = re.sub(r":\s*'([^']*)'", r': "\1"', cleaned)          # 值
    return re.sub(r",\s*([}\]])", r"\1", cleaned)

def _parse_llm(raw: str) -> tuple[str, str]:
    """返回 (zh_text, POJ_text)"""
    try:
        return _extract_from_json(raw)
    except Exception:
        pass
    try:
        return _extract_from_json(_normalize_jsonish(raw))
    except Exception:
        pass
    # 容错兜底
    return _regex_extract(raw)

def _extract_from_json(raw: str) -> tuple[str, str]:
    data = json.loads(raw)
    if isinstance(data, dict):
        return str(data.get("zh", "")), str(data.get("POJ", ""))
    raise ValueError

def _regex_extract(raw: str) -> tuple[str, str]:
    zh = re.search(r'"zh"\s*:\s*"([^"]+)"', raw)
    poj = re.search(r'"POJ"\s*:\s*"([^"]+)"', raw)
    return zh.group(1) if zh else "", poj.group(1) if poj else ""

# ================== 路由 ==================

@router.post(
    "/chat",
    response_model=BaseResponse,
    summary="与数字嘉庚对话",
    description="上传音频文件与数字嘉庚进行语音对话，支持多种方言输入输出，可选择是否返回字幕。",
    responses={
        200: {
            "description": "对话成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "数字嘉庚对话完成",
                        "data": {
                            "response_audio_url": "/uploads/jiageng_1700000000000_ab12cd.wav",
                            "subtitles": [
                                {
                                    "text": "您好，我是嘉庚。",
                                    "start_time": 0.0,
                                    "end_time": 2.5
                                }
                            ]
                        }
                    }
                }
            }
        },
        400: {"description": "音频文件格式不支持或文件过大"},
        502: {"description": "ASR/LLM/TTS 服务异常"}
    },
)
async def chat_with_jiageng(
    request: Request,
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    input_language: LanguageType = Form(LanguageType.MINNAN),
    output_language: LanguageType = Form(LanguageType.MINNAN),
    speaking_speed: float = Form(1.0),
    show_subtitles: bool = Form(False),
):
    start_time = time.time()
    logger.info("[DJ] 收到 /chat 请求")

    # 0) 会话管理
    session_id = _get_or_create_session(session_id)
    logger.info("[DJ] 使用会话ID: %s", session_id)
    
    # 定期清理过期会话
    _cleanup_old_sessions()

    # ===== 临时模拟逻辑：封装调用 =====
    try:
        # 可参数化：固定文本、音频文件名、延时
        mock = await mock_digital_jiageng(
            fixed_text="记得，你问我为什么创办厦门大学",
            audio_filename="4.wav",
            text_delay_seconds=1.2,
            total_latency_seconds=3.0,
        )

        subs: List[DigitalJiagengSubtitle] = []
        base_text = (mock.text or "").strip()
        if show_subtitles and base_text:
            est_total = (len(base_text) or 1) * 0.08
            total_dur = mock.audio_duration if (mock.audio_duration and mock.audio_duration > 0) else est_total
            # 先用纯字典结构切分，再映射到 Pydantic 模型，保持与原返回一致
            sliced = segment_text_to_subtitles(base_text, total_dur)
            subs = [DigitalJiagengSubtitle(**s) for s in sliced]

        # 保存历史
        _add_to_conversation_history(session_id, "", base_text)

        return BaseResponse(
            message="数字嘉庚对话完成",
            data=DigitalJiagengResponse(
                session_id=session_id,
                response_audio_url=mock.audio_url,
                subtitles=subs,
            )
        )
    except Exception as e:
        logger.exception("[DJ] 临时模拟逻辑异常: %s", str(e))
        # 若模拟失败，继续执行原有逻辑作为兜底

    # 1) 输入处理（仅音频文件）
    contents = await audio_file.read()
    
    # 统一的音频处理：格式校验、大小校验和格式转换
    processed_audio_bytes, processed_filename = process_audio_file(audio_file, contents)
    
    # 创建处理后的文件对象用于ASR
    class ProcessedFile:
        def __init__(self, filename):
            self.filename = filename
    
    processed_file = ProcessedFile(processed_filename)
    user_input = await _run_asr(processed_file, processed_audio_bytes, input_language.value)
    logger.info("[DJ] ASR完成: %s", user_input[:50])

    # 2) 构建提示
    # LLM始终生成带中文的回答，show_subtitles只控制是否返回字幕
    format_hint_json = {
        "zh": "中文普通话回答（带有一点闽南语特色）",
        "POJ": "对应的POJ白话文注音（不含标点符号）"
    }
    format_hint = f"严格以 JSON 返回：{json.dumps(format_hint_json, ensure_ascii=False)}"

    # --- 使用预加载的数据 ---
    example_text = "\n".join(
        [f'示例{i+1}：\nzh：{e.get("zh","")}\nPOJ：{e.get("POJ","")}' for i, e in enumerate(_MINNAN_EXAMPLES)]
    )
    
    
    sys_prompt = (
        "你是陈嘉庚，回答问题要代入角色。\n"
        "下面陈嘉庚资料：\n"
        f"{_JIAGENG_STORIES}\n"
        "注意最大回复字数不要超过40字。\n"
        "如果用户输入的问题不像一个合理的问题，则回答："
        "“这个问题我不太明白，请重新提问。”\n"
        # "如果用户输入比较口语化或含有闽南语特色词汇，回答时也要使用特色闽南语表达方式。\n"
        # "下面是闽南语特色词汇：\n"
        # f"{_MINNAN_LEXICON}\n"
        f"{format_hint}\n"
        "POJ 中将原逗号替换为空格，原空格替换为 '-'，不要输出除 JSON 之外的内容。\n"
        "下面是参考示例：\n"
        f"{example_text}"
    )
    user_prompt = (
        f"用户问题：{user_input}"
    )
    
    # 3) 构建多轮对话消息
    messages = [{"role": "system", "content": sys_prompt}]
    
    # 添加历史对话（最多保留最近10轮对话）
    history = conversation_history.get(session_id, [])
    if history:
        # 只保留最近10轮对话（50条消息）
        recent_history = history[-50:] if len(history) > 50 else history
        messages.extend(recent_history)
        logger.info("[DJ] 添加历史对话: %d 条消息", len(recent_history))
    
    # 添加当前用户输入
    messages.append({"role": "user", "content": user_prompt})
    
    # 调用 LLM
    try:
        llm_out = await llm_service.chat_messages(messages)
        response_text = llm_out.get("text", "")
    except Exception as e:
        logger.exception("[DJ] LLM 调用失败: %s", str(e))
        raise LLMServiceError(f"LLM 服务调用失败: {str(e)}")

    zh_text, POJ_text = _parse_llm(response_text)
    if not POJ_text:
        raise LLMServiceError("生成台罗拼音失败,请重试")

    # 4) TTS
    audio_url = None
    audio_duration: float | None = None
    if settings.tts_service_url or settings.tts_cjg_service_url:
        try:
            # 数字嘉庚默认使用cjg模式，传入中文文本
            tts_res = await tts_service.synthesize(
                text=zh_text,  # 传入中文文本而不是POJ拼音
                target_language="cjg",  # 强制使用陈嘉庚TTS服务
                speaking_rate=speaking_speed,
            )
            if tts_res.get("binary"):
                uploads_dir = Path(settings.upload_dir)
                uploads_dir.mkdir(parents=True, exist_ok=True)
                out_path = uploads_dir / f"jiageng_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}.wav"
                out_path.write_bytes(tts_res["binary"])
                # 获取真实音频时长
                audio_duration = get_duration_seconds(out_path.name, tts_res["binary"]) or None
                try:
                    audio_url = str(request.url_for("uploads", path=out_path.name))
                except Exception:
                    audio_url = f"/uploads/{out_path.name}"
                logger.info("[DJ] TTS success: file=%s size=%d", out_path, len(tts_res["binary"]))
            else:
                raise TTSServiceError("TTS 服务未返回音频数据")
        except Exception as e:
            logger.exception("[DJ] TTS 生成失败 text_preview=%s: %s", zh_text[:50], str(e))
            raise TTSServiceError(f"TTS 服务调用失败: {str(e)}")
    else:
        raise TTSServiceError("未配置 TTS 服务")

    # 5) 生成后端字幕（仅在 show_subtitles 为 True 时处理）
    subs: List[DigitalJiagengSubtitle] = []
    base_text = (zh_text or "").strip()  # 字幕只使用中文内容
    if show_subtitles and base_text:
        # 真实总时长；若不可得则按经验估算 0.08s/字符（含标点与空格）
        est_total = (len(base_text) or 1) * 0.08
        total_dur = audio_duration if (audio_duration and audio_duration > 0) else est_total
        # 标点集合（显示时过滤）
        punct = set('，,。.!！?？、；;：:（）()【】[]""''"…—-')
        # 逐字符扫描,遇到空格或标点即结束当前句；句内计时长度包含标点与空格
        segments: List[tuple[str,int]] = []  # (display_text, timed_len)
        buf_display: List[str] = []
        timed_len = 0
        for ch in base_text:
            # 计时累加（标点与空格也计时）
            timed_len += 1
            # display 不包含标点与空白
            if not ch.isspace() and ch not in punct:
                buf_display.append(ch)
            # 分隔条件：空白或标点
            if ch.isspace() or ch in punct:
                disp = ''.join(buf_display).strip()
                if disp or timed_len > 0:
                    segments.append((disp, timed_len))
                buf_display = []
                timed_len = 0
        # 收尾
        if buf_display or timed_len > 0:
            disp = ''.join(buf_display).strip()
            segments.append((disp, timed_len))

        # 过滤全空句,但仍使用 timed_len 参与分配
        total_units = sum(max(1, tl) for (_, tl) in segments) or 1
        t = 0.0
        for disp, tl in segments:
            dur = total_dur * (max(1, tl) / total_units)
            start = t
            end = t + dur
            text_out = disp
            # 避免空显示占位：若句子全为标点/空白,则跳过显示但推进时间
            if text_out:
                subs.append(DigitalJiagengSubtitle(text=text_out, start_time=round(start, 3), end_time=round(end, 3)))
            t = end

    # 预览前两个字幕
    if show_subtitles and subs:
        preview = subs[:2]
        try:
            logger.info("[DJ] subtitles preview: %s", [(s.text, s.start_time, s.end_time) for s in preview])
        except Exception:
            pass

    # 添加对话到历史记录（保存模型完整输出，若缺失则回退到中文）
    ai_response_text = response_text or zh_text or ""
    if ai_response_text:
        _add_to_conversation_history(session_id, user_input, ai_response_text)

    return BaseResponse(
        data=DigitalJiagengResponse(
            session_id=session_id,
            response_audio_url=audio_url,
            subtitles=subs,
        )
    )


@router.get(
    "/sessions/{session_id}/history",
    summary="获取对话历史",
    description="获取指定会话的对话历史记录"
)
async def get_conversation_history(session_id: str):
    """获取指定会话的对话历史"""
    if session_id not in conversation_history:
        return BaseResponse(
            success=False,
            message="会话不存在",
            data=None
        )
    
    history = conversation_history.get(session_id, [])
    metadata = session_metadata.get(session_id, {})
    
    return BaseResponse(
        data={
            "session_id": session_id,
            "history": history,
            "metadata": metadata,
            "total_messages": len(history)
        }
    )

@router.delete(
    "/sessions/{session_id}",
    summary="删除会话",
    description="删除指定会话及其历史记录"
)
async def delete_conversation(session_id: str):
    """删除指定会话"""
    if session_id not in conversation_history:
        return BaseResponse(
            success=False,
            message="会话不存在",
            data=None
        )
    
    conversation_history.pop(session_id, None)
    session_metadata.pop(session_id, None)
    
    return BaseResponse(
        message=f"会话 {session_id} 已删除"
    )

@router.get(
    "/sessions",
    summary="获取所有会话列表",
    description="获取所有活跃会话的基本信息"
)
async def list_sessions():
    """获取所有会话列表"""
    sessions = []
    for session_id, metadata in session_metadata.items():
        history_count = len(conversation_history.get(session_id, []))
        sessions.append({
            "session_id": session_id,
            "created_at": metadata.get("created_at").isoformat() if metadata.get("created_at") else None,
            "last_activity": metadata.get("last_activity").isoformat() if metadata.get("last_activity") else None,
            "message_count": metadata.get("message_count", 0),
            "history_count": history_count
        })
    
    return BaseResponse(
        data={
            "sessions": sessions,
            "total_sessions": len(sessions)
        }
    )

@router.get(
    "/info",
    summary="数字嘉庚接口说明",
    description="返回数字嘉庚聊天接口的参数说明与示例,便于 Swagger 查看."
)
async def jiageng_info():
    return BaseResponse(
        data={
            "endpoint": "/api/digital-jiageng/chat",
            "method": "POST",
            "form_fields": {
                "audio_file": "必填,音频文件",
                "session_id": "可选,会话ID用于多轮对话",
                "input_language": "minnan | hakka | taiwanese | mandarin",
                "output_language": "minnan | hakka | taiwanese | mandarin",
                "speaking_speed": 1.0,
                "show_subtitles": True
            },
            "session_management": {
                "get_history": "/api/digital-jiageng/sessions/{session_id}/history",
                "delete_session": "/api/digital-jiageng/sessions/{session_id}",
                "list_sessions": "/api/digital-jiageng/sessions"
            }
        }
    )
