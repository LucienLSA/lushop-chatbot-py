"""
MCP integration tools.

Uses a simple JSON-RPC over HTTP endpoint for MCP-compatible gateways.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from langchain.tools import tool


def _mcp_endpoint() -> str:
    return os.getenv("MCP_HTTP_ENDPOINT", "").strip()


@tool
def call_mcp_tool(method: str, params_json: str = "{}") -> str:
    """调用 MCP 网关工具（JSON-RPC over HTTP）。"""
    endpoint = _mcp_endpoint()
    if not endpoint:
        return json.dumps({"error": "MCP_HTTP_ENDPOINT not configured"}, ensure_ascii=False)

    try:
        params = json.loads(params_json) if params_json else {}
        if not isinstance(params, dict):
            params = {"value": params}
    except Exception as exc:
        return json.dumps({"error": f"invalid params_json: {exc}"}, ensure_ascii=False)

    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": "lushop-mcp-1",
        "method": method,
        "params": params,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    timeout = float(os.getenv("MCP_HTTP_TIMEOUT", "8"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            try:
                return json.dumps(json.loads(body), ensure_ascii=False)
            except Exception:
                return json.dumps({"raw": body}, ensure_ascii=False)
    except urllib.error.HTTPError as exc:
        return json.dumps({"error": f"mcp http error: {exc.code}", "reason": str(exc)}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"mcp call failed: {exc}"}, ensure_ascii=False)
