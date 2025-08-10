"""
语音交互API路由器 - 方言对话和问答功能
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import Optional, Dict, Any
import uuid
import json
import time
from pathlib import Path
from datetime import datetime

from app.models.schemas import (
    VoiceInteractionRequest, VoiceInteractionResponse,
    BaseResponse, ErrorResponse, LanguageType, AudioFormat
)
from app.core.config import settings
from app.services import asr_service, tts_service, llm_service

router = APIRouter()

# 模拟对话历史存储 (实际应该使用数据库)
conversation_history: Dict[str, list] = {}

# ============ 语音对话接口 ============

@router.post("/chat", response_model=BaseResponse, summary="语音对话")
async def voice_chat(
    audio_file: Optional[UploadFile] = File(None, description="音频文件"),
    text_input: Optional[str] = Form(None, description="文本输入"),
    conversation_id: Optional[str] = Form(None, description="对话ID"),
    user_language: LanguageType = Form(default=LanguageType.MINNAN, description="用户语言"),
    response_language: LanguageType = Form(default=LanguageType.MINNAN, description="回复语言"),
    response_mode: str = Form(default="both", description="回复模式: text, audio, both")
):
    """
    与AI进行方言语音对话
    
    - **audio_file**: 用户语音输入 (可选，与text_input二选一)
    - **text_input**: 用户文本输入 (可选，与audio_file二选一)
    - **conversation_id**: 对话ID，用于多轮对话
    - **user_language**: 用户使用的语言/方言
    - **response_language**: AI回复使用的语言/方言
    - **response_mode**: 回复模式 (text: 仅文本, audio: 仅语音, both: 文本+语音)
    """
    try:
        # 验证输入
        if not audio_file and not text_input:
            raise HTTPException(
                status_code=400,
                detail="请提供音频文件或文本输入"
            )
        
        # 生成或使用现有的对话ID
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # 处理用户输入
        user_input = ""
        
        if audio_file:
            # 验证音频文件
            file_extension = audio_file.filename.split('.')[-1].lower()
            if file_extension not in settings.allowed_audio_formats:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的音频格式: {file_extension}"
                )
            
            contents = await audio_file.read()
            if len(contents) > settings.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail="文件大小超过限制"
                )
            
            # 保存音频文件
            file_id = str(uuid.uuid4())
            file_path = Path(settings.upload_dir) / f"{file_id}.{file_extension}"
            with open(file_path, "wb") as f:
                f.write(contents)
            
            # 外部 ASR 服务
            if settings.asr_service_url:
                result = await asr_service.transcribe(
                    audio_file.filename, contents, source_language=user_language.value
                )
                user_input = result.get("text", "")
            else:
                # 模拟
                user_input = f"这是通过{user_language.value}语音识别得到的用户输入内容"
        
        if text_input:
            user_input = text_input
        
        # 获取对话历史
        if conversation_id not in conversation_history:
            conversation_history[conversation_id] = []
        
        history = conversation_history[conversation_id]
        
        # LLM 服务：输出台罗拼音
        response_text = None
        if settings.llm_service_url:
            llm_result = await llm_service.chat_to_taibun(user_input, history=history)
            response_text = llm_result.get("text")
        if not response_text:
            # 模拟回复
            response_text = generate_mock_response(user_input, user_language, response_language, history)
        
        # 生成语音回复
        response_audio_url = None
        if response_mode in ["audio", "both"]:
            audio_id = str(uuid.uuid4())
            audio_filename = f"{audio_id}_response.wav"
            audio_path = Path(settings.upload_dir) / audio_filename
            
            if settings.tts_service_url:
                tts_result = await tts_service.synthesize(
                    response_text, target_language=response_language.value
                )
                response_audio_url = tts_result.get("audio_url")
                # 若服务返回二进制，上层保存
                if not response_audio_url and tts_result.get("binary"):
                    with open(audio_path, "wb") as f:
                        f.write(tts_result["binary"])
                    response_audio_url = f"/uploads/{audio_filename}"
            else:
                # 创建模拟音频文件
                with open(audio_path, "wb") as f:
                    f.write(b'RIFF')
                    f.write(b'\x24\x08\x00\x00')
                    f.write(b'WAVE')
                response_audio_url = f"/uploads/{audio_filename}"
        
        # 更新对话历史
        history.append({
            "user": user_input,
            "assistant": response_text,
            "timestamp": datetime.now().isoformat(),
            "user_language": user_language,
            "response_language": response_language
        })
        
        # 限制对话历史长度
        if len(history) > 20:
            history = history[-20:]
            conversation_history[conversation_id] = history
        
        # 模拟情感和意图检测
        emotion = detect_emotion(user_input)
        intent = detect_intent(user_input)
        entities = extract_entities(user_input)
        
        mock_response = VoiceInteractionResponse(
            conversation_id=conversation_id,
            user_input=user_input,
            response_text=response_text,
            response_audio_url=response_audio_url,
            emotion=emotion,
            intent=intent,
            entities=entities
        )
        
        return BaseResponse(
            success=True,
            message="语音对话处理完成",
            data=mock_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音对话处理失败: {str(e)}")

# ============ 方言问答接口 ============

@router.post("/qa", response_model=BaseResponse, summary="方言问答")
async def dialect_qa(
    question: str = Form(..., description="用户问题"),
    question_language: LanguageType = Form(default=LanguageType.MINNAN, description="问题语言"),
    answer_language: LanguageType = Form(default=LanguageType.MINNAN, description="回答语言"),
    context: Optional[str] = Form(None, description="问题上下文"),
    return_audio: bool = Form(default=False, description="是否返回语音回答")
):
    """
    方言问答系统
    
    - **question**: 用户问题
    - **question_language**: 问题使用的语言/方言
    - **answer_language**: 回答使用的语言/方言
    - **context**: 问题的上下文信息 (可选)
    - **return_audio**: 是否返回语音形式的回答
    """
    try:
        if len(question.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="问题不能为空"
            )
        
        # TODO: 调用问答模型进行答案生成
        # 这里应该基于问题内容、语言类型和上下文生成准确的答案
        
        # 模拟问答结果
        answer = generate_mock_answer(question, question_language, answer_language, context)
        
        # 生成语音回答
        answer_audio_url = None
        if return_audio:
            audio_id = str(uuid.uuid4())
            audio_filename = f"{audio_id}_answer.wav"
            audio_path = Path(settings.upload_dir) / audio_filename
            
            # TODO: 调用TTS模型生成语音
            with open(audio_path, "wb") as f:
                f.write(b'RIFF')
                f.write(b'\x24\x08\x00\x00')
                f.write(b'WAVE')
            
            answer_audio_url = f"/uploads/{audio_filename}"
        
        # 模拟相关信息提取
        confidence = 0.88
        keywords = extract_keywords(question)
        category = classify_question(question)
        
        return BaseResponse(
            success=True,
            message="方言问答处理完成",
            data={
                "question": question,
                "answer": answer,
                "question_language": question_language,
                "answer_language": answer_language,
                "answer_audio_url": answer_audio_url,
                "confidence": confidence,
                "keywords": keywords,
                "category": category,
                "context_used": context is not None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"方言问答处理失败: {str(e)}")

# ============ 对话历史管理 ============

@router.get("/conversations/{conversation_id}", response_model=BaseResponse, summary="获取对话历史")
async def get_conversation_history(conversation_id: str):
    """
    获取指定对话的历史记录
    
    - **conversation_id**: 对话ID
    """
    try:
        if conversation_id not in conversation_history:
            raise HTTPException(
                status_code=404,
                detail="对话不存在"
            )
        
        history = conversation_history[conversation_id]
        
        return BaseResponse(
            success=True,
            message="获取对话历史成功",
            data={
                "conversation_id": conversation_id,
                "history": history,
                "total_turns": len(history),
                "created_at": history[0]["timestamp"] if history else None,
                "last_updated": history[-1]["timestamp"] if history else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")

@router.delete("/conversations/{conversation_id}", response_model=BaseResponse, summary="删除对话历史")
async def delete_conversation(conversation_id: str):
    """
    删除指定对话的历史记录
    
    - **conversation_id**: 对话ID
    """
    try:
        if conversation_id in conversation_history:
            del conversation_history[conversation_id]
            message = "对话历史删除成功"
        else:
            message = "对话不存在或已被删除"
        
        return BaseResponse(
            success=True,
            message=message,
            data={"conversation_id": conversation_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除对话历史失败: {str(e)}")

# ============ 语音情感分析 ============

@router.post("/emotion-analysis", response_model=BaseResponse, summary="语音情感分析")
async def analyze_emotion(
    audio_file: UploadFile = File(..., description="音频文件"),
    language: LanguageType = Form(default=LanguageType.MINNAN, description="音频语言")
):
    """
    分析语音中的情感
    
    - **audio_file**: 要分析的音频文件
    - **language**: 音频使用的语言/方言
    """
    try:
        # 验证文件格式
        file_extension = audio_file.filename.split('.')[-1].lower()
        if file_extension not in settings.allowed_audio_formats:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的音频格式: {file_extension}"
            )
        
        contents = await audio_file.read()
        if len(contents) > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail="文件大小超过限制"
            )
        
        # TODO: 调用情感分析模型
        # 这里应该分析音频中的情感特征，包括音调、语速、音量等
        
        # 模拟情感分析结果
        emotions = [
            {"emotion": "开心", "confidence": 0.45, "intensity": "中等"},
            {"emotion": "平静", "confidence": 0.30, "intensity": "中等"},
            {"emotion": "兴奋", "confidence": 0.15, "intensity": "轻微"},
            {"emotion": "担心", "confidence": 0.08, "intensity": "轻微"},
            {"emotion": "愤怒", "confidence": 0.02, "intensity": "很轻"}
        ]
        
        primary_emotion = emotions[0]
        
        # 音频特征分析
        audio_features = {
            "duration": len(contents) / 16000.0,
            "average_pitch": 220.5,  # Hz
            "pitch_variance": 45.2,
            "speaking_rate": 180,     # 词/分钟
            "volume_level": 0.72,     # 0-1
            "voice_quality": "清晰"
        }
        
        return BaseResponse(
            success=True,
            message="语音情感分析完成",
            data={
                "filename": audio_file.filename,
                "language": language,
                "primary_emotion": primary_emotion,
                "all_emotions": emotions,
                "audio_features": audio_features,
                "analysis_confidence": 0.85
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音情感分析失败: {str(e)}")

# ============ 辅助函数 ============

def generate_mock_response(user_input: str, user_lang: LanguageType, response_lang: LanguageType, history: list) -> str:
    """生成模拟的AI回复"""
    language_names = {
        LanguageType.MANDARIN: "普通话",
        LanguageType.MINNAN: "闽南话",
        LanguageType.HAKKA: "客家话",
        LanguageType.TAIWANESE: "台湾话"
    }
    
    responses = [
        f"我理解您用{language_names[user_lang]}说的内容，我会用{language_names[response_lang]}回复您。",
        f"这是一个很有趣的话题，让我们继续用{language_names[response_lang]}深入讨论。",
        f"根据我们之前的{len(history)}轮对话，我认为您的观点很有道理。",
        f"在{language_names[response_lang]}文化中，这个问题确实值得深入思考。"
    ]
    
    return responses[len(history) % len(responses)]

def generate_mock_answer(question: str, q_lang: LanguageType, a_lang: LanguageType, context: Optional[str]) -> str:
    """生成模拟的问答回复"""
    language_names = {
        LanguageType.MANDARIN: "普通话",
        LanguageType.MINNAN: "闽南话",
        LanguageType.HAKKA: "客家话",
        LanguageType.TAIWANESE: "台湾话"
    }
    
    base_answer = f"根据您用{language_names[q_lang]}提出的问题，我用{language_names[a_lang]}为您回答："
    
    if "天气" in question:
        return f"{base_answer}今天天气晴朗，温度适宜，适合外出活动。"
    elif "时间" in question:
        return f"{base_answer}现在是{datetime.now().strftime('%Y年%m月%d日 %H:%M')}。"
    elif "方言" in question or "闽南话" in question:
        return f"{base_answer}闽南话是一种重要的汉语方言，主要分布在福建南部、台湾等地区。"
    else:
        return f"{base_answer}这是一个很好的问题，根据我的理解和分析，我认为..."

def detect_emotion(text: str) -> str:
    """检测文本情感"""
    emotions = ["开心", "平静", "担心", "兴奋", "疑惑"]
    return emotions[len(text) % len(emotions)]

def detect_intent(text: str) -> str:
    """检测用户意图"""
    if "?" in text or "？" in text or "什么" in text or "怎么" in text:
        return "询问"
    elif "谢谢" in text or "感谢" in text:
        return "感谢"
    elif "再见" in text or "拜拜" in text:
        return "告别"
    else:
        return "聊天"

def extract_entities(text: str) -> list:
    """提取实体"""
    entities = []
    # 模拟实体提取
    if "天气" in text:
        entities.append({"entity": "天气", "type": "信息查询", "confidence": 0.9})
    if "时间" in text:
        entities.append({"entity": "时间", "type": "时间查询", "confidence": 0.85})
    
    return entities

def extract_keywords(text: str) -> list:
    """提取关键词"""
    # 简单的关键词提取模拟
    keywords = []
    common_words = ["的", "是", "在", "有", "和", "与", "或", "但", "然而"]
    words = text.split()
    for word in words:
        if len(word) > 1 and word not in common_words:
            keywords.append(word)
    return keywords[:5]  # 返回前5个关键词

def classify_question(question: str) -> str:
    """问题分类"""
    if "天气" in question:
        return "天气查询"
    elif "时间" in question or "日期" in question:
        return "时间查询"
    elif "方言" in question or "语言" in question:
        return "语言文化"
    elif "如何" in question or "怎么" in question:
        return "操作指导"
    else:
        return "一般问答" 