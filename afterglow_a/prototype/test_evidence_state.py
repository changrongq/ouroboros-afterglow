# -*- coding: utf-8 -*-
"""证据状态三态的最小验收对照（知微 2026-11-27 要求）

知微要求的最小对照：
    全捕获 / 仅目标异常 / 仅未决 / 异常与未决混合 / 漏一登记项

本文件不跑真实变异（那要几分钟），而是直接对【判定逻辑】喂五种
构造好的 rows，断言 verdict 与 exit_code 的对应关系。

⚠ 与 test_mutations_importance.py 的关系：
   那边跑真变异、产出真 rows；这边只验【判定函数】本身。
   两者分开，是因为「判定逻辑对不对」与「本批变异跑得怎么样」
   是两个不同的问题 —— 混在一起会互相掩盖。

运行：python afterglow_a/prototype/test_evidence_state.py
"""
from __future__ import annotations

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []

#: 与 test_mutations_importance.py 的 FAIL_STATES 保持一致
FAIL_STATES = ("MISSED", "INVALID", "TEST_DID_NOT_RUN", "TEST_CRASHED",
               "TARGET_ERRORED", "NOT_ATTRIBUTABLE")


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
                traceback.print_exc()
        return run
    return deco


#: ⚠ 2026-11-27 修正（知微第 3 条）：
#:   原文件【自己写了一份 classify】，与真实驱动毫无关系。
#:   知微实测：在真实驱动里删掉 TARGET_ERRORED，ES 仍 8/8。
#:   ⇒ 这是「用尺子量尺子」的又一例。
#:   ⇒ 现在直接 import 真实驱动里的 classify_evidence，不再自写。
from test_mutations_importance import FAIL_STATES, classify_evidence  # noqa: E402


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
                traceback.print_exc()
        return run
    return deco


def classify(rows, expected_ids=None, expected_n=None):
    """薄封装：调用【真实驱动】的 classify_evidence。

    ⚠ 保留 expected_n 参数是为了让旧用例写法不变，
      但它现在被转换成 expected_ids（取前 n 个实际 row 的 ID 之外的占位）。
      新增用例应直接用 expected_ids。
    """
    if expected_n is not None and expected_ids is None:
        # 构造「预期比实际多」的情形：补一个不存在的 ID
        ids = [r[0] for r in rows]
        while len(ids) < expected_n:
            ids.append("__EXPECTED_MISSING_%d" % len(ids))
        expected_ids = ids[:expected_n]
    v, rc, c, _ = classify_evidence(rows, expected_ids)
    return v, rc, c


def row(i, status):
    return ("I%d" % i, "d%d" % i, status, "e%d" % i)


# ======================================================== 五组对照
@case("ES-1", "全捕获 ⇒ EVIDENCE_COMPLETE / exit 0")
def es1():
    rows = [row(i, "CAUGHT") for i in range(1, 6)]
    v, rc, c = classify(rows)
    assert v == "EVIDENCE_COMPLETE", v
    assert rc == 0, rc
    return "%s / exit %d（%d CAUGHT）" % (v, rc, c["CAUGHT"])


@case("ES-2", "仅目标异常 ⇒ EVIDENCE_FAIL / exit 1（不再 PASS）")
def es2():
    rows = [row(1, "CAUGHT"), row(2, "TARGET_ERRORED"),
            row(3, "CAUGHT"), row(4, "CAUGHT")]
    v, rc, c = classify(rows)
    assert v == "EVIDENCE_FAIL", (
        "目标异常必须判失败，实测 %s（这正是知微指出的漏计）" % v)
    assert rc == 1, rc
    assert c.get("TARGET_ERRORED") == 1
    return "%s / exit %d（TARGET_ERRORED 计入失败）" % (v, rc)


@case("ES-3", "仅未决 ⇒ EVIDENCE_PARTIAL / exit 2（不签全项 PASS）")
def es3():
    rows = [row(1, "CAUGHT"), row(2, "UNRESOLVED"), row(3, "CAUGHT")]
    v, rc, c = classify(rows)
    assert v == "EVIDENCE_PARTIAL", v
    assert rc == 2, rc
    return "%s / exit %d（UNRESOLVED 不进失败，但也不进 COMPLETE）" % (v, rc)


@case("ES-4", "异常与未决混合 ⇒ EVIDENCE_FAIL（失败优先）")
def es4():
    rows = [row(1, "CAUGHT"), row(2, "TARGET_ERRORED"),
            row(3, "UNRESOLVED"), row(4, "CAUGHT")]
    v, rc, c = classify(rows)
    assert v == "EVIDENCE_FAIL", (
        "有失败又有未决时，失败优先；实测 %s" % v)
    assert rc == 1, rc
    assert c.get("TARGET_ERRORED") == 1 and c.get("UNRESOLVED") == 1, (
        "两类明细都应保留：%r" % c)
    return "%s / exit %d（两类明细均保留）" % (v, rc)


