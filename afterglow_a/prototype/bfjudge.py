# -*- coding: utf-8 -*-
"""B 层 L-A 判定层 —— 按 A 层 v0.4 定稿实现

绑定（唯一，不可只引其一）：
    A层_主设计候选v0.4_合并定稿_Mion_20261128.md     commit 9031df2
    + 附录A（沙盘证据录入）

已过时、不得再引：
    v0.3 (0d159cb) + 勘误001 (0251ee8) + 勘误002 (cbd6ea4)
    ⇒ 缺勘误003（含 B-SCOPE-4 与 E-16 scope 进返回结构）

本文件只实现【A 层已定义的字段与判据】。
不在 A 层定义的检查，一律不写进本文件——
    B-SCOPE-4：若某条 A 层约束需要断言才能被记住（如 C1-TYPE-1），
      该断言必须在报告里逐条列出，并注明它对应的 A 层条款编号。

⚠ 本文件不是重要性机制。它只判定「一条记录够不够格进入可学习集合」。
  不得据此声称任何记忆机制已被验证（CROSS-1..6）。

L-A 与 L-B 分文件：
    本文件 = L-A 准入判定（admitted / per_rule / origin_attribution /
             unknowns / reason_summary）
    lbjudge.py = L-B 影响判定（B3-OBS / B3-CLAIM / B4 / MECH / EXCLUDED）
    拆开是因为两者的输入域完全不同 —— L-B 要的是两臂读出与对照结果，
    L-A 要的是一条记录的自述字段。合并会让「一条记录的准入」
    和「一次对照的因果」共用一个返回字典，读的人分不清哪个字段属于哪次判定。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ============================================================ 常量（全部来自 A 层）

#: A1 的四种 reason（v0.4 §3.1）
A1_REASON = {
    "HUMAN_CHANNEL_OK",        # observed_origin == human_input
    "DISPATCH_NOT_QUALIFIED",  # system_dispatch：已知但不够格
    "ORIGIN_UNDETERMINED",     # 缺失 / unknown_origin：判不出
    "MODEL_GENERATED",         # model_generation
}

#: origin_attribution.value 的三个取值（v0.4 §3.2）
ORIGIN_VALUES = {"UNKNOWN", "HUMAN_DIRECT", "UNVERIFIED_TRANSFER"}

#: A3 的 match 状态（v0.4 §3.3 / §3.4）
A3_MATCH = {
    "NOT_COVERED",                 # 本版不做事件匹配
}

#: A3 的 multi_ref 状态（v0.4 §3.4 / C1-TYPE-2）
A3_MULTI_REF = {
    "NOT_TRIGGERABLE_BY_TYPE",     # 多条引用在基线类型下不可构造
}

#: 本版 source_ref 的类型（单值可空字符串）
#: ⚠ C1-TYPE-1（v0.4 §3.4）：若这里改成「列表」，C-1 在 A3 上立刻 APPLICABLE，
#:    A3 必须按 C-1 重审。
SOURCE_REF_IS_SINGLE: bool = True


# ============================================================ A1 / A2 / A3

def _a1(rec: Dict[str, Any]) -> Dict[str, str]:
    """A1：本次直接输入是否经人类通道进入。

    A 层依据：v0.4 §3.1（三态表）+ §3.2（承诺边界）

    ⚠ A1 = PASS 只签「本次直接输入是经人类通道进入的」。
      不签「不是我的回声」，不签「原始作者是某人」（§3.2）。
    """
    origin = rec.get("observed_origin")

    if origin == "human_input":
        return {"verdict": "PASS", "reason": "HUMAN_CHANNEL_OK"}
    if origin == "system_dispatch":
        # §3.1：已知事实，但不满足人类通道资格 ⇒ UNKNOWN 而非 FAIL
        # 且必须与 ORIGIN_UNDETERMINED 分开：
        #   前者是【不合格】，后者是【不知道】
        return {"verdict": "UNKNOWN", "reason": "DISPATCH_NOT_QUALIFIED"}
    if origin == "model_generation":
        return {"verdict": "FAIL", "reason": "MODEL_GENERATED"}
    # None（从未观测）或 unknown_origin ⇒ 真的判不出
    return {"verdict": "UNKNOWN", "reason": "ORIGIN_UNDETERMINED"}


def _a2(rec: Dict[str, Any]) -> Dict[str, str]:
    """A2：断言与观测是否一致。

    A 层依据：v0.4 §3.1（三态表）+ afcore.BASIS_CONFLICTS 四值

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


