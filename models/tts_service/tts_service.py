from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse
import torch, scipy
from transformers import VitsModel, AutoTokenizer, set_seed
import hashlib
import uuid
import os
import uvicorn
import re
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import time
import logging
import warnings
from transformers.utils import logging as hf_logging
from contextlib import asynccontextmanager

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("tts_service")

# 预先屏蔽冗余告警/日志
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub.*")
warnings.filterwarnings("ignore", message="`resume_download` is deprecated", category=FutureWarning)
hf_logging.set_verbosity_error()

# 1) 初始化 FastAPI（使用 lifespan，避免 on_event 弃用告警）
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[TTS] startup complete")
    try:
        yield
    finally:
        logger.info("[TTS] shutdown")

app = FastAPI(lifespan=lifespan)

# 2) 设备/精度
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# 为避免 VITS 在 flow/spline 步骤中出现 Half/Float 混用导致的运行时错误，这里统一使用 float32
DTYPE = torch.float32

# 3) 加载模型（只加载一次，避免每次请求都耗时）
model = VitsModel.from_pretrained("facebook/mms-tts-nan", torch_dtype=DTYPE)
model = model.to(DEVICE).eval()
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-nan")

# 默认合成参数
model.speaking_rate = 0.9
model.noise_scale = 1

# 线程池（仅在 CPU 下用于并行多段文本合成）
EXECUTOR = ThreadPoolExecutor(max_workers=min(4, (os.cpu_count() or 2))) if DEVICE == "cpu" else None

# 简易缓存（同样文本在进程内复用）
CACHE_DIR = "/tmp/tts_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# 启动日志
logger.info(
    "[TTS] service starting: device=%s dtype=%s sample_rate=%s cpu_workers=%s",
    DEVICE,
    str(DTYPE),
    getattr(model.config, "sampling_rate", "-"),
    getattr(EXECUTOR, "_max_workers", 0) if EXECUTOR else 0,
)



def _split_text(text: str) -> List[str]:
    """按标点或空格切分：
    - 若包含标点（。！？!?，,；;：: .），严格按标点切句
    - 否则把空格当作整段文本之间的分隔符，直接切段
    - 不再使用定长切片
    """
    s = (text or "").strip()
    if not s:
        return []

    # 标点集合
    punct_chars = set("。！？!?，,；;：:.")
    if any(ch in punct_chars for ch in s):
        parts: List[str] = []
        buf: list[str] = []
        for ch in s:
            buf.append(ch)
            if ch in punct_chars:
                seg = "".join(buf).strip()
                if seg:
                    parts.append(seg)
                buf = []
        # 尾巴没有标点也要输出
        tail = "".join(buf).strip()
        if tail:
            parts.append(tail)
        return parts

    # 否则：空格切分
    tokens = [t for t in re.split(r"\s+", s) if t]
    if tokens:
        return tokens

    # 没有空格也没有标点，则返回原文本
    return [s]



def _synthesize_segment(text: str, speaking_rate: float, seed: int = 42) -> torch.Tensor:
    logger.info(f"synthesize_segment: text={text}, speaking_rate={speaking_rate}, seed={seed}")
    set_seed(seed)
    inputs = tokenizer(text, return_tensors="pt")
    # 确保嵌入索引张量为 Long 类型，并迁移到正确设备
    moved: dict[str, torch.Tensor] = {}
    for key, value in inputs.items():
        if key in ("input_ids", "attention_mask", "token_type_ids"):
            moved[key] = value.to(dtype=torch.long, device=DEVICE)
        else:
            moved[key] = value.to(DEVICE)
    inputs = moved
    # 覆盖语速
    model.speaking_rate = speaking_rate
    # 推理
    # 统一使用 float32 精度，避免 dtype 不匹配问题
    with torch.inference_mode():
        out = model(**inputs).waveform[0]
    return out.detach().cpu()


def _concat_tensor_wav(parts: List[torch.Tensor]) -> np.ndarray:
    if not parts:
        return np.zeros((0,), dtype=np.int16)
    wav = torch.cat(parts, dim=-1).numpy().astype(np.float32)
    # 归一化到 int16
    if wav.size == 0:
        return np.zeros((0,), dtype=np.int16)
    max_amp = float(np.max(np.abs(wav))) or 1.0
    wav = np.clip(wav / max_amp, -1.0, 1.0)
    return (wav * 32767.0).astype(np.int16)


