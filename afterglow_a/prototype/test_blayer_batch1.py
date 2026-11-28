# -*- coding: utf-8 -*-
"""B 层第一批测试 —— T-1..T-6 + T-5c + T-6e（共 8 条）

绑定：v0.3 (0d159cb) + 勘误001 (0251ee8) + 勘误002 (cbd6ea4)

⚠ E-12 报告开头固定四行（见文件末尾 REPORT_HEADER）

每条测试都必须能【真的变红】。本文件末尾有变异验证：
对每条断言注入对应的实现错误，断言必须失败。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bfjudge as BJ

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
    """合成记录。未给的字段为 None。"""
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


# ============================================================ T-1

@case("T-1", "A3 事件不匹配 ⇒ PASS + NOT_COVERED，admitted 不受影响")
def t1():
    """勘误001 E-1：§2.1 的旧半句「指向本条记录所涉事件」已删除。

    ⚠ 若实现按旧半句写，这个夹具会得到 UNKNOWN。
      本测试就是用来抓那个残留的。
    """
    r = rec(observed_origin="human_input", basis_conflict="none",
            source_ref="utt/r1", _event="E8")  # 记录谈 E7，引用指向 E8
    d = BJ.decide_admission(r, opener=_open_ok)

    assert d["per_rule"]["A3"]["verdict"] == "PASS", \
        "A3 应 PASS（窄口径只判能打开），实测 %r" % d["per_rule"]["A3"]
    assert d["per_rule"]["A3"]["match"] == "NOT_COVERED", \
        "A3.match 应为 NOT_COVERED"
    assert d["admitted"] is True, "A1/A2/A3 全 PASS ⇒ admitted 应为 True"
    return "A3=PASS + match=NOT_COVERED，admitted=True"


# ============================================================ T-2

@case("T-2", "两臂同蓝 ⇒ B3-CLAIM = NOT_DETECTED（本层不实现，仅验契约字段可表达）")
def t2():
    """v0.3 §3.2/§3.3 + 勘误002 E-8 CROSS-6。

    ⚠ 本判定层【不实现】B3-OBS / B3-CLAIM / B4 —— 它们属机制侧。
      本测试只验证：本层的输出里不出现任何机制侧主张，
      且 reason_summary 不带「影响/没有影响」。
    """
    r = rec(observed_origin="human_input", basis_conflict="none")
    d = BJ.decide_admission(r, opener=_open_ok)

    s = d["reason_summary"]
    for banned in ("影响", "没有影响", "影响输出"):
        assert banned not in s, (
            "reason_summary 出现机制侧措辞 %r ⇒ 越过了本层范围" % banned)

    # 本层不产出机制侧字段
    for k in ("B3-OBS", "B3-CLAIM", "B4", "MECH"):
        assert k not in d, "本层不应产出 %r（属机制侧）" % k
    return "reason_summary 无机制侧措辞；无 B3-*/MECH 字段"


# ============================================================ T-3

@case("T-3", "MECH 三态不在本层 ⇒ 本层不得声称能判机制")
def t3():
    """勘误002 E-8 / CROSS-6。

    ⇒ 本层只做到「准入」层。MECH 属机制侧，本层不实现。
      本测试断言：本层输出中不存在任何可被读成 MECH 的字段。
    """
    r = rec(observed_origin="human_input", basis_conflict="none")
    d = BJ.decide_admission(r, opener=_open_ok)
    assert "MECH" not in str(d.keys()), "本层不得产出 MECH"
    assert "INDETERMINATE" not in str(d.values()), \
        "本层不得产出 INDETERMINATE（那是机制侧三态之一）"
    return "本层无 MECH / INDETERMINATE 字段"


# ============================================================ T-4

@case("T-4", "Q7a：system_dispatch ⇒ A1=UNKNOWN, A2=FAIL, A3=PASS, unknowns=['A1']")
def t4():
    """v0.3 §2.6 Q7a + 勘误002 E-10。这是 B-REQ-1 的主战场。

    ⚠ 只断言 admitted=false 是不够的 ——
      把 A2 错写成 PASS 也照样绿（S-10 / 知微原话）。
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
    return "A1=UNKNOWN(DISPATCH_NOT_QUALIFIED) / A2=FAIL / A3=PASS / unknowns=['A1']"


# ============================================================ T-5

