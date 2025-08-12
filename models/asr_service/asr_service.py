from fastapi import FastAPI, UploadFile, File
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import tempfile
import uvicorn
import logging
import sys
import time

# 初始化 FastAPI 应用
app = FastAPI(title="ASR Model Service")

# 基础日志输出（与Uvicorn整合到stdout）
logger = logging.getLogger("models.asr_service")
logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(sh)

# 加载模型（只加载一次，提升性能）
inference_pipeline = pipeline(
    task=Tasks.auto_speech_recognition,
    model="chenyongxian299/speech_UniASR_asr_2pass-minnan-16k-common-vocab3825",
    device="cpu"  # 可以改为 "gpu"
)

@app.post("/asr")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    接收音频文件并返回识别文本
    """
    try:
        start_ts = time.monotonic()
        # 读取并临时保存上传的文件
        data = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        # 模型推理
        result = inference_pipeline(input=tmp_path)
        text = result[0]['text'] if result and result[0] and 'text' in result[0] else ""

        elapsed_ms = (time.monotonic() - start_ts) * 1000
        logger.info(
            "[ASR] file=%s size=%dB -> text_preview=%s time=%.1fms",
            getattr(file, 'filename', 'uploaded.wav'),
            len(data) if data else 0,
            (text[:80] + '...') if text and len(text) > 80 else text,
            elapsed_ms,
        )

        return {"status": "success", "text": text}

    except Exception as e:
        logger.exception("[ASR] error during transcription")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # 启动服务，端口 9000
    uvicorn.run(app, host="0.0.0.0", port=9000)
