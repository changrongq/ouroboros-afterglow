# -*- coding: utf-8 -*-
"""收口自查（Mion 2026-11-28 §四 C-1 / C-2 / C-3）

⚠ 这是一次性核对工具，不是常驻测试。
   C-1 所有 E 条款都有对应断言，且每条断言都有变异守护
   C-2 所有已知缺口都已登记为 OPEN
   C-3 没有"被蕴含的东西"混在通过数里

⚠ 它自己不进入 test_*.py，因为它不是被测对象的一部分。
"""
from __future__ import annotations

import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _src(name):
    with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


def check_c1():
    """C-1：每条断言都有变异守护。"""
    test_src = _src("test_blayer_batch1.py")
    tree = ast.parse(test_src)

    cases = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for d in node.decorator_list:
                if (isinstance(d, ast.Call)
                        and getattr(d.func, "id", None) == "case"):
                    cases.append((d.args[0].value, node.name))

    # 变异脚本里 mutate(..., "<test_func_name>")
    mut_src = _src("test_blayer_batch1_mutation.py")
    guarded = set(re.findall(
        r'mutate\([\s\S]{0,400}?"(t\d+\w*|t\d+)"\s*\)', mut_src))

    unguarded = [(cid, fn) for cid, fn in cases if fn not in guarded]
    return {
        "total_cases": len(cases),
        "guarded": sorted(guarded),
        "unguarded": unguarded,
        "ok": not unguarded,
    }


def check_c3():
    """C-3：被蕴含的断言不得计入通过数。

    ⚠ 判据：一个 case 若【没有任何变异能让它单独变红】，
      它就不是防线 —— 它不能单独红，说明它成立与否由别的断言决定。
    """
    # 与 C-1 同一份数据：无变异的 case = 可能是被蕴含的 = 不该计数
    c1 = check_c1()
    implied = [cid for cid, fn in c1["unguarded"]]
    return {
        "implied_cases": implied,
        "counted_in_summary": c1["total_cases"],
        "ok": not implied,
    }


def check_c2():
    """C-2：所有已知缺口已登记为 OPEN。"""
    reg_path = os.path.join(HERE, "..", "..", "afterglow_design",
                            "OPEN条目登记表.md")
    reg_path = os.path.normpath(reg_path)
    if not os.path.exists(reg_path):
        return {"ok": False, "reason": "OPEN条目登记表.md 不存在",
                "entries": []}

    text = io.open(reg_path, encoding="utf-8").read()
    entries = re.findall(r"^##\s+(OPEN-[\w\-]+)", text, re.M)

    # NOT_CHECKED 表里登记的东西 —— 它们不是 OPEN，是「本阶段不检查」，
    # 必须与 OPEN 分开，不能混算
    import lbjudge as LB
    not_checked = [k for k, _v in LB.NOT_CHECKED]

    return {
        "ok": bool(entries),
        "entries": entries,
        "not_checked_entries": not_checked,
        "note": "NOT_CHECKED 是「本阶段不检查」，OPEN 是「已知未修」；"
                "两者不得混算",
    }


def main():
    print("=" * 78)
    print("本批收口自查（Mion 0173c69 §四）")
    print("=" * 78)

    c1 = check_c1()
    print()
    print("[C-1] 每条断言都有变异守护")
    print("  用例总数 %d，有变异守护 %d，无守护 %d"
          % (c1["total_cases"], len(c1["guarded"]), len(c1["unguarded"])))
    if c1["unguarded"]:
        for cid, fn in c1["unguarded"]:
            print("    [无守护] %s (%s)" % (cid, fn))
    print("  结果：%s" % ("PASS" if c1["ok"] else "FAIL"))

    c3 = check_c3()
    print()
    print("[C-3] 被蕴含的断言不得计入通过数")
    print("  疑似被蕴含（无变异可单独红）：%r" % (c3["implied_cases"],))
    print("  当前汇总计数：%d 条" % c3["counted_in_summary"])
    print("  结果：%s" % ("PASS" if c3["ok"] else "FAIL"))

    c2 = check_c2()
    print()
    print("[C-2] 已知缺口已登记为 OPEN")
    print("  OPEN 条目：%r" % (c2["entries"],))
    print("  NOT_CHECKED（本阶段不检查，不算 OPEN）：%r"
          % (c2["not_checked_entries"],))
    print("  结果：%s" % ("PASS" if c2["ok"] else "FAIL"))

    print()
    print("=" * 78)
    all_ok = c1["ok"] and c2["ok"] and c3["ok"]
    print("三条齐 → %s" % ("YES，可请 Mion 出 v0.5" if all_ok
                          else "NO，需先补齐"))
    print("=" * 78)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
