# -*- coding: utf-8 -*-
"""B 层第一批测试 —— T-1..T-6e（共 8 条），v0.4 绑定，全部正向断言

绑定：A层_主设计候选v0.4_合并定稿 (9031df2) + 附录A

⚠ 上一轮（v0.3 绑定）的 T-2/T-3/T-5/T-6 写成了【负向断言】
  （"本层不应产出 B3-*/MECH 字段"）。那是范围错误：
  B-SCOPE-1 明列了 B3-OBS / B3-CLAIM / B4 / MECH / EXCLUDED。
  Mion 已撤回"改标 N/A"的处置（d59a440 §〇）。
  ⇒ 本文件把四条改为【正向断言，有具体预期值】。

⚠ 每条测试都必须能【真的变红】：
  见 test_blayer_batch1_mutation.py。

报告开头固定四行见文件末尾 REPORT_HEADER。
"""
from __future__ import annotations

import ast
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bfjudge as BJ
import lbjudge as LB

RESULTS = []


def case(cid, name):
    def deco(fn):
        def run():
            try:
                d = fn()
                RESULTS.append((cid, name, True, d))
                print("  [PASS] %s %s — %s" % (cid, name, d))
            except AssertionError as e:
                RESULTS.append((cid, name, False, str(e)))
                print("  [FAIL] %s %s — %s" % (cid, name, e))
            except Exception as e:
                RESULTS.append((cid, name, False, repr(e)))
                print("  [ERR ] %s %s — %s" % (cid, name, e))
        return run
    return deco


def rec(**kw):
    """合成记录（L-A 侧）。未给的字段为 None。"""
    base = {
        "record_id": "r1", "content": "x",
        "source_kind": "user_utterance", "source_ref": "utt/r1",
        "participant_id": "A", "participation_basis": "first_person_report",
        "basis_ref": "utt/r1", "commitment_state": "not_a_commitment",
        "observed_origin": None, "basis_conflict": None,
    }
    base.update(kw)
    return base


def _open_ok(ref):
    return True


def _open_fail(ref):
    return False


# ============================================================ T-1（L-A）

@case("T-1", "A3 事件不匹配 ⇒ A3=PASS + NOT_COVERED + multi_ref")
def t1():
    """v0.4 §3.3 + §3.4 + §8.4 T-1。

    A3 窄口径只签「存在一条可打开的引用」。
    ⇒ 即使引用指向的是别的记录（事件不匹配），A3 仍 PASS。
    ⇒ 报告必须同时写 match 与 multi_ref 两个值。
    """
    r = rec(observed_origin="human_input", basis_conflict="none",
            source_ref="utt/r1", _event="E8")  # 记录谈 E7，引用指向 E8
    d = BJ.decide_admission(r, opener=_open_ok)

    a3 = d["per_rule"]["A3"]
    assert a3["verdict"] == "PASS", \
        "A3 应 PASS（窄口径只判能打开），实测 %r" % (a3,)
    assert a3["match"] == "NOT_COVERED", \
        "A3.match 应为 NOT_COVERED（事件匹配本版不做，§3.3）"
    assert a3["multi_ref"] == "NOT_TRIGGERABLE_BY_TYPE", \
        "A3.multi_ref 应为 NOT_TRIGGERABLE_BY_TYPE（§3.4 C1-TYPE-2）"
    assert d["admitted"] is True
    assert d["unknowns"] == []
    return "A3=PASS + match=NOT_COVERED + multi_ref=NOT_TRIGGERABLE_BY_TYPE"


# ============================================================ T-2（L-B）

