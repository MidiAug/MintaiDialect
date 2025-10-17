from fastapi import FastAPI, Query
import uvicorn

# 初始化 FastAPI 应用
app = FastAPI(title="LLM Model Service")

@app.get("/chat")
async def chat_with_llm(
    message: str = Query(..., description="用户输入的消息"),
    context: str = Query("", description="对话上下文")
):
    """
    与LLM模型进行对话
    """
    try:
        # TODO: 这里应该调用实际的LLM模型
        # 现在返回模拟响应
        response = f"这是对'{message}'的模拟LLM响应。实际应该调用闽台方言LLM模型。"
        
        return {
            "status": "success",
            "response": response,
            "context": context + f"\n用户: {message}\n助手: {response}"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "LLM Model Service"}

if __name__ == "__main__":
    # 启动服务，端口 9002
    uvicorn.run(app, host="0.0.0.0", port=9001)