# 4) 语音合成接口
@app.get("/tts")
def synthesize(
    request: Request,
    text: str = Query(..., description="要合成的文本"),
    speaking_rate: float = Query(0.9, ge=0.5, le=1.5, description="语速 0.5~1.5"),
    seed: int = Query(42, description="随机种子"),
    parallel: bool = Query(True, description="CPU 下是否多线程并行分段合成"),
):
    t0 = time.time()
    segments = _split_text(text)
    # 接收参数日志：包含原始 URL（便于查看 % 编码）、文本预览和 UTF-8 十六进制预览
    preview = (text[:200] + "...") if len(text or "") > 200 else (text or "")
    logger.info(
        "[TTS] received GET: url=%s len=%d rate=%.2f seed=%d parallel=%s text_preview=%s",
        str(request.url), len(text or ""), speaking_rate, seed, parallel, preview,
    )
    try:
        utf8_hex = (text or "").encode("utf-8", errors="ignore").hex()
        logger.debug("[TTS] utf8_hex_preview=%s", utf8_hex[:256])
    except Exception:
        pass
    logger.info(
        "[TTS] request: len=%d, segments=%d, device=%s, rate=%.2f, parallel=%s",
        len(text or ""), len(segments), DEVICE, speaking_rate, (parallel and DEVICE == "cpu"),
    )

    # 命中缓存（使用稳定摘要作为键，避免 Python 进程重启导致 hash() 改变）
    cache_sig = f"{speaking_rate}|{seed}|{text}".encode("utf-8")
    cache_key = hashlib.sha1(cache_sig).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.wav")
    if os.path.exists(cache_path):
        logger.info("[TTS] cache hit: path=%s", cache_path)
        return FileResponse(cache_path, media_type="audio/wav", filename="output.wav")

    if not segments:
        segments = [text]

    # CPU：可选择多线程；GPU：顺序合成更稳定
    wave_parts: List[torch.Tensor] = []
    if DEVICE == "cpu" and parallel and len(segments) > 1:
        future_map = {EXECUTOR.submit(_synthesize_segment, seg, speaking_rate, seed): idx for idx, seg in enumerate(segments)}
        wave_parts = [None] * len(segments)  # type: ignore
        for fut in as_completed(future_map):
            idx = future_map[fut]
            wave_parts[idx] = fut.result()
    else:
        for seg in segments:
            wave_parts.append(_synthesize_segment(seg, speaking_rate, seed))

    wav_np = _concat_tensor_wav(wave_parts)  # type: ignore

    # 保存临时 WAV 文件
    filename = f"{uuid.uuid4()}.wav"
    filepath = os.path.join("/tmp", filename)
    scipy.io.wavfile.write(
        filepath,
        rate=model.config.sampling_rate,
        data=wav_np,
    )

    # 同时写入缓存
    try:
        scipy.io.wavfile.write(cache_path, rate=model.config.sampling_rate, data=wav_np)
    except Exception:
        pass

    logger.info(
        "[TTS] done: total_time=%.1f ms, out=%s, sr=%s",
        (time.time() - t0) * 1000.0,
        filepath,
        getattr(model.config, "sampling_rate", "-"),
    )

    # 返回文件
    return FileResponse(filepath, media_type="audio/wav", filename="output.wav")

from pydantic import BaseModel


class TTSPostRequest(BaseModel):
    text: str
    speaking_rate: float = 0.9
    seed: int = 42
    parallel: bool = True


@app.post("/tts")
def synthesize_post(req: TTSPostRequest, request: Request):
    """兼容 JSON POST 协议，参数与 GET 等价。"""
    preview = (req.text[:200] + "...") if len(req.text or "") > 200 else (req.text or "")
    logger.info(
        "[TTS] received POST: url=%s len=%d rate=%.2f seed=%d parallel=%s text_preview=%s",
        str(request.url), len(req.text or ""), req.speaking_rate, req.seed, req.parallel, preview,
    )
    try:
        utf8_hex = (req.text or "").encode("utf-8", errors="ignore").hex()
        logger.info("[TTS] utf8_hex_preview=%s", utf8_hex[:256])
    except Exception:
        pass
    return synthesize(
        request=request,
        text=req.text,
        speaking_rate=req.speaking_rate,
        seed=req.seed,
        parallel=req.parallel,
    )


if __name__ == "__main__":
    # 启动服务，在脚本内运行请使用单进程；如需多进程请使用 uvicorn CLI：
    # PYTHONPATH=/path/to/data/MintaiDialect uvicorn models.tts_service.tts_service:app --host 0.0.0.0 --port 9002 --workers 2
    uvicorn.run(app, host="0.0.0.0", port=9002)
