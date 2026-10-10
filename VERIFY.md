# Independent Verification Guide

For 凌翼 / 睫 / 知微.

> **RC7 is FAILED QUALIFICATION / RETAINED FOR AUDIT** (see README). Any RC7-era hash printed
> elsewhere is NOT current. The RC8 hash table is regenerated at freeze time; until then treat
> every "current" hash as provisional.

---

## 0 · Reproduce the frozen hashes

**Authoritative source = the frozen bytes + the detached record, NOT this document.**
This doc deliberately does **not** hand-carry the full component hash table (it drifted
before). Derive it live:

```bash
# MANIFEST (authoritative: also in reports/MANIFEST_v0.1_HASH.txt)
wc -c reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md      # 25165
sha256sum reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md
# 61cbfd9f78e545ef5bc8f0bdd87fd10064721dea06d0de879537a2e6ca5a99ed

# SPEC (unchanged since b7ec)
wc -c spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md                  # 36719
sha256sum spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md
# b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33

# prereg (FREEZE_CANDIDATE bytes)
wc -c prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md                    # 52129
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

## 1 · Bound-runtime roles (RC8)

RC8 has an explicit, non-empty **required runtime role set** (`qualification_binding.py`) with an
exact role → path → hash map. Preflight FAILS (NON_QUALIFYING) if: any required role is missing,
or the observed role set ≠ the frozen required set; any role file-hash ≠ frozen; the MANIFEST
hash ≠ the detached record; the actual SPEC/prereg file hashes ≠ frozen constants; the fixture
contract identity ≠ frozen set. An **empty** role set must FAIL (no vacuous `all({})=True`).

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
python afterglow_harness/recompute_from_ledger.py --ledger artifacts/RC8/ledgers --out /tmp/recompute
# must re-derive L1/C1/T_write/pre-C2-C3/J-validity/reset-validity/post-C1-C2-C3/L2 and MATCH the run
```

---

## 4 · Adversarial regression (must ALL be rejected)

```bash
python afterglow_harness/adversarial_regression.py    # expect ADVERSARIAL REGRESSION = PASS
```

Covers: bad J timing · storage no-op · constant extra / absent pre-C3 · invalid reset V5f ·
V4b separability attack · reader that ignores substrate · empty/missing component-set attack ·
plus all prior known-answer regressions.

---

## 5 · Re-run everything

```bash
cd afterglow_harness
python smoke_components.py
python smoke_evaluator.py
python bd52_timing_witness_check.py
python adversarial_regression.py
python verify_manifest_binding.py
python run_known_answer_suite.py     # KNOWN_ANSWER_SUITE = PASS (QUALIFYING) only when frozen
```

---

## Canonical form expectations

```text
SPEC     : 36719 B, UTF-8, no BOM, LF, exactly one final newline
MANIFEST : 25165 B, UTF-8, no BOM, LF, exactly one final newline
```
