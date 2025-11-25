from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from vllm import LLM, SamplingParams
from contextlib import asynccontextmanager
import logging
import sys
import time
import asyncio
import gc
import torch

# 基础日志输出（与Uvicorn整合到stdout）
# 设置 logger，避免重复日志（uvicorn 会使用 root logger）
logger = logging.getLogger("models.vllm_service")
logger.setLevel(logging.INFO)
logger.propagate = False  # 防止传播到 root logger，避免重复

# 清除已有的 handler，避免重复
if logger.handlers:
    logger.handlers.clear()

# 添加自定义 handler
sh = logging.StreamHandler(sys.stdout)
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(sh)

# 全局变量存储模型实例
llm = None
device = "cuda"  # vLLM 目前只支持 GPU

# 请求模型
class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    context: str = ""
    max_length: int = 512
    temperature: float = 0.7

def load_model():
    """加载 vLLM 模型"""
    global llm
    try:
        model_name = "Qwen/Qwen3-1.7B"
        logger.info(f"[vLLM] 开始加载模型: {model_name} (设备: {device})")
        llm = LLM(model=model_name, tensor_parallel_size=1, gpu_memory_utilization=0.7)
        logger.info(f"[vLLM] 模型加载完成: {model_name}")
    except Exception as e:
        logger.exception(f"[vLLM] 模型加载失败: {str(e)}")
        raise

def unload_model():
    """卸载 vLLM 模型，释放GPU内存"""
    global llm
    if llm is not None:
        try:
            logger.info("[vLLM] 开始卸载模型，释放GPU内存...")
            # 删除模型实例
            del llm
            llm = None
            
            # 清理GPU缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            
            # 强制垃圾回收
            gc.collect()
            
            logger.info("[vLLM] 模型卸载完成，GPU内存已释放")
        except Exception as e:
            logger.exception(f"[vLLM] 模型卸载失败: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时加载模型，关闭时释放资源"""
    # 启动时加载模型
    load_model()
    yield
    # 关闭时卸载模型
    unload_model()

# 使用 lifespan 管理应用生命周期
app = FastAPI(title="vLLM Model Service", lifespan=lifespan)

@app.post("/chat")
async def chat_with_vllm(request: ChatRequest):
    """与vLLM模型对话，接收JSON格式的POST请求"""
    try:
        if llm is None:
            raise HTTPException(status_code=503, detail="模型未加载，请稍后重试")

        start_ts = time.monotonic()

        # 从请求模型中提取参数
        message = request.message
        context = request.context
        max_length = request.max_length
        temperature = request.temperature

        # 记录收到调用的详细信息
        logger.info(
            "[vLLM] 收到调用请求 | message_length=%d | context_length=%d | max_length=%d | temperature=%.2f",
            len(message), len(context), max_length, temperature
        )
        logger.info(
            "[vLLM] 请求参数详情 | message_preview=%s | context_preview=%s",
            (message[:100] + '...') if len(message) > 100 else message,
            (context[:100] + '...') if len(context) > 100 else (context if context else "(空)")
        )

        # 构建输入文本
        if context:
            input_text = f"{context}\n用户: {message}\n助手: "
        else:
            input_text = f"用户: {message}\n助手: "

        params = SamplingParams(temperature=temperature, max_tokens=max_length)


        # vLLM 的 generate 是同步的，需要在线程池中运行
        loop = asyncio.get_event_loop()
        
        def _generate():
            """在线程池中运行同步的 vLLM generate"""
            try:
                outputs = llm.generate([input_text], sampling_params=params)
                return list(outputs)
            except Exception as e:
                logger.exception(f"[vLLM] 模型生成失败: {str(e)}")
                raise
        
        try:
            outputs = await loop.run_in_executor(None, _generate)
        except Exception as e:
            logger.exception(f"[vLLM] 模型推理异常: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": f"模型推理失败: {str(e)}"}
            )
        
        # 获取最后一个输出（完整生成结果）
        # vLLM 返回 RequestOutput 对象，包含 outputs 列表
        response = ""
        if outputs and len(outputs) > 0:
            try:
                final_output = outputs[0]  # 第一个（也是唯一的）RequestOutput
                if hasattr(final_output, 'outputs') and len(final_output.outputs) > 0:
                    generated_text = final_output.outputs[0].text
                else:
                    # 兼容其他可能的属性
                    generated_text = getattr(final_output, 'outputs_text', '')
                
                # 提取助手回复（去除输入部分）
                if "助手: " in generated_text:
                    response = generated_text.split("助手: ")[-1].strip()
                else:
                    # 如果生成文本包含输入文本，则提取后面的部分
                    if generated_text.startswith(input_text):
                        response = generated_text[len(input_text):].strip()
                    else:
                        response = generated_text.strip()
            except Exception as e:
                logger.exception(f"[vLLM] 解析模型输出失败: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail={"status": "error", "message": f"解析模型输出失败: {str(e)}"}
                )

        elapsed_ms = (time.monotonic() - start_ts) * 1000
        
        # 记录模型响应详情
        response_preview = response[:20] if response else "(空)"
        logger.info(
            "[vLLM] 模型响应完成 | response_length=%d | response_preview=%s | time=%.1fms",
            len(response), response_preview, elapsed_ms
        )
        logger.info(
            "[vLLM] 完整响应摘要 | message=%s -> response=%s",
            (message[:50] + '...') if len(message) > 50 else message,
            (response[:50] + '...') if len(response) > 50 else response
        )

        # 更新上下文
        new_context = context + f"\n用户: {message}\n助手: {response}" if context else f"用户: {message}\n助手: {response}"

        return {
            "status": "success",
            "response": response,
            "context": new_context
        }

    except Exception as e:
        logger.exception("[vLLM] error during chat")
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})

@app.get("/health")
async def health_check():
    """健康检查接口"""
    model_loaded = llm is not None
    return {
        "status": "healthy" if model_loaded else "loading",
        "service": "vLLM Model Service",
        "model_loaded": model_loaded,
        "device": device
    }

if __name__ == "__main__":
    import uvicorn
    import os
    
    # 从环境变量读取配置，支持启动脚本传递的参数
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "9020"))
    log_level = os.getenv("LOG_LEVEL", "info")
    
    uvicorn.run(app, host=host, port=port, log_level=log_level)
