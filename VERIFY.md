# Independent Verification Guide (RC7)

For 凌翼 / 睫 / 知微. This mirrors the four-point interface requested.

---

## 0 · Reproduce the frozen hashes

```bash
wc -c reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md   # 23700
sha256sum reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md
# c61d8aa78cd55054c4c17ed280dcc14376829e6517e03563532834f23931d9b0

wc -c spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md   # 36719
sha256sum spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md
# b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33

# NOTE: the frozen PARENT prereg value ad0855b0… corresponds to the
# FREEZE_CANDIDATE bytes (52129 B), which is what prereg/ holds:
wc -c prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md   # 52129
sha256sum prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md
# ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4

# All .py must be LF (no CR). Example:
python -c "print(open('afterglow_harness/harness_constants.py','rb').read().count(b'\r'))"   # 0
```

Cross-check: `reports/MANIFEST_v0.1_HASH.txt` must carry the same MANIFEST value.

---

## 1 · Source hash → each `.py`

Recompute each file hash and compare to the table below (and to the MANIFEST §十三):

```bash
for f in afterglow_harness/*.py; do sha256sum "$f"; done
```

Execution-critical components (must match MANIFEST §十三):

```text
harness_constants.py   a0ce6180ceb6cc2fd1bc136909a0d30151ebd18cd39498f0c31feac6c8cbf7fb
storage.py             8271f42c6a9116e8b079bd759bb6b2d75fb75ee189b97d1445f71bf0206db7b7
writers.py             ae64731b322dc1c4e827d06562eacfbf83b42069d03ed9d4fbd502daaab0cc87
readers.py             83cbc20be47ec96871c830507e5ba9c26fa7e043319258b9e49328af8a867adc
observer.py            f8b68319dc4b8731eb869035884ed8767ebc96c54e7bc28059a5a47e05c3cf52
perturbation_j.py      d0920afdd9cc0a6bd14a45babb0da4468c7417a8c4ccd92896d0d66a7d06cc25
reset.py               d985c278330af1e552b545c791a32b351c83f51566c38b54321ce266374a9ca8
evaluator.py           101f1170dd8ad737ae79a29074ad168596ccb1fb844f4a9fc9766e2918b363dd
fixtures.py            916f62a10ca5a472cb5e5dbf62bf3da917cb4fb8c1fea23cf5526905a630e8c5
run_known_answer_suite.py    9953fa0f43efb96e05fcba011442eaef6a44d6a07c2cde9029c704af7c03e491  (bound driver)
verify_manifest_binding.py   8f9193a794c5b8bfa8e069e7dd2e93b132f04b1a22cddd1c40d2684eb71a771c  (bound driver)
```

---

## 2 · evaluator has NO fixture-id special-casing

- `fixture_V4_1` calls `evaluate_c2_attempt(rule_bundle, scope)` — invalidity derived from
  **scope + missing rule**, not from the fixture id.
- `fixture_V4b` calls `evaluate_c2_architectural(extra_interface_separable=False)`.
- No branch outputs `INVALID` "because fixture is X".

```bash
grep -n "fixture_id" afterglow_harness/evaluator.py   # should show NO result-branching on fixture id
```

---

## 3 · the driver really ran 13 fixtures

`artifacts/RC7/RC7_qualifying_run_raw.json` contains:

```text
binding_captured_before_first_fixture : {SPEC_HASH, MANIFEST_HASH, MANIFEST_BYTES, detached_match, component_binding_no_drift}
fixtures_total          : 13
fixtures_oracle_match   : 13
per_fixture             : [13 entries, each {fixture_id, expected, actual, oracle_match, ledger}]
```

`binding_captured_before_first_fixture` proves §16.2.2 order (hashes captured BEFORE the run).

---

## 4 · raw ledgers derive the 13/13

Each `artifacts/RC7/ledgers/<id>.json` carries `expected`, `actual`, `oracle_match`, `ledger`.
Reconcile `per_fixture` in the raw JSON against the 13 ledger files.

---

## Re-run it yourself (optional)

```bash
cd afterglow_harness
python smoke_components.py             # expect 29/29
python smoke_evaluator.py              # expect 18/18
python bd52_timing_witness_check.py    # expect PASS
python verify_counterexamples.py       # expect COUNTEREXAMPLE REGRESSION = PASS
python verify_manifest_binding.py      # expect BINDING_INTEGRITY = PASS
python run_known_answer_suite.py       # expect KNOWN_ANSWER_SUITE = PASS (13/13, full preflight)
```

`verify_counterexamples.py` reproduces the independent-review counterexamples (no-op
storage, wrong-J substitution, empty C3, INVALID L2) and asserts each is now REJECTED.

(The last will report QUALIFYING only if the frozen MANIFEST hash matches the current bytes.)

---

## Canonical form expectations

```text
SPEC     : 36719 B, UTF-8, no BOM, LF, exactly one final newline
MANIFEST : 22904 B, UTF-8, no BOM, LF, exactly one final newline
```
