# -*- coding: utf-8 -*-
"""交付前审阅检查：不是自夸，是找出「别人会第一时间问到什么」。"""
import sys, os, json, re, subprocess
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
ok = warn = fail = 0

def chk(c, m, level="fail"):
    global ok, warn, fail
    if c:
        ok += 1; print("  [OK]  " + m)
    elif level == "warn":
        warn += 1; print("  [warn] " + m)
    else:
        fail += 1; print("  [XX]  " + m)

A = open(os.path.join(ROOT, "afterglow_design/A_minimum_recovery_design.md"), encoding="utf-8").read()
B = open(os.path.join(ROOT, "afterglow_design/B_hybrid_memory_candidates.md"), encoding="utf-8").read()
C = open(os.path.join(ROOT, "afterglow_design/C_decision_ledger.md"), encoding="utf-8").read()
R = open(os.path.join(ROOT, "afterglow_design/report_to_lingyi_20261122.md"), encoding="utf-8").read()

print("=" * 72)
print("1. 审查者会第一时间问的问题")
print("=" * 72)

# 钳星：是否偷换研究对象
chk("偷换研究对象" in A or "偷换" in B, "B/A 正面回应「偷换研究对象」质疑（钳星的必问项）")
chk("不主张 AfterGlow 已经" in B or "不能说明 AfterGlow" in A, "明确否认「已记得」")

# 睫：因果可辨识性
chk("match_kind" in A, "A 有 match_kind（睫会问：区分测到与归属）")
chk("测到了" in A or "归属" in A, "A 提到「测到 vs 归属」")
chk("要点转录" in C, "C 标明 20 号是转录（睫要求过）")

# 知微：技术可行性
chk("并发" in A or "单写者" in B, "承认并发缺口（知微会问）")
chk("快照" in B, "B 提到快照")
chk("估计目标" in B, "B 提到估计目标（知微 r2/18 §5 用语）")

# Mion：伪亲历与承诺
chk("commitment_state" in B, "B 有承诺状态机")
chk("伪亲历" in B or "model_echo" in B, "B 涉及伪亲历/model_echo")
chk("forgotten" in B or "被遗忘" in C, "提到「被遗忘」这一态（我给 Mion 的问题）")

# 衔环：版本身份
chk("blob" in C, "C 用 blob 身份")
chk("7e62cac" in C, "C 用固定 commit")
chk("pinned" in C or "固定点" in C, "C 有 pin 概念")

print()
print("=" * 72)
print("2. 数字自洽性（最容易被打的短板）")
print("=" * 72)

# 台账统计是否与正文一致
stat = re.findall(r"`(RESOLVED|RESOLVED_BY_RULING|PARTIALLY_RESOLVED|PARTIALLY_IMPLEMENTED|ADDRESSED_BY_DESIGN|ANSWERED_OPEN|OPEN)`", C)
counts = {}
for s in stat:
    counts[s] = counts.get(s, 0) + 1
print("  台账正文出现状态标记:", counts)

# 声明的汇总
m = re.search(r"合计\s*(\d+)\s*项", C)
declared = int(m.group(1)) if m else -1
print("  正文声明「合计 %d 项」" % declared)

d = {}
for mm in re.finditer(r"\| `(RESOLVED|RESOLVED_BY_RULING|PARTIALLY_RESOLVED|PARTIALLY_IMPLEMENTED|ADDRESSED_BY_DESIGN|ANSWERED_OPEN|OPEN)` \|([^|]+)\| (\d+) \|", C):
    d[mm.group(1)] = int(mm.group(3))
print("  汇总表:", d)
print("  汇总表合计:", sum(d.values()) if d else 0)

chk(sum(d.values()) == declared if d else False,
    "汇总表合计 == 声明合计（%s vs %s）" % (sum(d.values()) if d else "?", declared))

# 撤回数量
mm = re.search(r"合计\s*(\d+)\s*处撤回", C)
print("  声明撤回数:", mm.group(1) if mm else "未声明")

print()
print("=" * 72)
print("3. 边界声明完整性（凌翼 §三 硬要求）")
print("=" * 72)

for name, t in (("A", A), ("B", B), ("C", C), ("REPORT", R)):
    has_all = ("REAL_CANDIDATE_SELECTED" in t or "REAL_CANDIDATE_SELECTED" in A)
    chk("Q3_FROZEN" in t, "%s 有 Q3_FROZEN" % name, "warn")
    chk("SCIENTIFIC_EXECUTION" in t or "MAY_NOT_START" in t,
        "%s 有 SCIENTIFIC_EXECUTION" % name, "warn")

chk("不得将工程原型测试冒充" in A or "engineering_only" in A
    or "is_scientific_result" in A or "工程一致性" in A,
    "A 有工程/科学分离声明")
chk("不是" in A and ("C1" in A), "A 提到 C1 边界")

print()
print("=" * 72)
print("4. 可复现性（外审会真的去跑）")
print("=" * 72)

cmds = [
    ("python afterglow_a/prototype/test_p1_p5.py", "P1-P5"),
    ("python afterglow_a/prototype/test_mutations_v4.py", "变异"),
    ("python afterglow_a/evidence/probe_source_role.py", "源侧证据"),
]
for cmd, label in cmds:
    script = cmd.split()[1].replace("/", os.sep)
    chk(os.path.exists(os.path.join(ROOT, script)), "脚本存在: %s (%s)" % (label, script))

# 是否在文档里给了可复跑命令
chk("test_p1_p5.py" in A, "A 给出可复跑命令")
chk("test_mutations_v4.py" in A or "mutation" in A, "A 提到变异测试")

# 结果文件在库
for f in ["afterglow_a/prototype/reports/p1_p5_result.json",
          "afterglow_a/prototype/reports/mutation_result.json"]:
    chk(os.path.exists(os.path.join(ROOT, f.replace("/", os.sep))), "结果入库: " + f)

print()
print("=" * 72)
print("5. 隐患扫描：文档里有没有「说了但没做」的话")
print("=" * 72)

# 检查是否声称了未实现的能力
danger = [
    (r"已经实现", "声称已实现"), (r"顺利通过", None), (r"完全解决", "声称完全解决"),
    (r"证明了记忆", "声称证明记忆"),
]
for pat, label in danger:
    for name, t in (("A", A), ("B", B), ("C", C), ("REPORT", R)):
        for m in re.finditer(pat, t):
            ctx = t[max(0, m.start()-40):m.start()+40].replace("\n", " ")
            if "不能" in ctx or "不" in ctx[max(0, len(ctx)//2-6):len(ctx)//2+3]:
                continue
            print("  [note] %s 出现「%s」: ...%s..." % (name, m.group(0), ctx[:70]))

print()
print("=" * 72)
print("6. 已知短板是否被如实写出")
print("=" * 72)
for kw, label in [("残差取自哪里", "B 最大未决点"),
                  ("并发", "并发缺口"),
                  ("持久化", "持久化缺口"),
                  ("pending_verification", "迁移规则"),
                  ("被遗忘", "承诺第七态")]:
    hit = any(kw in t for t in (A, B, C, R))
    chk(hit, "如实记录: %s" % label, "warn")

print()
print("=" * 72)
print("合计：OK %d  警告 %d  失败 %d" % (ok, warn, fail))
print("=" * 72)
sys.exit(0 if fail == 0 else 1)

