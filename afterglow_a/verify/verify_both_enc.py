# -*- coding: utf-8 -*-
"""GBK 下不仅要 rc=0，还要确认判定数字真的被打印出来。"""
import sys, os, subprocess, re
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

CASES = [
    ("afterglow_a/evidence/probe_source_role.py", "源侧证据",
     [("9 条", r"条目数:\s*9"), ("组合", r"m2_reflection_trigger"), ("缺省", r"'user'")]),
    ("afterglow_a/prototype/test_p1_p5.py", "P1-P5",
     [("合计", r"合计\s*17"), ("通过", r"通过\s*17"), ("失败0", r"失败\s*0")]),
    ("afterglow_a/prototype/test_mutations_v4.py", "变异",
     [("CAUGHT", r"CAUGHT\s*7"), ("REDUNDANT", r"REDUNDANT\s*2"),
      ("MISSED", r"MISSED\s*0"), ("VERDICT", r"VERDICT:\s*PASS")]),
]

ok = fail = 0
for f, label, checks in CASES:
    for enc_name, enc in [("UTF-8", "utf-8"), ("GBK", "gbk")]:
        env = dict(os.environ, PYTHONIOENCODING=enc)
        p = subprocess.run([sys.executable, f], cwd=ROOT, capture_output=True,
                           env=env, timeout=300)
        out = p.stdout.decode("utf-8", errors="replace")
        err = p.stderr.decode("utf-8", errors="replace")
        blob = out + err
        miss = [n for n, pat in checks if not re.search(pat, blob)]
        good = (p.returncode == 0 and not miss)
        if good: ok += 1
        else: fail += 1
        print("  [%s] %-10s %-6s rc=%-2d %s"
              % ("OK" if good else "XX", label, enc_name, p.returncode,
                 "" if good else "缺: " + ",".join(miss)))
        if not good and "UnicodeEncodeError" in blob:
            print("       UnicodeEncodeError 仍在")

print("\n结论：OK %d，失败 %d" % (ok, fail))
sys.exit(0 if fail == 0 else 1)
