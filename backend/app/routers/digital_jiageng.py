from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
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
import json

router = APIRouter(prefix="/api/digital-jiageng", tags=["数字嘉庚"])
logger = logging.getLogger(__name__)

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
    speaking_speed: float = Form(1.0)
):
    """
    与数字嘉庚进行对话
    支持语音输入和文本输入
    """
    start_time = time.time()
    
    try:
        # 参数验证
        if not audio_file and not text_input:
            raise HTTPException(
                status_code=400, 
                detail="必须提供音频文件或文本输入"
            )
        
        if audio_file:
            # 验证音频文件
            if not audio_file.content_type.startswith('audio/'):
                raise HTTPException(
                    status_code=400,
                    detail="不支持的音频格式"
                )
            
            if audio_file.size > 50 * 1024 * 1024:  # 50MB限制
                raise HTTPException(
                    status_code=400,
                    detail="音频文件过大，请上传小于50MB的文件"
                )
        
        # 1) 处理输入：若有音频，先进行 ASR
        if audio_file:
            if hasattr(audio_file, "read"):
                contents = await audio_file.read()
            else:
                contents = await audio_file.read()
            if settings.asr_service_url:
                asr_res = await asr_service.transcribe(audio_file.filename, contents, source_language=input_language.value)
                user_input = asr_res.get("text") or ""
            else:
                user_input = ""
            logger.info(f"处理音频文件: {audio_file.filename}")
        else:
            user_input = text_input or ""
        
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
        # 要求以 JSON 输出，便于解析：{"zh": "...", "tlp": "..."}
        # 其中 tlp 为接近厦门发音的 POJ 白话文注音；规则：原逗号→空格，原空格→ '-'
        prompt = (
            "你是陈嘉庚，请基于提供的资料进行角色化回答。"
            "严格以 JSON 返回：{\"zh\": \"中文普通话回答\", \"tlp\": \"对应的POJ白话文注音\"}。"
            "注意：tlp 中将原逗号替换为空格，将原空格替换为 '-'。不要输出除 JSON 之外的任何内容。\n"
            f"资料：{retrieved}\n"
            f"用户问题：{user_input}"
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ]
        llm_out = await llm_service.chat_messages(messages, model_hint=None)
        response_text = llm_out.get("text") or ""
        zh_text = response_text
        tlp_text = ""
        # 优先解析 JSON
        try:
            parsed = json.loads(response_text)
            zh_text = parsed.get("zh") or zh_text
            tlp_text = parsed.get("tlp") or ""
        except Exception:
            # 如果不是 JSON，就直接把整体文本作为中文回答（退化）
            pass
        # 简单情感设置（可后续接入情感模型）
        emotion = "睿智" if enable_role_play else "友好"
        
        # 3) TTS：将上一步中文或台罗输出转为语音（此处建议用台罗部分）
        response_audio_url = None
        try:
            if settings.tts_service_url:
                tts_input_text = tlp_text if tlp_text else zh_text
                tts_res = await tts_service.synthesize(
                    text=tts_input_text,
                    target_language=output_language.value,
                )
                response_audio_url = tts_res.get("audio_url")
        except Exception as _:
            response_audio_url = None
        
        processing_time = time.time() - start_time
        # 简单置信度占位
        confidence = 0.9
        
        # 将文本回答优先返回中文+台罗（若有）
        combined_text = zh_text if zh_text else response_text
        if tlp_text:
            combined_text = f"{combined_text}\n\n[POJ] {tlp_text}"

        response_data = JiagengChatResponse(
            response_text=combined_text,
            response_audio_url=response_audio_url,
            emotion=emotion,
            confidence=confidence,
            processing_time=processing_time
        )
        
        logger.info(f"嘉庚对话完成，处理时间: {processing_time:.2f}s")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="对话处理成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"嘉庚对话处理失败: {str(e)}")
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