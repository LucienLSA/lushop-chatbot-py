"""
运营分析工具
"""

import json
import os
from datetime import datetime
from typing import Any

import dotenv
from langchain.tools import tool

dotenv.load_dotenv()


def _mysql_config() -> dict[str, Any]:
    db = os.getenv("MYSQL_DATABASE", "").strip() or os.getenv("MYSQL_DB", "").strip() or "lushop"
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": db,
    }


def _query_one(cur, sql: str, args: tuple[Any, ...] = ()) -> float:
    try:
        cur.execute(sql, args)
        row = cur.fetchone()
        if not row:
            return 0.0
        if isinstance(row, dict):
            return float(next(iter(row.values())) or 0)
        return float(row[0] or 0)
    except Exception:
        return 0.0


def _identifier(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"unsafe identifier: {name}")
    return f"`{name}`"


def _pick_existing_table(cur, candidates: list[str]) -> str | None:
    for table in candidates:
        cur.execute(
            "SELECT COUNT(1) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s",
            (table,),
        )
        row = cur.fetchone()
        exists = int(next(iter(row.values()))) if isinstance(row, dict) else int(row[0])
        if exists > 0:
            return table
    return None


def _pick_database_with_order_table(conn, preferred: list[str]) -> tuple[str | None, str | None]:
    order_table_candidates = ["order_info", "orders", "order"]
    with conn.cursor() as cur:
        db_candidates = [d for d in preferred if d]
        if not db_candidates:
            cur.execute("SHOW DATABASES")
            rows = cur.fetchall()
            all_dbs = [next(iter(r.values())) if isinstance(r, dict) else r[0] for r in rows]
            db_candidates = [
                d for d in all_dbs if d not in {"information_schema", "mysql", "performance_schema", "sys"}
            ]

        for db in db_candidates:
            for table in order_table_candidates:
                cur.execute(
                    "SELECT COUNT(1) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                    (db, table),
                )
                row = cur.fetchone()
                exists = int(next(iter(row.values()))) if isinstance(row, dict) else int(row[0])
                if exists > 0:
                    return db, table
    return None, None


def _pick_existing_column(cur, table: str, candidates: list[str]) -> str | None:
    for col in candidates:
        cur.execute(
            "SELECT COUNT(1) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
            (table, col),
        )
        row = cur.fetchone()
        exists = int(next(iter(row.values()))) if isinstance(row, dict) else int(row[0])
        if exists > 0:
            return col
    return None


def _collect_ops_metrics(days: int = 30) -> dict[str, Any]:
    cfg = _mysql_config()
    try:
        import pymysql
    except Exception as exc:
        return {
            "source": "fallback",
            "error": f"pymysql unavailable: {exc}",
            "metrics": {
                "days": days,
                "order_count": 0,
                "paid_order_count": 0,
                "active_user_count": 0,
                "gmv": 0,
            },
        }

    conn = None
    try:
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
        )

        preferred_dbs = [cfg["database"]]
        extra_dbs = [x.strip() for x in os.getenv("MYSQL_DATABASES", "").split(",") if x.strip()]
        preferred_dbs.extend(extra_dbs)
        target_db, _ = _pick_database_with_order_table(conn, preferred_dbs)
        if not target_db:
            return {
                "source": "fallback",
                "error": "mysql query failed: no order table found in available databases",
                "metrics": {
                    "days": days,
                    "order_count": 0,
                    "paid_order_count": 0,
                    "active_user_count": 0,
                    "gmv": 0,
                },
            }

        with conn.cursor() as cur:
            cur.execute(f"USE {_identifier(target_db)}")

        with conn.cursor() as cur:
            table = _pick_existing_table(cur, ["order_info", "orders", "order"])
            if not table:
                return {
                    "source": "fallback",
                    "error": "mysql query failed: no order table found (order_info/orders/order)",
                    "metrics": {
                        "days": days,
                        "order_count": 0,
                        "paid_order_count": 0,
                        "active_user_count": 0,
                        "gmv": 0,
                    },
                }

            time_col = _pick_existing_column(cur, table, ["add_time", "created_at", "create_time", "pay_time"])
            user_col = _pick_existing_column(cur, table, ["user_id", "uid", "member_id"])
            pay_col = _pick_existing_column(cur, table, ["pay_status", "paid", "status", "order_status", "trade_status"])
            amount_col = _pick_existing_column(cur, table, ["order_mount", "total_amount", "pay_amount", "total", "amount"])

            t = _identifier(table)
            where_time = ""
            args: tuple[Any, ...] = ()
            if time_col:
                where_time = f" WHERE {_identifier(time_col)} >= NOW() - INTERVAL %s DAY"
                args = (days,)

            order_count = int(_query_one(cur, f"SELECT COUNT(1) FROM {t}{where_time}", args))

            paid_where = where_time
            paid_args = args
            if pay_col:
                cond = (
                    f"({_identifier(pay_col)} = 1 "
                    f"OR LOWER(CAST({_identifier(pay_col)} AS CHAR)) IN ('paid','success','completed','trade_success'))"
                )
                if paid_where:
                    paid_where = paid_where + f" AND {cond}"
                else:
                    paid_where = f" WHERE {cond}"

            paid_order_count = int(_query_one(cur, f"SELECT COUNT(1) FROM {t}{paid_where}", paid_args))

            if user_col:
                active_user_count = int(
                    _query_one(cur, f"SELECT COUNT(DISTINCT {_identifier(user_col)}) FROM {t}{where_time}", args)
                )
            else:
                active_user_count = 0

            if amount_col:
                gmv = _query_one(cur, f"SELECT COALESCE(SUM({_identifier(amount_col)}),0) FROM {t}{paid_where}", paid_args)
            else:
                gmv = 0.0

        conversion = round((paid_order_count / order_count) * 100, 2) if order_count else 0
        arpu = round(gmv / active_user_count, 2) if active_user_count else 0
        return {
            "source": "mysql",
            "metrics": {
                "database": target_db,
                "days": days,
                "order_count": order_count,
                "paid_order_count": paid_order_count,
                "active_user_count": active_user_count,
                "gmv": round(float(gmv), 2),
                "pay_conversion_pct": conversion,
                "arpu": arpu,
            },
        }
    except Exception as exc:
        return {
            "source": "fallback",
            "error": f"mysql query failed: {exc}",
            "metrics": {
                "days": days,
                "order_count": 0,
                "paid_order_count": 0,
                "active_user_count": 0,
                "gmv": 0,
                "pay_conversion_pct": 0,
                "arpu": 0,
            },
        }
    finally:
        if conn is not None:
            conn.close()


