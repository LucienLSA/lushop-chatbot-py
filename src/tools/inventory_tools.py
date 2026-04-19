"""
库存相关工具
"""

import json

from langchain.tools import tool

from src.utils.grpc_client import get_inventory_client, inventory_pb2


@tool
def check_stock(goods_id: int) -> str:
    """查询商品库存。"""
    try:
        client = get_inventory_client()
        resp = client.InvDetail(inventory_pb2.GoodsInvInfo(goodsId=goods_id))
        stock = getattr(resp, "num", None)
        return json.dumps({"goods_id": goods_id, "stock": stock}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"check_stock failed: {e}", "goods_id": goods_id}, ensure_ascii=False)