@case("T-2", "两臂同蓝、替代未排 ⇒ delta=0 / NOT_DETECTED / B4=INDETERMINATE")
def t2():
    """v0.4 §4.2 判定表 + §8.4 T-2。

    夹具：delivered=true, readout_valid=true, delta=0, EXCLUDED=false
    期望：B3-CLAIM == NOT_DETECTED
          B4 == INDETERMINATE
          措辞字段只许说「此次对照、该读出」—— 不是「没有影响」
    """
    obs = {"delivered": True, "readout_valid": True, "delta": 0}
    d = LB.judge_impact(obs, excluded=False,
                        run="run-1", fixture="T-2", readout="readout-1")

    assert d["B3-OBS"] == {"delta": 0, "delivered": True, "readout_valid": True}, \
        "B3-OBS 应逐字段等于输入，实测 %r" % (d["B3-OBS"],)
    assert d["B3-CLAIM"] == "NOT_DETECTED", \
        "delta=0 ⇒ B3-CLAIM=NOT_DETECTED，实测 %r" % d["B3-CLAIM"]
    assert d["B4"] == "INDETERMINATE", \
        "delta=0 ⇒ B4=INDETERMINATE（§4.2 表），实测 %r" % d["B4"]

    # §4.2 措辞纪律：B3-CLAIM 不是「没有影响」
    assert "没有影响" not in d["B3-CLAIM"]
    assert "NOT_DETECTED" != "NO_EFFECT", \
        "NOT_DETECTED 是「未检出」，不是「无影响」"

    # INDETERMINATE 出口必须带 scope（§4.7 E-16-1）
    for k in LB.SCOPE_KEYS:
        assert d["scope"].get(k) is not None, \
            "E-16-1 violated: scope 缺 %r" % k
    return "delta=0 ⇒ NOT_DETECTED / B4=INDETERMINATE / scope 齐全"


# ============================================================ T-3（L-B MECH）

@case("T-3", "一臂注入 E 向量 ⇒ MECH=INDETERMINATE（即使有差值）")
def t3():
    """v0.4 §六 + §8.4 T-3 + 勘误005 E-22-1。

    ⇒ r_A != r_B，但输入通路未受控 ⇒ MECH = INDETERMINATE。
    本阶段通路受控不可验（UNTESTABLE-1）⇒ DETECTED 分支【不可达】。

    ⚠ 上一版这里还有一条「反向证明」：传 pathway=True 应得 DETECTED。
      勘误005 E-22-1 之后，传 True 改为抛 UnsupportedPremise，
      ⇒ 那条反向证明【走不通了】，而且必须走不通 ——
        因为「通路受控」在本阶段不是能成立的输入。
      ⇒ 判据完整性改由 _branch_unreachable 单独承载（见 T-9 与 E-19-1）。
    """
    d = LB.judge_mechanism(
        r_a="BLUE", r_b="RED",                    # 确实有差值
        pathway_registered_and_controlled=False,  # 通路未受控
        drift_control_explains=False,
        readout_has_resolution=True,
        run="run-1", fixture="T-3", readout="readout-1")

    assert d["MECH"] == "INDETERMINATE", \
        "通路未受控 ⇒ MECH 必为 INDETERMINATE（即使 r_A != r_B），实测 %r" \
        % d["MECH"]
    assert "PATHWAY_NOT_CONTROLLED" in d["reasons"], \
        "INDETERMINATE 应给出理由 PATHWAY_NOT_CONTROLLED，实测 %r" % d["reasons"]

    # 判据完整性：DETECTED 分支的定义仍存在（E-19-1 不删除），
    # 但只能从 _branch_unreachable 取到 —— 不经 judge_mechanism。
    assert LB._branch_unreachable("BLUE", "RED")["MECH"] == "DETECTED", \
        "判据定义里 DETECTED 必须仍可表达（供将来通路受控时使用）"
    assert LB._branch_unreachable("BLUE", "BLUE")["MECH"] == "NOT_DETECTED"

    # 而本阶段的公开入口不允许得到 DETECTED（E-22-1 兜住）
    assert LB.describe()["mech_detected_reachable_in_this_stage"] is False
    return "r_A!=r_B + 通路未受控 ⇒ INDETERMINATE(PATHWAY_NOT_CONTROLLED)"


# ============================================================ T-4（L-A）

