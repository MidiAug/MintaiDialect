from fastapi import FastAPI, UploadFile, File
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import tempfile
import uvicorn

# 初始化 FastAPI 应用
app = FastAPI(title="ASR Model Service")

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
        # 临时保存上传的文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # 模型推理
        result = inference_pipeline(input=tmp_path)
        text = result[0]['text'] if result and result[0] and 'text' in result[0] else ""

        return {"status": "success", "text": text}

    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # 启动服务，端口 9001
    uvicorn.run(app, host="0.0.0.0", port=9001)
