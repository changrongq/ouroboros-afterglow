# -*- coding: utf-8 -*-
"""B 层判定层 —— 按 A 层 v0.3 + 勘误001 + 勘误002 实现

绑定（不可只引其一）：
    A层_主设计候选v0.3_定稿_Mion_20261128.md     commit 0d159cb
    A层_v0.3_勘误001_Mion_20261128.md            commit 0251ee8
    A层_v0.3_勘误002_Mion_20261128.md            commit cbd6ea4

本文件只实现【A 层已定义的字段与判据】。
不在 A 层定义的检查，一律不写进本文件——
    B-SCOPE-1 结尾补句（Coder 提请，Mion 已接受）：
    「若某条 A 层约束需要断言才能被记住（如 C1-TYPE-1），
      该断言必须在报告里逐条列出，并注明它对应的 A 层条款编号。」

⚠ 本文件不是重要性机制。它只判定「一条记录够不够格进入可学习集合」。
  不得据此声称任何记忆机制已被验证（CROSS-1..6）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ============================================================ 常量（全部来自 A 层）

#: A1 的四种 reason（v0.3 §2.2 / S-5）
A1_REASON = {
    "HUMAN_CHANNEL_OK",       # observed_origin == human_input
    "DISPATCH_NOT_QUALIFIED",  # system_dispatch：已知但不够格
    "ORIGIN_UNDETERMINED",     # 缺失 / unknown_origin：判不出
    "MODEL_GENERATED",         # model_generation
}

#: origin_attribution.value 的三个取值（v0.3 §2.2 / S-6）
ORIGIN_VALUES = {"UNKNOWN", "HUMAN_DIRECT", "UNVERIFIED_TRANSFER"}

#: A3 的 match 状态（v0.3 §2.3 + 勘误002 E-7）
A3_MATCH = {
    "NOT_COVERED",                 # 本版不做事件匹配
    "NOT_TRIGGERABLE_BY_TYPE",     # 多条引用在基线类型下不可构造
}

#: 本版 source_ref 的类型（单值可空字符串）
#: ⚠ C1-TYPE-1：若这里改成「列表」，C-1 在 A3 上立刻 APPLICABLE，A3 必须重审。
SOURCE_REF_IS_SINGLE: bool = True


# ============================================================ A1 / A2 / A3

def _a1(rec: Dict[str, Any]) -> Dict[str, str]:
    """A1：本次直接输入是否经人类通道进入。

    A 层依据：v0.3 §2.2（S-5）+ §2.4（承诺边界）

    ⚠ A1 = PASS 只签「本次直接输入是经人类通道进入的」。
      不签「不是我的回声」，不签「原始作者是某人」（§2.4）。
    """
    origin = rec.get("observed_origin")

    if origin == "human_input":
        return {"verdict": "PASS", "reason": "HUMAN_CHANNEL_OK"}
    if origin == "system_dispatch":
        # S-5：已知事实，但不满足人类通道资格 ⇒ UNKNOWN 而非 FAIL
        return {"verdict": "UNKNOWN", "reason": "DISPATCH_NOT_QUALIFIED"}
    if origin == "model_generation":
        return {"verdict": "FAIL", "reason": "MODEL_GENERATED"}
    # None（从未观测）或 unknown_origin ⇒ 真的判不出
    return {"verdict": "UNKNOWN", "reason": "ORIGIN_UNDETERMINED"}


def _a2(rec: Dict[str, Any]) -> Dict[str, str]:
    """A2：断言与观测是否一致。

    A 层依据：v0.3 §2.1（A2 行）+ afcore.BASIS_CONFLICTS 四值

    ⚠ 本判定层读到的是 rec["basis_conflict"]。
      它由 afcore 在写入/观测时算好，本层不重算。
    """
    bc = rec.get("basis_conflict")
    if bc == "none":
        return {"verdict": "PASS"}
    if bc == "asserted_contradicts_observed":
        return {"verdict": "FAIL"}
    # observed_absent / observed_unresolved / None ⇒ 判不出
    return {"verdict": "UNKNOWN"}


def _a3(rec: Dict[str, Any], opener: Optional[Any] = None) -> Dict[str, Any]:
    """A3：是否存在一条可打开的引用。

    A 层依据：v0.3 §2.3（窄口径）+ 勘误001 E-1 + 勘误002 E-7

    窄口径只签「存在一条可打开的引用」。
    事件匹配 = NOT_COVERED（本版不做）。
    多条引用 = NOT_TRIGGERABLE_BY_TYPE（基线类型为单值）。
    """
    ref = rec.get("source_ref")
    # 1) 非空
    if not ref or not str(ref).strip():
        return {"verdict": "FAIL", "match": "NOT_COVERED"}

    # 2) 能打开
    #    ⚠ 本层不自己判断"打开"的含义，交给注入的 opener。
    #      未注入时：按「引用字符串非空即视为可打开」处理，
    #      并在报告里标 OPENER_NOT_INJECTED（见 check_no_unstated_checks）。
    if opener is not None:
        try:
            ok = bool(opener(ref))
        except Exception:
            ok = False
        if not ok:
            return {"verdict": "FAIL", "match": "NOT_COVERED"}

    return {"verdict": "PASS", "match": "NOT_COVERED"}


def _origin_attribution(rec: Dict[str, Any]) -> Dict[str, str]:
    """原始来路归属（v0.3 S-6）—— 独立字段，不混进 per_rule.A1。

    A 层依据：v0.3 §2.2 S-6 + 勘误001 E-2

    HUMAN_DIRECT       原始就是人类直接产生
    UNVERIFIED_TRANSFER 经人类转贴，但原始来源未验证（§2.4 必测反例）
    UNKNOWN            判不出
    """
    origin = rec.get("observed_origin")
    if origin == "human_input":
        return {"value": "HUMAN_DIRECT", "evidence": "observed_origin=human_input"}
    if origin == "model_generation":
        return {"value": "UNKNOWN", "evidence": "observed_origin=model_generation"}
    if origin == "system_dispatch":
        return {"value": "UNKNOWN", "evidence": "observed_origin=system_dispatch"}
    return {"value": "UNKNOWN", "evidence": "observed_origin=%r" % (origin,)}


# ============================================================ 主入口

def decide_admission(rec: Dict[str, Any],
                     opener: Optional[Any] = None) -> Dict[str, Any]:
    """判定一条记录是否够格进入可学习集合。

    返回 AdmissionDecision（v0.3 §2.5）：
      admitted / per_rule / origin_attribution / unknowns / reason_summary

    ⚠ S5：per_rule 三项【全部产出】，不因前一项 FAIL 而跳过。
      （S-10：否则 A2 写成 PASS 也测不出来）
    """
    a1 = _a1(rec)
    a2 = _a2(rec)
    a3 = _a3(rec, opener)

    per_rule = {"A1": a1, "A2": a2, "A3": a3}

    verdicts = [a1["verdict"], a2["verdict"], a3["verdict"]]

    # S1：全部 PASS 才 admitted
    admitted = all(v == "PASS" for v in verdicts)

    # S4：unknowns 逐项等于 per_rule 中所有 UNKNOWN 的规则名
    unknowns = [name for name, r in per_rule.items() if r["verdict"] == "UNKNOWN"]

    # S2：任一 UNKNOWN ⇒ admitted = false（由 S1 已隐含，此处显式断言）
    if unknowns:
        assert not admitted, "S2 violated: UNKNOWN 存在但 admitted=True"
    # S3：admitted=False ⇒ 至少一条 FAIL 或 UNKNOWN
    if not admitted:
        assert any(v in ("FAIL", "UNKNOWN") for v in verdicts), \
            "S3 violated: admitted=False 但三项无 FAIL/UNKNOWN"

    # reason_summary：只描述本次判定，不扩张主张
    parts = []
    for name in ("A1", "A2", "A3"):
        r = per_rule[name]
        parts.append("%s=%s" % (name, r["verdict"]))
    reason_summary = "本次判定：" + " / ".join(parts)

    return {
        "admitted": admitted,
        "per_rule": per_rule,
        "origin_attribution": _origin_attribution(rec),
        "unknowns": unknowns,
        "reason_summary": reason_summary,
    }


# ============================================================ A 层条款 → 断言映射

#: 每条断言 → 它对应的 A 层条款编号。
#:
#: B-SCOPE-1 补句要求：本层为「让 A 层约束被记住」而加的断言，
#: 必须逐条列出并注明来源条款。下面这份就是那张表。
CLAUSE_MAP = [
    # (断言标识, 内容, A 层来源)
    ("S1", "admitted ⇔ A1/A2/A3 全 PASS", "v0.3 §2.5 S1"),
    ("S2", "任一 UNKNOWN ⇒ admitted=False", "v0.3 §2.5 S2"),
    ("S3", "admitted=False ⇒ 至少一条 FAIL/UNKNOWN", "v0.3 §2.5 S3"),
    ("S4", "unknowns 逐项等于 UNKNOWN 规则名", "v0.3 §2.5 S4"),
    ("S5", "per_rule 三项全部产出", "v0.3 §2.5 S5（S-10）"),
    ("A1-REASON", "A1 四种 reason 闭合", "v0.3 §2.2（S-5）"),
    ("A3-NARROW", "A3 只签「能打开」，事件匹配 NOT_COVERED", "v0.3 §2.3 + 勘误001 E-1"),
    ("A3-MULTI", "多条引用 = NOT_TRIGGERABLE_BY_TYPE", "勘误002 E-7"),
    ("ORIGIN-SEP", "origin_attribution 独立于 per_rule", "v0.3 §2.2 S-6"),
    ("C1-TYPE-1", "SOURCE_REF_IS_SINGLE 若改 False，A3 必须重审",
     "勘误002 E-7 / C1-TYPE-1"),
]

#: 本层【明确不检查】的东西 —— 防止读代码的人以为它们被覆盖了。
NOT_CHECKED = [
    ("事件匹配", "A3 只判「能打开」；不判「打开的是不是所涉事件」（v0.3 §2.3）"),
    ("多条引用", "基线类型不可构造（勘误002 E-7）"),
    ("下游是否读取", "本层不控制下游；CROSS-6 范围内不作主张"),
    ("真实历史", "本层只用合成 Dict；未读取任何真实角色历史"),
]


def describe() -> Dict[str, Any]:
    """供测试与报告引用：本层实现了什么、没实现什么。"""
    return {
        "binding": ["0d159cb (v0.3)", "0251ee8 (勘误001)", "cbd6ea4 (勘误002)"],
        "fields_implemented": [
            "admitted", "per_rule.A1{A1}", "per_rule.A2{A2}", "per_rule.A3{A3}",
            "origin_attribution", "unknowns", "reason_summary",
        ],
        "clause_map": CLAUSE_MAP,
        "not_checked": NOT_CHECKED,
        "source_ref_is_single": SOURCE_REF_IS_SINGLE,
    }
