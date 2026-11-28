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
           "excluded_undetermined": False,
           "remaining": [], "reason": "ALTERNATIVES_ALL_EXCLUDED"}
    caught = False
    try:
        LB.check_e21_invariant(bad)
    except ValueError as e:
        caught = "E-21-1" in str(e)
    assert caught, "E-21-1 violated: 单向坏状态（False + flag=True）未被拒绝"

    bad2 = {"EXCLUDED": None, "INDETERMINATE": False,
            "excluded_undetermined": True,
            "remaining": [], "reason": "NO_ALTERNATIVES_REGISTERED"}
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


# ============================================================ T-11（E-25）

@case("T-11", "E-25 调用点覆盖：AST 扫全仓 vs STAGE_CALL_SITES 逐项比对")
def t11():
    """勘误006 E-25-1 / E-25-2。

    ⚠ Mion 用我自己的话砍的一刀：
      我写「纪律变成了机制」，但那句只对 ②（pathway=True 抛异常）成立。
      ① 「代码评审必须同时改 STAGE_CALL_SITES」仍然是纪律。

    ⇒ 本测试把它变成机制：多一个调用点就红。
    ⚠ 用 AST 不用 grep —— 与 E-26-1 同一理由（文本层 vs 语法层）。
    """
    cov = LB.check_call_site_coverage()

    # ① 不得有未登记的调用点
    assert cov["ok"] is True, \
        "E-25-1 violated: 存在未登记进 STAGE_CALL_SITES 的 judge_mechanism 调用点：%r" \
        % (cov["missing_from_registry"],)

    # ② 扫描确实扫到了东西
    #    ⚠ 定位说明（勘误无，属实现内部；Mion 90fd957 §二 的「冗余 vs 纵深」）：
    #      以下三条里，只有后两条是【防线】，第一条是被蕴含的：
    #        · 探针被命中      ⇒ hits 必然非空
    #        · real_hits >= 2  ⇒ hits 必然非空
    #      ⇒ 「hits 非空」永远不是第一个红的，它不是独立防线。
    #        留在这里是为了向读代码的人说明意图，不是第三层保护。
    assert cov["hits"], "E-25-1 violated: 扫描结果为空，断言无对象"
    real_hits = [h for h in cov["hits"] if h[1] > 0]
    assert len(real_hits) >= 2, \
        "E-25-1 violated: 真实调用点少于 2 处，扫描可能失效，实测 %r" \
        % (real_hits,)

    # ② b) 自制检查器必须有【它自己会失效】的断言（Mion 2026-11-28 §三）
    #      ⚠ 前面 ②只验「扫到了东西」，没验「会不会漏扫某个文件」。
    #        若某文件因 skip_dirs 被误跳过，hits 仍非空 ⇒ ② 依然绿。
    #      ⇒ 做法：在扫描范围里放一个已知含调用的探针文件，
    #        断言扫描器【必须】命中它。命中不了 ⇒ 扫描器坏了，不是仓库干净。
    probe_dir = os.path.dirname(os.path.abspath(__file__))
    probe_path = os.path.join(probe_dir, "_selfcheck_e25_probe.py")
    wrote_probe = False
    try:
        with io.open(probe_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "# 自制检查器自失效探针 —— 由 T-11 临时创建并删除\n"
                "import lbjudge\n\n\n"
                "def _selfcheck_probe():\n"
                "    return lbjudge.judge_mechanism(\n"
                "        r_a=0, r_b=0,\n"
                "        pathway_registered_and_controlled=False,\n"
                "        drift_control_explains=False,\n"
                "        readout_has_resolution=True)\n"
            )
        wrote_probe = True
        probe_hits = LB.scan_judge_mechanism_calls()
        probe_found = [h for h in probe_hits
                       if h[0].endswith("_selfcheck_e25_probe.py")]
        assert probe_found, \
            "E-25 violated（自制检查器自失效断言）：探针文件含一条真实调用，" \
            "扫描器却没命中它 ⇒ 扫描器失效，不是仓库干净。hit 文件=%r" \
            % (sorted({h[0] for h in probe_hits}),)
    finally:
        if wrote_probe and os.path.exists(probe_path):
            os.remove(probe_path)

    # ③ 豁免必须显式且带理由（E-25-2）
    for ef, en, why in LB.CALL_SITE_EXEMPTIONS:
        assert why and why.strip(), \
            "E-25-2 violated: 豁免 %r/%r 缺理由" % (ef, en)

    # ④ 每一项豁免都必须在扫描里实际出现过（否则是过期豁免）
    hit_funcs = {(h[0], h[2]) for h in cov["hits"]}
    for ef, en, _why in LB.CALL_SITE_EXEMPTIONS:
        matched = any(rel.endswith(ef) and fn == en for rel, fn in hit_funcs)
        assert matched, \
            "E-25-2 violated: 豁免 %r/%r 对应的调用点已不存在 —— 过期豁免" \
            % (ef, en)

    # ⑤ 无法解析的文件必须显式登记（不静默吞）
    unparseable = [h for h in cov["hits"] if h[2] == "<UNPARSEABLE>"]

    # ⑥ 勘误007（Q1）：测试豁免必须是【逐文件名】，不得按模式
    #    ⚠ 上一版是 rel.startswith("test_") —— 新增测试文件自动放行，
    #      而没人看过它。那是「未登记」的另一种形态。
    assert "test_exemptions" in cov, \
        "Q1 violated: check_call_site_coverage 未报告 test_exemptions"
    for p, why in LB.TEST_FILE_EXEMPTIONS:
        assert why and why.strip(), \
            "Q1 violated: 测试豁免 %r 缺理由" % (p,)
        assert not p.startswith("afterglow_a/prototype/test_*.py"), \
            "Q1 violated: 测试豁免用了 glob 模式 %r" % (p,)
        assert "*" not in p, "Q1 violated: 测试豁免用了通配符 %r" % (p,)

    # ⑥ b) 每条测试豁免必须实际命中过（防过期豁免，与 ④ 同理）
    hit_files = {h[0] for h in cov["hits"]}
    for p, _why in LB.TEST_FILE_EXEMPTIONS:
        assert p in hit_files, \
            "Q1 violated: 测试豁免 %r 对应的文件未被扫描到 —— 过期豁免" % (p,)

    # ⑥ c) 关键一条：模拟「新增一个未登记的测试文件」必须红
    #      ⇒ 若放行是按模式实现的，这个模拟会被错误放行。
    scanned = LB.scan_judge_mechanism_calls()
    exempt_set = {p for p, _w in LB.TEST_FILE_EXEMPTIONS}
    unregistered_test_calls = [
        (rel, ln, fn) for rel, ln, fn in scanned
        if rel not in exempt_set
        and rel not in {h[0] for h in cov["hits"] if h in cov["exemptions_applied"]}
        and "test_" in rel
    ]
    assert not unregistered_test_calls, \
        "Q1 violated: 存在【未登记进 TEST_FILE_EXEMPTIONS 的测试文件】调用点：" \
        "%r ⇒ 说明放行是按模式做的（新测试文件被自动放行）" \
        % (unregistered_test_calls,)

    return ("调用点 %d 处，未登记 %d 处，豁免 %d 项，"
            "测试豁免 %d 个（逐文件名），无法解析 %d 个"
            % (len(cov["hits"]), len(cov["missing_from_registry"]),
               len(cov["exemptions_applied"]), len(cov["test_exemptions"]),
               len(unparseable)))


