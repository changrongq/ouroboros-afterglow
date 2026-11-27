# -*- coding: utf-8 -*-
"""基线核验与运行身份的反例测试（凌翼裁定 2026-11-27 第 3.2 项）

凌翼原话：
    「3.2：校验基线真实执行，并为每次运行建立独立身份、
          失败状态及旧报告失效机制。
     两项均需以针对性反例测试确认。」

知微原话（她实测出的两种形态）：
    ① 基线子进程替为 exit 0、零用例输出 ⇒ 仍 COMPLETE / 0
    ② 已有成功报告 + 模拟基线 exit 1 ⇒ 进程正确 exit 1，
       但结果路径字节不变，仍是上次的 COMPLETE

本文件对这两条各做反例：在【真实驱动】的临时副本上，
把基线替换成上述两种形态，然后核：
    - 退出码
    - 报告文件是否被本次覆盖
    - 报告里的 run_id 是否与本次不同（从而可判「读到旧报告」）

运行：python afterglow_a/prototype/test_baseline_freshness.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
DRIVER = "test_mutations_importance.py"
REPORT = os.path.join("reports", "mutations_importance_result.json")


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


def copy_tree(td):
    # ⚠ 2026-11-27：加 mutation_preflight.py —— 驱动 import 它，
    #   不拷进来基線子进程会 ImportError（BF 四条当场全红抓到的）。
    for f in ("afcore.py", "afrecover.py", "afimportance.py",
              "mutation_manifest.py", "mutation_preflight.py",
              "test_importance_a3b3.py",
              "test_importance_boundary.py", "test_evidence_state.py",
              DRIVER):
        src = os.path.join(HERE, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(td, f))
    os.makedirs(os.path.join(td, "reports"), exist_ok=True)


def run_driver(td, timeout=900):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, os.path.join(td, DRIVER)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=td, env=env, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def read_report(td):
    p = os.path.join(td, REPORT)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {"__unparseable__": True}


def seed_success_report(td):
    """造一份「上一次的成功报告」，模拟旧结果残留。"""
    p = os.path.join(td, REPORT)
    stub = {
        "run_id": "SEEDED-PREVIOUS-RUN",
        "verdict": "EVIDENCE_COMPLETE",
        "exit_code": 0,
        "baseline_ok": True,
        "counts": {"CAUGHT": 15},
        "rows": [],
        "note": "这是上一次运行留下的成功报告（测试种子）",
    }
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(stub, f, ensure_ascii=False, indent=2)
    return stub


def patch_run_target_test(td, replacement_body):
    """把驱动里的 run_target_test 换成替身（只替换基线那次的行为）。

    做法：不改驱动逻辑，只在文件末尾追加一个覆盖定义 ——
    但驱动是脚本且 main() 在末尾调用，所以必须在调用前注入。

    ⇒ 采用【源码改写】：在 `def main():` 之前插入替身定义，
      使后定义的 run_target_test 覆盖前者。
    """
    p = os.path.join(td, DRIVER)
    src = open(p, encoding="utf-8").read()
    marker = "\ndef main():"
    assert src.count(marker) == 1, "锚点数量异常：%d" % src.count(marker)
    inject = (
        "\n\n# ---- 测试注入：替换基线目标运行（只在测试副本里）\n"
        "_ORIG_RUN_TARGET_TEST = run_target_test\n"
        "def run_target_test(td):\n"
        + replacement_body
        + "\n"
    )
    src = src.replace(marker, inject + marker, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(src)


# ======================================================== 反例 ①
@case("BF-1", "基线 exit 0 但零用例输出 ⇒ 必须判失败并写本次报告")
def bf1():
    """知微实测形态 ①：
    「仅将基线目标子进程替为 exit 0、无任何 case 输出，
      其余 15 个变异与行为探针真实运行，仍判 COMPLETE / 0。」
    """
    with tempfile.TemporaryDirectory() as td:
        copy_tree(td)
        seed = seed_success_report(td)
        patch_run_target_test(
            td,
            "    return 0, ''   # 替身：exit 0、零用例输出")

        rc, out = run_driver(td)
        rep = read_report(td)

        assert rc != 0, (
            "基线零用例仍 exit 0 ⇒ 未拦住（知微实测的形态）")
        assert rep is not None, "基线失败后没写报告 ⇒ 仍残留旧报告"
        assert rep.get("run_id") != seed["run_id"], (
            "报告 run_id 仍是种子的 %r ⇒ 旧报告未失效" % seed["run_id"])
        assert rep.get("verdict") == "EVIDENCE_FAIL", (
            "verdict 应为 EVIDENCE_FAIL，实测 %r" % rep.get("verdict"))
        assert rep.get("baseline_ok") is False, "baseline_ok 应为 False"
        reason = (rep.get("baseline_detail") or {}).get("reason")
        assert reason == "baseline_zero_cases", (
            "失败原因应为 baseline_zero_cases，实测 %r" % reason)
        return ("exit=%d；报告被本次覆盖（run_id 已变）；"
                "reason=baseline_zero_cases" % rc)


# ======================================================== 反例 ②
@case("BF-2", "基线 exit 1 ⇒ 报告必须被本次覆盖，不得残留上次 COMPLETE")
def bf2():
    """知微实测形态 ②：
    「另在已有成功报告的临时目录模拟基线失败，本次进程 exit 1，
      但结果路径字节不变，仍是上次的 COMPLETE。
      它不是本次写出了一个成功结果；问题是消费者分不出报告属于哪次运行。」
    """
    with tempfile.TemporaryDirectory() as td:
        copy_tree(td)
        seed = seed_success_report(td)
        patch_run_target_test(
            td,
            "    return 1, '[FAIL] BASELINE_FAKE 基线替身失败'")

        rc, out = run_driver(td)
        rep = read_report(td)

        assert rc == 1, "基线失败应 exit 1，实测 %d" % rc
        assert rep is not None, "没写报告"
        assert rep.get("run_id") != seed["run_id"], (
            "报告仍是种子（run_id=%r）⇒ 消费者会读到上次的成功"
            % seed["run_id"])
        assert rep.get("verdict") == "EVIDENCE_FAIL", (
            "verdict 应为 EVIDENCE_FAIL，实测 %r" % rep.get("verdict"))
        reason = (rep.get("baseline_detail") or {}).get("reason")
        assert reason == "baseline_nonzero_exit", (
            "失败原因应为 baseline_nonzero_exit，实测 %r" % reason)
        return "exit=1；报告本次覆盖；reason=baseline_nonzero_exit"


# ======================================================== 反例 ③
@case("BF-3", "基线 exit 0、有用例但有用例失败 ⇒ 不得当基线通过")
def bf3():
    with tempfile.TemporaryDirectory() as td:
        copy_tree(td)
        seed_success_report(td)
        patch_run_target_test(
            td,
            "    return 0, '[PASS] A3-1a ok\\n[FAIL] A3-1b 基线替身'")

        rc, out = run_driver(td)
        rep = read_report(td)

        assert rc != 0, "基线有 FAIL 仍 exit 0"
        reason = (rep or {}).get("baseline_detail", {}).get("reason")
        assert reason == "baseline_cases_failed", (
            "应为 baseline_cases_failed，实测 %r" % reason)
        return "exit=%d；reason=baseline_cases_failed" % rc


# ======================================================== 正例对照
@case("BF-4", "反面对照：基线正常时 run_id 与 baseline_ok 均正确")
def bf4():
    """实际跑一次完整驱动（约 1–3 分钟），确认正常路径不被误伤。"""
    with tempfile.TemporaryDirectory() as td:
        copy_tree(td)
        seed = seed_success_report(td)
        rc, out = run_driver(td)
        rep = read_report(td)

        assert rc == 0, "正常基线应 exit 0，实测 %d" % rc
        assert rep is not None
        assert rep.get("run_id") != seed["run_id"], "报告未被本次覆盖"
        assert rep.get("baseline_ok") is True, "baseline_ok 应为 True"
        assert rep.get("verdict") == "EVIDENCE_COMPLETE", (
            "verdict 应为 EVIDENCE_COMPLETE，实测 %r" % rep.get("verdict"))
        n = (rep.get("baseline_detail") or {}).get("n_case")
        assert n and n > 0, "基线应记录实际运行过的 case 数，实测 %r" % n
        return "exit=0；run_id 已更新；baseline n_case=%d" % n


# ======================================================== 汇总
def main():
    print("=" * 82)
    print("基线核验与运行身份 · 反例测试（凌翼 2026-11-27 §3.2）")
    print("=" * 82)
    print()
    for f in (bf1, bf2, bf3, bf4):
        f()
    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print()
    print("=" * 82)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 82)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
