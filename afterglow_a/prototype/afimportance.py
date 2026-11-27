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
    ✗ 不计算 importance_score / 任何数值  # boundary-ok
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

#: 结论状态词。
#
# ⚠ 2026-11-26 更正（睫指出）：原注释写「⚠ 三者不合并」，实际只有 2 个值。
#   那是从别处抄来的残留 —— 注释说的数量与代码不符，
#   而读者会信注释。现按实际数量写。
#
# ⚠ 另一个必须写明的：本字段【不可】与 synthetic_ratios 的 basis 混读。
#   status = 这批能不能评估（EVALUATED / NOT_EVALUABLE）
#   basis  = 为什么是空 / 是不是空（empty / nonempty）
#   ⇒ 「判未判定」须读各自载体（status，或 basis + 比例为 None），
#     不许按「有没有 status 键」当跨函数统一信号。
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
      denominator_size: int,
      excluded: {rule: [record_id]},
      active_rules: [...],
      measurement_scope: "MEASURED_ON_SYNTHETIC_ONLY" | "NOT_MEASURED",
      allowed_use: str,                # 肯定式：这个返回值可以被用来做什么
      forbidden_use: str,              # 否定式：不能被读成什么
      note: str,
    }

    ⚠ 2026-11-26 修正（睫复核）：
      第一版把「肯定式定义」写在 note 里，后面紧跟一句否定式，
      于是读者把整段当注释。
      ⇒ 现拆成 allowed_use（可用途）/ forbidden_use（禁读法）两个必读字段。
      二者都必须存在：只有否定式的边界防误读，但不给使用范围。

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
            "allowed_use": ("可用于断言「本批次不可评估」（status 字段）；"
                            "可用于测试 C2 判据本身。"),
            "forbidden_use": ("不得把 candidates 为空集读成「没有重要项」；"
                              "不得把空集与「已判定为零」合并统计；"
                              "不得脱离 status 单独引用 candidates。"),
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
        "allowed_use": ("可用于断言「某记录未被已声明规则排除」；"
                        "可用于验证排除规则在合成夹具上的可逆性。"),
        "forbidden_use": ("不得把 candidates 读作「重要记忆已选出」；"  # boundary-ok
                          "不得把 set 大小变化读作重要性变化；"
                          "不得用于任何真实历史结论或科学结论。"),
        "note": ("候选资格集合 = 未被已声明规则排除的记录。"
                 "它不代表「重要记忆已经选出」。"),
    }


# ================================================================ 合成比例（仅合成）

