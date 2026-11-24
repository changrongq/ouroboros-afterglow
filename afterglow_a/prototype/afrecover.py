# -*- coding: utf-8 -*-
"""
AfterGlow-A 最小原型 · 恢复后行为验证（P5）

⚠ 重要边界：
  这里验证的是【工程一致性】——取回的是不是写进去的那些。
  这【不是】C1/C2/C3 任何一级的科学结果。
  （凌翼裁定 §三 明令：不得将工程原型测试冒充 C1/C2/C3 正式结果）

凌翼裁定 2026-11-24 §二：采用 B 方案，实施强制资格门禁。
  match_kind 保持纯集合关系语义，完整性另立维度，且失败必须阻断资格。

凌翼裁定 2026-11-24 §三：not_run 从集合关系枚举移出；
  未执行完整性校验不得默认为通过。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from afcore import MATCH_KINDS, SchemaError


# ---------------------------------------------------------------- 闭集

INTEGRITY_STATUSES = {
    "verified",     # 检查已执行，且通过
    "failed",       # 检查已执行，发现不一致
    "not_checked",  # 检查未执行 —— 不得读作通过
}

INELIGIBLE_REASONS = {
    "integrity_failed",
    "integrity_not_checked",
    "not_run",
    "no_expected_ids",
    "stale_check",
    "registration_not_independent",
}

_YES_NO = {"yes", "no"}


def classify_match(retrieved: Iterable[str],
                   expected: Optional[Iterable[str]],
                   ran: bool = True) -> Tuple[Optional[str], Dict[str, Any]]:
    """把取回集与期望集分类为四种集合关系之一。

    ★ 裁定 §三 + A §1.8 更正二：not_run 不是集合关系。
      未执行 / 未给期望集时返回 match_kind = None（不是字符串 "not_run"），
      并在 detail 里用 ran=False 表达。
      ⇒ 「没有 match_kind」与「match_kind 等于某值」是两件事。
    """
    if not ran or expected is None:
        return None, {
            "retrieved": sorted(set(retrieved)),
            "expected": None,
            "ran": False,
            "note": "未执行或未给期望集 ⇒ 没有 match_kind，不得读成通过",
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
        "ran": True,
    }
    return kind, detail


# ---------------------------------------------------------------- 期望集登记身份
#
# A §1.8（据睫 r2/23 第 ① 问）：没有这一维，exact 分不开两件事：
#   (a) 独立观察者按预登记期望集复算得到的 exact
#   (b) 实现把自己的输出回填成期望集得到的 exact
# ⇒ 同值不同后果，必须可区分。

REGISTRATION_FIELDS = (
    "registered_by",
    "registered_at",
    "registered_rev",
    "independent_of_write",   # "yes" / "no"
    "before_exposure",        # "yes" / "no"
)


def check_registration(reg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """校验期望集登记身份。返回规范化结果，不修改输入。"""
    if reg is None:
        return {
            "present": False,
            "independent": False,
            "problems": ["未提供 expected_ids_registration"],
        }

    problems: List[str] = []
    missing = [k for k in REGISTRATION_FIELDS if k not in reg]
    if missing:
        problems.append("缺少登记字段：%s" % (sorted(missing),))

    for k in ("independent_of_write", "before_exposure"):
        v = reg.get(k)
        if v is not None and v not in _YES_NO:
            problems.append("%s=%r 不在 yes/no 闭集内" % (k, v))

    if not (reg.get("registered_at") or "").strip():
        problems.append("registered_at 为空")

    independent = (
        reg.get("independent_of_write") == "yes"
        and reg.get("before_exposure") == "yes"
        and not problems
    )
    return {
        "present": True,
        "independent": independent,
        "problems": problems,
        "normalized": {k: reg.get(k) for k in REGISTRATION_FIELDS},
    }


# ---------------------------------------------------------------- 完整性检查
#
# 裁定 §二：gate 必须真正消费完整性结果，而不是并列打印。
# 因此本模块【自己执行】链校验，而不是等调用方传真假值 ——
# 传真假值会让「谁校验的、校验了什么范围」无法追。

def check_integrity(store, record_ids: Optional[Iterable[str]] = None
                    ) -> Dict[str, Any]:
    """对指定记录执行链校验，产出完整性结论。

    status : verified / failed / not_checked
    detail : 具体失败或无法判断的原因
    scope  : 检查覆盖了哪些记录、基于哪个快照
    """
    snap = store.snapshot_token() if hasattr(store, "snapshot_token") else None

    if record_ids is None:
        return {
            "status": "not_checked",
            "detail": ["未指定检查范围，不得默认为通过"],
            "scope": {"records": [], "snapshot": snap},
        }

    ids = sorted(set(record_ids))
    if not ids:
        return {
            "status": "not_checked",
            "detail": ["检查范围为空（无取回记录），不得默认为通过"],
            "scope": {"records": [], "snapshot": snap},
        }

    problems: List[str] = []
    checked: List[str] = []
    for rid in ids:
        hist = store.history(rid)
        if not hist:
            problems.append("%s 无历史，无法校验" % rid)
            continue
        ok, msgs = store.verify_chain(rid)
        checked.append(rid)
        if not ok:
            for m in msgs:
                problems.append("%s: %s" % (rid, m))

    status = "failed" if problems else ("verified" if checked else "not_checked")
    return {
        "status": status,
        "detail": problems,
        "scope": {"records": checked, "snapshot": snap},
    }


# ---------------------------------------------------------------- 恢复验证主入口

def verify_recovery(store, query_ref: str,
                    selector: Callable[[Dict[str, Any]], bool],
                    expected_ids: Optional[Iterable[str]],
                    ran: bool = True,
                    *,
                    registration: Optional[Dict[str, Any]] = None,
                    run_integrity_check: bool = True,
                    expected_snapshot: Optional[str] = None,
                    ) -> Dict[str, Any]:
    """执行一次恢复验证，并给出【恢复资格】。

    与旧版差异（凌翼裁定 2026-11-24 §二）：
      · match_kind 不再有 "not_run"；未执行时为 None
      · 新增 integrity_status / integrity_detail / integrity_scope /
        recovery_eligible / ineligible_reasons
      · recovery_eligible 是【当前快照】上的判断，不是历史判断

    ⚠ match_kind 与 integrity_status 是两条独立的轴：
      exact 不覆盖、也不掩盖 integrity_status 的失败。
      反过来说，integrity_status=verified 也不提升来源真实性
      （trusted_chain_anchor 恒为 not_established）。
    """
    # ---- 1. 取回
    retrieved_ids: List[str] = []
    if ran:
        for rec in store.sqlite_rows():
            if selector(rec):
                retrieved_ids.append(rec["record_id"])

    # ---- 2. 集合关系（纯集合语义，不带完整性含义）
    kind, detail = classify_match(retrieved_ids, expected_ids, ran=ran)

    if kind is not None and kind not in MATCH_KINDS and kind != "partial_overlap":
        raise SchemaError("match_kind=%r 不在闭集内" % (kind,))

    # ---- 3. 完整性检查（自己执行，不接收外部真假值）
    if run_integrity_check:
        integ = check_integrity(store, retrieved_ids)
    else:
        snap0 = store.snapshot_token() if hasattr(store, "snapshot_token") else None
        integ = {
            "status": "not_checked",
            "detail": ["调用方显式关闭了完整性检查，不得默认为通过"],
            "scope": {"records": [], "snapshot": snap0},
        }

    # ---- 4. 快照一致性：检查后对象若被替换，旧结论不得沿用
    stale: List[str] = []
    if expected_snapshot is not None and hasattr(store, "snapshot_token"):
        now_tok = store.snapshot_token()
        if now_tok != expected_snapshot:
            stale.append(
                "完整性检查所依据的快照 %s 与当前 %s 不同：旧结论不得沿用"
                % (expected_snapshot, now_tok))
            integ = {
                "status": "not_checked",
                "detail": list(integ["detail"]) + stale,
                "scope": integ["scope"],
            }

    # ---- 5. 期望集登记身份
    reg = check_registration(registration)

    # ---- 6. 资格门禁：逐条判，不合并为一个或
    reasons: List[str] = []

    if kind is None:
        reasons.append("not_run")
    elif not detail.get("expected"):
        # 期望集为空列表时，集合关系无意义（任何 retrieved 都会 disjoint）
        reasons.append("no_expected_ids")

    if integ["status"] == "failed":
        reasons.append("integrity_failed")
    elif integ["status"] != "verified":
        reasons.append("integrity_not_checked")

    if reg["present"] and not reg["independent"]:
        reasons.append("registration_not_independent")

    if stale:
        reasons.append("stale_check")

    eligible = (len(reasons) == 0)

    return {
        "recovery_id": "rec-" + query_ref,
        "query_ref": query_ref,
        "retrieved_ids": detail["retrieved"],
        "expected_ids": detail["expected"],
        "match_kind": kind,
        "missing": detail.get("missing", []),
        "extra": detail.get("extra", []),
        # 裁定 §二：四个新增维度
        "integrity_status": integ["status"],
        "integrity_detail": integ["detail"],
        "integrity_scope": integ["scope"],
        "recovery_eligible": eligible,
        "ineligible_reasons": sorted(set(reasons)),
        # A §1.8：登记身份
        "expected_ids_registration": reg,
        # 边界：门禁通过也不提升为科学结论
        "engineering_only": True,
        "is_scientific_result": False,
        "trusted_chain_anchor": "not_established",
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
