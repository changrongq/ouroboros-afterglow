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

#: 归因未知的显式标记（凌翼裁定回执 2026-11-27 §一）。
#:
#: 「如历史证据无法确定相应纠正依据，应显式报告归因未知，
#:   不得静默给出错误 ID。」
#:
#: ⚠ 用显式值而非「缺键」：缺键会让读者以为「没查到东西」，
#:   而显式值才能说「查过了，定不了」。
UNKNOWN_CAUSE = "ATTRIBUTION_UNKNOWN"


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


#: 「取回集」的唯一实现（Mion 2026-11-27 §4 R1/R3）。
#:
#: ⚠ 为什么必须抽成一处：
#:   Mion 原话——「『我们理解一致』不是保证。
#:   『两处代码各自实现同一个概念』本身就是我们治了一整轮的那个病。」
#:   ⇒ 在她写信之前，afrecover.summarize_conflicts 与
#:     afimportance.synthetic_ratios 各自算了一遍 record_only_ratio，
#:     且 total 的来源不同（前者 len(ids)，后者 len(scope)）。
#:   ⇒ 现在两边都必须调用本函数，不得自行构造范围。
#:
#: ⚠ R3：禁止任何一侧自行过滤或复制这段定义。
#:   本函数的契约：
#:     · scope_ids is None  ⇒ 全库当前版本
#:     · scope_ids 含重复   ⇒ 拒绝（否则同一记录被算两次，分母被算大）
#:     · scope_ids 含未知   ⇒ 拒绝（否则不完整范围冒充完整范围）
#:     · scope_ids == []    ⇒ 语义是「范围为空」，返回空列表，不报错
#:
#: 返回 (scope_records, scope_desc, by_id)
def retrieval_scope(store: RecoveryStore,
                    scope_ids: Optional[Iterable[str]] = None,
                    ) -> tuple:
    live = list(store.sqlite_rows())
    by_id = {r["record_id"]: r for r in live}

    if scope_ids is None:
        return live, "ALL_CURRENT_RECORDS", by_id

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

    return scope, "EXPLICIT_SCOPE", by_id

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

    # 取回集：**唯一实现**在 retrieval_scope()（Mion 2026-11-27 §4 R1/R3）
    #
    # ⚠ 2026-11-27 第三次修正（Mion 回执 §四）：
    #   原实现把范围构造写在本函数里，而 afrecover.summarize_conflicts
    #   另有一份。Mion：
    #     「『两处代码各自实现同一个概念』本身就是我们治了一整轮的那个病。」
    #   ⇒ 现在只调 retrieval_scope()，不得在此自行过滤。
    scope, scope_desc, by_id = retrieval_scope(store, scope_ids)

    # ---- 指标一：unverifiable_ratio（C1 分母 = first_person_report）
    denom = [r for r in scope
             if r.get("participation_basis") == "first_person_report"]
    n = len(denom)

    # ⚠ 2026-11-27 第四次修正（Mion 回执 §二）：(a)(b) 必须分项报
    #
    #   Mion：「『无法核验』= 我们没有能力判断它是不是伪亲历
    #          ≠ 我们判断过了但判不出
    #          ⇒ 从未观测 ⇒ 完全没判断过 ⇒ 不可核验，而且是最严重的一种。」
    #
    #   她还指出只算 (b) 会推出荒谬结论：
    #     「观测得越少，『可核验率』越高。」——反向激励。
    #
    #   ⇒ 合计仍进分子，但 (a)(b) 分解必须同时给出：
    #       (a) never_observed          从没看过    ← 流程缺口
    #       (b) observed_but_unresolved 看了判不出  ← 能力缺口
    #     否则不知道下一笔投入该补哪一头。
    never_observed = [
        r for r in denom if r.get("observed_origin") is None
    ]
    # (b) 只数「观测过、但 basis_conflict 落在无法判定的两个值上」，
    #     不与 (a) 重叠：observed_origin is None 的记录已在 (a)，
    #     不再进 (b)（否则同一记录被计两次，分子大于实际）。
    observed_but_unresolved = [
        r for r in denom
        if r.get("observed_origin") is not None
        and r.get("basis_conflict") in ("observed_absent",
                                        "observed_unresolved")
    ]
    unverifiable = never_observed + observed_but_unresolved
    assert len(unverifiable) == len({r["record_id"] for r in unverifiable}), (
        "(a)(b) 分解存在重叠 ⇒ 分子会大于实际不可核验记录数")
    assert len(unverifiable) <= n, "(a)(b) 合计超过了分母"

    # ---- 指标二：record_only_ratio（分母 = 取回集，与恢复层同口径）
    m = len(scope)
    record_only = [r for r in scope
                   if r.get("participation_basis") == "record_only"]

    # ---- 追加指标：denominator_attrition（Mion 回执 §三）
    #
    #   Mion：「若只数当前版本，则一条原本 first_person_report 的记录，
    #          被改成 record_only 之后，就从分母里消失。
    #          ⇒ 这是洗白档的操作路径。分母可以被改小，而比例会变好看。」
    #
    #   ⇒ denominator_attrition =
    #        (历史版本中曾为 first_person_report 的记录数)
    #      − (当前版本中 first_person_report 的记录数)
    #
    #   ⚠ 计数单位是【记录】，不是【版本】：
    #     同一条记录若历史上声称过 3 次、现在没声称，
    #     流失量是 1（一条记录离开了分母），不是 3。
    #     问的是「有多少条记录离开了分母」，不是「流失了多少次声称」。
    #
    #   ⚠ 范围：只统计【本次取回集内】的记录。
    #     若统计全库，则「本次只取回 3 条」时衰减量仍报全库的，
    #     两个数不同范围，会被误读成同一请求的两个侧面。
    #
    # ⚠ 2026-11-27 第五次补充（Mion 回执 第二封 §二，A2）：
    #   Mion：「attrition 回答『少了多少』，cause 回答『谁搬的』。
    #          只报前者，报告能看出问题但追不到动作。
    #          而这个项目里，【追得到动作】比【知道少了多少】重要 ——
    #          那正是溯源的全部意义。」
    #
    #   ⇒ 新增 denominator_attrition_cause =
    #        { <被移出分母的记录 id>: <那次 correct 的 correcting_record_id> }
    #
    #   ⚠ 数据来源不是新字段，是【已经存在的】relation 里的 correction_of 边：
    #        {"relation_type": "correction_of",
    #         "from_id": <被纠正的记录>, "to_id": <纠正依据>}
    #      ⇒ 之前没读它，不是因为不存在，是因为只报了「少了几条」。
    #
    # ⚠ 2026-11-27 第六次修正（凌翼裁定回执 §一，静态核对发现）：
    #
    #   原实现从【当前】relation 列表找【第一条】correction_of 就 break。
    #   而 correct() 是【追加】边（rel = list(cur.relation) + [新边]）。
    #   ⇒ 一条记录被纠正多次时，第一条边属于【最早那次】，
    #     而真正把 basis 搬离 first_person_report 的可能是后面某次。
    #   凌翼给的反例（我复现成立）：
    #      R 初始 first_person
    #      第 1 次由 first_person 记录 A 纠正 → R 仍是 first_person（未流失）
    #      第 2 次由 record_only 记录 B 纠正 → R 才退出分母
    #      旧实现给出 cause=A，正确答案是 B。
    #
    #   ⚠ 而且我此前的注释写的是「取最近一次把 basis 搬离的那次」，
    #     代码却是「取第一条」—— 注释声明的规则与实际行为相反。
    #     这比没写注释更糟：读者会信注释。
    #
    #   ⇒ 现在改为【按历史版本逐步比对来源字段】：
    #     找第一个满足「该版本 basis 已不是 first_person_report、
    #                 而紧邻的前一版本 basis 是 first_person_report」
    #     的版本，取该版本上的 correction_of 边。
    #     这一版就是【把记录搬出分母的那一版】。
    #
    #   ⇒ 若历史里找不到这样的一对版本（数据不自洽），
    #     或该版本上没有 correction_of 边，
    #     则【显式报归因未知】，不得静默给出一个 ID。
    #     （凌翼：「如历史证据无法确定相应纠正依据，
    #             应显式报告归因未知，不得静默给出错误 ID。」）
    attrition_ids = []
    attrition_cause = {}
    attrition_unknown = []
    for r in scope:
        rid = r["record_id"]
        cur_basis = r.get("participation_basis")
        if cur_basis == "first_person_report":
            continue                      # 还在分母里，未流失
        hist = store.history(rid)
        was_fpr = any(h.get("participation_basis") == "first_person_report"
                      for h in hist)
        if not was_fpr:
            continue
        attrition_ids.append(rid)

        # ---- 纠正依据记录：按历史版本逐步比对来源字段
        #
        # ⚠ 2026-11-27 措辞更正（凌翼裁定回执 §一）：
        #   此处原本写「谁搬的」。凌翼指出：
        #     「to_id 指的是纠正所引用的依据记录，
        #       不自动证明实际发起操作的是谁，
        #       更不等于外部可信来源认证。」
        #   ⇒ 本字段回答的是「引用了哪条记录作纠正依据」，
        #     不是「谁下的手」，也不是「该来源可信」。
        #
        # hist 按写入顺序（revision 递增）。
        # 找「前一版是 first_person_report、这一版不是」的跃变，
        # 该跃变对应的版本就是【把它搬出分母的那一版】。
        #
        # ⚠ 不能取 relation 列表首条：correct() 是追加边，
        #   首条属于最早一次纠正，而那次可能没改变 basis（凌翼反例）。
        cause = None
        prev_basis = None
        prev_edges = []
        for h in hist:
            this_basis = h.get("participation_basis")
            this_edges = [e for e in (h.get("relation") or [])
                          if e.get("relation_type") == "correction_of"]
            if (prev_basis == "first_person_report"
                    and this_basis != "first_person_report"):
                # 这一版【是】一处搬出分母的跃变。
                #
                # ⚠ relation 是【累计】的（correct() 追加），
                #   所以本版真正新增的边 = 本版边集 − 上一版边集。
                #   直接取首条会是【最早那次】纠正（凌翼反例里就是 A）。
                #
                # ⚠ 2026-11-27 第二次修正（AP-3 暴露）：
                #   不能在第一处跃变就 break ——
                #   记录可能【退出 → 恢复 → 再次退出】，
                #   当前 basis 由【最后一处跃变】决定。
                #   ⇒ 继续扫，每遇跃变就更新 cause，最后那次胜出。
                #
                # ⚠ 2026-11-27 第三次修正（凌翼第二次静态核对）：
                #   原用【to_id 集合差】判断新增边：
                #     new_edges = [e for e in this_edges
                #                  if e.to_id not in {pe.to_id for pe in prev_edges}]
                #   这在「同一条依据被重复引用」时误判为「无新增边」：
                #     R 第 1 次引用 A（A 当时 first_person）→ R 仍在分母
                #     A 自身被合法纠正为 record_only
                #     R 第 2 次仍引用 A → R 被搬出分母
                #   此时 rev3 确实新增了 ('A', 'cite #2') 这条边，
                #   但 to_id 仍是 'A' ⇒ 集合差为空 ⇒ 误报 ATTRIBUTION_UNKNOWN。
                #   （我已复现：cause['R'] = ATTRIBUTION_UNKNOWN，而新边就在那里。）
                #
                #   ⇒ 改为【按边数差取尾部新增】，不看 to_id 是否重复：
                #     累计列表是追加的，本版边集 = 上版边集 + 新增若干条。
                #     新增条数 = len(this) − len(prev)，取最后那个切片。
                #     这样重复引用同一依据也能被识别为「新增了一条边」。
                #
                # ⚠ 2026-11-27 第四次修正（知微独立复核 §2）：
                #   边数差仍会在【新增多条边】时歧义：
                #     跃变版同时新增 ('A', ...) 与 ('B', ...) 两条，
                #     原实现取新增段【首条】⇒ 签发 'A'，且 unknown 为空。
                #     但两条边都可能是造成跃变的原因 —— 这份确定性是假的。
                #   （知微实测：attrition=1, cause='A', unknown=[]；
                #     我已复现。她的做法是只改只读历史替身，未改真实历史。）
                #
                #   ⇒ 现在的签发规则（知微给定）：
                #     只有当【新增段恰好一条】、且该边可归属到本条记录
                #     （from_id 为空或等于 rid）、且目标有效（to_id 非空）时，
                #     才签发具体 ID；
                #     否则保留流失计数，cause 写 ATTRIBUTION_UNKNOWN，
                #     并列入 unknown 清单。
                #
                #   ⚠ 不要求依据记录也在本次取回集内（知微明确）：
                #     cause 只指【被引用的依据记录】，不是本次范围成员。
                n_new = len(this_edges) - len(prev_edges)
                if n_new <= 0:
                    # 跃变版没有新增边 ⇒ 这一处无法归因
                    cause = None
                else:
                    new_seg = this_edges[-n_new:]
                    if len(new_seg) != 1:
                        # 多条新增边 ⇒ 歧义，不猜
                        cause = None
                    else:
                        e0 = new_seg[0]
                        frm = e0.get("from_id")
                        to = e0.get("to_id")
                        if (frm not in (None, "", rid)) or not to:
                            # 边不归属本条记录，或目标无效 ⇒ 不签发
                            cause = None
                        else:
                            cause = to
            prev_basis = this_basis
            prev_edges = this_edges

        if cause is not None:
            attrition_cause[rid] = cause
        else:
            # 凌翼：「如历史证据无法确定相应纠正依据，
            #        应显式报告归因未知，不得静默给出错误 ID。」
            attrition_cause[rid] = UNKNOWN_CAUSE
            attrition_unknown.append(rid)
    denominator_attrition = len(attrition_ids)

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
            # Mion 回执 §二：空分支同样必须给出 (a)(b) 分解（均为 0），
            #   否则空/非空两分支键集合又不一致。
            "never_observed_count": 0,
            "observed_but_unresolved_count": 0,
            # Mion 回执 §三：空范围内不可能观察到流失（没有记录被取回），
            #   故为 0 —— 但必须与 denominator_size=0 同时出现，
            #   读者才知道「没有流失」与「分母本来就是 0」是一回事。
            "denominator_attrition": 0,
            "denominator_attrition_ids": [],
            # Mion 回执第二封 §二（A2）：纠正依据记录。空范围内没有搬动。
            # ⚠ 措辞按凌翼 2026-11-27 §一：这是「引用了哪条作依据」，
            #   不是操作者身份，也不等于来源可信。
            "denominator_attrition_cause": {},
            # 凌翼裁定回执 §一：归因未知的清单（空范围内自然为空）
            "denominator_attrition_unknown": [],
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
        # ---- Mion 回执 §二：(a)(b) 分项报（合计仍进分子）
        "never_observed_count": len(never_observed),
        "observed_but_unresolved_count": len(observed_but_unresolved),
        # ---- Mion 回执 §三：分母流失量
        "denominator_attrition": denominator_attrition,
        "denominator_attrition_ids": sorted(attrition_ids),
        # Mion 回执第二封 §二（A2）· 凌翼裁定 §一 措辞更正
        #   {被移出分母的记录 id: 把 basis 搬出分母的那一版所引用的依据记录 id}
        #
        # ⚠ 2026-11-27 凌翼措辞更正：
        #   「to_id 指的是纠正所引用的依据记录，
        #     不自动证明实际发起操作的是谁，
        #     更不等于外部可信来源认证。」
        #   ⇒ 本表回答「引用了哪条作依据」，不回答「谁操作的」，
        #     也不代表该来源可信。
        #
        # ⚠ 多次纠正时按【历史版本跃变】定位，
        #   不取 relation 列表首条（首条属于最早那次，可能没改变 basis）。
        # ⚠ 无法归因的记录，此表给 "ATTRIBUTION_UNKNOWN" 而不是缺键 ——
        #   凌翼：「应显式报告归因未知，不得静默给出错误 ID。」
        #   缺键会让读者以为「没查到东西」，显式值才不会。
        "denominator_attrition_cause": dict(attrition_cause),
        "denominator_attrition_unknown": sorted(attrition_unknown),
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
                          # 凌翼 2026-11-27 §一 措辞要求
                          "denominator_attrition_cause 的值是【纠正引用的"
                          "依据记录 id】，不是操作者身份，"
                          "也不等于外部可信来源认证；"
                          "不得仅凭 denominator_attrition 指控某条记录"
                          "发生了不当改写（凌翼：判 B，汇总预警指标）；"
                          "本函数的取回范围与 importance_candidates 的"
                          "全库过滤不是同一对象，不得把两者输出"
                          "当同一请求的结果组合。"),
        "note": ("合成夹具上的测量。只证明该指标能算出来，"
                 "不证明它在真实历史中等于此值。"
                 "两个比例的分母不同，不得合并引用。"),
    }
