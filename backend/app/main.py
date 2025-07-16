"""
闽台方言大模型系统 - FastAPI后端主入口
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

# 导入路由模块
from app.routers import asr_tts, speech_translation, voice_interaction, voice_cloning, digital_jiageng
from app.core.config import settings

# 创建FastAPI应用实例
app = FastAPI(
    title="闽台方言大模型API",
    description="闽台方言人工智能语音处理系统后端API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS中间件，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 前端开发服务器地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保上传目录存在
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)

# 配置静态文件服务，用于提供上传的音频文件
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 注册API路由
app.include_router(asr_tts.router, prefix="/api/asr-tts", tags=["语音文本互转"])
app.include_router(speech_translation.router, prefix="/api/speech-translation", tags=["语音互译"])
app.include_router(voice_interaction.router, prefix="/api/voice-interaction", tags=["语音交互"])
app.include_router(voice_cloning.router, prefix="/api/voice-cloning", tags=["音色克隆"])
app.include_router(digital_jiageng.router, tags=["数字嘉庚"])

@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径，返回API信息"""
    return """
    <html>
        <head>
            <title>闽台方言大模型API</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>🎤 闽台方言大模型API服务</h1>
            <p>欢迎使用闽台方言人工智能语音处理系统！</p>
            <ul>
                <li><a href="/docs">📚 API文档 (Swagger UI)</a></li>
                <li><a href="/redoc">📖 API文档 (ReDoc)</a></li>
            </ul>
            <h2>主要功能模块:</h2>
            <ul>
                <li>🔄 方言语音-中文文本互转</li>
                <li>🌐 方言语音-中文语音互译</li>
                <li>💬 方言语音交互</li>
                <li>🎭 方言音色克隆</li>
                <li>🎭 数字嘉庚对话</li>
            </ul>
        </body>
    </html>
    """

@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "message": "闽台方言大模型API服务运行正常",
        "version": "1.0.0"
    }

@app.get("/api/info")
async def api_info():
    """API信息接口"""
    return {
        "name": "闽台方言大模型API",
        "version": "1.0.0",
        "description": "闽台方言人工智能语音处理系统后端API",
        "features": [
            "方言语音识别 (ASR)",
            "方言文本转语音 (TTS)",
            "方言语音翻译",
            "方言语音对话",
            "方言音色克隆"
        ],
        "supported_formats": ["wav", "mp3", "flac", "m4a"],
        "max_file_size": "50MB"
    }

if __name__ == "__main__":
    import uvicorn
    # 开发环境启动配置
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 