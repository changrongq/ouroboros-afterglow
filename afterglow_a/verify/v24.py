# -*- coding: utf-8 -*-
"""知微审查落盘 + 四项修复的最终核验。"""
import sys, os, re, json, hashlib, glob
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1; print("  [OK]", m)
    else: bad += 1; print("  [XX]", m)

RD = os.path.join(ROOT, "discussions", "r2")
P24 = os.path.join(RD, "24_MEMCAND-R2_知微_第一阶段设计独立审查_REVISE_20261123.md")
T24 = open(P24, encoding="utf-8").read()
SRC = open(os.path.join(ROOT, "correspondence",
                        "给Coder_AfterGlow第一阶段设计独立审查_知微_20261123.md"),
           encoding="utf-8").read()
B = open(os.path.join(ROOT, "afterglow_design/B_hybrid_memory_candidates.md"), encoding="utf-8").read()
C = open(os.path.join(ROOT, "afterglow_design/C_decision_ledger.md"), encoding="utf-8").read()
A = open(os.path.join(ROOT, "afterglow_design/A_minimum_recovery_design.md"), encoding="utf-8").read()
R = open(os.path.join(RD, "README.md"), encoding="utf-8").read()

print("=== 1. 24 号保真 ===")
chk(SRC in T24, "原文 28843 B 逐字节包含")
b24 = open(P24, "rb").read()
chk(b24.count(b"\r\n") == 0, "纯 LF（与原文一致）")
chk("落盘说明块" in T24, "有说明块")
chk(hashlib.sha256(SRC.encode()).hexdigest()[:12] in T24, "头部含原文 sha256")
chk("REVISE" in T24, "含结论标签")

print("\n=== 2. 四项修复的代码事实 ===")
AF = open(os.path.join(ROOT, "afterglow_a/prototype/afcore.py"), encoding="utf-8").read()
chk("owned = Record(**copy.deepcopy(_body))" in AF, "ZA-01 insert 深拷贝")
chk("self._live[record_id] = Record(**copy.deepcopy(_body))" in AF, "ZA-01 revise 深拷贝")
chk("_REVISABLE" in AF and "illegal = set(changes) - self._REVISABLE" in AF,
    "ZA-02 字段白名单")
chk("但 source_ref 为空" in AF, "ZA-03 validate 拦空 ref")
chk("纠正依据不存在" in AF, "ZA-03 correct 拦悬空依据")
MT = open(os.path.join(ROOT, "afterglow_a/prototype/test_mutations_v4.py"), encoding="utf-8").read()
chk("NOT_EXECUTED" in MT, "ZA-04 新增 NOT_EXECUTED 分类")
chk('c["MISSED"] + c["INVALID"] + c["NOT_EXECUTED"]' in MT, "ZA-04 计入失败")

print("\n=== 3. B §4.3 已更正 ===")
chk("已撤回，保留可追溯" in B, "第一版标已撤回")
chk("不加载模型" in B, "引 amend 声明")
chk("U 是测量读出" in B, "更正 β 建议")
chk("撤回】" in B, "明确撤回")

print("\n=== 4. 台账与 README ===")
chk("一之零之三" in C, "台账有第三位审查结果")
chk("ZA-01" in C and "ZA-04" in C, "台账记四项")
chk("ZB-01" in C and "ZB-03" in C, "台账记三项待改")
chk("| **24** | **知微** |" in R, "README 索引含 24")
chk("   24 知微        LF" in R, "行尾表含 24")
chk("份 + 本 README" in R, "计数表述存在")

print("\n=== 5. 测试结果（读 JSON，不猜）===")
d = json.load(open(os.path.join(ROOT, "afterglow_a/prototype/reports/p1_p5_result.json"),
                   encoding="utf-8"))
np_ = sum(1 for x in d if x["pass"])
chk(np_ == len(d) == 17, "P1-P5 %d/%d（含 3 条 ZA）" % (np_, len(d)))
m = json.load(open(os.path.join(ROOT, "afterglow_a/prototype/reports/mutation_result.json"),
                   encoding="utf-8"))
chk(m["verdict"] == "PASS", "变异 VERDICT PASS")
chk(m["counts"]["MISSED"] == 0 and m["counts"]["INVALID"] == 0
    and m["counts"]["NOT_EXECUTED"] == 0,
    "变异 0 漏 0 无效 0 未执行（%s）" % m["counts"])

zh = json.load(open(os.path.join(ROOT, "afterglow_a/evidence/zh_hui_counterexamples.json"),
                    encoding="utf-8"))
nfix = sum(1 for r in zh["results"] if r["status"] == "FIXED")
chk(nfix == 4, "复现脚本显示 4/4 FIXED")
chk(any(r["status"] == "MY_READING_WAS_WRONG" for r in zh["results"]),
    "记录了我的读法错误")

print("\n=== 6. r2 文件数 ===")
n = len(glob.glob(os.path.join(RD, "*.md")))
chk(n >= 27, "r2 共 %d 个（应 ≥27）" % n)

print("\n核验：OK %d，问题 %d" % (ok, bad))
sys.exit(0 if bad == 0 else 1)