@case("T-4", "Q7a：system_dispatch ⇒ A1=UNKNOWN, A2=FAIL, A3=PASS, unknowns=['A1']")
def t4():
    """v0.4 §3.6 Q7a + §8.4 T-4。B-REQ-1 的主战场。

    ⚠ 只断言 admitted=false 不够 —— 把 A2 错写成 PASS 也照样绿（§3.5 S5）。
    """
    r = rec(observed_origin="system_dispatch",
            basis_conflict="asserted_contradicts_observed",
            source_ref="utt/r1")
    d = BJ.decide_admission(r, opener=_open_ok)

    assert d["per_rule"]["A1"]["verdict"] == "UNKNOWN", d["per_rule"]["A1"]
    assert d["per_rule"]["A1"]["reason"] == "DISPATCH_NOT_QUALIFIED", \
        "A1 reason 应为 DISPATCH_NOT_QUALIFIED（已知但不够格），实测 %r" \
        % d["per_rule"]["A1"]["reason"]
    assert d["per_rule"]["A2"]["verdict"] == "FAIL", d["per_rule"]["A2"]
    assert d["per_rule"]["A3"]["verdict"] == "PASS", d["per_rule"]["A3"]
    assert d["admitted"] is False
    assert d["unknowns"] == ["A1"], "unknowns 应为 ['A1']，实测 %r" % d["unknowns"]

    # S5：三项全部产出
    assert set(d["per_rule"]) == {"A1", "A2", "A3"}, \
        "S5 violated: per_rule 未产出全部三项"
    # ▲ v0.4 新增：A3 也要有 multi_ref（即使 PASS 也要写值）
    assert d["per_rule"]["A3"]["multi_ref"] == "NOT_TRIGGERABLE_BY_TYPE"
    return "A1=UNKNOWN(DISPATCH_NOT_QUALIFIED)/A2=FAIL/A3=PASS/unknowns=['A1']"


# ============================================================ T-5（L-B）

@case("T-5", "delta=null 落点 ⇒ readout_valid=false / delta=null / 两个 INDETERMINATE")
def t5():
    """v0.4 §4.3 D-1..D-3 + §8.4 T-5。

    readout_valid=false ⇒ delta 必为 null ⇒ B3-CLAIM 与 B4 都 INDETERMINATE。
    """
    obs = {"delivered": True, "readout_valid": False, "delta": None}
    d = LB.judge_impact(obs, excluded=False,
                        run="run-1", fixture="T-5", readout="readout-1")

    assert d["B3-OBS"]["delta"] is None, "delta 应为 null"
    assert d["B3-OBS"]["readout_valid"] is False
    assert d["B3-CLAIM"] == "INDETERMINATE", \
        "readout_valid=false ⇒ B3-CLAIM=INDETERMINATE，实测 %r" % d["B3-CLAIM"]
    assert d["B4"] == "INDETERMINATE"

    # D-1 反向：readout_valid=False 却给 delta=0.5 ⇒ 必须抛错
    caught = False
    try:
        LB.judge_impact({"delivered": True, "readout_valid": False,
                         "delta": 0.5}, excluded=False,
                        run="r", fixture="T-5", readout="o")
    except ValueError as e:
        caught = "D-1" in str(e)
    assert caught, "D-1 violated: readout_valid=False 时 delta 非 null 必须抛错"

    # D-1 另一反向：readout_valid=True 却给 delta=None ⇒ 必须抛错
    caught2 = False
    try:
        LB.judge_impact({"delivered": True, "readout_valid": True,
                         "delta": None}, excluded=False,
                        run="r", fixture="T-5", readout="o")
    except ValueError as e:
        caught2 = "D-1" in str(e)
    assert caught2, "D-1 violated: readout_valid=True 时 delta 为 null 必须抛错"
    return "readout_valid=false + delta=null ⇒ 两个 INDETERMINATE；D-1 双向可执行"


# ============================================================ T-5c（L-B）

