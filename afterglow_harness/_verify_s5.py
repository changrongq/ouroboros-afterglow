"""Verify §5 (ledger replay) attacks now FAIL."""
import json, tempfile, subprocess, sys
from pathlib import Path

led = Path("../afterglow_harness_artifacts/RC9_ledgers")

# wrong V0: flip actual L1 -> replay must FAIL (recomputed L1 != recorded)
v0 = json.loads((led / "V0.json").read_text(encoding="utf-8"))
v0["actual"]["L1"] = "PASS"
t = Path(tempfile.mkdtemp()); (t / "0.json").write_text(json.dumps(v0), encoding="utf-8")
r = subprocess.run([sys.executable, "recompute_from_ledger.py", "--ledger", str(t)],
                   capture_output=True, text=True)
print("wrong-V0 exit:", r.returncode, "->", r.stdout.strip().splitlines()[-1])

# empty actual -> zero checks -> FAIL
v5 = json.loads((led / "V5a.json").read_text(encoding="utf-8"))
v5["actual"] = {}
t2 = Path(tempfile.mkdtemp()); (t2 / "0.json").write_text(json.dumps(v5), encoding="utf-8")
r2 = subprocess.run([sys.executable, "recompute_from_ledger.py", "--ledger", str(t2)],
                    capture_output=True, text=True)
print("empty-actual exit:", r2.returncode, "->", r2.stdout.strip().splitlines()[-1])

# stale digest: change C J_after q_raw, drop reset_valid -> must FAIL
v5b = json.loads((led / "V5a.json").read_text(encoding="utf-8"))
for m in v5b["ledger"]["observations"].values():
    m["arms"]["C"]["J_after"]["q_raw"] = "00" * 8
    m["arms"]["C"].get("S_handoff", {})
t3 = Path(tempfile.mkdtemp()); (t3 / "0.json").write_text(json.dumps(v5b), encoding="utf-8")
r3 = subprocess.run([sys.executable, "recompute_from_ledger.py", "--ledger", str(t3)],
                    capture_output=True, text=True)
print("stale-digest exit:", r3.returncode, "->", r3.stdout.strip().splitlines()[-1])
