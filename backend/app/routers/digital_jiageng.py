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
        
        # TODO: 这里应该集成实际的语音识别模型
        # 当前使用模拟数据
        if audio_file:
            # 模拟语音识别
            user_input = "这是从语音识别得到的文本内容"
            logger.info(f"处理音频文件: {audio_file.filename}")
        else:
            user_input = text_input
        
        # TODO: 这里应该集成实际的对话模型
        # 当前使用预设回复
        if enable_role_play:
            # 嘉庚角色扮演模式
            jiageng_responses = [
                "教育是立国之本，兴学育人是我毕生的追求。青年人要志存高远，脚踏实地。",
                "诚毅二字，是做人做事的根本。诚以待人，毅以处事，这是我一生的座右铭。",
                "爱国不分先后，只要是中华儿女，都应该为国家的富强贡献自己的力量。",
                "办学如种树，需要长期坚持，不可急功近利。教育事业是百年树人的大计。",
                "华侨虽然身在海外，但心系祖国，根在中华，这是我们永远不变的情怀。",
                "知识改变命运，教育成就未来，这是我坚信不疑的道理。",
                "集美学校秉承'诚毅'校训，就是要培养德才兼备的人才。",
                "南洋虽好，终非久居之地。叶落归根，建设祖国是华侨的责任。"
            ]
            emotion = "睿智"
        else:
            # 普通AI助手模式
            jiageng_responses = [
                "您好！我是AI助手，很高兴为您服务。有什么可以帮助您的吗？",
                "我理解您的问题，让我为您详细解答。",
                "感谢您的提问，这确实是一个很好的问题。",
                "请问还有其他需要了解的内容吗？我很乐意为您解答。"
            ]
            emotion = "友好"
        
        # 随机选择回复
        import random
        response_text = random.choice(jiageng_responses)
        
        # TODO: 这里应该集成实际的语音合成模型
        # 当前使用模拟音频URL
        response_audio_url = f"/api/digital-jiageng/audio/{int(time.time())}.wav"
        
        processing_time = time.time() - start_time
        confidence = random.uniform(0.85, 0.98)
        
        response_data = JiagengChatResponse(
            response_text=response_text,
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