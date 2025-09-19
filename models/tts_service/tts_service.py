from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import torch, scipy
from transformers import VitsModel, AutoTokenizer, set_seed
import uuid, os, time, random, re, warnings, logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from contextlib import asynccontextmanager
from pydantic import BaseModel, validator
from transformers.utils import logging as hf_logging

# =============================
# 全局随机数种子固定，保证结果可复现
# =============================
def set_global_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# =============================
# 日志配置（支持 LOG_LEVEL 环境变量）
# =============================
log_level = os.getenv("LOG_LEVEL", "info").upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("tts_service")
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Uvicorn logger 单独调整
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(getattr(logging, log_level, logging.INFO))

# 过滤部分不必要的 HuggingFace 警告
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub.*")
warnings.filterwarnings("ignore", message="`resume_download` is deprecated", category=FutureWarning)
hf_logging.set_verbosity_error()


# =============================
# FastAPI 生命周期管理
# =============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[TTS] startup complete")
    try:
        yield
    finally:
        logger.info("[TTS] shutdown")


app = FastAPI(lifespan=lifespan)


# =============================
# 模型初始化
# =============================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float32

model = VitsModel.from_pretrained("facebook/mms-tts-nan", torch_dtype=DTYPE)
model = model.to(DEVICE).eval()
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-nan")


# CPU 情况下允许并行合成
EXECUTOR = ThreadPoolExecutor(max_workers=min(4, (os.cpu_count() or 2))) if DEVICE == "cpu" else None

logger.info(
    "[TTS] service starting: device=%s dtype=%s sample_rate=%s cpu_workers=%s",
    DEVICE,
    str(DTYPE),
    getattr(model.config, "sampling_rate", "-"),
    getattr(EXECUTOR, "_max_workers", 0) if EXECUTOR else 0,
)


# =============================
# 工具函数
# =============================
def _split_text(text: str) -> List[str]:
    """分割文本为语音片段，目前简单实现，必要时可改成按标点拆分"""
    s = (text or "").strip()
    return [s] if s else []


def _synthesize_segment(text: str, speaking_rate: float, seed: int = 42) -> torch.Tensor:
    """合成单个文本片段"""
    logger.debug(f"[TTS] segment: len={len(text)} rate={speaking_rate} seed={seed}")
    set_seed(seed)
    inputs = tokenizer(text, return_tensors="pt").to(DEVICE)
    model.speaking_rate = speaking_rate
    model.noise_scale = 0.0
    with torch.inference_mode():
        out = model(**inputs).waveform[0]
    return out.detach().cpu()


def _concat_tensor_wav(parts: List[torch.Tensor]) -> np.ndarray:
    """拼接多个语音片段，并归一化为 int16 PCM"""
    if not parts:
        return np.zeros((0,), dtype=np.int16)
    wav = torch.cat(parts, dim=-1).numpy().astype(np.float32)
    if wav.size == 0:
        return np.zeros((0,), dtype=np.int16)
    max_amp = float(np.max(np.abs(wav))) or 1.0
    wav = np.clip(wav / max_amp, -1.0, 1.0)
    return (wav * 32767.0).astype(np.int16)


# =============================
# 请求 Schema
# =============================
class TTSPostRequest(BaseModel):
    text: str
    speaking_rate: float = 1.0

# =============================
# API 路由
# =============================
@app.post("/tts")
def synthesize_post(req: TTSPostRequest, request: Request):
    logger.info("[TTS-SVC] 收到 /tts 请求: len(text)=%d, speaking_rate=%.2f", len(req.text or ""), req.speaking_rate)
    t0 = time.time()
    segments = _split_text(req.text)
    wave_parts: List[torch.Tensor] = []

    if DEVICE == "cpu" and len(segments) > 1:
        future_map = {EXECUTOR.submit(_synthesize_segment, seg, req.speaking_rate): idx for idx, seg in enumerate(segments)}
        wave_parts = [None]*len(segments)
        for fut in as_completed(future_map):
            wave_parts[future_map[fut]] = fut.result()
    else:
        for seg in segments:
            wave_parts.append(_synthesize_segment(seg, req.speaking_rate))

    wav_np = _concat_tensor_wav(wave_parts)
    filename = f"{uuid.uuid4()}.wav"
    filepath = os.path.join("/tmp", filename)
    scipy.io.wavfile.write(filepath, rate=model.config.sampling_rate, data=wav_np)
    logger.info("[TTS-SVC] 生成完成: file=%s time=%.1fms size=%d bytes", filepath, (time.time()-t0)*1000.0, os.path.getsize(filepath))

    return FileResponse(filepath, media_type="audio/wav", filename="output.wav")


# =============================
# 主程序入口（开发模式）
# =============================
if __name__ == "__main__":
    set_global_seed(42)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)