@case("T-5c", "反证：None 被当数值比较 ⇒ 必须抛错或走错分支")
def t5c():
    """v0.4 §4.3 D-2 + §8.4 T-5c。

    Python 里 None != 0 为 True；None > 0 抛 TypeError。
    ⇒ 若实现用 `if delta != 0:` 判「有差异」，null 会被判成「有差异」。
    ⇒ 本测试把这条【实现错误】变成【测试红】。
    """
    # ① 语言层的坑存在
    assert (None != 0) is True, "None != 0 应为 True（这是坑本身）"
    raised = False
    try:
        _ = (None > 0)
    except TypeError:
        raised = True
    assert raised, "None > 0 应抛 TypeError"

    # ② 本实现不踩这个坑：null + readout_valid=true 会先被 D-1 拦下
    caught = False
    try:
        LB.judge_impact({"delivered": True, "readout_valid": True,
                         "delta": None}, excluded=False,
                        run="r", fixture="T-5c", readout="o")
    except ValueError as e:
        caught = "D-1" in str(e)
    assert caught, "本实现必须显式拒绝 null，不得让它进到 delta != 0 的比较"

    # ③ 变异样本：把判据写成 `delta != 0` 的坏实现会被 T-5 抓红
    def broken(delta):
        # 故意错：不判 null
        return "HAS_DIFF" if delta != 0 else "NO_DIFF"

    assert broken(None) == "HAS_DIFF", \
        "坏实现会把 null 判成有差异 —— 这正是 T-5 要抓的（此处断言坏实现的行为）"
    # 而正确实现断言：null 不得以任何形式参与判断 ⇒ T-5 的 D-1 已覆盖
    return "None!=0 为 True（坑确实存在）；本实现由 D-1 显式拒绝"


# ============================================================ T-6（L-B EXCLUDED）

@case("T-6", "空跑重现漂移 ⇒ EXCLUDED=FALSE / delta 保留非零 / B4=INDETERMINATE")
def t6():
    """v0.4 §4.4 + §8.4 T-6。

    夹具：delta != 0，空跑对照重现了差值，替代解释清单未排除完
    期望：EXCLUDED == FALSE
          delta 保留非零（不被清零、不被抹掉）
          B4 == INDETERMINATE
          列出未排除项
    """
    alternatives = ["seasonal_drift", "readout_calibration"]
    ex = LB.evaluate_excluded(
        negative_control_reproduced=True,   # 空跑重现了
        alternative_terms=alternatives,
        excluded_terms=[],                  # 一条都没排除
        positive_control_ok=True)
    assert ex["EXCLUDED"] is False, "空跑重现 ⇒ EXCLUDED 必为 False"
    assert ex["reason"] == "NEGATIVE_CONTROL_REPRODUCED_DRIFT", ex["reason"]

    d = LB.judge_impact(
        {"delivered": True, "readout_valid": True, "delta": 0.3},
        excluded=ex["EXCLUDED"],
        run="run-1", fixture="T-6", readout="readout-1")

    assert d["B3-OBS"]["delta"] == 0.3, \
        "delta 必须保留非零原值（不得清零），实测 %r" % d["B3-OBS"]["delta"]
    assert d["B3-CLAIM"] == "SUPPORTED", d["B3-CLAIM"]
    assert d["B4"] == "INDETERMINATE", \
        "EXCLUDED=False ⇒ B4 必为 INDETERMINATE，实测 %r" % d["B4"]
    assert d.get("unexcluded") is True, "必须标出「列未排除项」"
    # 未排除项要能被列出（§4.4「列未排除项」）
    assert ex["remaining"] == alternatives, \
        "未排除项应逐条列出，实测 %r" % ex["remaining"]
    return "EXCLUDED=FALSE / delta 保留 0.3 / B4=INDETERMINATE / 未排除项逐条列出"


# ============================================================ T-6e（L-B EXCLUDED）

