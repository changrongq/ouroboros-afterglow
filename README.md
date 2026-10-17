# ouroboros-afterglow

AFTERGLOW Reference Harness — shared workspace for **凌翼 / 睫 / Coder / 船长**.

This repository is a **shared working tree**, and it is **live**: it changes as the work
progresses. It is **not** a frozen snapshot. The only frozen things are the artifacts
under `prereg/`, `spec/`, `artifacts/RC*/`, the MANIFEST under `reports/`, and the Q3
role set — each with a recorded hash. Everything else moves.

> **This README is a front page, not an authority.** Where any number here disagrees
> with `reports/`, the file under `reports/` wins. See *Front-page accountability* below.

---

## Layout

```
prereg/                  # frozen preregistration (FREEZE_CANDIDATE = frozen ad0855b0…)
spec/                    # frozen SPEC object + freeze record
reports/                 # implementation-binding MANIFEST + detached hash record + errata
reports/review_history/  # correspondence + review reports
afterglow_harness/       # the Reference Harness source (flat module layout, all .py)
artifacts/RC7/ RC8/ RC9/ RC10/ RC11/   # frozen run artifacts, one dir per candidate
tests/                   # (reserved)
README.md / VERIFY.md / .gitattributes / .gitignore
```

> **Deviation from the intended tree (documented honestly):** the MANIFEST lives under
> `reports/`, not a separate `manifest/`. Reason: the frozen, hash-bound drivers
> (`run_known_answer_suite.py`, `verify_manifest_binding.py`) hard-code
> `../reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md`. Moving the MANIFEST
> without editing those drivers would invalidate their bound hashes. All harness `.py`
> are kept in one flat directory (they import each other by bare module name). RC8 will
> introduce a bound qualification-binding module and may revisit this layout.

---

## Qualification lineage

```text
RC7  = FAILED QUALIFICATION / RETAINED FOR AUDIT (adversarial false-PASS defects)
RC8  = FAILED QUALIFICATION / RETAINED FOR AUDIT (seams: reader/pre-class/handoff/member/binding)
RC9  = NOT CLOSED / RETAINED FOR AUDIT (知微 4 P1)
RC10 = NOT CLOSED / RETAINED FOR AUDIT (知微 4 P1)
RC11 = CLOSED  (PHASE_A_QUALIFICATION = PASS; 凌翼 FINAL ADJUDICATION)
```

MANIFEST lineage: RC1 `b3802142…` → … → RC7 `c61d8aa7…`(FAILED) → RC8 `61cbfd9f…`(FAILED)
→ RC9 `67dfb538…`(NOT CLOSED) → RC10 `dd30e3ad…`(NOT CLOSED)
→ **RC11 `78bdb90f…`（CLOSED）**。

**RC11 is the CURRENT CLOSED CANDIDATE** (per `reports/review_history/INDEX.md`).
The lineage above stops at RC11 on purpose — RC7 is retained for audit only and is
**not** current. If any surface (this README, the repo *About* panel, an old summary)
still names RC7 `45acd8b1…` or `c61d8aa7…` as current, that surface is **stale**.

---

## RC11 — closure round (凌翼 R1–R5 + 知微 RC9/RC10/RC11 reviews)

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH (RC11) = 78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059
REFERENCE_HARNESS_SPEC_HASH                 = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
PARENT_PREREG_SHA256                        = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

RC11 repairs (all fail-open -> fail-closed):
- **ONE adjudication chain, TWO ingress**: `evidence_bundle.evaluate_bundle` is the sole judge;
  production (`fixtures.py`) builds the bundle from live runtime, replay (`replay_adapter.py`)
  builds it from raw ledger + the canonical contract (`evidence_contract.CONTRACT_BY_FIXTURE`).
  The ledger answers "what did I observe", never "what was required".
- **REQUIRED_EVIDENCE_CONSUMPTION_MATRIX**: every required field must be RECORDED ∧ CONSUMED
  (production) ∧ CONSUMED (replay) ∧ NEGATIVE-TESTED; missing/empty/malformed ⇒ FAIL CLOSED.
- **Same-run link**: `run_known_answer_suite.py` writes `RC11_run_manifest.json`; the single
  entry point replays THAT ledger dir — no hard-coded version path.
- **reader gate**: EXACT frozen probe set {0,2}; expected derived from `S_restored`; `raw_q` is a
  redundant cross-check only.
- **reset gate**: `reset_valid` mandatory (missing/malformed ⇒ INVALID); reset-preserve rule
  recomputed from raw bytes (`accepted_handoff == verified_restored`).
- **fixture identity**: filename stem == outer id == inner ledger id; unique; exact frozen 13-set.
- **V4.1/V4b**: full decision schema compared; V4b probe does STRUCTURAL + BEHAVIORAL (real ON/OFF
  calls) with a separable positive control.
- **Structured sub-verdicts** are tri-state (True/False/UNEVALUATED); a default is never True.
- **Adversarial regression** (54/54): all of the above, plus all prior RC7/RC8/RC9 false-PASS attacks.

  **Read this number correctly.** 54/54 is the **RC11** closure count. The earlier
  `13/13` figure belongs to **RC7's failing round** — RC7 was subsequently declared
  **NOT CLOSED**, and that 13/13 is precisely why: the suite passed while the
  adversarial machinery was still blind to the defects. A larger count on a later
  candidate does **not** retroactively validate the smaller one.

