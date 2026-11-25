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

from afcore import MATCH_KINDS, SchemaError, BASIS_CONFLICTS


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
    """校验期望集登记身份。返回规范化结果，不修改输入。

    ⚠ Z61-03（知微 2026-11-24 §5）：
      原实现只检查五个键是否存在，且只对 registered_at 检查非空。
      registered_by / registered_rev 为空串、None、纯空白时，
      仍被判 independent=True —— 登记人和版本都没有值，
      却被报告为「已给出合格登记」。

    ⇒ 现补齐：registered_by / registered_rev 必须是非空字符串（去空白后）。
    ⇒ 对 None / 空串 / 纯空白 一律记问题，并纳入负向测试。

    ⚠ 边界（承知微同节末段）：
      两个 yes 加上结构合法，最多验证「声明满足本地格式与标志条件」，
      【不能】独立证明「确实来自独立观察者、确实早于结果暴露」。
      不得把 independent=True 读作「独立来源证据已建立」。
    """
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

    # 时间必须可读，且 registry 里 registered_at 为必填
    if not (reg.get("registered_at") or "").strip():
        problems.append("registered_at 为空")

    # Z61-03：身份字段必须有实际取值。
    # None / 空串 / 纯空白 都不是「谁登记」「用哪一版登记」的答案。
    for k in ("registered_by", "registered_rev"):
        v = reg.get(k)
        if v is None:
            problems.append("%s 为 None（须为非空字符串）" % k)
        elif not isinstance(v, str):
            problems.append("%s 类型为 %s（须为字符串）" % (k, type(v).__name__))
        elif not v.strip():
            problems.append("%s 为空或纯空白（须给出实际取值）" % k)

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
      （见返回结构里的 scope_declaration：
        trusted_chain_anchor = NOT_ESTABLISHED，
        trusted_anchor_scope = OUT_OF_SCOPE_FOR_PROTOTYPE）。

    ⚠ 本函数的验收档位（凌翼裁定 2026-11-25 事项 A）：
      RECOVERY_GATE_IMPLEMENTED = VERIFIED_ENGINEERING_SYNTHETIC
      含义严格限定为：合成测试范围内，门禁实现、已定义拒绝条件
      和已执行变异验证达到当前工程验收要求。
      ⇒ 不得表述为「全部恢复安全性已建立」。
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
    #
    # ⚠ Z61-01（知微 2026-11-24 §3）：
    #   原实现只在调用方显式传 expected_snapshot 时才做比较，
    #   默认 None ⇒ G6 整体被跳过。而 check_integrity() 自己已经取得并
    #   返回了 scope.snapshot —— 那个才应该是默认比较基准。
    #   ⇒ 现改为：默认比较【本次检查实际取得的快照】。
    #     外部传入的 expected_snapshot 作为额外前提保留。
    #
    # ⚠ Z61-04（知微 2026-11-24 §6）：
    #   原实现在 stale 时把 integ["status"] 整体改写成 "not_checked"，
    #   于是「查过且失败」被改写成「未检查」，integrity_failed 丢失。
    #   ⇒ 现改为：failed 不被覆盖；stale 只作为【独立原因】记录。
    #     只有未失败的状态才降级为 not_checked（因为其结论已不可信）。
    stale: List[str] = []
    if hasattr(store, "snapshot_token"):
        now_tok = store.snapshot_token()
        checked_tok = (integ.get("scope") or {}).get("snapshot")

        # 基准一：本次检查实际取得的快照（默认生效，不可省略）
        if checked_tok is not None and now_tok != checked_tok:
            stale.append(
                "本次完整性检查所依据的快照 %s 与当前 %s 不同：旧结论不得沿用"
                % (checked_tok, now_tok))
        # 基准二：调用方显式给出的期望快照（额外前提）
        if expected_snapshot is not None and now_tok != expected_snapshot:
            stale.append(
                "调用方期望快照 %s 与当前 %s 不同：旧结论不得沿用"
                % (expected_snapshot, now_tok))

        if stale:
            if integ["status"] == "failed":
                # Z61-04：已经查过并失败 —— 这是既成事实，不得被覆盖。
                # 只追加说明，保留 failed 与 integrity_failed 原因码。
                integ = {
                    "status": "failed",
                    "detail": list(integ["detail"]) + stale,
                    "scope": integ["scope"],
                }
            else:
                # 未失败的状态在快照失效后不再可信 ⇒ 降级为 not_checked。
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

    # ---- 7. 冲突摘要（Mion 2026-11-24 回复2 §二② / 回复3 §三）
    #
    # 为什么【必须】在返回结构里，而不只在报告里：
    #   系统算出来然后扔掉，与「消费路径为空」是同一个病
    #   （我给衔环的信里写过：「此后谁读、读了做什么，代码里一个字都没有」）。
    #
    # 为什么【必须】区分 none 与 observed_absent：
    #   这两件事后果相反：
    #     none             = 算过，确认两路一致
    #     observed_absent  = 根本没观测通道，无所谓一致
    #   若把「没有观测」返回成 none，等于把缺席读成通过。
    #
    # 为什么【不影响】eligible（Mion 给的激励论证）：
    #   若 conflict 会拉低资格 ⇒ 系统学会「不标冲突」来换合格
    #   ⇒ 字段还在，值永远是 none
    #   ⇒ 一个会被激励去撒谎的字段，等于没有这个字段。
    conflict = summarize_conflicts(store, retrieved_ids)

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
        # Mion：冲突摘要必须随结果返回，且允许「缺席」是显式值
        "conflict_summary": conflict,
        # A §1.8：登记身份
        "expected_ids_registration": reg,
        # ---- 边界声明（凌翼裁定 2026-11-25 事项 A/B）
        #
        # ⚠ 原先这里只有 engineering_only / is_scientific_result 两个布尔值。
        #   凌翼裁定明确指出：
        #     「该限制应在设计文档、状态登记和对外报告中明确，
        #       不得仅用 is_scientific_result=False 代替完整的声明。」
        #   ⇒ 一个 False 不携带任何信息：
        #     读者无法从它得知「缺的是哪一类证据」。
        #   ⇒ 现改为逐项声明，每项都回答「缺什么」。
        "engineering_only": True,
        "is_scientific_result": False,
        "scope_declaration": {
            # 事项 A：工程级限定验收的语义边界
            "recovery_gate_status": "VERIFIED_ENGINEERING_SYNTHETIC",
            "recovery_gate_evidence": "SELF_TEST_REPORTED",
            # 事项 B：链外锚点排除在原型范围之外
            "trusted_chain_anchor": "NOT_ESTABLISHED",
            "trusted_anchor_scope": "OUT_OF_SCOPE_FOR_PROTOTYPE",
            # 未解决的独立证据缺口（逐项列出，不合并）
            "independent_recomputation": "NOT_ESTABLISHED",
            "real_history_validation": "NOT_PERFORMED",
            "external_source_attestation": "NOT_ESTABLISHED",
            # 已知边界（凌翼裁定 事项 A 末段三条）
            "known_limits": [
                # 未提交登记身份的兼容路径，不具备独立登记证明
                "registration_may_be_absent: 未提供登记身份时不得读作已登记",
                # recovery_eligible 不等于 match_kind=exact
                "eligible_neq_exact: 资格门禁通过不等于集合关系精确匹配",
                # 读、校验、消费不是经证明的原子事务
                "not_atomic: 读取/校验/消费不是经证明的原子事务",
            ],
            "note": ("本结论仅覆盖合成夹具上的工程自测；"
                     "不构成对来源真实性或恢复安全性的证明。"),
        },
    }


