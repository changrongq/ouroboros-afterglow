# -*- coding: utf-8 -*-
"""B 层 L-B 判定层 —— 影响与因果（按 A 层 v0.4 §4 / §6 实现）

绑定（唯一）：
    A层_主设计候选v0.4_合并定稿_Mion_20261128.md     commit 9031df2

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
    if excluded:
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

    返回 { EXCLUDED, remaining: [...], reason }
    """
    # 正对照失灵 ⇒ 不算 EXCLUDED（调用方应先走 INDETERMINATE 出口）
    if not positive_control_ok:
        return {"EXCLUDED": False, "remaining": list(alternative_terms),
                "reason": "POSITIVE_CONTROL_FAILED"}

    # 空跑对照重现了差值 ⇒ 不足以归因
    if negative_control_reproduced:
        return {"EXCLUDED": False, "remaining": list(alternative_terms),
                "reason": "NEGATIVE_CONTROL_REPRODUCED_DRIFT"}

    # 清单里未被排除的项
    excluded_set = set(excluded_terms)
    remaining = [t for t in alternative_terms if t not in excluded_set]

    # 清单为空 ⇒ 没有替代解释需要排除；此时空跑未重现 + 正对照有效 ⇒ EXCLUDED
    # ⚠ 但「清单为空」与「清单已被逐条排除」是两件事，
    #    报告里必须分开写（见 reason）。
    if alternative_terms and remaining:
        return {"EXCLUDED": False, "remaining": remaining,
                "reason": "ALTERNATIVES_NOT_ALL_EXCLUDED"}

    return {"EXCLUDED": True, "remaining": [],
            "reason": ("ALTERNATIVES_ALL_EXCLUDED" if alternative_terms
                       else "NO_ALTERNATIVES_REGISTERED")}


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
    """
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
    if not pathway_registered_and_controlled:
        _require_scope(scope)
        return {"MECH": "INDETERMINATE", "scope": scope,
                "reasons": ["PATHWAY_NOT_CONTROLLED"]}

    # 到这里才允许给出 DETECTED / NOT_DETECTED
    if r_a == r_b:
        return {"MECH": "NOT_DETECTED", "scope": scope, "reasons": []}
    return {"MECH": "DETECTED", "scope": scope, "reasons": []}


# ============================================================ A 层条款 → 断言映射

CLAUSE_MAP: List[Tuple[str, str, str]] = [
    ("B3-SPLIT", "B3 拆成 OBS 与 CLAIM，不混", "v0.4 §4.2"),
    ("B3-TABLE", "判定表五行不跳步", "v0.4 §4.2"),
    ("D-1", "delta=null ⇔ readout_valid=false", "v0.4 §4.3 D-1"),
    ("D-2", "null 不参与数值比较", "v0.4 §4.3 D-2"),
    ("D-3", "readout_valid 判定在 delta 之前", "v0.4 §4.3 D-3"),
    ("EXCL-3", "EXCLUDED 三条同时成立才算", "v0.4 §4.4"),
    ("EXCL-NOT-RUN", "「对照跑过」≠「排除成功」", "v0.4 §4.4"),
    ("ORDER-4", "四步顺序不许跳", "v0.4 §4.5"),
    ("TEXT-STATE", "文本干预与状态干预分开", "v0.4 §4.6"),
    ("E-16-1", "INDETERMINATE 返回值必须含 scope 三项", "v0.4 §4.7"),
    ("E-16-2", "scope 三项不全按实现错误处理", "v0.4 §4.7"),
    ("MECH-DETECTED", "DETECTED 仅在通路受控时可用", "v0.4 §六"),
    ("MECH-CONVERGE", "本阶段通路不可控 ⇒ DETECTED 不可达", "v0.4 §六"),
]

NOT_CHECKED: List[Tuple[str, str]] = [
    ("真实通路是否受控", "UNTESTABLE-1：本阶段不可验（v0.4 §六）"),
    ("归属性", "只检出存在性，不检出「是哪一条」（v0.4 §六）"),
    ("真实历史", "只用合成夹具；未读取任何真实角色历史"),
    ("B1/B2", "被保存 / 被检索不在本层；本层只判 B3/B4/MECH"),
]


def describe() -> Dict[str, Any]:
    return {
        "binding": ["9031df2 (v0.4 合并定稿)"],
        "fields_implemented": [
            "B3-OBS{delta,delivered,readout_valid}",
            "B3-CLAIM", "B4", "MECH", "EXCLUDED", "scope",
        ],
        "clause_map": CLAUSE_MAP,
        "not_checked": NOT_CHECKED,
        "mech_detected_reachable_in_this_stage": False,
        "mech_detected_reason": "通路受控前提不成立且不可验（UNTESTABLE-1）",
    }