@case("T-6e", "对照跑过且确实排除 ⇒ EXCLUDED=TRUE / B4=ESTABLISHED")
def t6e():
    """v0.4 §4.4 + §8.4 T-6e。

    夹具：delta=0.3，空跑未重现，替代解释清单逐条排除完毕，正对照有效
    期望：EXCLUDED == TRUE；B4 == ESTABLISHED

    ⇒ 没有这条，EXCLUDED 恒 False 也能全绿。
    """
    alternatives = ["seasonal_drift", "readout_calibration"]
    ex = LB.evaluate_excluded(
        negative_control_reproduced=False,   # 空跑未重现
        alternative_terms=alternatives,
        excluded_terms=alternatives,         # 逐条已排除
        positive_control_ok=True)
    assert ex["EXCLUDED"] is True, \
        "三条同时成立 ⇒ EXCLUDED 必为 True，实测 reason=%r" % ex["reason"]
    assert ex["remaining"] == []

    d = LB.judge_impact(
        {"delivered": True, "readout_valid": True, "delta": 0.3},
        excluded=ex["EXCLUDED"],
        run="run-1", fixture="T-6e", readout="readout-1")
    assert d["B3-CLAIM"] == "SUPPORTED"
    assert d["B4"] == "ESTABLISHED", \
        "delta!=0 且 EXCLUDED=TRUE ⇒ B4=ESTABLISHED，实测 %r" % d["B4"]

    # 反例：清单里有一条没排除 ⇒ EXCLUDED 必须翻回 False
    ex2 = LB.evaluate_excluded(
        negative_control_reproduced=False,
        alternative_terms=alternatives,
        excluded_terms=[alternatives[0]],   # 只排除一条
        positive_control_ok=True)
    assert ex2["EXCLUDED"] is False, \
        "有未排除项 ⇒ EXCLUDED 必为 False（否则「逐条排除」形同虚设）"
    assert ex2["remaining"] == [alternatives[1]]

    # 反例：正对照失灵 ⇒ 不得 EXCLUDED
    ex3 = LB.evaluate_excluded(
        negative_control_reproduced=False,
        alternative_terms=alternatives,
        excluded_terms=alternatives,
        positive_control_ok=False)
    assert ex3["EXCLUDED"] is False
    assert ex3["reason"] == "POSITIVE_CONTROL_FAILED"
    return "EXCLUDED=TRUE ⇒ B4=ESTABLISHED；漏一条/正对照失灵均必须翻 False"


# ============================================================ T-7（E-18）

@case("T-7", "E-18 清单为空 ⇒ EXCLUDED=INDETERMINATE（不是 TRUE）")
def t7():
    """勘误004 E-18-1 / E-18-3。

    上一版（6b4e3e5）我把「清单为空」判成 TRUE（NO_ALTERNATIVES_REGISTERED）。
    Mion 更正：空清单有两种不可区分的情形 ——
      (a) 确实没有替代解释 / (b) 没有人登记过
    ⇒ TRUE 会让「没登记」变成「不存在」，与 §4.4 要防的是同类错。

    E-18-3：空列表【永远不能产生 TRUE】。
    """
    # 三条前置全成立，唯独清单为空
    ex = LB.evaluate_excluded(
        negative_control_reproduced=False,
        alternative_terms=[],          # 空
        excluded_terms=[],
        positive_control_ok=True)

    assert ex["EXCLUDED"] is not True, \
        "E-18-3 violated: 空清单产出了 TRUE，实测 %r" % (ex["EXCLUDED"],)
    assert ex["EXCLUDED"] is None, \
        "E-18-1：空清单时 EXCLUDED 应为 None（三态里的「判不出」），实测 %r" \
        % (ex["EXCLUDED"],)
    assert ex["INDETERMINATE"] is True, \
        "必须另有 INDETERMINATE 标记，否则只看真假会把判不出读成 FALSE"
    assert ex["reason"] == "NO_ALTERNATIVES_REGISTERED", ex["reason"]

    # E-18-2：确实没有替代解释时，必须显式登记哨兵条目
    ex2 = LB.evaluate_excluded(
        negative_control_reproduced=False,
        alternative_terms=[LB.NONE_KNOWN],   # 显式哨兵
        excluded_terms=[LB.NONE_KNOWN],
        positive_control_ok=True)
    assert ex2["EXCLUDED"] is True, \
        "E-18-2：显式登记 NONE_KNOWN 并排除后应得到 TRUE，实测 %r" % (ex2,)
    assert ex2["reason"] == "ALTERNATIVES_ALL_EXCLUDED"

    # 反例：登记了 NONE_KNOWN 却没排除 ⇒ 也不得 TRUE
    ex3 = LB.evaluate_excluded(
        negative_control_reproduced=False,
        alternative_terms=[LB.NONE_KNOWN],
        excluded_terms=[],
        positive_control_ok=True)
    assert ex3["EXCLUDED"] is False, \
        "登记了却没排除 ⇒ 必须 FALSE，实测 %r" % (ex3["EXCLUDED"],)
    return "空清单 ⇒ None + INDETERMINATE；NONE_KNOWN 哨兵才可达 TRUE"


# ============================================================ T-8（E-19-2）