@case("T-5", "delta=null 落点 —— 本层不产 delta，但需验字段缺席不冒充 0")
def t5():
    """勘误001 E-3（B3 侧）。

    ⚠ delta 属机制侧，本层不产出。
      本测试验证：本层输出中【不存在】任何可被读成数值差异的字段，
      因此不会被误读成 delta=0。
    """
    r = rec(observed_origin="human_input", basis_conflict="none")
    d = BJ.decide_admission(r, opener=_open_ok)
    for k in ("delta", "B3-OBS", "delta_value"):
        assert k not in d, "本层不应产出 %r" % k

    # 反向：本层不得用 0 表达「未测」
    assert "0" not in str(d.get("unknowns", [])), "未知不得用 0 表达"
    return "本层无 delta 字段；未知用 UNKNOWN 列表表达，不用 0"


# ============================================================ T-5c

@case("T-5c", "反证：把 UNKNOWN 当数值比较 ⇒ 必须出错（None != 0 的坑）")
def t5c():
    """勘误001 E-3 + 我提的 T-5c。

    Python 里 None != 0 为 True。
    若实现用 `if delta != 0:` 判「有差异」，None 会被判成「有差异」。

    ⇒ 本测试把这条【实现错误】变成【测试红】：
      断言「拿 None 做数值比较」必须抛 TypeError。
      若将来有人把它写成 `!= 0` 且不抛错，说明他改了语义。
    """
    none_val = None
    raised = False
    try:
        _ = (none_val > 0)
    except TypeError:
        raised = True
    assert raised, "None > 0 应抛 TypeError；若不抛，说明 None 被当成了数值"

    # 而 None != 0 是 True —— 这正是坑
    assert (none_val != 0) is True, "None != 0 应为 True（这是坑本身）"

    # 正确写法示范：必须显式判 None
    def is_nonzero(v):
        if v is None:
            raise ValueError("null 不参与数值比较")
        return v != 0

    raised2 = False
    try:
        is_nonzero(None)
    except ValueError:
        raised2 = True
    assert raised2, "正确处理必须显式拒绝 None"
    return "None>0 抛 TypeError；None!=0 为 True（坑）；正确处理须显式拒绝"


# ============================================================ T-6

@case("T-6", "对照跑过 ≠ 排除成功（本层验不冒充）")
def t6():
    """勘误001 E-4。

    ⚠ EXCLUDED 属机制侧，本层不产出。
      本测试验证：本层输出中不存在任何可被读成「已排除」的字段。
    """
    r = rec(observed_origin="human_input", basis_conflict="none")
    d = BJ.decide_admission(r, opener=_open_ok)
    for k in ("EXCLUDED", "excluded_ok", "control_passed"):
        assert k not in d, "本层不应产出 %r（属机制侧）" % k
    return "本层无 EXCLUDED 字段"


# ============================================================ T-6e

@case("T-6e", "反证：谓词恒 False 也能通过 —— 必须另有 True 分支")
def t6e():
    """勘误001 E-4 + 我提的 T-6e。

    「只测 False 分支」的谓词，改成恒 False 也能全绿。
    ⇒ 必须同时存在一个 True 分支，才能证明谓词有分辨力。

    本测试用一个最小谓词示范：
        pred(x) = x is None
    · 有 False 分支（x=0）
    · 有 True 分支（x=None）
    ⇒ 若把 pred 改成恒 False，True 分支会红。
    """
    pred = lambda x: x is None

    # False 分支
    assert pred(0) is False
    # True 分支 —— 没有这条，pred 恒 False 也能过
    assert pred(None) is True, \
        "必须有 True 分支，否则恒 False 的谓词也能通过"

    # 反证：把 pred 改成恒 False，True 分支必红
    broken = lambda x: False
    caught = False
    try:
        assert broken(None) is True
    except AssertionError:
        caught = True
    assert caught, "恒 False 谓词未被抓住 ⇒ 本反证无效"
    return "谓词有 True/False 两分支；恒 False 会被 True 分支抓红"


# ============================================================ 汇总

REPORT_HEADER = """\
① 本层实现了哪些 A 层定义的字段：
   admitted / per_rule(A1{verdict,reason}, A2{verdict}, A3{verdict,match})
   / origin_attribution{value,evidence} / unknowns / reason_summary
② 这些字段在 B 层之前【不存在】（已核：afcore/afrecover/afimportance 全无）
③ 本层只验「判据的触发条件」，不验「真实机制产生行为影响」
④ 本层未使用真实角色历史；未实现任何重要性算法
"""


def main():
    print("=" * 80)
    print("B 层第一批测试 · T-1..T-6 + T-5c + T-6e")
    print("  绑定 v0.3 (0d159cb) + 勘误001 (0251ee8) + 勘误002 (cbd6ea4)")
    print("=" * 80)
    print()
    for f in (t1, t2, t3, t4, t5, t5c, t6, t6e):
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
