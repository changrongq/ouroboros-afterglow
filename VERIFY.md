# Independent Verification Guide

For 凌翼 / 睫 / 知微.

> **RC7, RC8, RC9, RC10 are RETAINED FOR AUDIT / NOT the current candidate** (see README).
> RC11 is the CURRENT CLOSED CANDIDATE (`PHASE_A_QUALIFICATION = PASS`; 凌翼 FINAL
> ADJUDICATION). Any hash printed in an older document is NOT current. Authoritative source
> = the frozen bytes + the detached record, NOT this document.

---

## 0 · Reproduce the frozen hashes

**Authoritative source = the frozen bytes + the detached record, NOT this document.**
This doc deliberately does **not** hand-carry the full component hash table (it drifted
before). Derive it live:

```bash
# MANIFEST (authoritative: also in reports/MANIFEST_v0.1_HASH.txt)
sha256sum reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md
# 78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059

# SPEC (unchanged since b7ec)
sha256sum spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md
# b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33

# prereg (FREEZE_CANDIDATE bytes)
sha256sum prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md
# ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4

# Component role→hash table (live, from the actual files — do NOT hand-copy)
python afterglow_harness/manifest_bind.py table   # BUILD tool; prints components/rules/fixtures

# All .py must be LF (no CR)
python -c "import glob;print([p for p in glob.glob('afterglow_harness/*.py') if b'\r' in open(p,'rb').read()])"
```

Cross-check: `reports/MANIFEST_v0.1_HASH.txt` must carry the same MANIFEST value. The
**bound** role→hash check runs in the qualification preflight (§1), not by hand here.

---

## 1 · Bound-runtime roles (RC11 — single registry, three-way equality)

`afterglow_harness/qualification_role_registry.py` is the ONE data-only role registry.
The MANIFEST §十三 carries the role table between `EXECUTION_CRITICAL_ROLE_TABLE_BEGIN/END`.
Preflight requires EXACT equality (non-empty):

```
registry EXECUTION_CRITICAL_ROLES  ==  MANIFEST parsed roles  ==  actual required files
```

FAILS if: any required role missing; role set ≠ frozen; any file-hash ≠ frozen; MANIFEST ≠
detached record; actual SPEC/prereg hashes ≠ frozen; fixture-contract hash ≠ bound; or any
BUILD_PROVENANCE role leaks into the execution-critical table. Empty set => FAIL.

```bash
python afterglow_harness/run_known_answer_suite.py    # full preflight must print all True
```

---

## 2 · Single frozen oracle source

`fixture_contracts.py` is the ONE bound canonical object (`FIXTURE_CONFIGS`, `FROZEN_ORACLES`,
`REQUIRED_FIXTURE_IDS`). `fixtures.py` consumes **config only**; the comparator consumes
**oracle only**; `evaluator.py` consumes **neither**.

```bash
grep -rn "oracle" afterglow_harness/evaluator.py      # must be EMPTY
```

---

## 3 · Ledger is independently recomputable

Raw observations per **member × arm × phase** (S_write / J_after / S_handoff / S_restored /
reset_witness); `J = NOT_APPLICABLE` where an arm has no J.

```bash
python afterglow_harness/recompute_from_ledger.py --ledger artifacts/RC11/ledgers
# CONTRACT-driven REQUIRED_SCOPE per fixture; zero checks / missing key / extra key => FAIL;
# digest recomputed from raw bytes; must MATCH the recorded run
```

---

## 4 · Adversarial regression (must ALL be rejected)

```bash
python afterglow_harness/adversarial_regression.py    # expect ADVERSARIAL REGRESSION = PASS
```

Covers: bad J timing · handoff discontinuity · storage no-op · constant extra / absent pre-C3 ·
invalid reset V5f · V4b separability attack · reader that ignores substrate · missing member ·
empty/missing component-set attack · plus all prior known-answer regressions.

---

## 5 · Re-run everything (single entry)

```bash
cd afterglow_harness
python qualify_phase_a.py     # THE single PASS entry: suite AND adversarial AND ledger replay
```

Individual checks:

```bash
python smoke_components.py
python smoke_evaluator.py
python adversarial_regression.py
python verify_manifest_binding.py
python run_known_answer_suite.py     # KNOWN_ANSWER_SUITE = PASS (QUALIFYING) only when frozen
```

---

## Canonical form expectations

```text
SPEC     : 36719 B, UTF-8, no BOM, LF, exactly one final newline
MANIFEST : 28142 B, UTF-8, no BOM, LF, exactly one final newline   (RC11)
```