def _a3(rec: Dict[str, Any],
        opener: Optional[Any] = None) -> Dict[str, Any]:
    """A3：是否存在一条可打开的引用。

    A 层依据：v0.4 §3.1（三态表）+ §3.3（窄口径）+ §3.4（multi_ref）

    三态（v0.4 §3.1 原文）：
        PASS     source_ref 非空，且能打开
        FAIL     source_ref 非空但确定打不开
        UNKNOWN  为空 / 解析器无法区分「不存在」与「访问受限」

    ⚠ 为什么「为空」判 UNKNOWN 而不是 FAIL（Mion 2026-11-28 补的理由）：
        ① 若判 FAIL，「缺引用」会淹没在「引用坏了」里 —— 两者补法不同
        ② S4 要求 unknowns 逐项等于 UNKNOWN 的规则名，
           空引用判 FAIL 后，它不会进 unknowns 清单 ⇒ 缺失就看不见了
        ⇒ 必须让「缺的东西」能被看见，而不是被归进「错误」。

    窄口径只签「存在一条可打开的引用」：
        match     = NOT_COVERED                  （事件匹配本版不做，§3.3）
        multi_ref = NOT_TRIGGERABLE_BY_TYPE      （单值类型，§3.4 C1-TYPE-2）
    """
    ref = rec.get("source_ref")
    match = "NOT_COVERED"
    multi_ref = "NOT_TRIGGERABLE_BY_TYPE"

    # 1) 为空 ⇒ UNKNOWN（不是 FAIL）
    if ref is None or not str(ref).strip():
        return {"verdict": "UNKNOWN", "match": match, "multi_ref": multi_ref}

    # 2) 能打开？
    #    ⚠ 本层不自己判断"打开"的含义，交给注入的 opener。
    #      未注入时按「引用字符串非空即视为可打开」处理，
    #      并在 describe() 里标 opener_injected_required=False。
    if opener is not None:
        try:
            ok = bool(opener(ref))
        except Exception:
            ok = False
        if not ok:
            # 提供了引用，但确定打不开 ⇒ FAIL
            return {"verdict": "FAIL", "match": match, "multi_ref": multi_ref}

    return {"verdict": "PASS", "match": match, "multi_ref": multi_ref}


def _origin_attribution(rec: Dict[str, Any]) -> Dict[str, str]:
    """原始来路归属（v0.4 §3.2）—— 独立字段，不混进 per_rule.A1。

    HUMAN_DIRECT        原始就是人类直接产生
    UNVERIFIED_TRANSFER 经人类转贴，但原始来源未验证（§3.2 必测反例）
    UNKNOWN             判不出

    ⚠ §3.2 必测反例：模型生成「我参加了 E7」→ 人类端【逐字转贴】。
      此时 observed_origin = human_input ⇒ A1 = PASS，
      但「不是我的回声」为假，原始归属在现有字段上【不可区分】
      ⇒ 该情形记 origin_attribution = UNKNOWN。

    ⇒ 因此本实现不把 human_input 直接签成 HUMAN_DIRECT：
      只有在记录额外标注 origin_evidence == "direct" 时才签 HUMAN_DIRECT。
      否则签 UNKNOWN —— 判不出就不签。
    """
    origin = rec.get("observed_origin")
    if origin == "human_input":
        if rec.get("origin_evidence") == "direct":
            return {"value": "HUMAN_DIRECT",
                    "evidence": "observed_origin=human_input, "
                                "origin_evidence=direct"}
        # 人类通道进来的，但无法区分原创 / 逐字转贴 ⇒ UNKNOWN
        return {"value": "UNKNOWN",
                "evidence": "observed_origin=human_input，"
                            "但现有字段无法区分原创与逐字转贴（§3.2 反例）"}
    if origin == "model_generation":
        return {"value": "UNKNOWN",
                "evidence": "observed_origin=model_generation"}
    if origin == "system_dispatch":
        return {"value": "UNKNOWN",
                "evidence": "observed_origin=system_dispatch"}
    return {"value": "UNKNOWN", "evidence": "observed_origin=%r" % (origin,)}


# ============================================================ 主入口

