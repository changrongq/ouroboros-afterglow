# -*- coding: utf-8 -*-
"""核验睫成文三项待办的落实情况。"""
import sys, os, re, subprocess, hashlib, glob
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
RD = os.path.join(ROOT, "discussions", "r2")
ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1; print("  [OK]", m)
    else: bad += 1; print("  [XX]", m)

print("=== 1. 25 号落盘保真 ===")
SRC = open(os.path.join(ROOT, "correspondence",
                        "给Coder_睫_AfterGlow第一阶段设计审查意见_成文原件_20261124.md"),
           encoding="utf-8").read()
P25 = os.path.join(RD, "25_MEMCAND-R2_睫_第一阶段设计审查意见_成文原件_CONDITIONAL_20261124.md")
T25 = open(P25, encoding="utf-8").read()
chk(SRC in T25, "原文 18698 B 逐字节包含")
b25 = open(P25, "rb").read()
chk(b25.count(b"\r\n") == 0, "25 号纯 LF")
chk(hashlib.sha256(SRC.encode()).hexdigest()[:12] in T25, "头部含原文 sha256")
for k in ["与 r2/20、r2/23 的「要点转录」不是同一等级", "选 C：问题不在枚举值",
          "拆列 + 一条 placebo 臂", "格一", "格二", "格三",
          "验证脚本不在树内", "不领「第几眼」"]:
    chk(k in T25, "25 号含「%s」" % k[:26])

print("\n=== 2. (c) r2/23 已标被替代 ===")
T23 = open(os.path.join(RD, "23_MEMCAND-R2_睫_第一阶段设计审查意见_CONDITIONAL_20261123.md"),
           encoding="utf-8").read()
chk("本文已被替代" in T23, "23 号有被替代标记")
chk("25_MEMCAND-R2" in T23, "23 号指向 25 号")
chk("不删除，保留作为来路记录" in T23, "说明不删")
chk("r2/20 确无逐字文本；而 r2/23 在聊天里其实有一份成文" in T23,
    "记她指出的 20/23 来路差别")

print("\n=== 3. (a) 台账分列脚本可复算性 ===")
C = open(os.path.join(ROOT, "afterglow_design/C_decision_ledger.md"), encoding="utf-8").read()
chk("一之零之四" in C, "有 §一之零之四")
chk("源码可复算（知微那格）" in C, "分列：知微那格")
chk("验证脚本可复算（睫这格）" in C, "分列：睫这格")
chk("本地验证，外部不可复算" in C, "标注本地验证")
chk("在 exp 树、main 树、11 个 PR 分支、外部仓库全树 —— 全部 0 命中" in C,
    "记录 0 命中实测")
for s in ["v_jie_all.py", "v_table.py", "chk_mails.py", "prereview.py", "verify_claims.py"]:
    chk(s in C, "表内列出 %s" % s)

print("\n=== 4. (b) 撤回那一格已归类 ===")
chk("1890 字节" in C, "记她撤回的内容")
chk("#52 元数据" in C or "同一次提交的 B 更新" in C, "记撤回理由")
chk("不改任何文件" in C, "记不改文件")

print("\n=== 5. 顺序与索引 ===")
heads = re.findall(r"^### (一之零[^\s·]*)", C, re.M)
chk(heads == ["一之零", "一之零之二", "一之零之三", "一之零之四"],
    "节序正确：%s" % heads)
R = open(os.path.join(RD, "README.md"), encoding="utf-8").read()
chk("| **25** | **睫** |" in R, "索引含 25")
chk("已被 25 号替代" in R, "23 号标被替代")
chk("   25 睫（成文）   LF" in R, "行尾表含 25")
chk("26 份 + 本 README" in R and "00–25" in R, "计数 26 份")

print("\n=== 6. r2 实际文件数 ===")
n = len(glob.glob(os.path.join(RD, "*.md")))
chk(n == 27, "r2 共 %d 个（26 份 + README）" % n)

print("\n=== 7. 功能未被影响 ===")
r = subprocess.run([sys.executable, "afterglow_a/prototype/test_p1_p5.py"],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                   errors="replace")
chk("合计 17" in (r.stdout + r.stderr), "P1-P5 仍 17 条")

print("\n核验：OK %d，问题 %d" % (ok, bad))
sys.exit(0 if bad == 0 else 1)