def summarize_conflicts(store, record_ids: Optional[Iterable[str]] = None
                        ) -> Dict[str, Any]:
    """汇总本次取回范围内的「声明 vs 观测」冲突状态。

    返回值恒含三个键，不可省略：
      basis_conflict : 四值之一（见 afcore.BASIS_CONFLICTS）
      affected_ids   : 落在该状态下的记录
      detail         : 人类可读说明

    ⚠ basis_conflict 表达的是【整批】的状态：
       · 只要有一条 asserted_contradicts_observed ⇒ 整批取该值（最严重优先）
       · 全部都没有观测通道 ⇒ observed_absent
       · 有观测但都判不出    ⇒ observed_unresolved
       · 全部有观测且一致    ⇒ none
       · 范围为空            ⇒ observed_absent（无记录 ≠ 无冲突）
    """
    if record_ids is None:
        return {
            "basis_conflict": "observed_absent",
            "affected_ids": [],
            "per_record": [],
            "counts": {},
            "detail": "未指定汇总范围 ⇒ observed_absent（不得读作 none）",
            "unverifiable_ratio": None,
            "unverifiable_ids": [],
            "unverifiable_note": "未指定范围 ⇒ 不可计算，不是 0。",
            "record_only_ratio": None,
            "record_only_ids": [],
            "record_only_note": "未指定范围 ⇒ 不可计算。",
            "pseudo_first_person_ids": [],
            "pseudo_first_person_note": "未指定范围 ⇒ 不可判定。",
            "observed_chained_ids": [],
            "observed_unchained_ids": [],
            "observed_chained_note": "未指定范围 ⇒ 不可判定。",
        }

    ids = sorted(set(record_ids))
    if not ids:
        return {
            "basis_conflict": "observed_absent",
            "affected_ids": [],
            "per_record": [],
            "counts": {},
            "detail": "取回集为空 ⇒ observed_absent（无记录 ≠ 无冲突）",
            "unverifiable_ratio": None,
            "unverifiable_ids": [],
            "unverifiable_note": "取回集为空 ⇒ 不可计算，不是 0。",
            "record_only_ratio": None,
            "record_only_ids": [],
            "record_only_note": "取回集为空 ⇒ 不可计算。",
            "pseudo_first_person_ids": [],
            "pseudo_first_person_note": "取回集为空 ⇒ 不可判定。",
            "observed_chained_ids": [],
            "observed_unchained_ids": [],
            "observed_chained_note": "取回集为空 ⇒ 不可判定。",
        }

    buckets: Dict[str, List[str]] = {}
    for rid in ids:
        rec = store.get(rid)
        if rec is None:
            buckets.setdefault("observed_absent", []).append(rid)
            continue
        val = rec.get("basis_conflict")
        if val is None:
            # 字段缺失 = 从未计算过 ⇒ 不得当作 none
            buckets.setdefault("observed_absent", []).append(rid)
        elif val not in BASIS_CONFLICTS:
            buckets.setdefault("observed_unresolved", []).append(rid)
        else:
            buckets.setdefault(val, []).append(rid)

    # ---- unverifiable_ratio（Mion 2026-11-24 回复3 §二）
    #
    # ⚠ 这个数【不是 FER】，不得混进任何合格率。
    #   它回答的是：「有多大比例的记录，我们无法判定它是否伪亲历」。
    #
    # ⇒ 它的用途是【分母】，不是指标：
    #   unverifiable_ratio 越高，任何关于伪亲历的结论可覆盖的范围就越小。
    #   ⇒ 它不是「伪亲历率」的估计，是「伪亲历结论适用范围」的上限。
    #
    # 口径：observed_absent 与 observed_unresolved 都计入「不可判定」，
    #       因为二者都无法回答「是否有冲突」。只有 none 与
    #       asserted_contradicts_observed 是可判定的（一有一无）。
    unverifiable = sorted(set(buckets.get("observed_absent", []))
                          | set(buckets.get("observed_unresolved", [])))
    total = len(ids)
    ratio = (len(unverifiable) / total) if total else None

    # ---- record_only_ratio（Mion 2026-11-24 回复4 §4.2）
    #
    # ⚠ 这是一个【行为漏洞】的度量，不是判定漏洞：
    #   record_only 的断言是「不指向任何陈述者」，模型生成不违反它 ⇒ 判 none。
    #   但这会让 record_only 成为【洗白档】：
    #   把本该 first_person_report 的内容标成 record_only，
    #   伪亲历就整体消失 —— 而且指标会变好看。
    #
    # ⇒ 判定管不了它，只有度量管得住。
    #
    # ⚠ 此指标【不是合格率】，是伪亲历统计可信度的前置条件。
    record_only_ids = []
    for rid in ids:
        rec = store.get(rid)
        if rec is not None and rec.get("participation_basis") == "record_only":
            record_only_ids.append(rid)
    record_only_ratio = (len(record_only_ids) / total) if total else None

    # ---- 观测是否进链（Mion 2026-11-24 回复4 §三 状态词）
    chained_ids = []
    unchained_ids = []
    for rid in ids:
        if hasattr(store, "observed_chained") and store.observed_chained(rid):
            chained_ids.append(rid)
        else:
            unchained_ids.append(rid)

    # 伪亲历派生标记（不是第五个 basis_conflict 值）
    pseudo_ids = []
    for rid in ids:
        if hasattr(store, "pseudo_first_person") and \
                store.pseudo_first_person(rid):
            pseudo_ids.append(rid)

    # 严重度优先：冲突 > 判不出 > 无观测 > 一致
    for level in ("asserted_contradicts_observed",
                  "observed_unresolved",
                  "observed_absent",
                  "none"):
        if level in buckets:
            return {
                "basis_conflict": level,
                "affected_ids": sorted(buckets[level]),
                # 知微 2026-11-24：逐条绑定记录 ID、版本与判定
                #   汇总保留各类数量；读者能看出【哪条可以怎样引用】。
                #   若只给一个枚举，三条各不相同的情形就读不出来。
                "per_record": build_per_record(store, ids, buckets),
                "counts": {k: len(v) for k, v in sorted(buckets.items())},
                "detail": {
                    "asserted_contradicts_observed":
                        "声明与系统观测不一致（asserted_contradicts_observed）",
                    "observed_unresolved": "有观测但判不出来源",
                    "observed_absent": "无观测通道（不得读作无冲突）",
                    "none": "两路观测一致",
                }[level],
                # ⚠ 单独一栏，不与任何合格率合并
                "unverifiable_ratio": ratio,
                "unverifiable_ids": unverifiable,
                "unverifiable_note":
                    "本值不是伪亲历率，而是「无法判定是否伪亲历」的记录占比；"
                    "它给出的是任何伪亲历结论的适用范围上限，不是结论本身。",
                # Mion 回复4 §4.2：行为漏洞的度量
                "record_only_ratio": record_only_ratio,
                "record_only_ids": sorted(record_only_ids),
                "record_only_note":
                    "record_only 比例上升 ⇒ 伪亲历统计的分母被抽空。"
                    "此指标不是合格率，是统计可信度的前置条件。",
                # Mion 回复4 §五：派生标记，不是第五值
                "pseudo_first_person_ids": sorted(pseudo_ids),
                "pseudo_first_person_note":
                    "basis_conflict 度量「断言与观测是否一致」，"
                    "不度量「是否伪亲历」。伪亲历是它的一个真子集。"
                    "⇒ 不得把 none 读成「没有伪亲历」，"
                    "也不得把 asserted_contradicts_observed 读成「有伪亲历」。",
                # Mion 回复4 §三：观测是否进链
                "observed_chained_ids": sorted(chained_ids),
                "observed_unchained_ids": sorted(unchained_ids),
                "observed_chained_note":
                    "未进链的记录，其观测值不在任何摘要内 ⇒ "
                    "改它不会被任何检查发现。",
            }

    return {
        "basis_conflict": "observed_unresolved",
        "affected_ids": [],
        "per_record": build_per_record(store, ids, buckets),
        "counts": {k: len(v) for k, v in sorted(buckets.items())},
        "detail": "无法归类 ⇒ observed_unresolved（不得读作 none）",
        "unverifiable_ratio": ratio,
        "unverifiable_ids": unverifiable,
        "unverifiable_note":
            "本值不是伪亲历率，而是「无法判定是否伪亲历」的记录占比。",
        "record_only_ratio": record_only_ratio,
        "record_only_ids": sorted(record_only_ids),
        "record_only_note":
            "record_only 比例上升 ⇒ 伪亲历统计的分母被抽空。",
        "pseudo_first_person_ids": sorted(pseudo_ids),
        "pseudo_first_person_note": "basis_conflict ≠ 伪亲历，后者是真子集。",
        "observed_chained_ids": sorted(chained_ids),
        "observed_unchained_ids": sorted(unchained_ids),
        "observed_chained_note": "未进链的观测值不在任何摘要内。",
    }


