# -*- coding: utf-8 -*-
"""
AfterGlow-A 最小原型 · 恢复后行为验证（P5）

⚠ 重要边界：
  这里验证的是【工程一致性】——取回的是不是写进去的那些。
  这【不是】C1/C2/C3 任何一级的科学结果。
  （凌翼裁定 §三 明令：不得将工程原型测试冒充 C1/C2/C3 正式结果）
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from afcore import MATCH_KINDS, SchemaError


def classify_match(retrieved: Iterable[str],
                   expected: Optional[Iterable[str]],
                   ran: bool = True) -> Tuple[str, Dict[str, Any]]:
    """把取回集与期望集分类为五值之一。"""
    if not ran or expected is None:
        return "not_run", {
            "retrieved": sorted(set(retrieved)),
            "expected": None,
            "note": "未执行或未给期望集 ⇒ not_run，不得读成通过",
        }

    r: Set[str] = set(retrieved)
    e: Set[str] = set(expected)

    if r == e:
        kind = "exact"
    elif r > e:
        kind = "superset"
    elif r < e:
        kind = "subset"
    elif not (r & e):
        kind = "disjoint"
    else:
        # 部分交集：既不超也不子。本原型不把它塞进四类里。
        # 诚实做法：单独报出来，不假装它属于某一类。
        kind = "partial_overlap"

    detail = {
        "retrieved": sorted(r),
        "expected": sorted(e),
        "missing": sorted(e - r),
        "extra": sorted(r - e),
        "intersection": sorted(r & e),
    }
    return kind, detail


def verify_recovery(store, query_ref: str,
                    selector, expected_ids: Optional[Iterable[str]],
                    ran: bool = True) -> Dict[str, Any]:
    """执行一次恢复验证并返回可记录的报告。"""
    retrieved_ids: List[str] = []
    if ran:
        for rec in store.sqlite_rows():
            if selector(rec):
                retrieved_ids.append(rec["record_id"])

    kind, detail = classify_match(retrieved_ids, expected_ids, ran=ran)

    if kind not in MATCH_KINDS and kind != "partial_overlap":
        raise SchemaError("match_kind=%r 不在闭集内" % (kind,))

    return {
        "recovery_id": "rec-" + query_ref,
        "query_ref": query_ref,
        "retrieved_ids": detail["retrieved"],
        "expected_ids": detail["expected"],
        "match_kind": kind,
        "missing": detail.get("missing", []),
        "extra": detail.get("extra", []),
        "engineering_only": True,
        "is_scientific_result": False,
    }


def check_unknown_preserved(store, record_id: str,
                            field_name: str) -> Dict[str, Any]:
    """检查某个字段是否仍是 unknown，而不是被缺省值填满。"""
    rec = store.get(record_id)
    if rec is None:
        return {"record_id": record_id, "found": False}
    val = rec.get(field_name)
    return {
        "record_id": record_id,
        "field": field_name,
        "value": val,
        "is_unknown": val == "unknown",
        "found": True,
    }
