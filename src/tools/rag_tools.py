"""
RAG retrieval tools for ecommerce domain knowledge.

This module provides a lightweight hybrid retriever:
- Optional embedding retrieval (if langchain_openai + API key available)
- Deterministic keyword fallback (always available)
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain.tools import tool


@dataclass
class _Chunk:
    source: str
    text: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _prompt_dir() -> Path:
    return _project_root() / "src" / "prompts"


def _ensure_default_kb() -> None:
    kb = _prompt_dir() / "ecommerce_kb.md"
    if kb.exists():
        return
    kb.parent.mkdir(parents=True, exist_ok=True)
    kb.write_text(
        """
# 电商客服知识库

## 订单与售后
- 订单取消：通常仅在未发货状态可直接取消。
- 退款：退款时效受支付渠道影响，通常 1-7 个工作日。
- 物流异常：建议先核验运单号和收货地址，再提交人工工单。

## 商品与库存
- 推荐策略：优先推荐有库存、评分高、近 30 天销量高的商品。
- 库存不足时：给出同品类替代商品，并明确到货时间。
- 价格说明：展示促销价与市场价时，需标注时间与活动条件。

## 运营分析
- 核心指标：GMV、订单量、支付转化率、复购率、客单价。
- 用户行为：浏览-加购-下单漏斗、品类偏好、流失风险。
- 报告建议：给出可执行动作（活动策略、库存策略、推荐策略）。
""".strip(),
        encoding="utf-8",
    )


def _load_docs() -> list[_Chunk]:
    _ensure_default_kb()
    chunks: list[_Chunk] = []
    for path in sorted(_prompt_dir().glob("**/*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        # Simple paragraph chunking.
        for part in re.split(r"\n\s*\n", text):
            part = part.strip()
            if len(part) < 20:
                continue
            chunks.append(_Chunk(source=str(path.relative_to(_project_root())), text=part))
    return chunks


def _tokenize(s: str) -> set[str]:
    words = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", s.lower())
    return {w for w in words if len(w) >= 2}


def _keyword_retrieve(query: str, top_k: int, docs: list[_Chunk]) -> list[dict[str, Any]]:
    q = _tokenize(query)
    scored: list[tuple[int, _Chunk]] = []
    for c in docs:
        overlap = len(q & _tokenize(c.text))
        if overlap > 0:
            scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, c in scored[:top_k]:
        out.append({"source": c.source, "score": score, "snippet": c.text[:300]})
    return out


class _EmbeddingRetriever:
    def __init__(self, docs: list[_Chunk]) -> None:
        self._ready = False
        self._vs = None
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return
        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document
        except Exception:
            return

        embeddings = OpenAIEmbeddings(model=os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small"))
        lang_docs = [Document(page_content=d.text, metadata={"source": d.source}) for d in docs]
        self._vs = FAISS.from_documents(lang_docs, embeddings)
        self._ready = True

    def retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        if not self._ready or self._vs is None:
            return []
        docs = self._vs.similarity_search_with_score(query, k=top_k)
        out = []
        for d, score in docs:
            out.append(
                {
                    "source": d.metadata.get("source", "unknown"),
                    "score": float(score),
                    "snippet": d.page_content[:300],
                }
            )
        return out


@lru_cache(maxsize=1)
def _runtime() -> tuple[list[_Chunk], _EmbeddingRetriever]:
    docs = _load_docs()
    return docs, _EmbeddingRetriever(docs)


@tool
def retrieve_knowledge(query: str, top_k: int = 3) -> str:
    """检索电商领域知识库（RAG）。"""
    docs, emb = _runtime()
    k = max(1, min(int(top_k), 8))

    results = emb.retrieve(query, k)
    mode = "embedding"
    if not results:
        results = _keyword_retrieve(query, k, docs)
        mode = "keyword"

    return json.dumps(
        {
            "query": query,
            "mode": mode,
            "hits": results,
        },
        ensure_ascii=False,
    )
