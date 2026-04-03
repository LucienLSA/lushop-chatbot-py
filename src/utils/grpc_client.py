# src/utils/grpc_client.py

"""
gRPC 客户端管理

连接 lushop-kratos 微服务
"""

import grpc
from typing import Optional

# 导入生成的 proto 文件
import sys
sys.path.append('/home/ubuntu/lushop-kratos')

from api.service.goods.v1 import goods_pb2, goods_pb2_grpc
from api.service.order.v1 import order_pb2, order_pb2_grpc
from api.service.user.v1 import user_pb2, user_pb2_grpc
from api.service.inventory.v1 import inventory_pb2, inventory_pb2_grpc

# 服务地址配置
SERVICE_ENDPOINTS = {
    'goods': 'localhost:50051',
    'order': 'localhost:50052',
    'user': 'localhost:50053',
    'inventory': 'localhost:50054',
}

# 客户端缓存
_clients = {}


def get_goods_client() -> goods_pb2_grpc.GoodsServiceStub:
    """获取商品服务客户端"""
    if 'goods' not in _clients:
        channel = grpc.insecure_channel(SERVICE_ENDPOINTS['goods'])
        _clients['goods'] = goods_pb2_grpc.GoodsServiceStub(channel)
    return _clients['goods']


def get_order_client() -> order_pb2_grpc.OrderServiceStub:
    """获取订单服务客户端"""
    if 'order' not in _clients:
        channel = grpc.insecure_channel(SERVICE_ENDPOINTS['order'])
        _clients['order'] = order_pb2_grpc.OrderServiceStub(channel)
    return _clients['order']


def get_user_client() -> user_pb2_grpc.UserServiceStub:
    """获取用户服务客户端"""
    if 'user' not in _clients:
        channel = grpc.insecure_channel(SERVICE_ENDPOINTS['user'])
        _clients['user'] = user_pb2_grpc.UserServiceStub(channel)
    return _clients['user']