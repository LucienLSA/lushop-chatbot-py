"""
Agent runtime helpers.

Provide a remote-first execution path with a deterministic local fallback so the
API can keep working even when cloud model access is unavailable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from src.agent.config import HAS_REMOTE_MODEL
from src.agent.customer_service import customer_service_agent
from src.agent.user_analyst import user_analyst
from src.tools.analytics_tools import analyze_behavior, generate_report
from src.tools.goods_tools import get_goods_detail, search_goods
from src.tools.inventory_tools import check_stock
from src.tools.order_tools import cancel_order, query_order
from src.tools.rag_tools import retrieve_knowledge
from src.tools.user_tools import get_user_info, get_user_orders

logger = logging.getLogger(__name__)


def _normalize_response(result: Any) -> str:
    if isinstance(result, str):
        return result

    content = getattr(result, "content", None)
    if isinstance(content, str) and content.strip():
        return content

    if isinstance(result, dict):
        output = result.get("output")
        if isinstance(output, str) and output.strip():
            return output

        messages = result.get("messages") or []
        if messages:
            last_message = messages[-1]
            last_content = getattr(last_message, "content", None)
            if isinstance(last_content, str) and last_content.strip():
                return last_content
            if isinstance(last_message, dict):
                dict_content = last_message.get("content")
                if isinstance(dict_content, str) and dict_content.strip():
                    return dict_content

    return str(result)


def _extract_first_int(text: str) -> int | None:
    match = re.search(r"(?<!\d)(\d+)(?!\d)", text)
    if not match:
        return None
    return int(match.group(1))


def _keyword_for_search(text: str) -> str:
    cleaned = re.sub(r"[，。！？,.;:：]", " ", text)
    cleaned = re.sub(r"\b(推荐|搜索|查找|找|看看|商品|帮我|适合|入门|高端|热门|有哪些|哪款|哪种|一下|关于|的)\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text.strip()


def _safe_json_loads(s: str) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return {"raw": s}


def _build_customer_plan(text: str) -> list[str]:
    plan: list[str] = ["knowledge"]
    if any(keyword in text for keyword in ("库存", "库存量", "余量")):
        plan.append("stock")
    if any(keyword in text for keyword in ("取消订单", "撤销订单", "取消")):
        plan.append("cancel_order")
    elif "订单" in text:
        plan.append("query_order")
    if any(keyword in text for keyword in ("详情", "介绍", "信息", "推荐", "搜索", "找", "商品")):
        plan.append("goods")
    if len(plan) == 1:
        plan.append("suggest")
    return plan


def _local_customer_service(message: str, user_id: int) -> str:
    text = message.strip()
    plan = _build_customer_plan(text)
    entity_id = _extract_first_int(text)
    results: dict[str, Any] = {"plan": plan, "user_id": user_id}

    if "knowledge" in plan:
        results["knowledge"] = _safe_json_loads(retrieve_knowledge.invoke({"query": text, "top_k": 3}))

    if "stock" in plan:
        if entity_id is None:
            results["stock"] = {"error": "请提供商品ID以查询库存"}
        else:
            results["stock"] = _safe_json_loads(check_stock.invoke({"goods_id": entity_id}))

    if "cancel_order" in plan:
        if entity_id is None:
            results["cancel_order"] = {"error": "请提供订单ID以取消订单"}
        else:
            results["cancel_order"] = cancel_order.invoke(
                {"order_id": entity_id, "user_id": user_id, "reason": "用户主动取消"}
            )

    if "query_order" in plan:
        payload = {"user_id": user_id}
        if entity_id is not None:
            payload["order_id"] = entity_id
        results["orders"] = _safe_json_loads(query_order.invoke(payload))

    if "goods" in plan:
        if entity_id is not None and any(keyword in text for keyword in ("详情", "介绍", "信息", "查看")):
            results["goods_detail"] = _safe_json_loads(get_goods_detail.invoke({"goods_id": entity_id}))
        else:
            keyword = _keyword_for_search(text)
            results["goods_search"] = _safe_json_loads(search_goods.invoke({"keyword": keyword, "page": 1, "page_size": 5}))

    if "suggest" in plan:
        results["suggestion"] = "你可以试试问我商品推荐、订单查询、库存查询或取消订单。"

    return json.dumps(results, ensure_ascii=False)


def _local_user_analysis(user_id: int, report_type: str) -> str:
    # 本地编排链路：用户信息 + 历史订单 + RAG 业务知识，再生成行为摘要与报告
    user_info = get_user_info.invoke({"user_id": user_id})
    orders = get_user_orders.invoke({"user_id": user_id})
    knowledge = retrieve_knowledge.invoke({"query": f"用户分析 {report_type} 模板", "top_k": 3})
    behavior = analyze_behavior.invoke(
        {
            "user_info": user_info,
            "orders": orders,
            "report_type": report_type,
        }
    )
    report = generate_report.invoke(
        {
            "user_id": user_id,
            "report_type": report_type,
            "behavior_summary": f"{behavior}\n\nRAG参考：{knowledge}",
        }
    )
    return report


async def run_customer_service(message: str, user_id: int) -> str:
    if HAS_REMOTE_MODEL:
        try:
            result = await customer_service_agent.ainvoke(
                {
                    "messages": [{"role": "user", "content": message}],
                    "user_id": user_id,
                }
            )
            return _normalize_response(result)
        except Exception as exc:  # pragma: no cover - network/provider failure path
            logger.warning("Remote customer service agent failed; falling back locally: %s", exc)

    return await asyncio.to_thread(_local_customer_service, message, user_id)


async def run_user_analysis(user_id: int, report_type: str) -> str:
    if HAS_REMOTE_MODEL:
        try:
            result = await user_analyst.ainvoke(
                {
                    "user_id": user_id,
                    "report_type": report_type,
                }
            )
            return _normalize_response(result)
        except Exception as exc:  # pragma: no cover - network/provider failure path
            logger.warning("Remote user analyst failed; falling back locally: %s", exc)

    return await asyncio.to_thread(_local_user_analysis, user_id, report_type)

