# -*- coding: utf-8 -*-
"""全面核验睫三格 + 一句话级的修复。"""
import sys, os, re, subprocess, hashlib, glob, json
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1; print("  [OK]", m)
    else: bad += 1; print("  [XX]", m)

C = open(os.path.join(ROOT, "afterglow_design/C_decision_ledger.md"), encoding="utf-8").read()
A = open(os.path.join(ROOT, "afterglow_design/A_minimum_recovery_design.md"), encoding="utf-8").read()
R = open(os.path.join(ROOT, "correspondence/README.md"), encoding="utf-8").read()
P23 = os.path.join(ROOT, "discussions/r2",
                   "23_MEMCAND-R2_睫_第一阶段设计审查意见_CONDITIONAL_20261123.md")
T23 = open(P23, encoding="utf-8").read()

print("=== 格一：表头 ===")
chk("### 引用身份表（git blob SHA-1，40 位）" in C, "表头已改")
# 只查「表头行」是否还是旧的，不把台账里叙述历史的那一行算进来
head_lines = [l for l in C.split("\n") if l.strip().startswith("### 引用身份表")]
chk(all("sha256" not in l for l in head_lines),
    "表头行不含 sha256（当前表头：%s）" % (head_lines[0].strip()[:38] if head_lines else "无"))

print("\n=== 格一实地复算 8 行 ===")
rows = re.findall(r"\|\s*`(\d{2})`[^|]*\|\s*`([0-9a-f]{40})`\s*\|", C)
mapping = {}
for p in glob.glob(os.path.join(ROOT, "discussions/r2/*.md")):
    m = re.match(r"^(\d{2})_", os.path.basename(p))
    if m: mapping[m.group(1)] = "discussions/r2/" + os.path.basename(p)
n1 = n256 = 0
for num, val in rows:
    rel = mapping.get(num)
    if not rel: continue
    r = subprocess.run(["git", "ls-files", "-s", rel], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    if not r.stdout.strip(): continue
    sha1 = r.stdout.split()[1]
    blob = subprocess.run(["git", "cat-file", "blob", sha1], cwd=ROOT,
                          capture_output=True).stdout
    if sha1 == val: n1 += 1
    if hashlib.sha256(blob).hexdigest()[:40] == val: n256 += 1
chk(len(rows) == 8, "表 8 行（%d）" % len(rows))
chk(n1 == len(rows), "全部 = SHA-1（%d/%d）" % (n1, len(rows)))
chk(n256 == 0, "无一 = sha256[:40]（%d）" % n256)

print("\n=== 格二：判定是否落进 r2/23 ===")
for k in ["不必被 match_kind 表达", "expected_ids 的登记身份", "两种答案并不并存",
          "不住在同一张表里"]:
    chk(k in T23, "r2/23 含「%s」" % k[:26])

print("\n=== 格三：A §1.8 ===")
chk("partial_overlap" in A, "含 partial_overlap")
chk("「未执行」不是一个 `match_kind` 值" in A, "not_run 移出枚举")
chk("expected_ids_registration" in A, "新增登记身份字段")
chk("registered_by" in A and "before_exposure" in A, "五个最小字段")
chk("本来就【不】表达因果归属" in A or "不住在同一张表" in A or "不是」这张表" in A,
    "边界重申")

print("\n=== 一句话级 (a)：编号 ===")
chk("r2/12` §3.2 后撤回" in C, "台账 R2-2 已改为 r2/12 §3.2")
chk(not re.search(r"r2/18`?\s*§3\.", C), "台账无 r2/18 §3.x")
chk(len(re.findall(r"r2/18`?\s*§6", C)) == 2, "r2/18 §6 保留（两处）")

print("\n=== 一句话级 (b)：r2 数量 ===")
n_r2 = len(glob.glob(os.path.join(ROOT, "discussions/r2/*.md")))
chk(n_r2 >= 27, "r2 现有 %d 个文件（应 ≥27：00-24 共 25 份 + 24/25 + README）" % n_r2)

print("\n=== 一句话级 (c)：README 入口 ===")
chk("五之二 · 本目录之外还有哪里" in R, "README 有 §五之二")
chk("afterglow_design/" in R, "提及 afterglow_design")
chk("afterglow_a/" in R, "提及 afterglow_a")
chk("discussions/" in R, "提及 discussions")

print("\n=== 23 号本身 ===")
chk("CONDITIONAL / FETCHED" in T23, "结论记录")
chk("要点转录" in T23, "标明证据等级")
chk("被替代" in T23, "说明若她成文则标被替代")
chk("选 C：问题不在枚举值" in T23, "第 ① 问答复在")
chk("拆列 + 一条 placebo 臂" in T23, "第 ② 问答复在")
b23 = open(P23, "rb").read()
chk(b23.count(b"\r\n") == 0, "23 号纯 LF")

print("\n核验：OK %d，问题 %d" % (ok, bad))
sys.exit(0 if bad == 0 else 1)