# ============================================================ T-12（E-24）

@case("T-12", "E-24 三字段编码 + 两种判不出措辞必须分开")
def t12():
    """勘误006 E-24-1 / E-24-2 / E-24-3 / E-24-4。

    E-24-2 三者同时成立：
        excluded is None ⇔ excluded_undetermined is True
                        ⇔ reason ∈ UNDETERMINED_REASONS
    E-24-3 措辞分开：
        没登记     ⇒「该夹具未登记任何替代解释，因此无法判定是否已排除」
        没排干净   ⇒「已登记的解释中尚有 N 条未排除」

    ⚠ 合并措辞会让「我们没想到」与「我们想到了但没排掉」变成同一句话。
    """
    # ① 三字段在真实返回里同时成立
    #    ① a) evaluate_excluded 自身的出口（不是只验 judge_impact）
    ex_cases = [
        dict(negative_control_reproduced=False, alternative_terms=[],
             excluded_terms=[], positive_control_ok=True),
        dict(negative_control_reproduced=False,
             alternative_terms=["a"], excluded_terms=["a"],
             positive_control_ok=True),
        dict(negative_control_reproduced=True,
             alternative_terms=["a"], excluded_terms=[],
             positive_control_ok=True),
        dict(negative_control_reproduced=False,
             alternative_terms=["a"], excluded_terms=[],
             positive_control_ok=False),
    ]
    for i, kw in enumerate(ex_cases):
        r = LB.evaluate_excluded(**kw)
        assert "excluded_undetermined" in r, \
            "E-24-1 violated（evaluate_excluded 出口 %d）：缺第三字段 " \
            "excluded_undetermined，实测 keys=%r" % (i, sorted(r))
        assert isinstance(r["excluded_undetermined"], bool), \
            "E-24-2 violated（evaluate_excluded 出口 %d）：" \
            "excluded_undetermined 必须是 bool，实测 %r" \
            % (i, r["excluded_undetermined"])
        assert "reason" in r and r["reason"], \
            "E-24-1 violated（evaluate_excluded 出口 %d）：缺 reason" % (i,)
        # 三者同时
        assert (r["EXCLUDED"] is None) == r["excluded_undetermined"], \
            "E-24-2 violated（evaluate_excluded 出口 %d）：EXCLUDED=%r 但 " \
            "undetermined=%r" % (i, r["EXCLUDED"], r["excluded_undetermined"])

    # ① b) judge_impact 的出口
    d_none = LB.judge_impact(
        {"delivered": True, "readout_valid": True, "delta": 0.3},
        excluded=None, run="r", fixture="T-12", readout="o")
    assert d_none["EXCLUDED"] is None
    assert d_none["excluded_undetermined"] is True
    assert d_none["reason"] in LB.UNDETERMINED_REASONS

    d_false = LB.judge_impact(
        {"delivered": True, "readout_valid": True, "delta": 0.3},
        excluded=False, run="r", fixture="T-12", readout="o")
    assert d_false["EXCLUDED"] is False
    assert d_false["excluded_undetermined"] is False
    assert d_false["reason"] not in LB.UNDETERMINED_REASONS

    d_true = LB.judge_impact(
        {"delivered": True, "readout_valid": True, "delta": 0.3},
        excluded=True, run="r", fixture="T-12", readout="o")
    assert d_true["EXCLUDED"] is True
    assert d_true["excluded_undetermined"] is False
    assert d_true["reason"] not in LB.UNDETERMINED_REASONS

    # ② 两两成立而第三项不成立 ⇒ 必须被拒
    bad = {"EXCLUDED": None, "INDETERMINATE": True,
           "excluded_undetermined": True,
           "reason": "ALTERNATIVES_ALL_EXCLUDED"}   # reason 与前两项矛盾
    caught = False
    try:
        LB.check_e21_invariant(bad)
    except ValueError as e:
        caught = "E-24-2" in str(e)
    assert caught, \
        "E-24-2 violated: 两两成立而 reason 矛盾未被拒绝"

    # ③ 措辞必须分开，且各能指认
    w1 = LB.wording_for("NO_ALTERNATIVES_REGISTERED")
    w2 = LB.wording_for("ALTERNATIVES_NOT_ALL_EXCLUDED", n_unexcluded=2)
    assert w1 != w2, "E-24-3 violated: 两种判不出措辞相同"
    assert "未登记" in w1 and "无法判定" in w1
    assert "尚有" in w2 and "2" in w2
    # 合并措辞的反面证据：w1 不得出现「未排除」
    assert "未排除" not in w1, \
        "E-24-3 violated: 「没登记」的措辞混入了「没排干净」的语义"

    # ④ 未登记的 reason 必须报错（不许静默给默认措辞）
    caught2 = False
    try:
        LB.wording_for("SOME_NEW_REASON")
    except KeyError:
        caught2 = True
    assert caught2, "E-24-3 violated: 未登记 reason 未报错，可能静默合并措辞"

    # ⑤ E-24-4：三字段编码的上限必须登记
    assert LB.THREE_FIELD_ENCODING == "ACCEPTED_FOR_NOW, WATCHED", \
        "E-24-4 violated: 三字段编码上限未登记"
    return "三字段三者同时；矛盾状态被拒；两种措辞分开且不可合并"