@case("T-8", "E-19-2 / E-22-2 不可达性断言：登记入口都不产生 DETECTED")
def t8():
    """勘误004 E-19-2 + 勘误005 E-22-2 / E-22-3。

    ⚠ Mion：「现在『不可达』是你在报告里说的，不是测试断言的。」
    ⚠ Mion 追一层：「『已登记的都测了』在没有穷尽性依据时价值等于零。」

    E-19-1：DETECTED 保留在枚举里（不删）。
    E-22-2：入口逐个点名，逐个断言抛同一异常。
    E-22-3：本表覆盖【不穷尽】，COVERAGE 标 PARTIAL_FOR_REGISTERED_ENTRIES。
    """
    # E-19-1：枚举里必须有 DETECTED
    assert "DETECTED" in LB.MECH, \
        "E-19-1 violated: DETECTED 不得从枚举里删除"

    scan = LB.scan_stage_call_sites()
    assert scan["results"], "扫描表不得为空"
    assert scan["detected_reachable"] is False, \
        "E-22 violated: 登记入口产生了 DETECTED，实测 %r" % (scan["results"],)

    # 每个登记入口都必须收敛到 INDETERMINATE
    for name, m in scan["results"]:
        assert m == "INDETERMINATE", \
            "入口 %r 产出 %r，本阶段应全部收敛到 INDETERMINATE" % (name, m)

    # E-22-2：逐个断言 pathway=True 抛【同一个】UnsupportedPremise
    raises = LB.assert_unsupported_premise_raises()
    assert len(raises) == len(LB.STAGE_CALL_SITES), \
        "E-22-2 violated: 逐项断言数与登记入口数不一致"
    for name, ok in raises:
        assert ok is True, \
            "E-22-2 violated: 入口 %r 传 pathway=True 未抛 UnsupportedPremise" \
            % (name,)

    # 逐个入口点名（不是只说"4 个"）
    names = [n for n, _m in scan["results"]]
    assert names == [n for n, _k, _w in LB.STAGE_CALL_SITES], \
        "登记入口必须与扫描结果一一对应，实测 %r vs %r" % (
            names, [n for n, _k, _w in LB.STAGE_CALL_SITES])

    # E-22-3：不许沉默 —— 必须显式标覆盖不穷尽
    assert scan["coverage"] == "PARTIAL_FOR_REGISTERED_ENTRIES", \
        "E-22-3 violated: 未给穷尽性依据时必须标 PARTIAL，实测 %r" \
        % (scan["coverage"],)
    assert LB.COVERAGE_HOW_MISS_IS_FOUND.strip(), \
        "E-22-3(b) violated: 标了 PARTIAL 却没说明「漏的怎么被发现」"

    # 关键一条：即使 r_A != r_B 也不得 DETECTED
    d = LB.judge_mechanism(
        r_a="BLUE", r_b="RED", pathway_registered_and_controlled=False,
        drift_control_explains=False, readout_has_resolution=True,
        run="r", fixture="T-8", readout="o")
    assert d["MECH"] != "DETECTED"
    return ("%d 个登记入口全部 INDETERMINATE + 全部抛 UnsupportedPremise；"
            "覆盖标 PARTIAL" % len(scan["results"]))


# ============================================================ T-9（E-22-1）

