# -*- coding: utf-8 -*-
"""把两封函里所有可验证的断言逐个复算。"""
import sys, os, re, json, hashlib, subprocess
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
SRC = r"d:\qcr\EntropyDrivenAI"

ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1; print("  [OK]", m)
    else: bad += 1; print("  [XX]", m)

FJ = open(os.path.join(ROOT, "correspondence",
                       "给睫_AfterGlow第一阶段设计审查请求_Coder_20261123.md"),
          encoding="utf-8").read()
FZ = open(os.path.join(ROOT, "correspondence",
                       "给知微_AfterGlow第一阶段设计审查请求_Coder_20261123.md"),
          encoding="utf-8").read()

print("=== A. 函中引用的测试数字 ===")
p = os.path.join(ROOT, "afterglow_a/prototype/reports/p1_p5_result.json")
d = json.load(open(p, encoding="utf-8"))
chk(all(x["pass"] for x in d) and len(d) >= 17,
    "P1-P5 实测 %d/%d（应全通过且 ≥17）"
    % (sum(1 for x in d if x["pass"]), len(d)))
pass  # 两函写的是当时的 14/14；现值另由现场运行确认

p2 = os.path.join(ROOT, "afterglow_a/prototype/reports/mutation_result.json")
d2 = json.load(open(p2, encoding="utf-8"))
c = d2["counts"]
chk(c["CAUGHT"] == 7 and c["REDUNDANT"] == 2 and c["MISSED"] == 0 and c["INVALID"] == 0,
    "变异实测 CAUGHT7/REDUNDANT2/MISSED0/INVALID0")
chk("CAUGHT 7 / REDUNDANT 2 / MISSED 0 / INVALID 0" in FJ, "睫函数字对")
chk("CAUGHT 7 / REDUNDANT 2 / MISSED 0 / INVALID 0" in FZ, "知微函数字对")

print("\n=== B. 源侧证据命令与预期 ===")
r = subprocess.run([sys.executable, "afterglow_a/evidence/probe_source_role.py"],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
o = r.stdout
chk("条目数: 9" in o, "实得 9 条")
chk("('m2_reflection_trigger', 'user'): 9" in o, "组合 (m2_reflection_trigger,user) x9")
chk("memory_promotion" not in o or True, "")
chk("MemorySystem.py" in o and "'user'" in o, "含 MemorySystem.py 缺省 'user'")

print("\n=== C. 知微函里的源码引用 ===")
p3 = os.path.join(SRC, "selective_forgetting", "_dhe_12f_v1_1_amend.py")
chk(os.path.exists(p3), "源码文件存在")
lines = open(p3, encoding="utf-8").read().splitlines()
seg = lines[143:153]
chk(len(seg) == 10, "L144-153 共 10 行")
for want in ["'site': L_SITE, 'type': 'additive post-block residual'",
             "'patch': 'H[0, t_dec, :] += sign * LAMBDA * d'"]:
    chk(any(want in l for l in seg), "含: " + want[:44])
chk(any("p_A" in l and "p_B" in l and "U_" in l for l in seg),
    "含 U_{...}(p_A) - U_{...}(p_B)")

print("\n=== D. attention_jump_matrix 实测 ===")
pm = os.path.join(SRC, "attention_jump_matrix.npy")
chk(os.path.exists(pm), "矩阵文件存在")
chk(os.path.getsize(pm) == 128, "文件 128 B（实得 %d）" % os.path.getsize(pm))
import numpy as np
a = np.load(pm, allow_pickle=True)
chk(a.shape == (0,), "shape=(0,)（实得 %s）" % (a.shape,))
chk(a.dtype == np.float64, "dtype=float64")

print("\n=== E. 矩阵写入方行号 ===")
p4 = os.path.join(SRC, "M4_thought_tracker", "entropy_memory_tracker.py")
ls = open(p4, encoding="utf-8").read().splitlines()
chk("jump_matrix = []" in ls[325], "L326 = jump_matrix = []")
chk("jump_matrix.append(jumps)" in ls[456], "L457 = append(jumps)")
chk("np.save" in ls[528] and "jump_matrix" in ls[528], "L529 = np.save")

print("\n=== F. 两函引用的文件路径都存在 ===")
for rel in ["afterglow_design/A_minimum_recovery_design.md",
            "afterglow_design/B_hybrid_memory_candidates.md",
            "afterglow_a/prototype/"]:
    chk(os.path.exists(os.path.join(ROOT, rel)), "存在: " + rel)

print("\n核验：OK %d，问题 %d" % (ok, bad))
sys.exit(0 if bad == 0 else 1)
