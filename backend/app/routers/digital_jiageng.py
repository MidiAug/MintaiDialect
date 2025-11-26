"""
数字嘉庚路由模块
职责：只负责 HTTP 层参数接收与结果返回，业务全部下沉到 jiageng_service / conversation_service
"""
from fastapi import APIRouter, File, UploadFile, Form, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import time
import json

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


@router.post(
    "/chat/stream",
    summary="与数字嘉庚对话（流式）",
    description="上传音频文件与数字嘉庚进行语音对话（流式版本），支持实时返回片段音频和字幕。",
)
async def chat_with_jiageng_stream(
    request: Request,
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    input_language: LanguageType = Form(LanguageType.MINNAN),
    output_language: LanguageType = Form(LanguageType.MINNAN),
    speaking_speed: float = Form(1.0),
    show_subtitles: bool = Form(False),
    prompt_style: str = Form("pause_format", description="提示词风格：normal/pause_format/structured"),
):
    """
    数字嘉庚流式对话接口：
    - 返回 SSE (Server-Sent Events) 格式的流式响应
    - 每次检测到 "｜" 分隔符时，立即返回该片段的音频和字幕
    - 最后返回完整结果
    
    数据格式：
    - 片段数据：{"type": "segment", "segment_index": 0, "text": "...", "audio_url": "...", "audio_duration": 1.2, "subtitles": [...]}
    - 完成数据：{"type": "complete", "text": "...", "all_segments": [...]}
    - 错误数据：{"type": "error", "error": "...", "text": "...", "all_segments": [...]}
    """
    try:
        # 验证必需参数
        if not audio_file:
            raise HTTPException(status_code=400, detail="缺少音频文件")
        
        if not audio_file.filename:
            logger.warning("[DJ-Stream] 音频文件名为空")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[DJ-Stream] 参数验证失败: %s", e)
        raise HTTPException(status_code=400, detail=f"参数验证失败: {str(e)}")
    
    start_time = time.time()
    logger.info("[DJ-Stream] 收到 /chat/stream 请求")
    logger.info("[DJ-Stream] 参数: session_id=%s, input_language=%s, output_language=%s, speaking_speed=%s, show_subtitles=%s, prompt_style=%s",
                session_id, input_language, output_language, speaking_speed, show_subtitles, prompt_style)
    
    # 1) 会话管理
    session_id = conversation_service.get_or_create_session(session_id)
    logger.info("[DJ-Stream] 使用会话ID: %s", session_id)
    conversation_service.cleanup_old_sessions()
    
    # 2) 读取原始音频字节
    try:
        audio_bytes = await audio_file.read()
        logger.info("[DJ-Stream] 音频文件读取成功: filename=%s, size=%d bytes", 
                   audio_file.filename, len(audio_bytes))
    except Exception as e:
        logger.exception("[DJ-Stream] 音频文件读取失败: %s", e)
        raise
    
    async def generate_stream():
        """生成 SSE 流式响应"""
        first_chunk_sent = False  # 标记是否已发送第一条响应
        try:
            logger.info("[DJ-Stream] 开始流式处理")
            async for chunk in jiageng_service.chat_with_audio_stream(
                audio_filename=audio_file.filename or "recording.wav",
                audio_bytes=audio_bytes,
                session_id=session_id,
                input_language=input_language,
                speaking_speed=speaking_speed,
                show_subtitles=show_subtitles,
                prompt_style=prompt_style,
            ):
                # 将 Pydantic 模型转换为字典（处理 subtitles 中的 DigitalJiagengSubtitle）
                def convert_to_dict(obj):
                    """递归转换 Pydantic 模型为字典"""
                    if isinstance(obj, list):
                        return [convert_to_dict(item) for item in obj]
                    elif hasattr(obj, 'dict'):
                        # Pydantic 模型
                        return obj.dict()
                    elif hasattr(obj, 'model_dump'):
                        # Pydantic v2 模型
                        return obj.model_dump()
                    elif isinstance(obj, dict):
                        return {k: convert_to_dict(v) for k, v in obj.items()}
                    else:
                        return obj
                
                serializable_chunk = convert_to_dict(chunk)
                
                # 记录第一条响应发送时间
                if not first_chunk_sent:
                    first_response_time = time.time() - start_time
                    logger.info("[DJ-Stream] 第一条响应发送，耗时: %.2f秒", first_response_time)
                    first_chunk_sent = True
                
                # 格式化为 SSE 格式
                # 注意：确保 JSON 序列化时正确处理中文字符
                json_str = json.dumps(serializable_chunk, ensure_ascii=False)
                yield f"data: {json_str}\n\n"
            
            # 发送完成标记
            yield "data: [DONE]\n\n"
            
            elapsed_time = time.time() - start_time
            logger.info("[DJ-Stream] /chat/stream 请求完成，耗时: %.2f秒", elapsed_time)
            
        except Exception as e:
            logger.exception("[DJ-Stream] 流式处理异常: %s", e)
            # 发送错误信息
            error_chunk = {
                "type": "error",
                "error": str(e),
                "text": "",
                "all_segments": [],
            }
            json_str = json.dumps(error_chunk, ensure_ascii=False)
            yield f"data: {json_str}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
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
