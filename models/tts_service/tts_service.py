from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
import torch, scipy
from transformers import VitsModel, AutoTokenizer, set_seed
import uuid
import os
import uvicorn

# 1) 初始化 FastAPI
app = FastAPI()

# 2) 加载模型（只加载一次，避免每次请求都耗时）
model = VitsModel.from_pretrained("facebook/mms-tts-nan")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-nan")

model.speaking_rate = 0.9
model.noise_scale = 0.3

# 3) 语音合成接口
@app.get("/tts")
def synthesize(text: str = Query(..., description="要合成的文本")):
    # 转张量
    inputs = tokenizer(text, return_tensors="pt")
    set_seed(42)  # 固定随机种子
    with torch.no_grad():
        waveform = model(**inputs).waveform[0]

    # 保存临时 WAV 文件
    filename = f"{uuid.uuid4()}.wav"
    filepath = os.path.join("/tmp", filename)
    scipy.io.wavfile.write(
        filepath,
        rate=model.config.sampling_rate,
        data=waveform.cpu().numpy()
    )

    # 返回文件
    return FileResponse(filepath, media_type="audio/wav", filename="output.wav")

if __name__ == "__main__":
    # 启动服务，端口 9000
    uvicorn.run(app, host="0.0.0.0", port=9000)