- **BD-57 + independent review**: BD-57 is listed here as *work performed*, **not** as
  *support*. The independent review of that round concluded **RC7 NOT CLOSED**; the
  review is the reason RC8 exists. Citing it as backing for a claim would invert it.

---

## Status

```text
PHASE_A_QUALIFICATION = PASS (RC11)  [by qualify_phase_a.py: suite + adversarial + replay]
RC11 = CLOSED                        [凌翼 FINAL ADJUDICATION on commit 5e17fe8]
SCIENTIFIC_CLAIM_ELIGIBILITY  = NONE
OS_LEVEL_ISOLATION            = NOT ESTABLISHED
SCIENTIFIC_EXECUTION          = MAY NOT START
```

---

## What this is NOT

- Not scientific evidence of memory / Afterglow mechanism (PHASE A is harness validation).
- Not authorized for scientific execution (OS-level isolation is not yet implemented;
  the reset layer is logic-level only — see the MANIFEST §十).

---

## Front-page accountability

睫 raised this on 2026-10-17, and it is recorded here rather than argued against.

Every number in this file is a **harness-validation** number. None of them is a
scientific result. That gap is not implied by the numbers — it has to be **said**, so
it is said here explicitly:

> `PHASE_A_QUALIFICATION = PASS`, `RC11 = CLOSED`, and `54/54` all describe the
> **instrument**. They do **not** license a single scientific claim. 凌翼's ruling
> carries `SCIENTIFIC_EXECUTION = MAY NOT START`; that ruling is about the experiment,
> and nothing on this page overrides it.

The numbers above and `MAY NOT START` are not in tension — they are about different
things — but a reader arriving at a front page will not know that unless this paragraph
exists. So it exists.

### Current disposition of the isolation layer (2026-10-17)

```text
PROBE_CLEAN_HISTORY            = VERIFIED        (frozen Q3 probe path: pid 35048, 37200)
PERSISTENT_BUSINESS_CLEAN      = NOT ESTABLISHED
CURRENT_BUSINESS_AUDIT         = UNRESOLVED
PERSISTENT_WORKER_CLEAN_BLOCK  = ACTIVE          (凌翼 JIE FOUR PROPOSALS RULING, item 4)
PROBE_CLEAN != BUSINESS_CLEAN  = TRUE            (item 1; verdict binds SUBJECT + SCOPE)
OPTION_A                       = NOT AUTHORIZED  (no name/path/device-class skipping)
OPTION_B                       = ACTIVE           (no CLEAN claim, no wiring)
OPTION_C                       = LIMITED FEASIBILITY ONLY
C_TWO_SNAPSHOT_EARLY_STOP      = DIAGNOSTIC ONLY
C_OBSERVATION_BOUNDARY         = NOT DEFINED
C_FEASIBILITY                  = NOT ESTABLISHED
C_CURRENT_EXPLORATION          = STOPPED
V2_WIRING                      = NOT AUTHORIZED
```

`HANDLE_AUDIT_CLEAN` has real evidence **twice, both on the short-lived probe path**.
Trustworthy evidence count on the **persistent business worker path = 0**.

Unresolved causes are counted separately, because they are not the same finding:
`unresolved_operational` (permission/operation failure — fixable) versus
`unresolved_no_identity` (the object has no readable file identity — not fixable by
privilege). If the former is 0 and the latter is not, more privilege will never make
the number reach 0.

### Why OPTION C exploration is stopped, not merely "incomplete"

凌翼's ruling settled the reasoning, so it is recorded rather than paraphrased:

> `E(t1) == E(t2)` does **not** prove quiescence.
> `E(t1) != E(t2)` does **not** prove snapshot impossibility.

Both outcomes of a two-snapshot comparison are therefore non-proofs, and the comparison
stays diagnostic. Before any snapshot reasoning can count, three things must be defined:

1. **OBSERVATION BOUNDARY** — what is inside versus outside the observed set
2. **SNAPSHOT / COVERAGE SEMANTICS** — what a snapshot is taken to cover
3. **TIME SCOPE OF ASSURANCE** — how long a snapshot verdict is claimed to hold

None of the three is currently defined. The consequence is mechanical, not a judgement
call: **`C_FEASIBILITY = NOT ESTABLISHED`, and the current exploration stops.** This is
encoded as `quiescence_gate()` in `afterglow_harness/q3_business_handle_audit_v2.py` so
the stop condition is executable rather than a sentence in a report.

A CLEAN produced by the V2 auditor is scoped to a **point-in-time single enumeration**.
Handles opened after that enumeration lie outside it. It is never a quiescence claim,
and it is never promoted to `PERSISTENT_BUSINESS_CLEAN`.


---

## Authority map

| Surface | In git? | Authority |
|---|---|---|
| `reports/`, `artifacts/RC*/`, `prereg/`, `spec/` | yes | **authoritative** |
| `README.md` (this file) | yes | front page; reviewable, traceable |
| GitHub repository *About* panel | **no** | facade only; never authoritative |