@tool
def aggregate_sales_and_user_metrics(days: int = 30) -> str:
    """自动汇总商品销量/订单转化/活跃用户等运营数据。"""
    d = max(1, min(int(days), 365))
    return json.dumps(_collect_ops_metrics(d), ensure_ascii=False)


@tool
def analyze_behavior(user_info: str, orders: str, report_type: str = "comprehensive") -> str:
    """基于用户与订单信息生成行为分析摘要。"""
    try:
        u = json.loads(user_info) if isinstance(user_info, str) else user_info
    except Exception:
        u = {"raw_user_info": str(user_info)}

    try:
        o = json.loads(orders) if isinstance(orders, str) else orders
    except Exception:
        o = {"raw_orders": str(orders)}

    order_list = o.get("orders", []) if isinstance(o, dict) else []
    total_orders = len(order_list)

    ops = _collect_ops_metrics(30)
    return json.dumps(
        {
            "report_type": report_type,
            "user_id": u.get("id"),
            "total_orders": total_orders,
            "ops_metrics": ops.get("metrics", {}),
            "insight": "用户有持续消费行为，建议结合最近浏览与复购商品做个性化推荐。",
        },
        ensure_ascii=False,
    )


@tool
def generate_report(user_id: int, report_type: str, behavior_summary: str) -> str:
    """将分析结果整理成 Markdown 报告。"""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"# 用户分析报告\n\n"
        f"- 用户ID: {user_id}\n"
        f"- 报告类型: {report_type}\n"
        f"- 生成时间: {now}\n\n"
        f"## 核心结论\n\n{behavior_summary}\n"
    )


@tool
def generate_ops_report(days: int = 30) -> str:
    """生成智能运营分析报告（销量、活跃、转化）。"""
    payload = _collect_ops_metrics(max(1, min(int(days), 365)))
    m = payload.get("metrics", {})
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        "# 智能运营分析报告\n\n"
        f"- 时间窗口: 最近 {m.get('days', days)} 天\n"
        f"- 数据源: {payload.get('source', 'unknown')}\n"
        f"- 生成时间: {now}\n\n"
        "## 指标汇总\n\n"
        f"- 订单总量: {m.get('order_count', 0)}\n"
        f"- 支付订单量: {m.get('paid_order_count', 0)}\n"
        f"- 活跃用户数: {m.get('active_user_count', 0)}\n"
        f"- GMV: {m.get('gmv', 0)}\n"
        f"- 支付转化率: {m.get('pay_conversion_pct', 0)}%\n"
        f"- ARPU: {m.get('arpu', 0)}\n\n"
        "## 优化建议\n\n"
        "1. 对高浏览低转化商品做价格与详情页 A/B 测试。\n"
        "2. 对高复购用户分群做精准推荐与优惠触达。\n"
        "3. 对低库存高销量商品设置补货预警。\n"
    )
