from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import time
from datetime import datetime

from ..models.schemas import (
    BaseResponse, 
    LanguageType,
    AudioFormat
)
from app.core.config import settings
from app.services import asr_service, tts_service, llm_service
from pathlib import Path
import tempfile
import subprocess
import json
import re
import wave

router = APIRouter(prefix="/api/digital-jiageng", tags=["数字嘉庚"])
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ============ 请求/响应模型 ============

class JiagengSettings(BaseModel):
    enable_role_play: bool = True
    input_language: LanguageType = LanguageType.MINNAN
    output_language: LanguageType = LanguageType.MINNAN
    voice_gender: str = "male"  # male, female
    speaking_speed: float = 1.0

class JiagengChatRequest(BaseModel):
    text_input: Optional[str] = None
    settings: JiagengSettings

class JiagengChatResponse(BaseModel):
    response_text: str
    response_audio_url: Optional[str] = None
    emotion: str
    confidence: float
    processing_time: float
    subtitle_text: Optional[str] = None
    subtitles: Optional[List[Dict]] = None

class JiagengInfo(BaseModel):
    name: str
    birth_year: int
    death_year: int
    titles: list[str]
    achievements: list[str]
    famous_quotes: list[str]

# ============ 核心功能路由 ============

@router.post("/chat", response_model=BaseResponse)
async def chat_with_jiageng(
    audio_file: Optional[UploadFile] = File(None),
    text_input: Optional[str] = Form(None),
    enable_role_play: bool = Form(True),
    input_language: LanguageType = Form(LanguageType.MINNAN),
    output_language: LanguageType = Form(LanguageType.MINNAN),
    voice_gender: str = Form("male"),
    speaking_speed: float = Form(1.0),
    show_subtitles: bool = Form(True)
):
    """
    与数字嘉庚进行对话
    支持语音输入和文本输入
    """
    start_time = time.time()
    
    try:
        logger.info("[DJ] 收到 /chat 请求")
        logger.info(
            "[DJ] 入参: text_input=%s, has_audio=%s, show_subtitles=%s, enable_role_play=%s, input_language=%s, output_language=%s, voice_gender=%s, speaking_speed=%s",
            (text_input[:50] + '...') if text_input and len(text_input) > 50 else text_input,
            bool(audio_file is not None), show_subtitles,
            enable_role_play, input_language, output_language, voice_gender, speaking_speed,
        )

        # 参数验证
        if not audio_file and not text_input:
            raise HTTPException(
                status_code=400, 
                detail="必须提供音频文件或文本输入"
            )
        
        if audio_file:
            # 验证音频文件 MIME
            if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
                raise HTTPException(status_code=400, detail="不支持的音频格式")
        
        # 1) 处理输入：若有音频，先进行 ASR
        if audio_file:
            contents = await audio_file.read()
            logger.debug("[DJ] 上传音频: filename=%s, content_type=%s, size=%s bytes",
                         audio_file.filename, audio_file.content_type, len(contents))
            # 尺寸校验（基于内容长度）
            if len(contents) > settings.max_file_size:
                raise HTTPException(status_code=400, detail="音频文件过大，请上传小于50MB的文件")

            # 若为 webm/ogg/m4a/mp3/flac 等，尝试用 ffmpeg 转 WAV（16k/mono）
            input_ct = (audio_file.content_type or "").lower()
            needs_convert = any(
                ct in input_ct for ct in ["webm", "ogg", "m4a", "mp3", "flac"]
            )
            if needs_convert:
                # 无法安装系统 ffmpeg 时，直接跳过转码，依赖 ASR 管道自行处理
                logger.warning("[DJ] 检测到非WAV音频，但系统无ffmpeg可用，将直接使用原始字节流")
            if settings.asr_service_url:
                # 传入转码后的 WAV 字节
                logger.debug("[DJ] 调用ASR服务: url=%s", settings.asr_service_url)
                asr_res = await asr_service.transcribe(
                    audio_file.filename or "recording.wav",
                    contents,
                    source_language=input_language.value,
                )
                user_input = asr_res.get("text") or ""
                logger.info("[DJ] ASR完成: text=%s", (user_input[:120] + '...') if len(user_input) > 120 else user_input)
            else:
                user_input = ""
            logger.info(f"[DJ] 处理音频文件完成: {audio_file.filename}")
        else:
            user_input = text_input or ""
            logger.debug("[DJ] 使用文本输入: %s", (user_input[:120] + '...') if len(user_input) > 120 else user_input)
        
        # 2) 构建 messages（OpenAI 兼容），融合可选检索内容
        sys_prompt = "扮演陈嘉庚，根据提供的信息回答问题，要做到代入角色，不要回复与角色无关的内容。"
        retrieved = ""
        if settings.jiageng_retrieval_path:
            path = Path(settings.jiageng_retrieval_path)
            if path.exists():
                try:
                    retrieved = path.read_text(encoding="utf-8")
                except Exception:
                    retrieved = ""
        # 根据 show_subtitles 动态要求 LLM 输出
        # - 勾选字幕：同时需要中文与台罗 -> {"zh": "...", "POJ": "..."}
        # - 不勾选：仅返回台罗 -> {"POJ": "..."}
        if show_subtitles:
            format_hint = "严格以 JSON 返回：{\\\"zh\\\": \\\"中文普通话回答\\\", \\\"POJ\\\": \\\"对应的POJ白话文注音\\\"}。"
        else:
            format_hint = "严格以 JSON 返回：{\\\"POJ\\\": \\\"对应的POJ白话文注音\\\"}。不要包含 zh 字段。"
        prompt = (
            "你是陈嘉庚，请基于提供的资料进行角色化回答。"
            f"{format_hint}"
            "注意：POJ 中将原逗号替换为空格，将原空格替换为 '-'。不要输出除 JSON 之外的任何内容。\n"
            "示例输出文本和拼音对如下：\n"
            "zh：我深知国家要强，民族要振兴，根本在于教育。我连小时候贫，未受过稳定的教育，深谙一识之所需。后来侨居于南阳，经商有成，我便立志：处贫穷之处，有机会；利用此，有机会。我募远子孙，守祖，若愿万迁学，资助教育，赴革命运。我常说：教育不是营利的事业，要有牺牲精神。我希望透过教育，唤起民族觉醒，达成国民素质，使国家集强起来。\n"
            "POJ：Góa-chhim-chai-kok-ka-beh-kiông-siāng bîn-cho̍k-beh-chìn-heng kun-pún-chāi-ū-kau-io̍k Góa-liân-siàu-sî-ka-phîn bô-îⁿ-siū-ūn-téng-ê-kau-io̍k chhim-káng-chi̍t-sik-ê-só͘-iàu Āu-lâi-chhōe--tī-Lâm-iông-cheng-siong-ū-sêng góa-piān-lia̍p-chì: chô͘-būn-chhù--chū-ū-sē-hōe lī-iōng--chū-ū-sē-hōe Góa-bō-oán-chú-sun-siú-chô͘ nā-oán-bān-chhian-ha̍k-chú-īn-kau-io̍k-hō͘-kái-bēng-ūn Góa-chêng--seh: “kau-io̍k-bō-sī-îng-lī-ê-siā-gia̍p beh-ū-hi-seng-seng-sîn.” Góa-hi-bāng-tōng-kò͘-kau-io̍k-hoàⁿ-khí-bîn-cho̍k-kak-síng thit-sîng-kok-bîn-só͘-chì hō͘-kok-ka-chi̍n-chēng-kiông--lāi.\n"
            f"资料：{retrieved}\n"
            f"用户问题：{user_input}"
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ]
        logger.debug("[DJ] 调用LLM服务，messages条数=%d", len(messages))
        response_text = ""
        try:
            llm_out = await llm_service.chat_messages(messages, model_hint=None)
            response_text = llm_out.get("text") or ""
            logger.info("[DJ] LLM返回文本: %s", (response_text) )
        except Exception:
            logger.exception("[DJ] LLM 调用失败，使用降级回复")
            # 降级：如果无法连接LLM，给出保底文本，保持链路可用
            response_text = (user_input or "您好！我已收到您的消息，我们稍后给出更详细的回答。")
        zh_text = ""
        POJ_text = ""
        # 优先解析 JSON（未勾选字幕时不会把原始 JSON 作为中文落下）
        def _normalize_jsonish_str(s: str) -> str:
            if not s:
                return ""
            cleaned = s.strip()
            # 去掉代码围栏
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
            # 替换中文引号/冒号为英文
            cleaned = cleaned.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
            cleaned = cleaned.replace('：', ':')
            # 尝试把单引号键/值替换为双引号（仅在看起来像 JSON 的情况下）
            # 先处理键名 'zh': -> "zh":
            cleaned = re.sub(r"'([A-Za-z_]+)'\s*:\s*", r'"\1": ', cleaned)
            # 值用单引号的 'xxx' -> "xxx"
            cleaned = re.sub(r":\s*'([^'\\]*(?:\\.[^'\\]*)*)'", r': "\1"', cleaned)
            # 若出现 { \"zh\": \"...\" } 这类伪 JSON，将 \" 解为 "，并清理常见转义
            if re.search(r"\{\s*\\\"", cleaned):
                cleaned = cleaned.replace('\\"', '"')
                cleaned = cleaned.replace('\\n', ' ')
                cleaned = cleaned.replace('\\t', ' ')
            # 移除尾随逗号
            cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
            return cleaned

        def _extract_field(raw: str, key: str) -> str:
            if not raw:
                return ""
            # 1) 标准 JSON 键 "key": "..."
            m = re.search(rf'"{key}"\s*:\s*"((?:\\.|[^"\\])*)"', raw, flags=re.IGNORECASE | re.DOTALL)
            if m:
                val = m.group(1)
                try:
                    # 尝试用 JSON 再解码一次，处理 \uXXXX 等
                    return json.loads('"' + val + '"')
                except Exception:
                    return val.replace('\\n', ' ').replace('\\t', ' ').replace('\\"', '"').strip()
            # 2) 单引号 JSON 风格 'key': '...'
            m = re.search(rf"'{key}'\s*:\s*'((?:\\.|[^'\\])*)'", raw, flags=re.IGNORECASE | re.DOTALL)
            if m:
                val = m.group(1)
                try:
                    return json.loads('"' + val.replace('"', '\\"') + '"')
                except Exception:
                    return val.replace('\\n', ' ').replace('\\t', ' ').replace("\\'", "'").strip()
            # 3) 行内格式：key: 值 / key：值（直到换行或下一个键名出现）
            m = re.search(rf'(?:^|\n)\s*{key}\s*[:：]\s*(.+?)(?=\n\s*[A-Za-z_]+\s*[:：]|\n*$)', raw, flags=re.IGNORECASE | re.DOTALL)
            if m:
                val = m.group(1)
                val = val.strip().strip('"').strip("'")
                return val
            return ""

        def _parse_llm(raw_in) -> tuple[str, str]:
            # 统一为字符串
            raw: str
            if isinstance(raw_in, str):
                raw = raw_in
            else:
                try:
                    raw = json.dumps(raw_in, ensure_ascii=False)
                except Exception:
                    raw = str(raw_in)
            # 首次尝试：原文直接 JSON
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    zh_v = data.get('zh') or data.get('ZH') or data.get('Zh')
                    POJ_v = data.get('POJ') or data.get('POJ') or data.get('POJ')
                    return (str(zh_v or ''), str(POJ_v or ''))
            except Exception:
                pass
            # 二次：normalize 后再 JSON
            cleaned = _normalize_jsonish_str(raw)
            try:
                data2 = json.loads(cleaned)
                if isinstance(data2, dict):
                    zh_v = data2.get('zh') or data2.get('ZH') or data2.get('Zh')
                    POJ_v = data2.get('POJ') or data2.get('POJ') or data2.get('POJ')
                    return (str(zh_v or ''), str(POJ_v or ''))
            except Exception:
                pass
            # 三次：截取最外层 { ... } 再试
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1 and end > start:
                candidate = cleaned[start:end+1]
                try:
                    data3 = json.loads(candidate)
                    if isinstance(data3, dict):
                        zh_v = data3.get('zh') or data3.get('ZH') or data3.get('Zh')
                        POJ_v = data3.get('POJ') or data3.get('POJ') or data3.get('POJ')
                        return (str(zh_v or ''), str(POJ_v or ''))
                except Exception:
                    pass
            # 最后：用正则直接抽取字段（容错，避免整体失败）
            zh_guess = _extract_field(cleaned, 'zh') or _extract_field(raw, 'zh')
            POJ_guess = _extract_field(cleaned, 'POJ') or _extract_field(raw, 'POJ')
            # 极简兜底：若仍未取到，尝试非贪婪匹配双引号包裹的值
            if not POJ_guess:
                m_last = re.search(r'"POJ"\s*:\s*"(.*?)"', raw, flags=re.DOTALL)
                if m_last:
                    POJ_guess = m_last.group(1)
            return zh_guess, POJ_guess

        zh_text, POJ_text = _parse_llm(response_text)
        # # 保障 TTS 连贯性：统一将空白替换为 '-'，去重连续 '-'
        # if POJ_text:
        #     tmp = POJ_text
        #     tmp = tmp.replace('，', ' ').replace(',', ' ')
        #     tmp = re.sub(r"\s+", '-', tmp.strip())
        #     tmp = re.sub(r"-{2,}", '-', tmp)
        #     POJ_text = tmp
        # logger.debug("[DJ] 解析LLM输出: zh_len=%s POJ_len=%s", len(zh_text), len(POJ_text))

        # 简单情感设置（可后续接入情感模型）
        emotion = "睿智" if enable_role_play else "友好"
        
        # 若缺失台罗，直接抛错，让前端给出重试提示
        if not POJ_text:
            logger.error("[DJ] LLM 未返回台罗文本，无法进行TTS")
            raise HTTPException(status_code=502, detail="生成台罗拼音失败，请重试")

        # 3) TTS：仅使用台罗拼音（POJA/POJ）转语音
        response_audio_url = None
        backend_subtitles = []
        try:
            tts_res = None
            if settings.tts_service_url:
                logger.debug("[DJ] 调用TTS服务: url=%s, 台罗文本长度=%d", settings.tts_service_url, len(POJ_text))
                tts_res = await tts_service.synthesize(
                    text=POJ_text,
                    target_language=output_language.value,
                )
                # 若返回直接是音频二进制，则保存到 uploads 并返回 URL
                if tts_res and tts_res.get("binary"):
                    uploads_dir = Path(settings.upload_dir)
                    uploads_dir.mkdir(parents=True, exist_ok=True)
                    ts = int(time.time() * 1000)
                    out_path = uploads_dir / f"jiageng_reply_{ts}.wav"
                    with open(out_path, "wb") as f:
                        f.write(tts_res["binary"]) 
                    response_audio_url = f"/uploads/{out_path.name}"
                    logger.info("[DJ] TTS音频已保存: %s", out_path)
                    # 计算时长并生成后端字幕（仅当需要字幕且有中文）
                    audio_duration = _compute_wav_duration_seconds(out_path)
                    backend_subtitles = _build_subtitles_from_zh(zh_text, audio_duration) if show_subtitles and zh_text else []
                elif tts_res:
                    response_audio_url = tts_res.get("audio_url")
                    logger.info("[DJ] TTS返回音频URL: %s", response_audio_url)
                    backend_subtitles = []
        except Exception as _:
            logger.exception("[DJ] TTS 处理失败")
            response_audio_url = None
        
        processing_time = time.time() - start_time
        # 简单置信度占位
        confidence = 0.9
        
        # 将文本回答优先返回台罗（当前阶段用于 TTS），字幕文本单独返回
        combined_text = POJ_text or zh_text or response_text

        response_data = JiagengChatResponse(
            response_text=combined_text,
            response_audio_url=response_audio_url,
            emotion=emotion,
            confidence=confidence,
            processing_time=processing_time,
            subtitle_text=zh_text,
            subtitles=backend_subtitles if (show_subtitles and zh_text) else []
        )
        
        logger.info(f"[DJ] 嘉庚对话完成，处理时间: {processing_time:.2f}s, 有音频={bool(response_audio_url)}, show_subtitles={show_subtitles}")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="对话处理成功"
        )
        
    except HTTPException:
        logger.exception("[DJ] HTTPException")
        raise
    except Exception as e:
        logger.exception(f"[DJ] 嘉庚对话处理失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"对话处理失败: {str(e)}"
        )

