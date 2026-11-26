# -*- coding: utf-8 -*-
"""候选资格集合 · 第 5 项 A3/B3 限定原型

授权依据（凌翼 2026-11-25 裁定）：
    问题一：甲（修订版）—— 允许用【合成召回事件流】表达高频，
            要求多次事件指向同一个 record_id，
            不得用复制多条独立记录冒充同一记录被多次召回。
    问题二：授权实现一个【不计算分数、不训练、不排序】的候选资格集合函数，
            仅用于 A3/B3 合成工程测试。

状态：
    CANDIDATE_FILTER_PROTOTYPE = AUTHORIZED_LIMITED
    FULL_IMPORTANCE_LEARNER    = NOT_AUTHORIZED

本模块【明确不做】的事
----------------------
    ✗ 不计算 importance_score / 任何数值
    ✗ 不训练
    ✗ 不排序（返回的是 set，不是有序列表）
    ✗ 不读写 reports/ 中任何「重要性结论」
    ✗ 不引入相似度 / 召回计数 / 频次 这些统计量

本模块【做什么】
----------------
    importance_candidates(store, trace) -> set[record_id]

    「候选资格」= 一条记录【没有被已声明规则排除掉】。
    它不代表「重要记忆已经选出」，只代表「它没被排除」。

    ⇒ 这是凌翼要求的边界：「该集合不代表『重要记忆已经选出』。」

为什么用集合而不是分数
----------------------
    B1 要求 model_generation 的记录【不得进入「重要」集合】。
    「不得进入集合」可以用 membership 断言；
    「分数要低」只能用阈值断言，而阈值是 B2 明文禁止的。
    ⇒ 用集合，B1 可以 100% 按文字实现，不需要任何阈值。

合成召回事件流（问题一 甲）
---------------------------
    召回事件 = {"record_id": ..., "at": ..., "query_ref": ...}
    「高频」= 同一 record_id 出现多次事件。
    ⚠ 禁止用「复制多条独立记录」冒充「同一记录被多次召回」——
      那会改变取回集大小，是另一种东西。
    ⇒ 本模块提供 synthetic_trace() 构造器，且【显式校验】不重复 record_id
      的独立性假设：每条事件必须指向 store 中真实存在的 record_id。

边界（不声称的事）
------------------
    该方式只验证【合成条件下的排除不变性】，
    不建立真实召回频率的实测证据。
    任何由此得出的比例只能标 MEASURED_ON_SYNTHETIC_ONLY。
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from afcore import (BASIS_CONFLICTS, OBSERVED_ORIGINS, Record,
                    RecoveryStore, SchemaError)

# ================================================================ 闭集

#: 排除规则的标识。每条规则都必须能被【单独关闭】，以便 B3-③ 的变异观测。
EXCLUSION_RULES = {
    # B1（凌翼转述 Mion 回复6 §四 B1）：
    #   observed_origin = model_generation 的记录，
    #   不得进入「重要」集合。
    "R_MODEL_GENERATION",
    # C2 保护：分母为空时结论必须是 NOT_EVALUABLE。
    #   ⚠ 这不是 B1 的一部分，是【另一个判据】。
    #     凌翼裁定第 5 条：「J3 的空分母判据……不能用 B3 的结果代替。」
    "R_EMPTY_DENOMINATOR",
}

#: 结论状态词。⚠ 三者不合并。
CANDIDATE_STATUS = {
    "EVALUATED",        # 有分母、规则已应用
    "NOT_EVALUABLE",    # 分母为空 —— 不是「没有重要项」，也不是 0
}

#: 合成测量前缀。凌翼裁定第 6 条：
#:   合成基线只允许标记 MEASURED_ON_SYNTHETIC_ONLY，不写正式重要性结论。
SYNTHETIC_PREFIX = "MEASURED_ON_SYNTHETIC_ONLY"


# ================================================================ 合成召回事件流

def synthetic_trace(store: RecoveryStore,
                    events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """校验并规范化一条【合成召回事件流】。

    events 每一项：{"record_id": str, "at": str, "query_ref": str}

    ⚠ 凌翼问题一（甲）的硬要求：
        「要求多次事件指向同一个 record_id，
          不得用复制多条独立记录冒充同一记录被多次召回。」

    因此本函数：
      1. 每条事件的 record_id 必须【真实存在】于 store（否则拒绝）；
      2. 允许多条事件指向同一 record_id（这才是「高频」）；
      3. 不要求 record_id 互不相同 —— 重复即高频，
         但【事件本身】必须是不同事件（以 (record_id, at, query_ref) 去重，
         完全相同的两条事件视为重复提交，直接拒绝）。
    """
    out: List[Dict[str, Any]] = []
    seen_events = set()
    for i, ev in enumerate(events):
        for k in ("record_id", "at", "query_ref"):
            if k not in ev:
                raise SchemaError("召回事件 #%d 缺字段 %s" % (i, k))
        rid = ev["record_id"]
        if store.get(rid) is None:
            raise SchemaError(
                "召回事件 #%d 指向不存在的 record_id=%r。"
                "「同一记录被多次召回」要求该记录真实存在；"
                "用不存在的 ID 复制造不出高频。" % (i, rid))
        key = (rid, ev["at"], ev["query_ref"])
        if key in seen_events:
            raise SchemaError(
                "召回事件 #%d 与前面完全相同 (%r, %r, %r)。"
                "完全重复的事件不是「多次召回」，是重复提交。"
                % (i, rid, ev["at"], ev["query_ref"]))
        seen_events.add(key)
        out.append({"record_id": rid, "at": ev["at"],
                    "query_ref": ev["query_ref"]})
    return out


def recall_counts(trace: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """统计每条 record_id 在合成事件流里被召回的次数。

    ⚠ 这个数【只用于合成测试的输入】，不进入任何重要性计算，
      也不写入 reports/。B2：与召回次数【无关】—— 这里统计它，
      是为了在测试里证明「无论多少次，排除都不变」，
      不是为了让次数参与筛选。
    """
    counts: Dict[str, int] = {}
    for ev in trace:
        counts[ev["record_id"]] = counts.get(ev["record_id"], 0) + 1
    return counts


# ================================================================ 候选资格集合

def importance_candidates(store: RecoveryStore,
                          trace: Optional[Iterable[Dict[str, Any]]] = None,
                          exclude: Optional[Iterable[str]] = None,
                          ) -> Dict[str, Any]:
    """返回候选资格集合。**不计算分数、不训练、不排序。**

    参数
    ----
    store    : 记录存储
    trace    : 合成召回事件流（可空；空时按「全量记录」作为分母）
    exclude  : 要【关闭】的排除规则集合。
               ⚠ 这个参数只用于变异观测（B3-③），不得用于生产路径。

    返回
    ----
    {
      status: "EVALUATED" | "NOT_EVALUABLE",
      candidates: set[record_id],      # 未分数、未排序
      denominator_size: int,           # |asserted == first_person_report 的记录数|
      excluded: {rule: [record_id]},   # 每条规则排除了谁
      active_rules: [...],
      measurement_scope: "SYNTHETIC" | "NOT_MEASURED",
      note: str,
    }

    ⚠ C2：分母为空 ⇒ status = NOT_EVALUABLE，且 candidates 为空集。
      不是「没有重要项」，也不是 0。
    """
    rules = set(EXCLUSION_RULES)
    off = set(exclude or ())
    unknown_off = off - rules
    if unknown_off:
        raise SchemaError("exclude 含未知规则：%s" % sorted(unknown_off))
    active = rules - off

    # ---- 分母：asserted == first_person_report 的记录（C1 口径）
    #   ⚠ 用 live 视图，不是历史。判据针对「当前这句话」，不针对旧版。
    live = list(store.sqlite_rows())
    denominator = [r for r in live
                   if r.get("participation_basis") == "first_person_report"]
    denom_size = len(denominator)

    excluded: Dict[str, List[str]] = {r: [] for r in sorted(rules)}
    candidates: Set[str] = set()

    for rec in live:
        rid = rec["record_id"]

        # ---- 规则 R_MODEL_GENERATION（B1）
        if ("R_MODEL_GENERATION" in active
                and rec.get("observed_origin") == "model_generation"):
            excluded["R_MODEL_GENERATION"].append(rid)
            continue

        candidates.add(rid)

    # ---- 规则 R_EMPTY_DENOMINATOR（C2）
    #
    # ⚠ 这条规则不是「排除某条记录」，是「整批结论不可评估」。
    #   所以在分母为空时，candidates 必须是空集，
    #   而不是「全量记录」或「排除后剩下的」。
    if ("R_EMPTY_DENOMINATOR" in active) and denom_size == 0:
        excluded["R_EMPTY_DENOMINATOR"] = sorted(candidates)
        return {
            "status": "NOT_EVALUABLE",
            "candidates": set(),
            "denominator_size": 0,
            "excluded": excluded,
            "active_rules": sorted(active),
            "measurement_scope": (SYNTHETIC_PREFIX if trace is not None
                                  else "NOT_MEASURED"),
            "note": ("分母为 0 ⇒ NOT_EVALUABLE。"
                     "这不是「没有重要项」，也不是 0（C2）。"),
        }

    return {
        "status": "EVALUATED",
        "candidates": candidates,
        "denominator_size": denom_size,
        "excluded": excluded,
        "active_rules": sorted(active),
        "measurement_scope": (SYNTHETIC_PREFIX if trace is not None
                              else "NOT_MEASURED"),
        "note": ("候选资格集合 = 未被已声明规则排除的记录。"
                 "它不代表「重要记忆已经选出」。"),
    }


# ================================================================ 合成比例（仅合成）

def synthetic_ratios(store: RecoveryStore,
                     trace: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """在合成夹具上算 unverifiable_ratio 与 record_only_ratio。

    ⚠ D3 / 凌翼裁定第 6 条：
       合成夹具上的基线只能证明「这个指标能算出来」，
       【不能】证明「它等于多少」。
       状态词只能写 MEASURED_ON_SYNTHETIC_ONLY。

    ⚠ 红线（Mion 回复6 §五 D5 / C 红线）：
       无基线前，任何重要性结论不得写入 reports/。
       本函数【不写任何文件】。调用方拿到值后只能放进测试断言里。

    ⚠ 2026-11-25 修正（C1 口径）：
       第一版分母用 len(live)（全体记录）。
       但 C1 明文规定分母 = |asserted == first_person_report 的记录数|。
       ⇒ 两者不同：record_only / third_person 的记录不属于「重要性判断」的分母。
       ⇒ 第一版因此永远不为空（只要库里有一条记录），
         于是「空分母 ⇒ None」这条判据从未被触发过。
         这是【判据与实现口径不一致】，不是测试问题。
    """
    live = list(store.sqlite_rows())

    # C1：分母 = asserted == first_person_report 的记录数
    denominator = [r for r in live
                   if r.get("participation_basis") == "first_person_report"]
    n = len(denominator)

    if n == 0:
        return {
            "measurement_scope": SYNTHETIC_PREFIX,
            "unverifiable_ratio": None,
            "record_only_ratio": None,
            "denominator_size": 0,
            "basis": "empty",
            "note": ("分母（asserted==first_person_report）为空 ⇒ 比例无定义（不是 0）。"),
        }

    unverifiable = [r for r in denominator
                    if r.get("basis_conflict") in
                    ("observed_absent", "observed_unresolved")]
    record_only = [r for r in denominator
                   if r.get("participation_basis") == "record_only"]

    return {
        "measurement_scope": SYNTHETIC_PREFIX,
        "unverifiable_ratio": len(unverifiable) / n,
        "record_only_ratio": len(record_only) / n,
        "denominator_size": n,
        "unverifiable_ids": sorted(r["record_id"] for r in unverifiable),
        "record_only_ids": sorted(r["record_id"] for r in record_only),
        "note": ("合成夹具上的测量。只证明该指标能算出来，"
                 "不证明它在真实历史中等于此值。"),
    }