@case("T-9", "E-22-1 pathway=True ⇒ 抛 UnsupportedPremise（不是 ValueError）")
def t9():
    """勘误005 E-22-1。

    ⚠ Mion 的理由：
      ValueError 读作「你传错了值」，意味着调用方改一下就能对。
      而 pathway=True 在本阶段不是值的问题，是【这个前提本身不存在】。
      ⇒ 区别在于谁来修。

    上一版我靠「没有调用方会传 True」保证不可达 ——
    那是纪律，不是机制。新调用方传 True 就能拿到 DETECTED，没有任何东西阻止。
    """
    # ① 必须是 UnsupportedPremise
    caught_type = None
    try:
        LB.judge_mechanism(
            r_a="BLUE", r_b="RED",
            pathway_registered_and_controlled=True,
            drift_control_explains=False, readout_has_resolution=True,
            run="r", fixture="T-9", readout="o")
    except LB.UnsupportedPremise:
        caught_type = "UnsupportedPremise"
    except ValueError:
        caught_type = "ValueError"
    except Exception as e:
        caught_type = type(e).__name__

    assert caught_type == "UnsupportedPremise", \
        "E-22-1 violated: 应抛 UnsupportedPremise，实测 %r" % (caught_type,)

    # ② 它不是 ValueError 的子类（否则 except ValueError 也会吞掉，语义混了）
    assert not issubclass(LB.UnsupportedPremise, ValueError), \
        "UnsupportedPremise 不应是 ValueError 子类 —— 否则两类错误无法区分"

    # ③ 即使 r_A == r_B 也要抛（前提不存在与结果无关）
    caught2 = False
    try:
        LB.judge_mechanism(
            r_a="BLUE", r_b="BLUE",
            pathway_registered_and_controlled=True,
            drift_control_explains=False, readout_has_resolution=True,
            run="r", fixture="T-9", readout="o")
    except LB.UnsupportedPremise:
        caught2 = True
    assert caught2, "E-22-1: 前提不存在时，无论 r_A/r_B 如何都必须抛"
    return "pathway=True ⇒ UnsupportedPremise（非 ValueError 子类），r_A==r_B 时同样抛"


# ============================================================ T-10（E-21）

@case("T-10", "E-21-1 双向不变量 + E-21-2 本层不布尔化消费 EXCLUDED")
def t10():
    """勘误005 E-21-1 / E-21-2。

    E-21-1 双向：
        EXCLUDED is None      ⇔  INDETERMINATE is True
        EXCLUDED in {T,F}      ⇒  INDETERMINATE is False
    ⚠ 必须双向：单向（None ⇒ flag=True）允许 flag=True 而 value=False 的坏状态。

    E-21-2 本层内不得布尔化消费：
        反例源码 grep `if excluded:` / `bool(excluded)` / `excluded or`
    """
    # ① 四个出口全部满足双向不变量
    cases = [
        dict(negative_control_reproduced=False, alternative_terms=[],
             excluded_terms=[], positive_control_ok=True),          # None/True
        dict(negative_control_reproduced=False,
             alternative_terms=["a"], excluded_terms=["a"],
             positive_control_ok=True),                             # True/False
        dict(negative_control_reproduced=True,
             alternative_terms=["a"], excluded_terms=[],
             positive_control_ok=True),                             # False/False
        dict(negative_control_reproduced=False,
             alternative_terms=["a"], excluded_terms=[],
             positive_control_ok=False),                            # False/False
    ]
    for i, kw in enumerate(cases):
        r = LB.evaluate_excluded(**kw)
        is_none = (r["EXCLUDED"] is None)
        assert is_none == r["INDETERMINATE"], \
            "E-21-1 violated（出口 %d）：EXCLUDED=%r 但 INDETERMINATE=%r" \
            % (i, r["EXCLUDED"], r["INDETERMINATE"])

    # ② 单项不满足时必须抛（不是静默通过）
    bad = {"EXCLUDED": False, "INDETERMINATE": True,
           "remaining": [], "reason": "X"}
    caught = False
    try:
        LB.check_e21_invariant(bad)
    except ValueError as e:
        caught = "E-21-1" in str(e)
    assert caught, "E-21-1 violated: 单向坏状态（False + flag=True）未被拒绝"

    bad2 = {"EXCLUDED": None, "INDETERMINATE": False,
            "remaining": [], "reason": "X"}
    caught2 = False
    try:
        LB.check_e21_invariant(bad2)
    except ValueError as e:
        caught2 = "E-21-1" in str(e)
    assert caught2, "E-21-1 violated: 反向坏状态（None + flag=False）未被拒绝"

    # ③ E-21-2：本层源码不得出现布尔化消费
    #    ⚠ 不能用文本 grep —— 第一版我用 grep，结果命中的是
    #      一条【注释】里写的反例（"`if excluded:` 会把 None 和 False 混在一起"）。
    #      文本 grep 分不清代码与注释，会把说明文字当成违规。
    #      ⇒ 改用 AST：只看真实语法树里的 If 判断与 Call 实参。
    src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "lbjudge.py")
    with io.open(src_path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=src_path)

    def _is_excluded_name(node):
        return isinstance(node, ast.Name) and node.id == "excluded"

    violations = []

    for node in ast.walk(tree):
        # (a) if excluded:  /  elif excluded:
        if isinstance(node, ast.If) and _is_excluded_name(node.test):
            violations.append(("if excluded:", node.lineno))
        # (b) bool(excluded)
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "bool"
                and len(node.args) == 1
                and _is_excluded_name(node.args[0])):
            violations.append(("bool(excluded)", node.lineno))
        # (c) excluded or <default>
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            if any(_is_excluded_name(v) for v in node.values):
                violations.append(("excluded or ...", node.lineno))

    assert not violations, \
        "E-21-2 violated: lbjudge.py 出现布尔化消费 %r —— " \
        "None 与 False 在布尔语境相同但语义相反" % (violations,)

    # 正向：AST 里必须出现 `excluded is None` / `excluded is True` 显式三路
    has_none_cmp = False
    has_true_cmp = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and _is_excluded_name(node.left):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, ast.Is) and isinstance(comp, ast.Constant):
                    if comp.value is None:
                        has_none_cmp = True
                    elif comp.value is True:
                        has_true_cmp = True
    assert has_none_cmp, "E-21-2 violated: 未用显式 `excluded is None` 三路判断"
    assert has_true_cmp, "E-21-2 violated: 未用显式 `excluded is True` 三路判断"
    return "4 个出口双向不变量全通过；单项坏状态被拒；AST 无布尔化消费"


