"""
qualify_phase_a.py — THE single Phase-A qualification entry point (RC9).

凌翼 R2/R4: "什么程序决定 PASS 终于只有一个入口". Exit 0 ONLY if ALL of:

    binding preflight
    AND known-answer suite
    AND adversarial regression
    AND ledger replay

all pass. Any failure => exit non-zero.

Usage:
    python qualify_phase_a.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def _run(script: str, *args: str) -> tuple[int, str]:
    p = subprocess.run([PY, str(HERE / script), *args], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def main() -> int:
    steps = []

    # 1. binding preflight + known-answer suite (the driver prints full preflight)
    rc, out = _run("run_known_answer_suite.py")
    suite_ok = (rc == 0 and "KNOWN_ANSWER_SUITE = PASS" in out)
    steps.append(("known_answer_suite", suite_ok))

    # 2. adversarial regression
    rc, out = _run("adversarial_regression.py")
    steps.append(("adversarial_regression", rc == 0 and "PASS" in out.splitlines()[-1]))

    # 3. ledger replay (required scope; zero-check must FAIL)
    ledger = HERE.parent / "afterglow_harness_artifacts" / "RC9_ledgers"
    rc, out = _run("recompute_from_ledger.py", "--ledger", str(ledger))
    steps.append(("ledger_replay", rc == 0 and "RECOMPUTE_FROM_LEDGER = PASS" in out))

    print("=" * 72)
    print("PHASE A QUALIFICATION — single entry point")
    print("=" * 72)
    all_ok = True
    for name, ok in steps:
        all_ok &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print("=" * 72)
    print("PHASE_A_QUALIFICATION =", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
