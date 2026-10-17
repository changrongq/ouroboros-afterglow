"""LINGYI `JIE FOUR PROPOSALS RULING` (2026-10-17) — executable conformance check.

This driver does NOT touch a live worker, does NOT gather evidence, and does NOT decide
anything about isolation. It only asserts that the ruling is represented in code such
that the forbidden moves are actually blocked:

  item 1  PROBE_CLEAN != BUSINESS_CLEAN ... verdict carries SUBJECT + SCOPE
  item 2  TWO-SNAPSHOT EARLY STOP = DIAGNOSTIC ONLY ... gate is CLOSED until the three
          definitions exist, and records C_FEASIBILITY_NOT_ESTABLISHED + STOP if absent
  item 3  UNREADABLE TARGET CONTROL => UNRESOLVED, never CLEAN; simulation is not proof
  item 4  PERSISTENT_WORKER_CLEAN_BLOCK = ACTIVE, present in every applicable verdict

Expected: DISTINCT_RESULTS: PASS
"""
from __future__ import annotations

import sys

import q3_business_handle_audit_v2 as V

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILURES.append(name)


def main() -> int:
    print("== item 1: PROBE_CLEAN != BUSINESS_CLEAN ==")
    check("ruling date pinned", V.LINGYI_JIE_RULING_DATE == "2026-10-17", V.LINGYI_JIE_RULING_DATE)
    check("probe != business flag", V.PROBE_CLEAN_IS_NOT_BUSINESS_CLEAN is True)
    check("PERSISTENT_BUSINESS_CLEAN = NOT ESTABLISHED",
          V.PERSISTENT_BUSINESS_CLEAN == "NOT ESTABLISHED", V.PERSISTENT_BUSINESS_CLEAN)
    r = V.V2AuditResult(pid=1, status=V.V2_CLEAN, target_path="x")
    check("verdict has subject", r.subject in (V.VERDICT_SUBJECT_PROBE, V.VERDICT_SUBJECT_BUSINESS),
          r.subject)
    check("verdict has scope", bool(r.scope), r.scope)
    check("CLEAN not promotable to business", r.promotable_to_business_clean is False)

    print("== item 2: two-snapshot early stop ==")
    check("early stop is DIAGNOSTIC ONLY",
          V.C_TWO_SNAPSHOT_EARLY_STOP == "DIAGNOSTIC ONLY", V.C_TWO_SNAPSHOT_EARLY_STOP)
    check("three required definitions listed",
          len(V.C_QUIESCENCE_PROOF_REQUIRED_DEFINITIONS) == 3,
          str(V.C_QUIESCENCE_PROOF_REQUIRED_DEFINITIONS))
    g = V.quiescence_gate()          # nothing defined -- the honest current state
    check("gate CLOSED with no definitions", g["gate_open"] is False)
    check("missing lists all three", len(g["missing"]) == 3, str(g["missing"]))
    check("quiescence_proven stays False", g["quiescence_proven"] is False)
    check("records C_FEASIBILITY_NOT_ESTABLISHED",
          g["c_feasibility"] == "NOT ESTABLISHED", g["c_feasibility"])
    check("records STOP CURRENT EXPLORATION", g["exploration"] == "STOPPED", g["exploration"])
    check("carries the persistent block",
          g["persistent_worker_clean_block"] == "ACTIVE")
    # even with equal snapshots, quiescence cannot be claimed while the gate is closed
    check("equal snapshots cannot prove quiescence", g["quiescence_proven"] is not True)
    g2 = V.quiescence_gate(True, True, True)
    check("gate opens only when all three asserted", g2["gate_open"] is True)
    check("opening the gate still does not prove quiescence", g2["quiescence_proven"] is None)

    print("== item 3: unreadable target control ==")
    check("result is UNRESOLVED",
          V.UNREADABLE_TARGET_CONTROL_RESULT == V.V2_UNRESOLVED,
          V.UNREADABLE_TARGET_CONTROL_RESULT)
    check("never CLEAN", V.UNREADABLE_TARGET_CONTROL_MAY_BE_CLEAN is False)
    check("simulation is not completeness proof",
          V.SIMULATION_IS_COMPLETENESS_PROOF is False)

    print("== item 4: persistent blocker restatement ==")
    check("PERSISTENT_WORKER_CLEAN_BLOCK = ACTIVE",
          V.PERSISTENT_WORKER_CLEAN_BLOCK == "ACTIVE", V.PERSISTENT_WORKER_CLEAN_BLOCK)
    check("present on default verdict",
          r.persistent_worker_clean_block == "ACTIVE", r.persistent_worker_clean_block)

    print("== route ==")
    check("OPTION_A NOT AUTHORIZED", V.ROUTE_OPTION_A == "NOT AUTHORIZED", V.ROUTE_OPTION_A)
    check("OPTION_B ACTIVE", V.ROUTE_OPTION_B == "ACTIVE", V.ROUTE_OPTION_B)
    check("OPTION_C LIMITED FEASIBILITY ONLY",
          V.ROUTE_OPTION_C == "LIMITED FEASIBILITY ONLY", V.ROUTE_OPTION_C)

    print("== jie's split constants ==")
    check("operational constant", V.UNRESOLVED_KIND_OPERATIONAL == "operational")
    check("no_identity constant", V.UNRESOLVED_KIND_NO_IDENTITY == "no_identity")

    print()
    if FAILURES:
        print(f"DISTINCT_RESULTS: FAIL={len(FAILURES)} {FAILURES}")
        return 1
    print("DISTINCT_RESULTS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
