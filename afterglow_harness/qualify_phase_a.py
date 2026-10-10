"""
qualify_phase_a.py — THE single Phase-A qualification entry point (RC11).

凌翼 R2/R4: "什么程序决定 PASS 终于只有一个入口". Exit 0 ONLY if ALL of:

    binding preflight
    AND known-answer suite
    AND adversarial regression
    AND ledger replay  (of THE RUN THIS SUITE JUST PRODUCED)

凌翼/知微 RC11 §4: the suite and the replay MUST be linked by the SAME-RUN
identity. This entry point does NOT hard-code a version ledger path; it reads
the RUN MANIFEST that run_known_answer_suite.py just wrote, and replays THAT
ledger dir. If the suite wrote RC<N>_ledgers, this replays RC<N>_ledgers — never
a stale previous-version dir.

Any failure => exit non-zero.

Usage:
    python qualify_phase_a.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
ROOT = HERE.parent
ARTIFACTS = ROOT / "afterglow_harness_artifacts"
RUN_MANIFEST_PATH = ARTIFACTS / "RC11_run_manifest.json"


def _run(script: str, *args: str) -> tuple[int, str]:
    p = subprocess.run([PY, str(HERE / script), *args], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def main() -> int:
    steps = []

    # 0. delete any prior run manifest so a stale one can never be consumed
    if RUN_MANIFEST_PATH.exists():
        RUN_MANIFEST_PATH.unlink()

    # 1. binding preflight + known-answer suite (the driver prints full preflight)
    rc, out = _run("run_known_answer_suite.py")
    suite_ok = (rc == 0 and "KNOWN_ANSWER_SUITE = PASS" in out)
    steps.append(("known_answer_suite", suite_ok))

    # 2. adversarial regression
    rc, out = _run("adversarial_regression.py")
    steps.append(("adversarial_regression", rc == 0 and "PASS" in out.splitlines()[-1]))

    # 3. ledger replay — of the SAME RUN's ledger dir (from the RUN MANIFEST)
    replay_ok = False
    if RUN_MANIFEST_PATH.exists():
        try:
            run_manifest = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8"))
            ledger_dir = run_manifest["ledger_dir"]
            rc, out = _run("recompute_from_ledger.py", "--ledger", str(ledger_dir))
            replay_ok = (rc == 0 and "RECOMPUTE_FROM_LEDGER = PASS" in out)
        except Exception as e:  # malformed manifest => FAIL CLOSED
            print(f"run manifest unreadable: {e}")
            replay_ok = False
    else:
        print("run manifest missing => this run produced no ledger dir => FAIL")
    steps.append(("ledger_replay", replay_ok))

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
