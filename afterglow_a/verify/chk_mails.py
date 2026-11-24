# -*- coding: utf-8 -*-
"""检查两封函的结构完整性：围栏配对、章节齐全、无残留问题。"""
import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

FILES = {
    "睫": os.path.join(ROOT, "correspondence", "给睫_AfterGlow第一阶段设计审查请求_Coder_20261123.md"),
    "知微": os.path.join(ROOT, "correspondence", "给知微_AfterGlow第一阶段设计审查请求_Coder_20261123.md"),
}

FENCE = "`" * 3
ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1; print("  [OK]", m)
    else: bad += 1; print("  [XX]", m)

for name, p in FILES.items():
    b = open(p, "rb").read()
    s = b.decode("utf-8")
    print("=" * 70)
    print("%s 函 : %d B, \\r\\r\\n=%d" % (name, len(b), b.count(b"\r\r\n")))
    print("=" * 70)

    n = s.count(FENCE)
    chk(n % 2 == 0, "代码围栏配对（%d 个，%s）" % (n, "偶数" if n % 2 == 0 else "奇数！"))
    chk(b.count(b"\r\r\n") == 0, "无 \\r\\r\\n 损坏")
    chk("ab53fca" in s, "固定点为 ab53fca")
    chk("88b819e" not in s, "无旧固定点 88b819e")
    chk("_harden_stdio" in s, "含加固具体说明")

    # 章节
    for sec in ["一 · 审查对象", "二 · 职责原话", "判断标准"]:
        chk(sec in s, "含章节: " + sec)

    # 越界词
    for w in ["请你直接打", "自我怀疑", "我不确定", "求谅解"]:
        chk(w not in s, "无「%s」" % w)

    # 单行表格连续性（表格行之间不能有非表格行）
    lines = s.split("\n")
    in_tbl = False
    tbl_broken = []
    for i, ln in enumerate(lines):
        is_row = ln.strip().startswith("|")
        if is_row and not in_tbl:
            in_tbl = True
        elif not is_row and in_tbl:
            if ln.strip() == "":
                in_tbl = False
            else:
                tbl_broken.append((i + 1, ln[:50]))
                in_tbl = False
    chk(not tbl_broken, "表格无断裂行" +
        ("" if not tbl_broken else " → %s" % tbl_broken[:2]))

    print()

print("核验：OK %d，问题 %d" % (ok, bad))
sys.exit(0 if bad == 0 else 1)
