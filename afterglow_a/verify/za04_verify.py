# -*- coding: utf-8 -*-
"""验证 ZA-04 修复：语法错误变异必须被判 NOT_EXECUTED，且整体 FAIL。"""
import sys, os, shutil, subprocess, tempfile, json
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
P = os.path.join(ROOT, "afterglow_a", "prototype")
OUT = os.path.join(P, "reports", "za04_negcheck.json")

tmp = tempfile.mkdtemp(prefix="za04chk_")
try:
    for f in os.listdir(P):
        p = os.path.join(P, f)
        if os.path.isfile(p) and f.endswith(".py"):
            shutil.copy2(p, tmp)
    shutil.copytree(os.path.join(P, "synthetic"), os.path.join(tmp, "synthetic"))

    # 注入语法错误
    tgt = os.path.join(tmp, "afcore.py")
    s = open(tgt, encoding="utf-8", newline="").read()
    s = s.replace("class SchemaError(Exception):", "class SchemaError(Exception)", 1)
    open(tgt, "w", encoding="utf-8", newline="").write(s)

    # 用【修后】的 run_in 逻辑判定（直接 import 驱动里的函数）
    sys.path.insert(0, tmp)
    import test_mutations_v4 as drv
    rc, passed, total, out, execd, saw, crash = drv.run_in(tmp)

    print("=== 修后判定 ===")
    print("  rc           =", rc)
    print("  passed/total = %d/%d" % (passed, total))
    print("  saw_summary  =", saw)
    print("  hard_crash   =", crash)
    print("  executed     =", execd)
    print("  ⇒ 旧逻辑 caught =", (rc != 0) or (passed != total), "（会算 CAUGHT）")
    print("  ⇒ 新逻辑 status =", "NOT_EXECUTED" if not execd else "CAUGHT")

    ok = (not execd) and (not saw) and crash
    print("\n[%s] ZA-04 修复生效：语法错误被判 NOT_EXECUTED" % ("OK" if ok else "XX"))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"rc": rc, "passed": passed, "total": total,
                   "saw_summary": saw, "hard_crash": crash,
                   "executed": execd,
                   "old_logic_would_say": "CAUGHT",
                   "new_logic_says": "NOT_EXECUTED" if not execd else "CAUGHT",
                   "za04_fixed": ok}, f, ensure_ascii=False, indent=2)
    print("结果:", OUT)
    sys.exit(0 if ok else 1)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