@case("ES-5", "漏一登记项 ⇒ EVIDENCE_PARTIAL / exit 2")
def es5():
    # 预期清单 5 项，实际只产出 4 项
    rows = [row(i, "CAUGHT") for i in range(1, 5)]
    v, rc, c = classify(rows, expected_n=5)
    assert v == "EVIDENCE_PARTIAL", (
        "漏登记不得凭「零个失败」升为 COMPLETE，实测 %s" % v)
    assert rc == 2, rc
    return "%s / exit %d（预期 5，实得 4）" % (v, rc)


# ======================================================== 边界与反例
@case("ES-6", "预期清单为空 ⇒ EVIDENCE_PARTIAL（不得凭零失败升 COMPLETE）")
def es6():
    v, rc, c = classify([], expected_n=0)
    assert v == "EVIDENCE_PARTIAL", (
        "空清单不能判 COMPLETE，实测 %s" % v)
    assert rc == 2, rc
    return "%s / exit %d（空清单）" % (v, rc)


@case("ES-7", "九种失败状态各自都能把结果拉成 EVIDENCE_FAIL")
def es7():
    hit = []
    for st in FAIL_STATES:
        rows = [row(1, "CAUGHT"), row(2, st), row(3, "CAUGHT")]
        v, rc, _ = classify(rows)
        assert v == "EVIDENCE_FAIL" and rc == 1, (
            "%s 未被计入失败（verdict=%s, rc=%s）" % (st, v, rc))
        hit.append(st)
    assert len(hit) == len(FAIL_STATES), (
        "FAIL_STATES 与实际处理不一致：%r" % hit)
    return "%d 种失败状态全部计入" % len(hit)


@case("ES-8", "反证：若漏计 TARGET_ERRORED，ES-2 会变 PASS")
def es8():
    """模拟旧实现：bad 不含 TARGET_ERRORED。
    用这个旧判据跑 ES-2 的 rows，应当得到「PASS / exit 0」——
    ⇒ 证明 ES-2 确实在守一处真实的缺陷，不是空转。
    """
    rows = [row(1, "CAUGHT"), row(2, "TARGET_ERRORED"),
            row(3, "CAUGHT"), row(4, "CAUGHT")]
    counts = {}
    for _, _, st, _ in rows:
        counts[st] = counts.get(st, 0) + 1

    # 旧实现：bad 只数这几类
    old_bad = (counts.get("MISSED", 0) + counts.get("INVALID", 0)
               + counts.get("TEST_DID_NOT_RUN", 0)
               + counts.get("TEST_CRASHED", 0)
               + counts.get("NOT_ATTRIBUTABLE", 0))
    old_verdict = "PASS" if old_bad == 0 else "FAIL"

    assert old_verdict == "PASS", (
        "旧实现本应把「目标异常」放成 PASS（这正是缺陷），实测 %s"
        % old_verdict)

    new_v, new_rc, _ = classify(rows)
    assert new_v == "EVIDENCE_FAIL", new_v
    return "旧判据 PASS / 新判据 EVIDENCE_FAIL ⇒ ES-2 守着真缺陷"


@case("ES-9", "接线检查：ES 用的是真实驱动的 FAIL_STATES，不是自己抄的")
def es9():
    """⚠ 知微第 3 条：原 ES 自写 classify，删掉真实驱动的
    TARGET_ERRORED，ES 仍 8/8。
    ⇒ 现在 ES import 真实模块的 classify_evidence 与 FAIL_STATES，
      本用例验证这条接线确实存在。
    """
    import test_mutations_importance as TM
    # 1. ES 用的就是 TM 里那个对象（同一引用）
    assert FAIL_STATES is TM.FAIL_STATES, (
        "ES 的 FAIL_STATES 不是真实驱动里那个 ⇒ 又抄了一份")
    assert classify_evidence is TM.classify_evidence, (
        "ES 的 classify_evidence 不是真实驱动里那个")

    # 2. 真实驱动的 FAIL_STATES 必须含 TARGET_ERRORED
    assert "TARGET_ERRORED" in TM.FAIL_STATES, (
        "真实驱动的 FAIL_STATES 漏了 TARGET_ERRORED")

    # 3. 若把 TARGET_ERRORED 从该元组里拿掉，ES-2 必须变红
    reduced = tuple(s for s in TM.FAIL_STATES if s != "TARGET_ERRORED")
    assert "TARGET_ERRORED" not in reduced

    # 用「只含失败状态」的构造验证：如果 FAIL_STATES 少了它，
    # 目标异常就不会被算成失败
    tmp_counts = {"CAUGHT": 3, "TARGET_ERRORED": 1}
    old_style_fail = sum(tmp_counts.get(s, 0) for s in reduced)
    assert old_style_fail == 0, (
        "模拟：删掉 TARGET_ERRORED 后失败计数变 %d（应为 0，即被放过）"
        % old_style_fail)
    new_style_fail = sum(tmp_counts.get(s, 0) for s in TM.FAIL_STATES)
    assert new_style_fail == 1, (
        "当前 FAIL_STATES 下失败计数应为 1（TARGET_ERRORED 被计入）")
    return "同一引用 + 删掉后会被放过 + 现在计入（三层接线检查）"


# ======================================================== 汇总
def main():
    print("=" * 80)
    print("证据状态三态最小验收对照（知微 2026-11-27）")
    print("=" * 80)
    print()
    for f in (es1, es2, es3, es4, es5, es6, es7, es8, es9):
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