def decide_admission(rec: Dict[str, Any],
                     opener: Optional[Any] = None) -> Dict[str, Any]:
    """判定一条记录是否够格进入可学习集合。

    返回 AdmissionDecision（v0.4 §3.5）：
      admitted / per_rule / origin_attribution / unknowns / reason_summary

    ⚠ S5：per_rule 三项【全部产出】，不因前一项 FAIL 而跳过。
      （S5 由来：否则 A2 写成 PASS 也测不出来）
    """
    a1 = _a1(rec)
    a2 = _a2(rec)
    a3 = _a3(rec, opener)

    per_rule = {"A1": a1, "A2": a2, "A3": a3}
    verdicts = [a1["verdict"], a2["verdict"], a3["verdict"]]

    # S1：全部 PASS 才 admitted
    admitted = all(v == "PASS" for v in verdicts)

    # S4：unknowns 逐项等于 per_rule 中所有 UNKNOWN 的规则名
    #     ⚠ 现在可能含 A3（因为 §3.1 新增 UNKNOWN 分支）
    unknowns = [n for n, r in per_rule.items() if r["verdict"] == "UNKNOWN"]

    # S2：任一 UNKNOWN ⇒ admitted = false（由 S1 已隐含，此处显式断言）
    if unknowns:
        assert not admitted, "S2 violated: UNKNOWN 存在但 admitted=True"
    # S3：admitted=False ⇒ 至少一条 FAIL 或 UNKNOWN
    if not admitted:
        assert any(v in ("FAIL", "UNKNOWN") for v in verdicts), \
            "S3 violated: admitted=False 但三项无 FAIL/UNKNOWN"

    # reason_summary：只描述本次判定，不扩张主张
    parts = ["%s=%s" % (n, per_rule[n]["verdict"])
             for n in ("A1", "A2", "A3")]
    reason_summary = "本次判定：" + " / ".join(parts)

    return {
        "admitted": admitted,
        "per_rule": per_rule,
        "origin_attribution": _origin_attribution(rec),
        "unknowns": unknowns,
        "reason_summary": reason_summary,
    }


# ============================================================ A 层条款 → 断言映射

#: 每条断言 → 它对应的 A 层条款位置（v0.4 节号，勘误号已并入正文）。
#:
#: B-SCOPE-4 要求：本层为「让 A 层约束被记住」而加的断言，
#: 必须逐条列出并注明来源条款。下面这份就是那张表。
CLAUSE_MAP: List[Tuple[str, str, str]] = [
    # (断言标识, 内容, A 层来源)
    ("S1", "admitted ⇔ A1/A2/A3 全 PASS", "v0.4 §3.5 S1"),
    ("S2", "任一 UNKNOWN ⇒ admitted=False", "v0.4 §3.5 S2"),
    ("S3", "admitted=False ⇒ 至少一条 FAIL/UNKNOWN", "v0.4 §3.5 S3"),
    ("S4", "unknowns 逐项等于 UNKNOWN 规则名（可能含 A3）", "v0.4 §3.5 S4"),
    ("S5", "per_rule 三项全部产出", "v0.4 §3.5 S5"),
    ("A1-REASON", "A1 四种 reason 闭合；DISPATCH≠UNDETERMINED", "v0.4 §3.1"),
    ("A1-BOUNDARY", "A1=PASS 只签通道资格，不签回声/原作者", "v0.4 §3.2"),
    ("A3-NARROW", "A3 只签「能打开」，事件匹配 NOT_COVERED", "v0.4 §3.3"),
    ("A3-EMPTY-UNKNOWN", "source_ref 为空 ⇒ UNKNOWN（不是 FAIL）", "v0.4 §3.1"),
    ("A3-MULTI", "多条引用 = NOT_TRIGGERABLE_BY_TYPE", "v0.4 §3.4 C1-TYPE-2"),
    ("ORIGIN-SEP", "origin_attribution 独立于 per_rule", "v0.4 §3.2"),
    ("ORIGIN-REPOST", "human_input 但无法区分原创/转贴 ⇒ UNKNOWN",
     "v0.4 §3.2 必测反例"),
    ("C1-TYPE-1", "SOURCE_REF_IS_SINGLE 若改 False，A3 必须重审",
     "v0.4 §3.4 C1-TYPE-1"),
]

#: 本层【明确不检查】的东西 —— 防止读代码的人以为它们被覆盖了。
NOT_CHECKED: List[Tuple[str, str]] = [
    ("事件匹配", "A3 只判「能打开」；不判「打开的是不是所涉事件」（v0.4 §3.3）"),
    ("多条引用", "基线类型不可构造（v0.4 §3.4）"),
    ("下游是否读取", "本层不控制下游；CROSS-6 范围内不作主张"),
    ("真实历史", "本层只用合成 Dict；未读取任何真实角色历史"),
    ("机制影响", "MECH / B3 / B4 / EXCLUDED 由 lbjudge.py 判定，不在本文件"),
]


def describe() -> Dict[str, Any]:
    """供测试与报告引用：本层实现了什么、没实现什么。"""
    return {
        "binding": ["9031df2 (v0.4 合并定稿) + 附录A"],
        "fields_implemented": [
            "admitted",
            "per_rule.A1{verdict,reason}",
            "per_rule.A2{verdict}",
            "per_rule.A3{verdict,match,multi_ref}",
            "origin_attribution{value,evidence}",
            "unknowns",
            "reason_summary",
        ],
        "clause_map": CLAUSE_MAP,
        "not_checked": NOT_CHECKED,
        "source_ref_is_single": SOURCE_REF_IS_SINGLE,
        "opener_injected_required": False,
        "note_opener": "opener 未注入时按「引用字符串非空即视为可打开」处理",
    }
