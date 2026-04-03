# src/api/routes.py

"""
FastAPI 路由定义

提供 HTTP API 供前端调用
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.agent.customer_service import customer_service_agent
from src.agent.user_analyst import user_analyst

app = FastAPI(title="Lushop AI Assistant API")


class ChatRequest(BaseModel):
    message: str
    user_id: int
    session_id: Optional[str] = None


class AnalysisRequest(BaseModel):
    user_id: int
    report_type: str = "comprehensive"  # comprehensive, behavior, preference


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    智能客服对话接口
    """
    try:
        response = await customer_service_agent.ainvoke({
            "messages": [{"role": "user", "content": request.message}],
            "user_id": request.user_id,
        })
        return {"success": True, "response": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analysis")
async def analyze_user(request: AnalysisRequest):
    """
    用户分析报告接口
    """
    try:
        response = await user_analyst.ainvoke({
            "user_id": request.user_id,
            "report_type": request.report_type,
        })
        return {"success": True, "report": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}