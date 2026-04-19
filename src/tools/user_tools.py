"""
用户相关工具
"""

import json

from langchain.tools import tool

from src.tools.order_tools import query_order
from src.utils.grpc_client import get_user_client, user_pb2


@tool
def get_user_info(user_id: int) -> str:
    """获取用户基本信息。"""
    try:
        client = get_user_client()
        resp = client.GetUserById(user_pb2.IdRequest(id=user_id))
        data = {
            "id": getattr(resp, "id", user_id),
            "nickname": getattr(resp, "nickName", ""),
            "gender": getattr(resp, "gender", ""),
            "mobile": getattr(resp, "mobile", ""),
            "role": getattr(resp, "role", None),
        }
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"id": user_id, "warning": f"get_user_info fallback: {e}"}, ensure_ascii=False)


@tool
def get_user_orders(user_id: int) -> str:
    """获取用户订单历史。"""
    return query_order.invoke({"user_id": user_id})
