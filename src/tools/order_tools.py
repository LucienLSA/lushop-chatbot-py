# src/tools/order_tools.py

"""
订单相关工具

连接 lushop-kratos Order Service
"""

from langchain.tools import tool
from src.utils.grpc_client import get_order_client

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
    if order_id:
        response = client.GetOrder(order_pb2.OrderRequest(id=order_id))
    else:
        response = client.GetOrderList(order_pb2.OrderFilterRequest(userId=user_id))
    return format_order_response(response)


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
    response = client.CancelOrder(order_pb2.CancelOrderRequest(
        orderId=order_id,
        userId=user_id,
        reason=reason,
    ))
    return "订单取消成功" if response.success else f"取消失败: {response.message}"