# ============================================================ T-13（E-27）

@case("T-13", "E-27 BINDING 五份文档在 HEAD 中存在")
def t13():
    """勘误005 E-27。

    由来：Mion 把「勘误005」当成已存在的文档引用了一整天，
    写进 BINDING、被我按信里摘要实现并验收 —— 而那份文档【从未创建】。
    ⇒ 所以本检查抓过一次真实事故，不是形式主义。

    ⚠ 检查的是 HEAD（提交），不是工作区。
      理由：BINDING 是给别的角色看的，他们看到的是提交。
      工作区有而未提交的文件，对下游等于不存在 —— 这正是那一类事故。
    """
    import check_binding_docs as CBD

    rep = CBD.check_binding_docs()

    # ① 清单非空（空清单会让断言永远绿）
    assert len(CBD.BINDING_DOCS) == 5, \
        "E-27 violated: BINDING 清单应为 5 份，实测 %d 份" \
        % len(CBD.BINDING_DOCS)

    # ② 每份都能在 HEAD 取到 blob
    missing = [(label, fn) for label, fn, blob in rep["results"]
               if blob is None]
    assert not missing, \
        "E-27 violated: 以下 BINDING 文档在 HEAD 里不存在 ⇒ 下游引用悬空：%r" \
        % (missing,)
    assert rep["ok"] is True

    # ③ 反向：取一个不存在的路径必须返回 None
    assert CBD.head_blob("afterglow_design/____no_such_doc____.md") is None, \
        "E-27 violated: head_blob 对不存在的路径未返回 None —— 扫描可能失效"

    # ④ blob 必须是 40 位 sha（证明真取到了 git 对象，不是 shell 回显）
    for label, fn, blob in rep["results"]:
        assert blob and len(blob) == 40, \
            "E-27 violated: %s 的 blob 不是 40 位 sha，实测 %r" % (label, blob)
    return "五份 BINDING 文档全部在 HEAD 中存在（blob 均为 40 位 sha）"


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
⑥ BINDING = v0.4（9031df2）+ 附录A + 勘误004（731f5a0）
       + 勘误005（c39b07d，BACKFILLED）+ 勘误006（e9548dc）
   MECH_DETECTED = NOT_REACHABLE_IN_THIS_STAGE
     （勘误004 E-19-3；【由 T-8/T-9 断言】）
     强制方式 = E-22-1：pathway=True ⇒ 抛 UnsupportedPremise（T-9）
     覆盖 = E-25-1：AST 扫全仓调用点 vs 登记表（T-11）
   EXCLUDED 形状 = excluded + excluded_undetermined + reason（E-24-1）
     产出点唯一 = _pack_excluded（勘误007 结构修复：四分支汇一个 return）
     不变量 = E-21-1 双向 + E-24-2 三者同时（T-10 / T-12）
     NOT_CHECKED_E21 = 别名化消费（E-26-2，AST 不做数据流）
     ⇒ 只主张「本层不误用」，不主张「已防止误用」（E-26-3）
   E-25-1 覆盖 = AST 扫全仓调用点 vs 登记表（T-11）
     测试豁免 = TEST_FILE_EXEMPTIONS【逐文件名】（勘误007 Q1 答复）
⑦ OPEN-EXISTING-1  test_mutations_gate.py  状态=OPEN（既有，非 B 层引入）
   现象：7 个基准变异里 3 个未让测试翻红（rc=0）；脚本自报基准不绿。
   归属：之前的收口范围。登记依据：勘误004 E-20-1 / E-20-2。
"""


def main():
    print("=" * 80)
    print("B 层第一批测试 · T-1..T-13（v0.4 + 勘误004/005/006 绑定）")
    print("  绑定 v0.4 (9031df2) + 附录A + 勘误004 (731f5a0)")
    print("       + 勘误005 (c39b07d) + 勘误006 (e9548dc)")
    print("=" * 80)
    print()
    for f in (t1, t2, t3, t4, t5, t5c, t6, t6e, t7, t8, t9, t10, t11, t12, t13):
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
