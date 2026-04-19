"""
商品相关工具

连接 lushop-kratos Goods Service
"""

import json
import os
from langchain.tools import tool

from src.utils.grpc_client import get_goods_client, goods_pb2


def _goods_to_dict(item) -> dict:
    return {
        "id": getattr(item, "id", None),
        "name": getattr(item, "name", ""),
        "shop_price": getattr(item, "shopPrice", None),
        "market_price": getattr(item, "marketPrice", None),
        "brief": getattr(item, "goodsBrief", ""),
    }


def format_goods_response(response) -> str:
    items = []
    for item in getattr(response, "data", []) or []:
        items.append(_goods_to_dict(item))
    return json.dumps({"total": getattr(response, "total", len(items)), "items": items}, ensure_ascii=False)


def format_goods_detail(response) -> str:
    return json.dumps(_goods_to_dict(response), ensure_ascii=False)


def _call_goods_search(client, req, prefer_es: bool):
    # Prefer ES retrieval when gateway provides GoodsListES.
    if prefer_es and hasattr(client, "GoodsListES"):
        return client.GoodsListES(req)
    return client.GoodsList(req)

@tool
def search_goods(keyword: str, category_id: int = None, page: int = 1, page_size: int = 10, prefer_es: bool = True) -> str:
    """
    搜索商品
    
    Args:
        keyword: 搜索关键词
        category_id: 分类 ID（可选）
        page: 页码
        page_size: 每页数量
    
    Returns:
        商品列表 JSON 字符串
    """
    client = get_goods_client()
    req = goods_pb2.GoodsFilterRequest(
        keyWords=keyword,
        pages=page,
        pagePerNums=page_size,
    )
    if category_id is not None:
        req.topCategory = category_id

    use_es = prefer_es and os.getenv("GOODS_SEARCH_BACKEND", "es").lower() in {"es", "hybrid"}
    try:
        response = _call_goods_search(client, req, use_es)
        return format_goods_response(response)
    except Exception as e:
        return json.dumps({"error": f"search_goods failed: {e}", "keyword": keyword}, ensure_ascii=False)


@tool
def search_goods_es(keyword: str, page: int = 1, page_size: int = 10) -> str:
    """使用 ES 商品库检索商品（若网关支持 GoodsListES）。"""
    client = get_goods_client()
    req = goods_pb2.GoodsFilterRequest(keyWords=keyword, pages=page, pagePerNums=page_size)
    try:
        if not hasattr(client, "GoodsListES"):
            return json.dumps({"error": "GoodsListES not supported by current goods service"}, ensure_ascii=False)
        response = client.GoodsListES(req)
        return format_goods_response(response)
    except Exception as e:
        return json.dumps({"error": f"search_goods_es failed: {e}", "keyword": keyword}, ensure_ascii=False)

@tool
def get_goods_detail(goods_id: int) -> str:
    """
    获取商品详情
    
    Args:
        goods_id: 商品 ID
    
    Returns:
        商品详情 JSON 字符串
    """
    client = get_goods_client()
    try:
        response = client.GetGoodsDetail(goods_pb2.GoodInfoRequest(id=goods_id))
        return format_goods_detail(response)
    except Exception as e:
        return json.dumps({"error": f"get_goods_detail failed: {e}", "goods_id": goods_id}, ensure_ascii=False)