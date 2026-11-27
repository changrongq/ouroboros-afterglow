# -*- coding: utf-8 -*-
"""凌翼 2026-11-27 裁定回执的定点回归

覆盖两条：
  裁定一 · 多次纠正的 cause 归因（含退出/恢复/再次退出）
  裁定二 · MUTATION_PREFLIGHT（含负向：锚点失效必须在跑变异前拒绝）

凌翼原话（裁定一）：
    「当前 synthetic_ratios() 在累计 relation 列表里取第一条 correction_of，
      可能在多次纠正时归因错误。
      请先构造：
        - 首次纠正后仍是 first_person_report；
        - 再次纠正后变成 record_only；
        - 验证 cause 对应实际造成这次分母流失的纠正依据。
      还应覆盖退出、恢复、再次退出分母的多次转换。
      如历史证据无法确定相应纠正依据，应显式报告归因未知，
      不得静默给出错误 ID。」

运行：python afterglow_a/prototype/test_attrition_preflight.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
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
                traceback.print_exc()
        return run
    return deco


from afcore import Record, RecoveryStore  # noqa: E402
import afimportance as AI                   # noqa: E402
import mutation_preflight as PF             # noqa: E402
import test_mutations_importance as TM      # noqa: E402

PIN = "2026-11-27T00:00:00Z"


def _rec(rid, basis):
    return Record(
        record_id=rid, content="c-%s" % rid,
        source_kind="user_utterance", source_ref="utt/%s" % rid,
        participant_id=("A" if basis != "record_only" else None),
        participation_basis=basis, basis_ref="utt/%s" % rid,
        commitment_state="not_a_commitment", revision=1,
        prev_digest=None, changed_at=PIN, change_authority="synthetic")


def _store(*recs):
    s = RecoveryStore()
    for r in recs:
        s.insert(r)
    return s


# ================================================ 裁定一 · cause 归因

@case("AP-1", "凌翼反例：两次纠正，cause 必须是第二次的依据")
def ap1():
    """⚠ 凌翼静态推导出的反例，我复现成立，旧实现确实给错。

    旧实现：从累计 relation 取首条 ⇒ 给出 A（错）
    正确：  B（第二次纠正才把 R 搬出分母）
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))

    s.correct("R", "v2", "A", "first")
    assert s.get("R")["participation_basis"] == "first_person_report", (
        "前提：第一次纠正后 R 应仍是 first_person_report")
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 0

    s.correct("R", "v3", "B", "second")
    assert s.get("R")["participation_basis"] == "record_only"

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition"] == 1
    cause = r["denominator_attrition_cause"]["R"]
    assert cause == "B", (
        "cause 应为第二次纠正依据 'B'，实测 %r。"
        "若为 'A' 说明仍取累计 relation 首条。" % (cause,))
    return "cause='B'（不是 'A'）"


@case("AP-2", "三次纠正：取真正跃变那一版")
def ap2():
    """前两次都不改变 basis（都是 first_person），第三次才搬走。"""
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("A2", "first_person_report"),
               _rec("Z", "record_only"))
    s.correct("R", "v2", "A", "c1")
    s.correct("R", "v3", "A2", "c2")
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 0
    s.correct("R", "v4", "Z", "c3")

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition_cause"]["R"] == "Z", (
        "应追到第三次的 'Z'，实测 %r"
        % r["denominator_attrition_cause"]["R"])
    return "三条边中选第三条 'Z'"


@case("AP-3", "退出 → 恢复 → 再次退出，cause 跟着最后一次跃变")
def ap3():
    """凌翼要求覆盖「退出、恢复、再次退出」的多次转换。"""
    s = _store(_rec("R", "first_person_report"),
               _rec("out1", "record_only"),
               _rec("back1", "first_person_report"),
               _rec("out2", "record_only"))

    s.correct("R", "v2", "out1", "exit-1")
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 1
    assert AI.synthetic_ratios(s, [])["denominator_attrition_cause"]["R"] \
        == "out1"

    s.correct("R", "v3", "back1", "recover")
    r2 = AI.synthetic_ratios(s, [])
    assert r2["denominator_attrition"] == 0, (
        "恢复后应回到 0，实测 %d" % r2["denominator_attrition"])
    assert r2["denominator_attrition_cause"] == {}

    s.correct("R", "v4", "out2", "exit-2")
    r3 = AI.synthetic_ratios(s, [])
    assert r3["denominator_attrition"] == 1
    assert r3["denominator_attrition_cause"]["R"] == "out2", (
        "再次退出应追到 'out2'，实测 %r"
        % r3["denominator_attrition_cause"]["R"])
    return "exit(out1) → recover → exit(out2)，cause 跟最后跃变"


