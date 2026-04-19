# Lushop Chatbot (Python)

基于 FastAPI + LangChain 的电商助手，已对齐 lushop-kratos 的 gRPC 服务接口。

## 功能

- 智能客服：商品检索、商品详情、订单查询、取消订单、库存查询
- 用户分析：用户信息聚合、订单聚合、行为摘要、报告生成
- RAG 检索：从 `src/prompts` 知识库检索业务上下文（embedding 可选，关键词检索兜底）
- ES 检索：商品搜索支持优先走 Elasticsearch（不可用时回退 gRPC）
- MySQL 运营分析：聚合销量、用户活跃、转化等指标并生成运营报告
- MCP/第三方集成：支持通过 JSON-RPC 调用 MCP 网关与 webhook 推送
- gRPC 对接：goods / order / user / inventory 四个服务

## 项目结构

```txt
src/
  agent/
    config.py
    customer_service.py
    user_analyst.py
  api/
    routes.py
  tools/
    goods_tools.py
    order_tools.py
    inventory_tools.py
    user_tools.py
    analytics_tools.py
  utils/
    grpc_client.py
  proto/
    api/service/**/v1/*_pb2.py
    api/service/**/v1/*_pb2_grpc.py
```

## 依赖与环境

- Python 3.10+
- 建议使用项目内 .venv

安装关键依赖：

```bash
source .venv/bin/activate
pip install fastapi uvicorn langchain grpcio grpcio-tools python-dotenv requests pymysql
```

## 配置

在 .env 中至少配置：

- OPENAI_API_KEY / ANTHROPIC_API_KEY / XAI_API_KEY / GOOGLE_API_KEY（至少一个可用；没有也能启动本地兜底模式）
- GOODS_SERVICE_ADDR（默认 localhost:50052）
- ORDER_SERVICE_ADDR（默认 localhost:50053）
- USER_SERVICE_ADDR（默认 localhost:50051）
- INVENTORY_SERVICE_ADDR（默认 localhost:50054）

建议补充：

- GOODS_SEARCH_BACKEND=es（可切换为 `grpc`）
- ELASTICSEARCH_URL、ELASTICSEARCH_INDEX（启用 ES 检索时）
- MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DATABASE（启用运营聚合时）
- MYSQL_DATABASES（可选，逗号分隔，配置多个候选库供自动探测）
- MCP_HTTP_ENDPOINT（启用 MCP 工具时）
- THIRD_PARTY_WEBHOOK_URL、THIRD_PARTY_WEBHOOK_TOKEN（启用第三方 webhook 时）
- RAG_PROMPTS_DIR（默认 `src/prompts`）

## 启动

```bash
source .venv/bin/activate
uvicorn src.api.routes:app --host 127.0.0.1 --port 8100
```

健康检查：

```bash
curl http://127.0.0.1:8100/health
```

## 接口示例

客服接口：

```bash
curl -X POST http://127.0.0.1:8100/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"推荐一款苹果手机","user_id":1}'
```

分析接口：

```bash
curl -X POST http://127.0.0.1:8100/api/analysis \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"report_type":"comprehensive"}'
```

运营报告接口：

```bash
curl -X POST http://127.0.0.1:8100/api/ops-report \
  -H "Content-Type: application/json" \
  -d '{"days":30}'
```

运营报告 + webhook 推送：

```bash
curl -X POST http://127.0.0.1:8100/api/ops-report \
  -H "Content-Type: application/json" \
  -d '{"days":30,"push_webhook":true,"webhook_url":"https://example.com/webhook"}'
```

## 说明

- 当前仓库已清理 docs assistant 模板遗留代码，保留电商助手主链路。
- 没有云端模型 Key 时，聊天与分析接口会自动切到本地规则/工具兜底。
- 若下游 gRPC 服务未启动，工具会返回结构化错误信息而非进程崩溃。
- ES/MySQL/MCP/Webhook 均为可选增强能力，不可用时会返回可读错误并由 Agent 继续执行其他工具。
