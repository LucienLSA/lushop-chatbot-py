"""
用户分析报告 Agent

功能：
- 用户消费行为分析
- 用户画像生成
- 消费趋势预测
- 个性化推荐
"""

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate

from src.tools.user_tools import get_user_info, get_user_orders
from src.tools.analytics_tools import generate_report, analyze_behavior

user_analyst_prompt = """你是 lushop 电商平台的用户分析专家。

你的职责是：
1. 分析用户消费行为和偏好
2. 生成用户画像报告
3. 提供个性化商品推荐
4. 预测用户消费趋势

分析维度：
- 消费金额分布
- 购买频次统计
- 品类偏好分析
- 活跃度评估
- 流失风险预警

输出格式：
使用 Markdown 格式，包含图表描述和数据洞察。
"""

user_analyst = create_agent(
    model=configurable_model,
    tools=[
        get_user_info,          # 获取用户基本信息
        get_user_orders,        # 获取用户订单历史
        analyze_behavior,       # 行为分析
        generate_report,        # 生成报告
    ],
    system_prompt=user_analyst_prompt,
)