@case("AP-4", "回归：单次纠正仍然正确（不因修复而退化）")
def ap4():
    s = _store(_rec("R", "first_person_report"),
               _rec("only", "record_only"))
    s.correct("R", "v2", "only", "single")
    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition_cause"] == {"R": "only"}
    return "单次：cause='only'"


@case("AP-5", "归因未知必须显式报告，不得静默给错 ID")
def ap5():
    """凌翼：「如历史证据无法确定相应纠正依据，
            应显式报告归因未知，不得静默给出错误 ID。」

    构造：一条记录现在不是 first_person，历史里有过 first_person，
    但跃变那一版【没有】correction_of 边。
    直接篡改历史来模拟（normal 路径产生不了这种数据）。
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("donor", "record_only"))
    s.correct("R", "v2", "donor", "wash")

    # 模拟「跃变版缺边」：把 rev2 的 relation 清空
    for h in s._history["R"]:
        if h.get("revision") == 2:
            h["relation"] = []

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition"] == 1, (
        "前提：仍应算作流失，实测 %d" % r["denominator_attrition"])
    cause = r["denominator_attrition_cause"].get("R")
    assert cause == AI.UNKNOWN_CAUSE, (
        "无法归因时应为 %r，实测 %r（不得静默给一个 ID）"
        % (AI.UNKNOWN_CAUSE, cause))
    assert r["denominator_attrition_unknown"] == ["R"], (
        "应同时列出归因未知的记录，实测 %r"
        % r["denominator_attrition_unknown"])
    return "缺边 ⇒ cause=ATTRIBUTION_UNKNOWN 且列入 unknown"


@case("AP-6", "反证：AP-1 不是空的 —— 取累计首条会得到 'A'")
def ap6():
    """若把算法改回「取累计 relation 首条」，必须得到 'A'。
    证明 AP-1 的断言有分辨力。
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))
    s.correct("R", "v2", "A", "first")
    s.correct("R", "v3", "B", "second")

    # 旧算法的行为：取当前 relation 的第一条 correction_of
    old_cause = None
    for edge in (s.get("R").get("relation") or []):
        if edge.get("relation_type") == "correction_of":
            old_cause = edge.get("to_id")
            break
    assert old_cause == "A", (
        "旧算法应给出 'A'（证明它确实错），实测 %r" % old_cause)

    new_cause = AI.synthetic_ratios(s, [])["denominator_attrition_cause"]["R"]
    assert new_cause == "B" and new_cause != old_cause
    return "旧算法 'A' / 新算法 'B' —— 有分辨力"


# ================================================ 裁定二 · preflight

@case("AP-7", "preflight 正常态：计划与登记一致、锚点各命中一次")
def ap7():
    pf = PF.preflight([m[0] for m in TM.MUTATIONS],
                      os.path.join(HERE, TM.TARGET),
                      TM.MUTATIONS)
    assert pf["ok"] is True, "正常计划被拒：%r" % pf["reasons"]
    assert pf["n_plan"] == pf["n_registered"], (
        "计划 %d / 登记 %d" % (pf["n_plan"], pf["n_registered"]))
    assert all(a["count"] == 1 for a in pf["anchors"])
    return "%d 条，全部 count==1" % pf["n_plan"]


@case("AP-8", "负向：人为使锚点失效 ⇒ preflight 必须拒绝")
def ap8():
    """凌翼裁定二：「增加一个负向回归：人为使锚点失效，
    preflight 应在完整变异运行前拒绝执行。」
    """
    bad = list(TM.MUTATIONS)
    # 把 I1 的旧锚点换成一个不存在的字符串
    m = bad[0]
    bad[0] = (m[0], m[1], "__ANCHOR_THAT_DOES_NOT_EXIST__", m[3], m[4])

    pf = PF.preflight([x[0] for x in bad],
                      os.path.join(HERE, TM.TARGET), bad)
    assert pf["ok"] is False, "锚点失效未被拒绝 ⇒ fail-open，违反裁定二第 3 条"
    assert any("锚点命中 0 次" in r for r in pf["reasons"]), pf["reasons"]
    return "拒绝执行，原因：%s" % pf["reasons"][0]


