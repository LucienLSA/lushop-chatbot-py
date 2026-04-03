"""
商品相关工具

连接 lushop-kratos Goods Service
"""

import grpc
from langchain.tools import tool
from src.util.grpc_client import get_goods_client

@tool
def search_goods(keyword: str, category_id: int = None, page: int = 1, page_size: int = 10) -> str:
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
    response = client.SearchGoods(goods_pb2.GoodsFilterRequest(
        keyword=keyword,
        categoryId=category_id,
        page=page,
        pageSize=page_size,
    ))
    return format_goods_response(response)

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
    response = client.GetGoodsDetail(goods_pb2.GoodsInfoRequest(
        id=goods_id,
    ))
    return format_goods_detail(response)