# ============================================================ 汇总

REPORT_HEADER = """\
① 本层实现了哪些 A 层定义的字段：
   L-A: admitted / per_rule(A1{verdict,reason}, A2{verdict},
        A3{verdict,match,multi_ref}) / origin_attribution{value,evidence}
        / unknowns / reason_summary
   L-B: B3-OBS{delta,delivered,readout_valid} / B3-CLAIM / B4 / MECH
        / EXCLUDED（三态：True/False/None+INDETERMINATE）
        / scope{this_run,this_fixture,this_readout}
② 这些字段在 B 层之前【不存在】（已核：afcore/afrecover/afimportance 全无）
③ 本层只验「判据的触发条件」，不验「真实机制产生行为影响」
④ 本层未使用真实角色历史；未实现任何重要性算法
⑤ B-SCOPE-1..4 的解释依据为「裁定二授权最小失败条件测试；
   不建待测对象则无法写测试」，由 Mion 判断，凌翼核定中。
⑥ BINDING = v0.4（9031df2）+ 附录A + 勘误004（731f5a0）+ 勘误005（cc0b6fb）
   MECH_DETECTED = NOT_REACHABLE_IN_THIS_STAGE
     （勘误004 E-19-3；【由 T-8/T-9 断言】，不是仅在此处声明）
     强制方式 = E-22-1：pathway=True ⇒ 抛 UnsupportedPremise（T-9）
     覆盖穷尽性 = PARTIAL_FOR_REGISTERED_ENTRIES（E-22-3(b)，T-8 断言）
   EXCLUDED 空清单 = INDETERMINATE（勘误004 E-18-1）
   EXCLUDED 形状 = {True,False,None} + INDETERMINATE: bool（勘误005 E-21）
   E-21-1 双向不变量（每个出口校验）；E-21-2 本层不布尔化消费（AST 检查，T-10）
⑦ OPEN-EXISTING-1  test_mutations_gate.py  状态=OPEN（既有，非 B 层引入）
   现象：7 个基准变异里 3 个未让测试翻红（rc=0）；脚本自报基准不绿。
   归属：之前的收口范围。登记依据：勘误004 E-20-1 / E-20-2。
"""


def main():
    print("=" * 80)
    print("B 层第一批测试 · T-1..T-10（v0.4 + 勘误004/005 绑定，全正向断言）")
    print("  绑定 v0.4 (9031df2) + 附录A + 勘误004 (731f5a0) + 勘误005 (cc0b6fb)")
    print("=" * 80)
    print()
    for f in (t1, t2, t3, t4, t5, t5c, t6, t6e, t7, t8, t9, t10):
        f()
    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print()
    print("=" * 80)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 80)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
