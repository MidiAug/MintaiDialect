from fastapi import APIRouter, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging, time, json, re
from pathlib import Path
import uuid

from ..models.schemas import BaseResponse, LanguageType, DigitalJiagengSubtitle, DigitalJiagengResponse, DigitalJiagengChatRequest
from app.core.config import settings
from app.core.exceptions import ValidationError, LLMServiceError, TTSServiceError, ASRServiceError
from app.services import asr_service, tts_service, llm_service
from app.services.audio_utils import get_duration_seconds

router = APIRouter(prefix="/api/digital-jiageng", tags=["数字嘉庚"])
logger = logging.getLogger(__name__)

# ================== 工具函数 ==================

def _validate_audio(file: UploadFile, contents: bytes):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise ValidationError("不支持的音频格式")
    
    # 限制音频文件大小为10MB
    max_size = settings.max_file_size
    if len(contents) > max_size:
        raise ValidationError(f"音频文件过大，请上传小于10MB的文件，当前文件大小为 {len(contents) / 1024 / 1024:.2f}MB")

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
    input_language: LanguageType = Form(LanguageType.MINNAN),
    output_language: LanguageType = Form(LanguageType.MINNAN),
    speaking_speed: float = Form(1.0),
    show_subtitles: bool = Form(False),
):
    start_time = time.time()
    logger.info("[DJ] 收到 /chat 请求")

    # 1) 输入处理（仅音频文件）
    contents = await audio_file.read()
    _validate_audio(audio_file, contents)
    user_input = await _run_asr(audio_file, contents, input_language.value)
    logger.info("[DJ] ASR完成: %s", user_input[:50])

    # 2) 构建提示
    if show_subtitles:
        format_hint_json = {
            "zh": "中文普通话回答（带有一点闽南语特色）",
            "POJ": "对应的POJ白话文注音（不含标点符号）"
        }
    else:
        format_hint_json = {
            "POJ": "对应的POJ白话文注音"
        }
    format_hint = f"严格以 JSON 返回：{json.dumps(format_hint_json, ensure_ascii=False)}"

    # --- 嘉庚故事、闽南语特色词汇、示例闽南语&POJ列表 ---
    jiageng_stories = Path(settings.jiageng_stories_path).read_text(encoding="utf-8")
    minnan_lexicon = json.loads(Path(settings.minnan_lexicon_path).read_text(encoding="utf-8"))
    minnan_examples = json.loads(Path(settings.minnan_examples_path).read_text(encoding="utf-8"))
    example_text = "\n".join(
        [f'示例{i+1}：\nzh：{e.get("zh","")}\nPOJ：{e.get("POJ","")}' for i, e in enumerate(minnan_examples)]
    )
    
    
    sys_prompt = (
        "你是陈嘉庚，回答问题要代入角色。\n"
        "下面陈嘉庚资料：\n"
        f"{jiageng_stories}\n"
        "注意最大回复字数不要超过100字。\n"
        "如果用户输入的问题不像一个合理的问题，则回答："
        "“这个问题我不太明白，请重新提问。”\n"
        "如果用户输入比较口语化或含有闽南语特色词汇，回答时也要使用特色闽南语表达方式。\n"
        "下面是闽南语特色词汇：\n"
        f"{minnan_lexicon}\n"
        f"{format_hint}\n"
        "POJ 中将原逗号替换为空格，原空格替换为 '-'，不要输出除 JSON 之外的内容。\n"
        "下面是参考示例：\n"
        f"{example_text}"
    )
    user_prompt = (
        f"用户问题：{user_input}"
    )
    
    # 3) 调用 LLM
    try:
        llm_out = await llm_service.chat_messages(
            [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]
        )
        response_text = llm_out.get("text", "")
    except Exception as e:
        logger.exception("[DJ] LLM 调用失败: %s", str(e))
        raise LLMServiceError(f"LLM 服务调用失败: {str(e)}")

    zh_text, POJ_text = _parse_llm(response_text)
    if not POJ_text:
        raise LLMServiceError("生成台罗拼音失败，请重试")

    # 4) TTS
    audio_url = None
    audio_duration: float | None = None
    if settings.tts_service_url:
        try:
            tts_res = await tts_service.synthesize(
                text=POJ_text,
                target_language=output_language.value,
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
            logger.exception("[DJ] TTS 生成失败 text_preview=%s: %s", POJ_text[:50], str(e))
            raise TTSServiceError(f"TTS 服务调用失败: {str(e)}")
    else:
        raise TTSServiceError("未配置 TTS 服务")

    # 5) 生成后端字幕（仅在 show_subtitles 为 True 时处理）
    subs: List[DigitalJiagengSubtitle] = []
    base_text = (zh_text or POJ_text or "").strip()
    if show_subtitles and base_text:
        # 真实总时长；若不可得则按经验估算 0.08s/字符（含标点与空格）
        est_total = (len(base_text) or 1) * 0.08
        total_dur = audio_duration if (audio_duration and audio_duration > 0) else est_total
        # 标点集合（显示时过滤）
        punct = set('，,。.!！?？、；;：:（）()【】[]“”‘’"…—-')
        # 逐字符扫描，遇到空格或标点即结束当前句；句内计时长度包含标点与空格
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

        # 过滤全空句，但仍使用 timed_len 参与分配
        total_units = sum(max(1, tl) for (_, tl) in segments) or 1
        t = 0.0
        for disp, tl in segments:
            dur = total_dur * (max(1, tl) / total_units)
            start = t
            end = t + dur
            text_out = disp
            # 避免空显示占位：若句子全为标点/空白，则跳过显示但推进时间
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

    return BaseResponse(
        data=DigitalJiagengResponse(
            response_audio_url=audio_url,
            subtitles=subs,
        )
    )


@router.get(
    "/info",
    summary="数字嘉庚接口说明",
    description="返回数字嘉庚聊天接口的参数说明与示例，便于 Swagger 查看。"
)
async def jiageng_info():
    return BaseResponse(
        data={
            "endpoint": "/api/digital-jiageng/chat",
            "method": "POST",
            "form_fields": {
                "audio_file": "必填，音频文件",
                "input_language": "minnan | hakka | taiwanese | mandarin",
                "output_language": "minnan | hakka | taiwanese | mandarin",
                "speaking_speed": 1.0,
                "show_subtitles": True
            }
        }
    )
