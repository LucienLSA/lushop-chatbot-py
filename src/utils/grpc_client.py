# src/utils/grpc_client.py

"""
gRPC 客户端管理

连接 lushop-kratos 微服务
"""

import os
import grpc
from pathlib import Path
from types import SimpleNamespace

import sys
# 导入本项目内生成的 proto 文件
_PROTO_ROOT = Path(__file__).resolve().parents[1] / "proto"
if str(_PROTO_ROOT) not in sys.path:
    sys.path.append(str(_PROTO_ROOT))


class _DummyMessage:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


try:
    from api.service.goods.v1 import goods_pb2, goods_pb2_grpc
    from api.service.order.v1 import order_pb2, order_pb2_grpc
    from api.service.user.v1 import user_pb2, user_pb2_grpc
    from api.service.inventory.v1 import inventory_pb2, inventory_pb2_grpc
except Exception:
    goods_pb2 = SimpleNamespace(GoodsFilterRequest=_DummyMessage, GoodInfoRequest=_DummyMessage)
    order_pb2 = SimpleNamespace(OrderRequest=_DummyMessage, OrderFilterRequest=_DummyMessage, OrderStatus=_DummyMessage)
    user_pb2 = SimpleNamespace(IdRequest=_DummyMessage)
    inventory_pb2 = SimpleNamespace(GoodsInvInfo=_DummyMessage)
    goods_pb2_grpc = None
    order_pb2_grpc = None
    user_pb2_grpc = None
    inventory_pb2_grpc = None

# 服务地址配置
SERVICE_ENDPOINTS = {
    'goods': os.getenv('GOODS_SERVICE_ADDR', 'localhost:50052'),
    'order': os.getenv('ORDER_SERVICE_ADDR', 'localhost:50053'),
    'user': os.getenv('USER_SERVICE_ADDR', 'localhost:50051'),
    'inventory': os.getenv('INVENTORY_SERVICE_ADDR', 'localhost:50054'),
}

# 客户端缓存
_clients = {}


def get_goods_client():
    """获取商品服务客户端"""
    if goods_pb2_grpc is None:
        raise RuntimeError("goods proto modules unavailable; check lushop-kratos python proto path")
    if 'goods' not in _clients:
        channel = grpc.insecure_channel(SERVICE_ENDPOINTS['goods'])
        _clients['goods'] = goods_pb2_grpc.GoodsStub(channel)
    return _clients['goods']


def get_order_client():
    """获取订单服务客户端"""
    if order_pb2_grpc is None:
        raise RuntimeError("order proto modules unavailable; check lushop-kratos python proto path")
    if 'order' not in _clients:
        channel = grpc.insecure_channel(SERVICE_ENDPOINTS['order'])
        _clients['order'] = order_pb2_grpc.OrderStub(channel)
    return _clients['order']


def get_user_client():
    """获取用户服务客户端"""
    if user_pb2_grpc is None:
        raise RuntimeError("user proto modules unavailable; check lushop-kratos python proto path")
    if 'user' not in _clients:
        channel = grpc.insecure_channel(SERVICE_ENDPOINTS['user'])
        _clients['user'] = user_pb2_grpc.UserStub(channel)
    return _clients['user']


def get_inventory_client():
    """获取库存服务客户端"""
    if inventory_pb2_grpc is None:
        raise RuntimeError("inventory proto modules unavailable; check lushop-kratos python proto path")
    if 'inventory' not in _clients:
        channel = grpc.insecure_channel(SERVICE_ENDPOINTS['inventory'])
        _clients['inventory'] = inventory_pb2_grpc.InventoryStub(channel)
    return _clients['inventory']
