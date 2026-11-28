# -*- coding: utf-8 -*-
"""B 层 L-B 判定层 —— 影响与因果（按 A 层 v0.4 §4 / §6 实现）

绑定（唯一，三件不可只引其一）：
    A层_主设计候选v0.4_合并定稿_Mion_20261128.md     commit 9031df2
    + 附录A（沙盘证据录入）
    + A层_v0.4_勘误004_Mion_20261128.md              commit 731f5a0
      E-18  EXCLUDED 空清单 ⇒ INDETERMINATE（三态补齐）
      E-19  MECH = DETECTED 保留 + 不可达性测试
      E-20  既有红灯必须登记为 OPEN

实现范围（v0.4 §8.1 B-SCOPE-1 明列的字段）：
    B3-OBS    { delta, delivered, readout_valid }
    B3-CLAIM  SUPPORTED | NOT_DETECTED | INDETERMINATE
    B4        ESTABLISHED | INDETERMINATE
    MECH      DETECTED | NOT_DETECTED | INDETERMINATE
    EXCLUDED  bool
    INDETERMINATE 的 scope 进【返回结构】（v0.4 §4.7 E-16）

⚠ 硬边界（v0.4 §六）：
    MECH = DETECTED 只在【输入通路已注册且受控】时可用。
    本阶段「通路受控」不可验（UNTESTABLE-1），
    ⇒ 本实现的 DETECTED 路径【必然收敛到 INDETERMINATE】。
    这不是「做不到所以不做」，是判据本身规定的收敛点。
    ⇒ 更准确地说：本文件的默认路径不会返回 MECH=DETECTED；
      函数保留了 DETECTED 分支，但只有调用方显式声明
      pathway_registered_and_controlled=True 才能到达 ——
      而本阶段该声明不可验，故 T-3 用默认路径验证收敛。
    ⇒ T-3 就是验这个：即使 r_A != r_B，通路未受控 ⇒ INDETERMINATE。

⚠ 本文件不是重要性机制：
    不含任何评分、排序、学习器、真实历史读取（B-SCOPE-2）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ============================================================ 常量（全部来自 A 层）

B3_CLAIM = {"SUPPORTED", "NOT_DETECTED", "INDETERMINATE"}
B4 = {"ESTABLISHED", "INDETERMINATE"}
MECH = {"DETECTED", "NOT_DETECTED", "INDETERMINATE"}

#: v0.4 §4.7 E-16-1：INDETERMINATE 的 scope 必须三项齐全
SCOPE_KEYS = ("this_run", "this_fixture", "this_readout")

#: 勘误004 E-18-2：清单「确实没有替代解释」时，必须显式登记一个哨兵条目，
#: 不得用空列表表达。
NONE_KNOWN = "NONE_KNOWN"

#: 勘误005 E-22-1：本阶段不该被提出的前提。
class UnsupportedPremise(Exception):
    """本阶段不存在的前提被传入。

    ⚠ E-22-1：为什么不是 ValueError ——
      ValueError 读作「你传错了值」，意味着【调用方改一下就能对】。
      而 pathway_registered_and_controlled=True 在本阶段不是值的问题，
      是【这个前提本身不存在】（通路受控不可验，UNTESTABLE-1）。
      ⇒ 区别在于谁来修：值错是调用方修；前提不存在是【能力】没到，
        改参数不会让它成立。
    """


#: 勘误005 E-22-3(b)：本层覆盖穷尽性【未证】。
#: 「已登记 4 个入口」≠「只有 4 个入口」——
#: 这与 E-18 同形：没登记 ≠ 不存在。
COVERAGE = "PARTIAL_FOR_REGISTERED_ENTRIES"
COVERAGE_HOW_MISS_IS_FOUND = (
    "新增入口若未登记进 STAGE_CALL_SITES，E-22-2 的逐项断言不会覆盖它；"
    "发现方式：① 任何 importer 新增 judge_mechanism 调用点时，"
    "代码评审必须同时改这张表（写在 NOT_CHECKED 里）；"
    "② MECH 构造点唯一（仅 judge_mechanism），故【产 MECH 的地方】可穷尽，"
    "但【调用方会不会传 pathway=True】穷不尽 —— 后者靠 E-22-1 抛异常兜住。"
)


# ============================================================ scope（§4.7）

def _scope(run: Optional[str] = None,
           fixture: Optional[str] = None,
           readout: Optional[str] = None) -> Dict[str, Any]:
    """构造 INDETERMINATE 的 scope（v0.4 §4.7 E-16-1）。

    ⚠ E-16-2：scope 三项不全的 INDETERMINATE，按【实现错误】处理。
      ⇒ 本函数不补齐、不猜；缺就给 None，
        INDETERMINATE 的调用方必须校验（见 _require_scope）。
    ⇒ 理由与 C-2 同源：若 scope 只在报告里（L4），
      下游拿到的就是一个裸的 INDETERMINATE（L1 缺失）。
    """
    return {
        "this_run": run,
        "this_fixture": fixture,
        "this_readout": readout,
    }


def _require_scope(scope: Dict[str, Any]) -> None:
    """E-16-2：scope 三项不全 ⇒ 抛错（实现错误，不是判据模糊）。"""
    missing = [k for k in SCOPE_KEYS if scope.get(k) is None]
    if missing:
        raise ValueError(
            "E-16-2 violated: INDETERMINATE 的 scope 缺 %r；"
            "scope 三项不全按实现错误处理" % (missing,))


# ============================================================ delta 三约束（§4.3）

def _check_delta_contract(delta: Any, readout_valid: bool) -> None:
    """§4.3 D-1 / D-2 / D-3 的可执行校验。

    D-1  delta = null 当且仅当 readout_valid = false
    D-2  null 【不参与】任何数值比较（==0 / !=0 / >0 / <0 都不行）
    D-3  readout_valid 的判定在 delta 之前

    ⚠ 为什么写死：
        Python 里 None != 0 → True；None > 0 → TypeError
        ⇒ 若代码写成 `if delta != 0:`，null 会被判成【有差异】。
    """
    # D-1：双向当且仅当
    if not readout_valid and delta is not None:
        raise ValueError(
            "D-1 violated: readout_valid=False 时 delta 必须为 null，实测 %r"
            % (delta,))
    if readout_valid and delta is None:
        raise ValueError(
            "D-1 violated: readout_valid=True 时 delta 不得为 null")

    # D-2：null 不参与数值比较 —— 本实现用显式分支，不做隐式比较。
    #      这里只做类型校验：非 null 时必须是数值（不接受 bool）。
    if delta is not None:
        if isinstance(delta, bool) or not isinstance(delta, (int, float)):
            raise ValueError(
                "D-2 violated: delta 必须是 number|null，实测 %r" % (delta,))

    # D-3：调用顺序由 judge_impact 保证（先判 readout_valid，再碰 delta）


# ============================================================ B3 / B4（§4.2 表）

def judge_impact(b3_obs: Dict[str, Any],
                 excluded: bool,
                 run: Optional[str] = None,
                 fixture: Optional[str] = None,
                 readout: Optional[str] = None) -> Dict[str, Any]:
    """按 v0.4 §4.2 判定表 + §4.5 四步顺序判定 B3-CLAIM / B4。

    输入 b3_obs = { delta, delivered, readout_valid }
    输入 excluded = EXCLUDED（bool，由 evaluate_excluded 得出）

    返回 { B3-OBS, B3-CLAIM, B4, scope }

    §4.5 判定顺序（不许跳）：
        第 1 步  干预是否送达？        未送达 ⇒ 两个 INDETERMINATE
        第 2 步  读出是否有分辨力？    读不出 ⇒ 两个 INDETERMINATE
        第 3 步  记 B3-OBS 的 delta
        第 4 步  判 B3-CLAIM / B4（按 §4.2 表）
    """
    delivered = bool(b3_obs.get("delivered"))
    readout_valid = bool(b3_obs.get("readout_valid"))
    delta = b3_obs.get("delta")

    # D-1 / D-2 先校验（D-3：readout_valid 在 delta 之前已取出）
    _check_delta_contract(delta, readout_valid)

    scope = _scope(run, fixture, readout)
    obs = {"delta": delta, "delivered": delivered, "readout_valid": readout_valid}

    # 第 1 步：未送达
    if not delivered:
        _require_scope(scope)
        return {"B3-OBS": obs, "B3-CLAIM": "INDETERMINATE",
                "B4": "INDETERMINATE", "scope": scope}

    # 第 2 步：读出无分辨力
    if not readout_valid:
        _require_scope(scope)
        return {"B3-OBS": obs, "B3-CLAIM": "INDETERMINATE",
                "B4": "INDETERMINATE", "scope": scope}

    # 第 3 步已由 obs 记录；第 4 步按 §4.2 表
    #   此时 D-1 已保证 delta 不是 None，可安全做数值比较
    if delta == 0:
        # delta = 0 ⇒ NOT_DETECTED / B4 = INDETERMINATE
        # 措辞：只许写「该读出在此次对照未检出差异」
        _require_scope(scope)
        return {"B3-OBS": obs, "B3-CLAIM": "NOT_DETECTED",
                "B4": "INDETERMINATE", "scope": scope}

    # delta != 0
    # ⚠ 勘误005 E-21-2：本层内不得对 EXCLUDED 做布尔化消费。
    #   `if excluded:` 会把 None 和 False 混在一起（两者在布尔语境相同，
    #   但语义相反：None=判不出 / False=判出了没排除成功）。
    #   ⇒ 必须显式三路。
    if excluded is None:
        _require_scope(scope)
        return {"B3-OBS": obs, "B3-CLAIM": "SUPPORTED",
                "B4": "INDETERMINATE", "scope": scope,
                "unexcluded": True,
                "excluded_undetermined": True}
    if excluded is True:
        return {"B3-OBS": obs, "B3-CLAIM": "SUPPORTED",
                "B4": "ESTABLISHED", "scope": scope}

    # delta != 0 且 EXCLUDED = FALSE ⇒ SUPPORTED / INDETERMINATE（列未排除项）
    _require_scope(scope)
    return {"B3-OBS": obs, "B3-CLAIM": "SUPPORTED",
            "B4": "INDETERMINATE", "scope": scope,
            "unexcluded": True}


# ============================================================ EXCLUDED（§4.4）

def evaluate_excluded(negative_control_reproduced: bool,
                      alternative_terms: List[str],
                      excluded_terms: List[str],
                      positive_control_ok: bool) -> Dict[str, Any]:
    """§4.4：EXCLUDED = TRUE 当且仅当三条同时成立。

    ① 已登记的替代解释清单【逐条】被有效排除，且
    ② 空跑对照未重现差值，且
    ③ 正对照有效

    对照检出了足以解释差值的漂移        ⇒ EXCLUDED = FALSE
    清单里有任何一条未被排除            ⇒ EXCLUDED = FALSE
    正对照失灵                          ⇒ 先进入 INDETERMINATE 出口

    ⚠ 「对照跑过」不等于「排除成功」。
      本函数按【清单逐条已被排除】判定，不按「跑过对照」判定。

    ⚠ 勘误004 E-18（本版更正，上一版实现为 TRUE）：
      「替代解释清单为空」在现有字段上有两种不可区分的情形：
        (a) 确实没有替代解释   ⇒ 「逐条排除」平凡成立
        (b) 没有人登记过       ⇒ 我们不知道有没有
      ⇒ 空清单产生 TRUE，会让 EXCLUDED 在「我们没想过」的时候变成 TRUE。
        那正是 §4.4 要防的同类错误：把「没登记」当成「不存在」。
      ⇒ E-18-1 清单为空 ⇒ EXCLUDED = INDETERMINATE，
                       reason = NO_ALTERNATIVES_REGISTERED
      ⇒ E-18-2 若确实没有替代解释，必须显式登记哨兵条目 NONE_KNOWN，
               不得用空列表表达
      ⇒ E-18-3 空列表的唯一含义是「没人登记」，因此【永远不能产生 TRUE】

    返回 { EXCLUDED: True|False|None, INDETERMINATE: bool,
           remaining: [...], reason }
    ⇒ ⚠ 三态表达：EXCLUDED 为 None 且 INDETERMINATE=True 表示「判不出」。
      调用方若只看真假，会把「判不出」读成「FALSE」，所以两个字段都要看。
    ⇒ 每个出口都过一遍 check_e21_invariant（E-21-1 双向不变量）。
    """
    return _finalize_excluded(_excl_branch(
        negative_control_reproduced, alternative_terms,
        excluded_terms, positive_control_ok))


def _excl_branch(negative_control_reproduced, alternative_terms,
                 excluded_terms, positive_control_ok) -> Dict[str, Any]:
    """evaluate_excluded 的分支计算（不含不变量校验）。"""
    # 正对照失灵 ⇒ 不算 EXCLUDED（调用方应先走 INDETERMINATE 出口）
    if not positive_control_ok:
        return {"EXCLUDED": False, "INDETERMINATE": False,
                "remaining": list(alternative_terms),
                "reason": "POSITIVE_CONTROL_FAILED"}

    # 空跑对照重现了差值 ⇒ 不足以归因
    if negative_control_reproduced:
        return {"EXCLUDED": False, "INDETERMINATE": False,
                "remaining": list(alternative_terms),
                "reason": "NEGATIVE_CONTROL_REPRODUCED_DRIFT"}

    # E-18-1：清单为空 ⇒ INDETERMINATE（不是 TRUE）
    if not alternative_terms:
        return {"EXCLUDED": None, "INDETERMINATE": True,
                "remaining": [],
                "reason": "NO_ALTERNATIVES_REGISTERED"}

    # 清单里未被排除的项
    excluded_set = set(excluded_terms)
    remaining = [t for t in alternative_terms if t not in excluded_set]

    if remaining:
        return {"EXCLUDED": False, "INDETERMINATE": False,
                "remaining": remaining,
                "reason": "ALTERNATIVES_NOT_ALL_EXCLUDED"}

    # E-18-3：非空清单且逐条排除 ⇒ 这时才允许 TRUE
    return {"EXCLUDED": True, "INDETERMINATE": False,
            "remaining": [], "reason": "ALTERNATIVES_ALL_EXCLUDED"}


def _finalize_excluded(result: Dict[str, Any]) -> Dict[str, Any]:
    """E-21-1：每个出口都做双向不变量校验，再返回。"""
    check_e21_invariant(result)
    return result


# ============================================================ MECH（§六）

def judge_mechanism(r_a: Any, r_b: Any,
                    pathway_registered_and_controlled: bool,
                    drift_control_explains: bool,
                    readout_has_resolution: bool,
                    run: Optional[str] = None,
                    fixture: Optional[str] = None,
                    readout: Optional[str] = None) -> Dict[str, Any]:
    """§六 MECH 三态判定。

    MECH =
      NOT_DETECTED   r_A == r_B，且输入通路已注册受控，且漂移对照未解释差异
      DETECTED       r_A != r_B，且输入通路已注册受控，且漂移对照未解释差异
      INDETERMINATE  以下任一：
                       · 输入通路未受控
                       · 空跑漂移足以解释差值
                       · 读出无分辨力

    ⚠ 关键一句（v0.4 §六）：
      DETECTED 只在【输入通路已注册且受控】时可用。否则一律 INDETERMINATE
      —— 即使 r_A != r_B。

    ⚠ 本阶段 pathway_registered_and_controlled 恒为 False 且不可验
      （UNTESTABLE-1）⇒ DETECTED 分支【在本阶段不可达】。
      本函数保留该分支是为了让判据完整；
      测试 T-3 必须验：即使 r_A != r_B，通路未受控 ⇒ INDETERMINATE。

    ⚠ 勘误005 E-22-1（本版加强）：
      传 pathway_registered_and_controlled=True ⇒ 抛 UnsupportedPremise。
      理由：这在本阶段不是「可以成立的输入」，而是【不该被提出的前提】。
      上一版靠「没有调用方会传 True」来保证不可达 —— 那是【纪律】，
      不是【机制】：新调用方传 True 就能拿到 DETECTED，而没有任何东西阻止。
      ⇒ 改成抛异常后，不可达从「靠没人这么调」变成「这么调就炸」。
    """
    # E-22-1：该前提本阶段不存在 ⇒ 抛，不返回
    if pathway_registered_and_controlled:
        raise UnsupportedPremise(
            "E-22-1: pathway_registered_and_controlled=True 在本阶段不可成立"
            "（通路受控不可验，UNTESTABLE-1）。"
            "这不是值错误，是本阶段没有这个能力 —— 改参数不会让它成立。")

    scope = _scope(run, fixture, readout)

    # 任一前置不成立 ⇒ INDETERMINATE（顺序不影响结论，但逐一列出）
    if not readout_has_resolution:
        _require_scope(scope)
        return {"MECH": "INDETERMINATE", "scope": scope,
                "reasons": ["READOUT_NO_RESOLUTION"]}
    if drift_control_explains:
        _require_scope(scope)
        return {"MECH": "INDETERMINATE", "scope": scope,
                "reasons": ["DRIFT_CONTROL_EXPLAINS"]}

    # 到这里 pathway 必为 False（True 已在上方抛异常）
    _require_scope(scope)
    return {"MECH": "INDETERMINATE", "scope": scope,
            "reasons": ["PATHWAY_NOT_CONTROLLED"]}


def _branch_unreachable(r_a: Any, r_b: Any) -> Dict[str, Any]:
    """保留 DETECTED / NOT_DETECTED 分支的判据定义（E-19-1：不删除）。

    ⚠ 这个函数【当前没有任何调用路径】。它存在的唯一理由是：
      判据上 DETECTED 是有定义的（§六：通路受控时可用），只是本阶段够不到。
      删掉 = 假装这个分支不需要存在；
      将来补上通路受控能力时，没有人会记得要把它加回来（与 C1-TYPE-1 同源）。

    ⇒ 若真要调用它，必须先经过 E-22-1 的检查（即在拿到通路受控能力后，
      重新审 E-22-1 是否还成立）。
    """
    m = "NOT_DETECTED" if r_a == r_b else "DETECTED"
    return {"MECH": m}


# ============================================================ E-19-2 不可达性

#: 本阶段调用方【实际可能】传入的 MECH 参数组合。
#:
#: ⚠ E-19-2 要求「断言本阶段任何调用路径都不产生 DETECTED」。
#:   但「任何调用路径」不能靠枚举全部可能的参数组合（那是数学上无限的），
#:   只能靠【枚举本阶段实际存在的调用入口】—— 即下面这张表。
#:
#: ⇒ 这张表的每一项都必须能指认到本仓库里的一处真实调用点。
#:   若某天新增了一个调用点而没有加进这张表，
#:   那不可达性断言就不再覆盖它 —— 这是本表的已知边界，写在 NOT_CHECKED 里。
#:
#: 每一项 = (调用点名称, 参数 dict, 依据)
STAGE_CALL_SITES: List[Tuple[str, Dict[str, Any], str]] = [
    (
        "T-3 默认路径",
        {"r_a": "BLUE", "r_b": "RED",
         "pathway_registered_and_controlled": False,
         "drift_control_explains": False,
         "readout_has_resolution": True},
        "本阶段通路受控不可验（UNTESTABLE-1）⇒ 恒传 False",
    ),
    (
        "无差值 + 通路未受控",
        {"r_a": "BLUE", "r_b": "BLUE",
         "pathway_registered_and_controlled": False,
         "drift_control_explains": False,
         "readout_has_resolution": True},
        "同上；验 NOT_DETECTED 也走不到",
    ),
    (
        "有差值 + 漂移可解释",
        {"r_a": "BLUE", "r_b": "RED",
         "pathway_registered_and_controlled": False,
         "drift_control_explains": True,
         "readout_has_resolution": True},
        "空跑漂移先收敛到 INDETERMINATE",
    ),
    (
        "有差值 + 读出无分辨力",
        {"r_a": "BLUE", "r_b": "RED",
         "pathway_registered_and_controlled": False,
         "drift_control_explains": False,
         "readout_has_resolution": False},
        "读出无分辨力先收敛到 INDETERMINATE",
    ),
]


def scan_stage_call_sites() -> Dict[str, Any]:
    """E-22-2：逐一跑本阶段每个登记入口，收集 MECH 取值。

    返回 { results: [(name, MECH)], detected_reachable: bool, coverage: str }
    ⇒ detected_reachable 必须为 False。
    ⇒ 这是【测试断言的依据】，不是报告里的说明文字。

    ⚠ E-22-3：本函数的覆盖【不穷尽】，COVERAGE 标
      PARTIAL_FOR_REGISTERED_ENTRIES。理由见 COVERAGE_HOW_MISS_IS_FOUND。
    """
    results = []
    for name, kwargs, _why in STAGE_CALL_SITES:
        d = judge_mechanism(run="scan", fixture=name, readout="scan", **kwargs)
        results.append((name, d["MECH"]))
    reachable = any(m == "DETECTED" for _n, m in results)
    return {"results": results, "detected_reachable": reachable,
            "coverage": COVERAGE}


def assert_unsupported_premise_raises() -> List[Tuple[str, bool]]:
    """E-22-2：逐项断言 pathway=True 会抛【同一个】异常类型。

    返回 [(入口名, 是否抛 UnsupportedPremise)]
    ⇒ 调用方（测试）断言每一项都为 True，且异常类型一致。
    """
    out = []
    for name, kwargs, _why in STAGE_CALL_SITES:
        call = dict(kwargs)
        call["pathway_registered_and_controlled"] = True
        try:
            judge_mechanism(run="scan", fixture=name, readout="scan", **call)
            out.append((name, False))
        except UnsupportedPremise:
            out.append((name, True))
        except Exception:
            # 抛了别的类型 ⇒ 不算通过（E-22-1 要求同一个异常）
            out.append((name, False))
    return out


# ============================================================ A 层条款 → 断言映射

CLAUSE_MAP: List[Tuple[str, str, str]] = [
    ("B3-SPLIT", "B3 拆成 OBS 与 CLAIM，不混", "v0.4 §4.2"),
    ("B3-TABLE", "判定表五行不跳步", "v0.4 §4.2"),
    ("D-1", "delta=null ⇔ readout_valid=false", "v0.4 §4.3 D-1"),
    ("D-2", "null 不参与数值比较", "v0.4 §4.3 D-2"),
    ("D-3", "readout_valid 判定在 delta 之前", "v0.4 §4.3 D-3"),
    ("EXCL-3", "EXCLUDED 三条同时成立才算", "v0.4 §4.4"),
    ("EXCL-NOT-RUN", "「对照跑过」≠「排除成功」", "v0.4 §4.4"),
    ("E-18-1", "清单为空 ⇒ EXCLUDED=INDETERMINATE",
     "勘误004 E-18-1"),
    ("E-18-3", "空列表永不产生 TRUE（三态补齐）", "勘误004 E-18-3"),
    ("E-21-1", "双向不变量：EXCLUDED is None ⇔ INDETERMINATE is True",
     "勘误005 E-21-1"),
    ("E-21-2", "本层内不得布尔化消费 EXCLUDED", "勘误005 E-21-2"),
    ("ORDER-4", "四步顺序不许跳", "v0.4 §4.5"),
    ("TEXT-STATE", "文本干预与状态干预分开", "v0.4 §4.6"),
    ("E-16-1", "INDETERMINATE 返回值必须含 scope 三项", "v0.4 §4.7"),
    ("E-16-2", "scope 三项不全按实现错误处理", "v0.4 §4.7"),
    ("MECH-DETECTED", "DETECTED 仅在通路受控时可用", "v0.4 §六"),
    ("E-19-1", "DETECTED 保留在枚举里（不删除）", "勘误004 E-19-1"),
    ("E-22-1", "pathway=True ⇒ 抛 UnsupportedPremise（不是 ValueError）",
     "勘误005 E-22-1"),
    ("E-22-2", "入口清单显式登记 + 逐个断言抛同一异常", "勘误005 E-22-2"),
    ("E-22-3", "穷尽性依据：标 PARTIAL_FOR_REGISTERED_ENTRIES",
     "勘误005 E-22-3(b)"),
]

NOT_CHECKED: List[Tuple[str, str]] = [
    ("真实通路是否受控", "UNTESTABLE-1：本阶段不可验（v0.4 §六）"),
    ("归属性", "只检出存在性，不检出「是哪一条」（v0.4 §六）"),
    ("真实历史", "只用合成夹具；未读取任何真实角色历史"),
    ("B1/B2", "被保存 / 被检索不在本层；本层只判 B3/B4/MECH"),
    ("SCAN 表外的新调用点",
     "scan_stage_call_sites 只覆盖 STAGE_CALL_SITES 列出的入口；"
     "新增调用点未登记进该表时，不可达性断言不覆盖它（E-19-2 已知边界）"),
]


def check_e21_invariant(result: Dict[str, Any]) -> None:
    """勘误005 E-21-1：双向不变量（可执行校验）。

        EXCLUDED is None          ⇔  INDETERMINATE is True
        EXCLUDED in {True, False}  ⇒  INDETERMINATE is False

    ⚠ 为什么必须【双向】：
      单向（None ⇒ flag=True）允许 flag=True 而 value=False 的坏状态存在。
      ⇒ 那会让「判不出」标记挂在一个已判定的值上，读的人无从判断哪个对。
    """
    value = result.get("EXCLUDED")
    flag = result.get("INDETERMINATE")

    # 必须是三态之一，不是别的
    if value not in (True, False, None):
        raise ValueError(
            "E-21-1 violated: EXCLUDED 必须 ∈ {True, False, None}，实测 %r"
            % (value,))
    if not isinstance(flag, bool):
        raise ValueError(
            "E-21-1 violated: INDETERMINATE 必须是 bool，实测 %r" % (flag,))

    is_none = (value is None)
    if is_none != flag:
        raise ValueError(
            "E-21-1 violated（双向）：EXCLUDED is None=%r 但 "
            "INDETERMINATE=%r；两者必须同时成立或同时不成立"
            % (is_none, flag))


def describe() -> Dict[str, Any]:
    return {
        "binding": [
            "9031df2 (v0.4 合并定稿)",
            "附录A",
            "731f5a0 (勘误004: E-18 / E-19 / E-20)",
            "cc0b6fb (勘误005: E-21 / E-22 / E-23)",
        ],
        "fields_implemented": [
            "B3-OBS{delta,delivered,readout_valid}",
            "B3-CLAIM", "B4", "MECH", "EXCLUDED", "scope",
        ],
        "clause_map": CLAUSE_MAP,
        "not_checked": NOT_CHECKED,
        "mech_detected_reachable_in_this_stage": False,
        "mech_detected_enforcement": "E-22-1：pathway=True 抛 UnsupportedPremise",
        "mech_detected_assertion": "test_blayer_batch1.py::t8 / t9",
        "coverage": COVERAGE,
        "coverage_how_miss_is_found": COVERAGE_HOW_MISS_IS_FOUND,
        "excluded_empty_list": "INDETERMINATE（勘误004 E-18-1）",
        "excluded_shape": "EXCLUDED ∈ {True,False,None} + INDETERMINATE: bool",
        "excluded_invariant": "E-21-1 双向：None ⇔ flag=True",
    }