@router.get("/info", response_model=BaseResponse)
async def get_jiageng_info():
    """获取陈嘉庚先生的基本信息"""
    try:
        info = JiagengInfo(
            name="陈嘉庚",
            birth_year=1874,
            death_year=1961,
            titles=[
                "华侨领袖",
                "著名实业家", 
                "教育家",
                "慈善家",
                "社会活动家"
            ],
            achievements=[
                "创办厦门大学",
                "创办集美学校",
                "南洋华侨抗日救国运动的领导者",
                "被誉为'华侨旗帜、民族光辉'",
                "倾资兴学，资助教育事业",
                "支持祖国抗战，贡献巨大"
            ],
            famous_quotes=[
                "诚毅二字乃人生立身处世之道",
                "教育为立国之本",
                "宁可变卖大厦，也要支持教育",
                "应该用自己的财富来培养人才",
                "华侨须有爱国之心，爱乡之情"
            ]
        )
        
        return BaseResponse(
            success=True,
            data=info,
            message="获取嘉庚信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取嘉庚信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取信息失败: {str(e)}"
        )

@router.get("/quotes")
async def get_jiageng_quotes():
    """获取陈嘉庚名言警句"""
    try:
        quotes = [
            {
                "quote": "诚毅二字乃人生立身处世之道",
                "context": "这是陈嘉庚的人生格言，也是集美学校的校训"
            },
            {
                "quote": "教育为立国之本",
                "context": "体现了陈嘉庚对教育事业重要性的深刻认识"
            },
            {
                "quote": "宁可变卖大厦，也要支持教育",
                "context": "展现了陈嘉庚倾资兴学的决心和魄力"
            },
            {
                "quote": "应该用自己的财富来培养人才",
                "context": "陈嘉庚财富观和人才观的体现"
            },
            {
                "quote": "华侨须有爱国之心，爱乡之情",
                "context": "陈嘉庚对华侨群体的期望和要求"
            }
        ]
        
        return BaseResponse(
            success=True,
            data={"quotes": quotes},
            message="获取名言成功"
        )
        
    except Exception as e:
        logger.error(f"获取名言失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取名言失败: {str(e)}"
        )

