"""q3_report_facts.py — generate REPORT NUMBERS from ARCHIVED evidence.

凌翼 engineering suggestion (2026-10-16): "让脚本从本次归档证据中直接生成 PID、句柄值和
测试结果，尽量不再由人手抄写。这是减少错误源头，而不是增加一层审查。"

This tool does NOT judge correctness and adds NO acceptance layer. It merely PARSES
the archived raw output files (which are the byte-truth) and prints report-ready facts,
so numbers in reports are machine-read instead of hand-copied. (I repeatedly quoted
stale run values; this removes the hand-copy source.)

Usage:
    python q3_report_facts.py <archived_raw_file> [more files ...]

It recognises the raw-output shapes produced by:
  · q3_t0_enumerator_experiment            (worker_pid_spawned/enumerated, class16/64...)
  · _test_v2_producer / v2_trusted_producer_raw      (worker pid, reported handle 344...)
  · _test_v2_benign   / v2_benign_control_raw        (worker pid, benign handle ...)
  · _test_v2_t1neg    / v2_t1_negative_recheck_raw   (worker pid ... benign ... protected ...)

Output is plain text you can paste into a report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _facts_from_text(text: str) -> dict:
    out: dict = {}
    # "worker pid 39732 benign 300 protected 324"  (T1 negative recheck)
    m = re.search(r"worker pid (\d+) benign (\d+) protected (\d+)", text)
    if m:
        out["worker_pid"] = int(m.group(1))
        out["benign_handle"] = int(m.group(2))
        out["protected_handle"] = int(m.group(3))
    # "worker pid 34048 benign handle 300"  (benign control)
    if "worker_pid" not in out:
        m = re.search(r"worker pid (\d+) benign handle (\d+)", text)
        if m:
            out["worker_pid"] = int(m.group(1))
            out["benign_handle"] = int(m.group(2))
    # "worker pid 39848 reported handle 344"  (producer)
    if "worker_pid" not in out:
        m = re.search(r"worker pid (\d+) reported handle (\d+)", text)
        if m:
            out["worker_pid"] = int(m.group(1))
            out["reported_handle"] = int(m.group(2))
    # T0 JSON-ish lines
    m = re.search(r'"worker_pid_spawned":\s*(\d+)', text)
    if m:
        out["worker_pid_spawned"] = int(m.group(1))
    m = re.search(r'"worker_pid_enumerated":\s*(\d+)', text)
    if m:
        out["worker_pid_enumerated"] = int(m.group(1))
    for cls in ("class16", "class64"):
        m = re.search(rf'"{cls}_count":\s*(\d+)', text)
        if m:
            out[f"{cls}_count"] = int(m.group(1))
        for lbl in ("ha", "hb"):
            m = re.search(rf'"{cls}_saw_{lbl}":\s*(true|false)', text)
            if m:
                out[f"{cls}_saw_{lbl}"] = (m.group(1) == "true")
    # controls=[...]  (benign accepted line)
    for m in re.finditer(r"controls=\s*\[([0-9,\s]*)\]", text):
        vals = [int(x) for x in re.findall(r"\d+", m.group(1))]
        out.setdefault("controls_seen", []).append(vals)
    # VERDICT lines
    verdicts = re.findall(r"^\s*\[?(P|N1|N1b|N2)\b[^\n]*", text, re.MULTILINE)
    verdicts += re.findall(r"(positive producer verification|forged/unverified rejection|hand-built rejected|benign control accepted|target==protected excluded|target-as-benign rejected|identity-unreadable rejected|no-comparable-target rejected):\s*(PASS|FAIL)",
                           text)
    if verdicts:
        out["verdict_lines"] = verdicts
    # any [PASS]/[FAIL]
    out["pass_count"] = len(re.findall(r"\bPASS\b", text))
    out["fail_count"] = len(re.findall(r"\bFAIL\b", text))
    return out


def main(argv) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    for path in argv[1:]:
        p = Path(path)
        if not p.is_file():
            print(f"# MISSING: {p}")
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        facts = _facts_from_text(text)
        print(f"# === FACTS FROM {p.name} (machine-read; do NOT hand-copy) ===")
        for k in sorted(facts):
            print(f"{k} = {facts[k]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