def build_per_record(store, ids: List[str],
                     buckets: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """逐条绑定：记录 ID / 版本 / 判定 / 该条可否引用。

    知微 2026-11-24：
      「一次取回三条记录，一条自述与观测相符，一条从未收到观测，
        第三条存在矛盾。如果 conflict_summary 只返回一个枚举，
        读者就看不出哪条可以怎样引用。」

    ⇒ 逐条给出，汇总另保留各类数量。
    """
    rev_of = {}
    for level, rids in buckets.items():
        for rid in rids:
            rev_of[rid] = level

    out = []
    for rid in ids:
        rec = store.get(rid)
        level = rev_of.get(rid, "observed_absent")

        # 该条的观测链信息（若已进链）
        chain = []
        if hasattr(store, "observed_chain"):
            chain = store.observed_chain(rid)
        last = chain[-1] if chain else {}

        # 可否引用：只有判定明确（none / asserted_contradicts_observed）
        # 且已进链时，才允许把「来源」的说法挂到这条上。
        citable = (level in ("none", "asserted_contradicts_observed")
                   and bool(last))
        if level == "observed_absent":
            why = "无观测 ⇒ 无法判定来源，不得引用其来源说法"
        elif level == "observed_unresolved":
            why = "有观测但判不出 ⇒ 来源不确定，不得引用"
        elif level == "asserted_contradicts_observed":
            why = "断言与观测冲突 ⇒ 可引用「有冲突」这一事实，不得引用其自述来源"
        else:
            why = "断言与观测一致 ⇒ 可引用其来源说法（仅限本机此刻）"

        out.append({
            "record_id": rid,
            "revision": rec.get("revision") if rec else None,
            "record_digest": (last.get("observed_record_digest")
                              if last else None),
            "asserted": rec.get("participation_basis") if rec else None,
            "observed_origin": rec.get("observed_origin") if rec else None,
            "basis_conflict": level,
            "pseudo_first_person": (last.get("pseudo_first_person", False)
                                    if last else False),
            "chained": bool(chain),
            "citable_as_source": citable,
            "citation_limit": why,
        })
    return out


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