def synthetic_ratios(store: RecoveryStore,
                     trace: Optional[Iterable[Dict[str, Any]]] = None,
                     scope_ids: Optional[Iterable[str]] = None,
                     ) -> Dict[str, Any]:
    """在合成夹具上算两个覆盖比例。

    ⚠ 2026-11-26 修正（知微复核）—— 两处口径错误，均已复现：

    【错误一】unverifiable_ratio 把「从未观测」报成 0%
      第一版只看 basis_conflict ∈ {observed_absent, observed_unresolved}。
      而【从未调用 record_observed】的记录，basis_conflict = None，
      ⇒ 被算作「可判定」，于是唯一那条从未观测的记录报成 0% 不可核验。
      而同一库上 afrecover.summarize_conflicts 把该 ID 列为不可核验。
      ⇒ 修：observed_origin is None 也计入不可核验
        （「没有观测通道」与「观测了但判不出」都属于无法判定）。

    【错误二】record_only_ratio 结构性恒零
      第一版分母 = first_person_report，再从其中找 record_only
      ⇒ 分子恒为 0，指标永远没有监测能力。
      ⇒ 修：该比例的分母改用【指定的取回集】（scope_ids），
        不再用 first_person 分母。两个指标分母本就不同：
            unverifiable_ratio  分母 = first_person_report（C1 规定）
            record_only_ratio   分母 = 取回集（与恢复层同口径）
      ⚠ 不要简单把两个分母都改回 len(live) —— 那会把 C1 也改错。

    ⚠ 口径必须显式登记：两个指标的总体不同，且各自写明。
    """
    live = list(store.sqlite_rows())
    by_id = {r["record_id"]: r for r in live}

    # 取回集：未指定时视为「全库当前版本」
    #
    # ⚠ 2026-11-26 修正（知微定点复验）—— 显式范围会静默改变样本总体：
    #
    #   原实现：scope = [by_id[i] for i in scope_ids if i in by_id]
    #   ⇒ ① 重复 ID 被保留 ⇒ [r1,ro1,ro1] 的分母变成 3
    #          同一集合重复提交，比例从 0.5 变成 0.667
    #      ② 不存在的 ID 被静默丢弃 ⇒ [ghost] 与 [] 返回完全相同
    #          「没能解析任何 ID」与「本次范围本来为空」混成了一件事
    #
    #   ⇒ 现在：重复 ID 与未知 ID 一律【拒绝】，并列出是哪些。
    #      理由：契约说的是「记录集合」，集合语义下重复无意义；
    #      而静默丢弃会让「不完整范围」冒充「完整范围」。
    if scope_ids is None:
        scope = live
        scope_desc = "ALL_CURRENT_RECORDS"
        unresolved = []
    else:
        requested = list(scope_ids)
        seen = set()
        dup = []
        unknown = []
        scope = []
        for rid in requested:
            if rid in seen:
                dup.append(rid)
                continue
            seen.add(rid)
            if rid not in by_id:
                unknown.append(rid)
                continue
            scope.append(by_id[rid])

        if dup:
            raise SchemaError(
                "scope_ids 含重复 ID %s。范围是【记录集合】，"
                "重复提交会把同一记录算两次，从而改变分母与比例。"
                % (sorted(set(dup)),))
        if unknown:
            raise SchemaError(
                "scope_ids 含不存在的 ID %s。"
                "不得静默丢弃 —— 那会让不完整范围冒充完整范围。"
                "若本次确实没有取回任何记录，请传 []，"
                "它的语义是「范围为空」，不是「解析失败」。"
                % (sorted(unknown),))

        scope_desc = "EXPLICIT_SCOPE"
        unresolved = []

    # ---- 指标一：unverifiable_ratio（C1 分母 = first_person_report）
    denom = [r for r in scope
             if r.get("participation_basis") == "first_person_report"]
    n = len(denom)
    unverifiable = [
        r for r in denom
        if r.get("observed_origin") is None            # 从未观测
        or r.get("basis_conflict") in ("observed_absent", "observed_unresolved")
    ]

    # ---- 指标二：record_only_ratio（分母 = 取回集，与恢复层同口径）
    m = len(scope)
    record_only = [r for r in scope
                   if r.get("participation_basis") == "record_only"]

    if n == 0 and m == 0:
        # ⚠ 2026-11-26 修正（知微 + 睫）：空分支原本只有 10 键，
        #   而非空分支 12 键（缺 ids_meaning 与两个 ids 列表，多 basis）。
        #   ⇒ 同一函数两种键集合 ⇒ 「完整清单」这个说法站不住。
        #   ⇒ 现按【同一键集合】返回；空分支的两个 ids 列表为 []，
        #     并用 basis="empty" 说明为何是空 —— 不靠「缺键」表达。
        return {
            "measurement_scope": SYNTHETIC_PREFIX,
            "scope_description": scope_desc,
            "unverifiable_ratio": None,
            "record_only_ratio": None,
            "denominator_size": 0,
            "record_only_denominator_size": 0,
            "unverifiable_ids": [],
            "record_only_ids": [],
            "ids_meaning": ("unverifiable_ids = 无法判定是否伪亲历的记录 ID；"
                            "record_only_ids = 断言类别为 record_only 的记录 ID。"
                            "两者都不是「已识别的名单」——前者是判不了，"
                            "后者是自述类别，均不构成对任何记录的指控或确认。"),
            "basis": "empty",
            "allowed_use": "可用于断言「两个比例均无定义」（值为 None）。",
            "forbidden_use": ("不得把 None 写作 0；"
                              "不得把空分母读作「全部可判定」；"
                              "本函数的取回范围与 importance_candidates 的"
                              "全库过滤不是同一对象，不得把两者输出"
                              "当同一请求的结果组合。"),
            "note": ("两个分母均为 0 ⇒ 两个比例都无定义（不是 0）。"
                     "unverifiable 与 record_only 的分母不同，见两个 "
                     "denominator_size 字段。"),
        }

    return {
        "measurement_scope": SYNTHETIC_PREFIX,
        "scope_description": scope_desc,
        # 分母口径逐项写明 —— 两个指标分母不同，不许默认相同
        "denominator_size": n,                 # unverifiable 的分母
        "record_only_denominator_size": m,     # record_only 的分母
        "unverifiable_ratio": (len(unverifiable) / n) if n else None,
        "record_only_ratio": (len(record_only) / m) if m else None,
        # ⚠ 下面两个 ID 列表是【无法核验/只记录 的记录 ID】，
        #   不是「已识别的伪亲历名单」也不是「已识别的洗白档名单」。
        #   名字里带 ids 容易被读成「判定结果」，故此处写明。
        "unverifiable_ids": sorted(r["record_id"] for r in unverifiable),
        "record_only_ids": sorted(r["record_id"] for r in record_only),
        # 与空分支保持同一键集合（2026-11-26：两分支键必须一致）
        "basis": "nonempty",
        "ids_meaning": ("unverifiable_ids = 无法判定是否伪亲历的记录 ID；"
                        "record_only_ids = 断言类别为 record_only 的记录 ID。"
                        "两者都不是「已识别的名单」——前者是判不了，"
                        "后者是自述类别，均不构成对任何记录的指控或确认。"),
        "allowed_use": ("可用于在合成夹具上验证比例可算；"
                        "可用于回归测试的固定断言。"),
        "forbidden_use": ("不得写入 reports/ 或任何正式报告；"
                          "不得当作真实历史中的比例；"
                          "不得把 unverifiable_ids 读作已识别名单；"
                          "两个比例分母不同，不得合并引用；"
                          "本函数的取回范围与 importance_candidates 的"
                          "全库过滤不是同一对象，不得把两者输出"
                          "当同一请求的结果组合。"),
        "note": ("合成夹具上的测量。只证明该指标能算出来，"
                 "不证明它在真实历史中等于此值。"
                 "两个比例的分母不同，不得合并引用。"),
    }
