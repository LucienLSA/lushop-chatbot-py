# src/tools/order_tools.py

"""
订单相关工具

连接 lushop-kratos Order Service
"""

import json

from langchain.tools import tool

from src.utils.grpc_client import get_order_client, order_pb2


def format_order_response(response) -> str:
    if hasattr(response, "data"):
        orders = []
        for item in getattr(response, "data", []) or []:
            orders.append(
                {
                    "id": getattr(item, "id", None),
                    "user_id": getattr(item, "userId", None),
                    "status": getattr(item, "status", None),
                    "order_sn": getattr(item, "orderSn", ""),
                    "total": getattr(item, "total", None),
                }
            )
        return json.dumps({"total": getattr(response, "total", len(orders)), "orders": orders}, ensure_ascii=False)

    if hasattr(response, "orderInfo"):
        info = getattr(response, "orderInfo", None)
        goods_items = []
        for g in getattr(response, "goods", []) or []:
            goods_items.append(
                {
                    "goods_id": getattr(g, "goodsId", None),
                    "goods_name": getattr(g, "goodsName", ""),
                    "goods_price": getattr(g, "goodsPrice", None),
                    "nums": getattr(g, "nums", None),
                }
            )
        return json.dumps(
            {
                "id": getattr(info, "id", None),
                "user_id": getattr(info, "userId", None),
                "status": getattr(info, "status", None),
                "order_sn": getattr(info, "orderSn", ""),
                "total": getattr(info, "total", None),
                "goods": goods_items,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "id": getattr(response, "id", None),
            "user_id": getattr(response, "userId", None),
            "status": getattr(response, "status", None),
            "order_sn": getattr(response, "orderSn", ""),
        },
        ensure_ascii=False,
    )

@tool
def query_order(user_id: int, order_id: int = None) -> str:
    """
    查询用户订单
    
    Args:
        user_id: 用户 ID
        order_id: 订单 ID（可选，不传则查询所有订单）
    
    Returns:
        订单信息 JSON 字符串
    """
    client = get_order_client()
    try:
        if order_id:
            response = client.OrderDetail(order_pb2.OrderRequest(id=order_id, userId=user_id))
        else:
            response = client.OrderList(order_pb2.OrderFilterRequest(userId=user_id, pages=1, pagePerNums=20))
        return format_order_response(response)
    except Exception as e:
        return json.dumps({"error": f"query_order failed: {e}", "user_id": user_id, "order_id": order_id}, ensure_ascii=False)


@tool
def cancel_order(order_id: int, user_id: int, reason: str = "") -> str:
    """
    取消订单
    
    Args:
        order_id: 订单 ID
        user_id: 用户 ID
        reason: 取消原因
    
    Returns:
        操作结果
    """
    client = get_order_client()
    try:
        client.UpdateOrderStatus(
            order_pb2.OrderStatus(
                id=order_id,
                status="TRADE_CLOSED",
            )
        )
        msg = "订单取消成功"
        if reason:
            msg = f"订单取消成功，原因：{reason}"
        return msg
    except Exception as e:
        return f"取消失败: {e}"