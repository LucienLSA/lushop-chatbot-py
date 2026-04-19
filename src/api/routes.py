# src/api/routes.py

"""
FastAPI 路由定义

提供 HTTP API 供前端调用
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

from src.agent.runtime import run_customer_service, run_user_analysis
from src.tools.analytics_tools import generate_ops_report
from src.tools.integration_tools import send_webhook

app = FastAPI(title="Lushop AI Assistant API")


class ChatRequest(BaseModel):
    message: str
    user_id: int
    session_id: Optional[str] = None


class AnalysisRequest(BaseModel):
    user_id: int
    report_type: str = "comprehensive"  # comprehensive, behavior, preference


class OpsReportRequest(BaseModel):
    days: int = 30
    push_webhook: bool = False
    webhook_url: Optional[str] = None


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    智能客服对话接口
    """
    try:
        response = await run_customer_service(request.message, request.user_id)
        return {"success": True, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analysis")
async def analyze_user(request: AnalysisRequest):
    """
    用户分析报告接口
    """
    try:
        response = await run_user_analysis(request.user_id, request.report_type)
        return {"success": True, "report": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ops-report")
async def ops_report(request: OpsReportRequest):
    """智能运营分析报告接口（销量、转化、活跃）。"""
    try:
        report = generate_ops_report.invoke({"days": request.days})
        webhook_result = None
        if request.push_webhook:
            target = request.webhook_url
            if not target:
                raise HTTPException(status_code=400, detail="push_webhook=true 时必须提供 webhook_url")
            payload_json = json.dumps({"type": "ops_report", "report": report}, ensure_ascii=False)
            webhook_result = send_webhook.invoke(
                {
                    "url": target,
                    "payload_json": payload_json,
                }
            )

        return {"success": True, "report": report, "webhook_result": webhook_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