@case("AP-9", "负向：计划少于登记（清单缩水）⇒ 必须拒绝")
def ap9():
    plan = [m[0] for m in TM.MUTATIONS if m[0] != "I14"]
    pf = PF.preflight(plan, os.path.join(HERE, TM.TARGET), TM.MUTATIONS)
    assert pf["ok"] is False, "清单缩水未被拒绝 ⇒ 违反裁定二第 1 条"
    assert pf["missing_ids"] == ["I14"], pf["missing_ids"]
    return "missing_ids=['I14']"


@case("AP-10", "负向：计划含未登记项 ⇒ 必须拒绝")
def ap10():
    plan = [m[0] for m in TM.MUTATIONS] + ["I_GHOST"]
    pf = PF.preflight(plan, os.path.join(HERE, TM.TARGET), TM.MUTATIONS)
    assert pf["ok"] is False
    assert pf["unknown_ids"] == ["I_GHOST"], pf["unknown_ids"]
    return "unknown_ids=['I_GHOST']"


@case("AP-11", "要求 4：preflight 失败也留下带本次 run_id 的报告")
def ap11():
    """凌翼：「失败也必须留下具有本次 run_id 的可辨认结果，
    不得沿用旧报告。」

    ⇒ 跑真驱动，但先破坏目标文件的一个锚点（在临时目录里做），
      验证报告被覆写且 run_id 变化、verdict=EVIDENCE_FAIL、
      baseline 未运行。
    """
    import shutil
    import subprocess

    with tempfile.TemporaryDirectory() as td:
        work = os.path.join(td, "proto")
        shutil.copytree(HERE, work,
                        ignore=shutil.ignore_patterns("__pycache__",
                                                      "*.npy"))
        # 破坏 I1 的锚点
        m = TM.MUTATIONS[0]
        p = os.path.join(work, TM.TARGET)
        with open(p, encoding="utf-8") as f:
            src = f.read()
        assert src.count(m[2]) == 1
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(src.replace(m[2], "__BROKEN_ANCHOR__", 1))

        r = subprocess.run([sys.executable,
                            os.path.join(work, "test_mutations_importance.py")],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           cwd=work, timeout=600,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        assert r.returncode == 1, (
            "preflight 失败时退出码应为 1，实测 %d" % r.returncode)

        rep = os.path.join(work, "reports",
                           "mutations_importance_result.json")
        assert os.path.exists(rep), "preflight 失败未写报告"
        with open(rep, encoding="utf-8") as f:
            d = json.load(f)

    assert d["verdict"] == "EVIDENCE_FAIL", d["verdict"]
    assert d["manifest_check"] == "NOT_RUN_PREFLIGHT_FAILED", \
        d["manifest_check"]
    assert d["baseline_ok"] is None, (
        "preflight 失败时基线不应被运行，实测 baseline_ok=%r"
        % d["baseline_ok"])
    assert d.get("preflight", {}).get("ok") is False
    assert d.get("run_id"), "报告必须带 run_id"
    assert d.get("rows") == [], "preflight 失败时不应有变异行"
    return "verdict=FAIL / baseline 未跑 / 带 run_id"


@case("AP-12", "反证：正常计划下 preflight 通过，证明 AP-8/9/10 不是恒假")
def ap12():
    """若 preflight 永远返回 False，AP-8/9/10 也都会绿。
    这里必须有一条能通过的，证明上面三条有分辨力。
    """
    ok = PF.preflight([m[0] for m in TM.MUTATIONS],
                      os.path.join(HERE, TM.TARGET), TM.MUTATIONS)
    assert ok["ok"] is True, "正常计划应通过，实测 reasons=%r" % ok["reasons"]
    assert ok["reasons"] == []
    return "正常计划 ok=True / reasons=[]"


# ================================================ 汇总
def main():
    print("=" * 80)
    print("凌翼 2026-11-27 裁定 · 定点回归（cause 归因 + preflight）")
    print("=" * 80)
    print()
    for f in (ap1, ap2, ap3, ap4, ap5, ap6, ap7, ap8, ap9, ap10,
              ap11, ap12):
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
