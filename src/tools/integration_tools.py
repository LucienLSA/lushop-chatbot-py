"""Third-party integration tools."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from langchain.tools import tool


@tool
def send_webhook(url: str, payload_json: str) -> str:
    """向第三方 webhook 发送 JSON 数据。"""
    try:
        payload = json.loads(payload_json) if payload_json else {}
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"invalid payload_json: {exc}"}, ensure_ascii=False)

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return json.dumps({"ok": True, "status": resp.status, "body": body[:1000]}, ensure_ascii=False)
    except urllib.error.HTTPError as exc:
        return json.dumps({"ok": False, "status": exc.code, "error": str(exc)}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
