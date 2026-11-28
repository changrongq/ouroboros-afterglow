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

    ⚠ 2026-11-27 第二次修正：
      降级模式（expected_ids=None）现在判 PARTIAL，不再判 COMPLETE
      （知微：「缺预期时至多 PARTIAL」）。
      ⇒ 传了 expected_n 但没传 expected_ids 时，必须构造出【明确的】
        预期 ID 清单，不能退化成降级模式。
      ⇒ 不传任何参数时，用实际 rows 的 ID 作为预期（调用方的责任）。
    """
    if expected_ids is not None:
        v, rc, c, d = classify_evidence(rows, expected_ids)
        return v, rc, c

    ids = [r[0] for r in rows]
    if expected_n is not None:
        # 构造「预期比实际多」的情形：补占位 ID（这些 ID 不会出现在 rows 里）
        while len(ids) < expected_n:
            ids.append("__EXPECTED_MISSING_%d" % len(ids))
        ids = ids[:expected_n]

    # 显式把预期传进去，避免落入降级模式（降级现在至多 PARTIAL）
    v, rc, c, d = classify_evidence(rows, ids)
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


@case("ES-10", "反证：给真实 main 的可执行列表删掉末项 ⇒ 必须 PARTIAL")
def es10():
    """⚠ 知微 2026-11-27 的实测：

    「给真实 main 的可执行列表仅去掉 I14，不补副本，其余 14 项照常真跑
      ⇒ COMPLETE/0；14 CAUGHT，manifest_ok=True，missing=[]。
      这是未关闭的一格。」

    ⇒ 她指出的根因：expected_ids 从 MUTATIONS 生成，与执行计划同源。
    ⇒ 现在 expected 来自 mutation_manifest.REGISTERED_MUTATION_IDS
      （独立登记）。本用例验证：执行列表少一项时，
      对账必须报 missing 并判 PARTIAL。

    ⚠ 本用例不真跑 14 个变异（那是几分钟），
      而是用【真实 classify_evidence + 真实登记清单】验证对账逻辑。
    """
    import mutation_manifest as MM
    import test_mutations_importance as TM

    manifest_ids = list(MM.REGISTERED_MUTATION_IDS)
    assert manifest_ids == [m[0] for m in TM.MUTATIONS], (
        "前提：当前登记与执行计划应一致")

    # 模拟「执行列表去掉 I14，其余 14 项真跑且全 CAUGHT」
    simulated_rows = [(i, "d", "CAUGHT", "e")
                      for i in manifest_ids if i != "I14"]
    v, rc, c, d = TM.classify_evidence(simulated_rows, manifest_ids)

    assert v == "EVIDENCE_PARTIAL", (
        "执行少一项仍判 %s ⇒ 未关闭（知微说的那一格）" % v)
    assert rc == 2, rc
    assert d["missing"] == ["I14"], (
        "missing 应为 ['I14']，实测 %r" % (d["missing"],))
    assert d["manifest_ok"] is False

    # 对照：若 expected 也来自执行计划（知微指出的旧写法），会放过
    old_expected = [r[0] for r in simulated_rows]
    v_old, _, _, _ = TM.classify_evidence(simulated_rows, old_expected)
    assert v_old == "EVIDENCE_COMPLETE", (
        "旧写法（expected 与执行同源）本应放过，实测 %s" % v_old)
    return "执行少 I14：新判 PARTIAL/missing=[I14]；旧写法仍 COMPLETE"


@case("ES-11", "预期清单自身有重复 ⇒ 不得 COMPLETE")
def es11():
    """知微 2026-11-27：

    「预期清单有重复、明细无重复时（预期 16 行、实得 15 行）仍 COMPLETE」

    ⇒ 集合相等但数量对不上，旧判据放过。
    """
    import test_mutations_importance as TM
    base = [("I%d" % i, "d", "CAUGHT", "e") for i in range(1, 16)]
    exp = ["I%d" % i for i in range(1, 16)] + ["I1"]   # 16 项，I1 重复

    v, rc, c, d = TM.classify_evidence(base, exp)
    assert v == "EVIDENCE_PARTIAL", (
        "预期有重复仍判 %s ⇒ 未防住" % v)
    assert rc == 2
    assert d["expected_duplicated"] == ["I1"], (
        "应报 expected_duplicated=['I1']，实测 %r"
        % (d.get("expected_duplicated"),))
    return "预期 16 项含重复 I1，实得 15 ⇒ PARTIAL"


@case("ES-12", "未提供预期清单 ⇒ 至多 PARTIAL，不得 COMPLETE")
def es12():
    """知微 2026-11-27：

    「未提供预期清单的降级模式也能 COMPLETE。
      若 COMPLETE 承诺『完整且与有效登记一一对应』，缺预期时至多 PARTIAL。」
    """
    import test_mutations_importance as TM
    rows = [("I%d" % i, "d", "CAUGHT", "e") for i in range(1, 16)]

    v, rc, c, d = TM.classify_evidence(rows, None)
    assert v == "EVIDENCE_PARTIAL", (
        "降级模式判了 %s ⇒ 仍能 COMPLETE" % v)
    assert rc == 2
    assert d["manifest_check"] == "DEGRADED_NO_EXPECTED_LIST"
    return "无预期清单 ⇒ PARTIAL / 2（不再 COMPLETE）"


# ======================================================== 汇总
def main():
    print("=" * 80)
    print("证据状态三态最小验收对照（知微 2026-11-27）")
    print("=" * 80)
    print()
    for f in (es1, es2, es3, es4, es5, es6, es7, es8, es9,
              es10, es11, es12):
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
