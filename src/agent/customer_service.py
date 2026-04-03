"""
智能客服 Agent

功能：
- 商品咨询与推荐
- 订单状态查询
- 售后问题处理
- 常见问题解答
"""

from langchain.agents import create_agent

from src.tools.goods_tools import search_goods, get_goods_detail
from src.tools.order_tools import query_order, cancel_order
from src.tools.inventory_tools import check_stock

customer_service_prompt = """你是 lushop 电商平台的智能客服助手。

你的职责是：
1. 解答用户关于商品的问题
2. 帮助用户查询订单状态
3. 处理售后问题
4. 提供购物建议

服务原则：
- 友好、专业、高效
- 准确理解用户需求
- 提供具体可行的解决方案
- 必要时引导用户联系人工客服

常见场景：
- 商品咨询：介绍商品特点、规格、价格
- 订单查询：查询订单状态、物流信息
- 售后处理：退换货、退款、投诉
- 账户问题：登录、注册、密码重置
"""

customer_service_agent = create_agent(
    model=configurable_model,
    tools=[
        search_goods,           # 搜索商品
        get_goods_detail,       # 商品详情
        query_order,            # 查询订单
        cancel_order,           # 取消订单
        check_stock,            # 库存查询
    ],
    system_prompt=customer_service_prompt,
)