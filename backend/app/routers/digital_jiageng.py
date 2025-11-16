"""
数字嘉庚路由模块
职责：只负责 HTTP 层参数接收与结果返回，业务全部下沉到 jiageng_service / conversation_service
"""
from fastapi import APIRouter, File, UploadFile, Form, Request
from typing import Optional
import logging
import time

from ..models.schemas import BaseResponse, LanguageType, DigitalJiagengResponse
from app.services import jiageng_service, conversation_service

router = APIRouter(prefix="/api/digital-jiageng", tags=["数字嘉庚"])
logger = logging.getLogger(__name__)


@router.post(
    "/chat",
    response_model=BaseResponse,
    summary="与数字嘉庚对话",
    description="上传音频文件与数字嘉庚进行语音对话，支持多种方言输入输出，可选择是否返回字幕。",
)
async def chat_with_jiageng(
    request: Request,
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    input_language: LanguageType = Form(LanguageType.MINNAN),
    output_language: LanguageType = Form(LanguageType.MINNAN),
    speaking_speed: float = Form(1.0),
    show_subtitles: bool = Form(False),
    use_mock: bool = Form(False, description="是否使用模拟嘉庚（联调/演示用）"),
):
    """
    数字嘉庚主入口：
    - 路由层只做参数接收与调用服务
    - ASR / LLM / TTS / 字幕与会话历史全部在服务层处理
    """
    start_time = time.time()
    logger.info("[DJ] 收到 /chat 请求")

    # 1) 会话管理（路由层只负责拿到 session_id）
    session_id = conversation_service.get_or_create_session(session_id)
    logger.info("[DJ] 使用会话ID: %s", session_id)
    conversation_service.cleanup_old_sessions()

    # 2) 读取原始音频字节
    audio_bytes = await audio_file.read()

    # 3) 根据 use_mock 决定走模拟流程还是真实流程（业务在 jiageng_service）
    if use_mock:
        result = await jiageng_service.mock_chat(
            session_id=session_id,
            show_subtitles=show_subtitles,
        )
    else:
        result = await jiageng_service.chat_with_audio(
            audio_filename=audio_file.filename or "recording.wav",
            audio_bytes=audio_bytes,
            session_id=session_id,
            input_language=input_language,
            speaking_speed=speaking_speed,
            show_subtitles=show_subtitles,
        )

    elapsed_time = time.time() - start_time
    logger.info("[DJ] /chat 请求完成，耗时: %.2f秒", elapsed_time)

    return BaseResponse(
        message="数字嘉庚对话完成",
        data=DigitalJiagengResponse(
            session_id=session_id,
            response_audio_url=result.get("audio_url"),
            subtitles=result.get("subtitles") or [],
        ),
    )


@router.get(
    "/sessions/{session_id}/history",
    summary="获取对话历史",
    description="获取指定会话的对话历史记录"
)
async def get_conversation_history(session_id: str):
    """获取指定会话的对话历史"""
    history = conversation_service.get_conversation_history(session_id)
    metadata = conversation_service.get_session_metadata(session_id)
    
    if metadata is None:
        return BaseResponse(
            success=False,
            message="会话不存在",
            data=None
        )
    
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
    metadata = conversation_service.get_session_metadata(session_id)
    
    if metadata is None:
        return BaseResponse(
            success=False,
            message="会话不存在",
            data=None
        )
    
    conversation_service.delete_session(session_id)
    
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
    sessions = conversation_service.list_all_sessions()
    
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