@router.get("/history")
async def get_conversation_history(limit: int = 50):
    """获取对话历史记录"""
    try:
        # TODO: 从数据库获取真实的对话历史
        # 当前返回模拟数据
        history = [
            {
                "id": "conv_001",
                "user_message": "嘉庚先生，您对教育有什么看法？",
                "jiageng_response": "教育是立国之本，兴学育人是我毕生的追求。",
                "timestamp": "2024-01-01T10:00:00Z",
                "emotion": "睿智"
            }
        ]
        
        return BaseResponse(
            success=True,
            data={"history": history, "total": len(history)},
            message="获取历史记录成功"
        )
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取历史记录失败: {str(e)}"
        )

# ============ 工具函数 ============

def validate_jiageng_settings(settings: JiagengSettings) -> bool:
    """验证嘉庚对话设置"""
    if settings.speaking_speed < 0.5 or settings.speaking_speed > 2.0:
        return False
    
    if settings.voice_gender not in ["male", "female"]:
        return False
    
    return True 

def _compute_wav_duration_seconds(path: Path) -> float:
    try:
        with open(path, 'rb') as f:
            riff = f.read(12)
            if len(riff) < 12 or riff[0:4] != b'RIFF' or riff[8:12] != b'WAVE':
                return 0.0
            fmt_found = False
            data_size = None
            sample_rate = None
            channels = None
            bits_per_sample = None
            # 迭代 chunk
            while True:
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                chunk_id = hdr[0:4]
                chunk_size = int.from_bytes(hdr[4:8], 'little', signed=False)
                if chunk_id == b'fmt ':
                    fmt = f.read(chunk_size)
                    if len(fmt) >= 16:
                        # wFormatTag(2) nChannels(2) nSamplesPerSec(4) nAvgBytesPerSec(4) nBlockAlign(2) wBitsPerSample(2)
                        wFormatTag = int.from_bytes(fmt[0:2], 'little')
                        channels = int.from_bytes(fmt[2:4], 'little')
                        sample_rate = int.from_bytes(fmt[4:8], 'little')
                        # avg = int.from_bytes(fmt[8:12], 'little')
                        # blockAlign = int.from_bytes(fmt[12:14], 'little')
                        bits_per_sample = int.from_bytes(fmt[14:16], 'little')
                        # 仅支持 PCM(1) 与 IEEE float(3)
                        if wFormatTag not in (1, 3):
                            logger.warning('[DJ] WAV 非PCM/Float格式: %s', wFormatTag)
                        fmt_found = True
                    else:
                        # 跳过异常 fmt
                        fmt_found = False
                elif chunk_id == b'data':
                    data_size = chunk_size
                    # 跳过读取数据
                    f.seek(chunk_size, 1)
                else:
                    # 跳过其他 chunk（fact/list 等）
                    f.seek(chunk_size, 1)
                # chunk 对齐到偶数字节
                if (chunk_size % 2) == 1:
                    f.seek(1, 1)
            if not fmt_found or data_size is None or not sample_rate or not channels or not bits_per_sample:
                return 0.0
            bytes_per_sample = max(1, bits_per_sample // 8)
            total_frames = data_size // (bytes_per_sample * channels)
            duration = total_frames / float(sample_rate)
            return float(duration)
    except Exception:
        logger.exception('[DJ] 读取 WAV 时长失败')
        return 0.0

def _build_subtitles_from_zh(zh_text: str, duration: float) -> List[Dict]:
    if not zh_text:
        return []
    text = (zh_text or '').strip()
    # 按标点切句
    parts: List[str] = []
    buf = ''
    punct = set('，,。.!！？?；、')
    for ch in text:
        buf += ch
        if ch in punct:
            seg = buf.strip()
            if seg:
                parts.append(seg)
            buf = ''
    if buf.strip():
        parts.append(buf.strip())

    # 若过长的句子，继续按固定长度切块，避免一次性显示
    MAX_CHARS = 14
    def _charlen(s: str) -> int:
        return len(re.sub(r"[\s，,。.!！？?；、]", "", s))
    refined: List[str] = []
    for p in parts:
        clean = re.sub(r"[，,。.!！？?；、]", "", p)
        if len(clean) > MAX_CHARS:
            for i in range(0, len(clean), MAX_CHARS):
                refined.append(clean[i:i+MAX_CHARS])
        else:
            refined.append(p)

    if not refined:
        refined = [text]

    # 基础时长：每字0.5s
    per_char = 0.5
    base = [max(0.6, _charlen(s) * per_char) for s in refined]
    total_base = sum(base) or 1.0
    target_total = duration if (duration and duration > 0) else total_base
    scale = target_total / total_base
    # 最小时长下限+二次归一
    first = [b * scale for b in base]
    min_floor = min(0.9, target_total / max(1, len(refined) * 1.8))
    floored = [max(min_floor, d) for d in first]
    sum_floor = sum(floored) or 1.0
    scale2 = target_total / sum_floor
    final = [d * scale2 for d in floored]

    # 生成字幕（前端直接播放时消费）
    subs: List[Dict] = []
    acc = 0.0
    for i, s in enumerate(refined):
        start = acc
        dur = final[i]
        acc += dur
        end = target_total if i == len(refined) - 1 else min(target_total, acc)
        # 展示用去标点
        display = re.sub(r"[，,。.!！？?；、\\]", "", s).strip()
        subs.append({
            "text": display,
            "start_time": round(start, 3),
            "end_time": round(max(start + 0.2, end), 3)
        })
    return subs 