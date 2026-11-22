# -*- coding: utf-8 -*-
"""固定 source_role 现状证据（供设计文档引用，可复算）。"""
import sys, os, json, hashlib, subprocess
sys.stdout.reconfigure(encoding="utf-8")
SRC = r"d:\qcr\EntropyDrivenAI"
ROOT = r"d:\qcr\ouroboros-afterglow"

print("=" * 72)
print("FACT-1  medium_term_memories.json 逐条来源")
print("=" * 72)
p = os.path.join(SRC, "medium_term_memories.json")
raw = open(p, "rb").read()
print("bytes=%d  sha256=%s" % (len(raw), hashlib.sha256(raw).hexdigest()))
d = json.loads(raw.decode("utf-8"))
items = d if isinstance(d, list) else d.get("memories", [])
print("条目数:", len(items))
combos = {}
for it in items:
    k = (it.get("source"), it.get("source_role"))
    combos[k] = combos.get(k, 0) + 1
print("(source, source_role) 组合:", combos)

print()
print("=" * 72)
print("FACT-2  候选池条目缺字段")
print("=" * 72)
p2 = os.path.join(SRC, "temp_candidate_fact_memories.json")
raw2 = open(p2, "rb").read()
print("bytes=%d  sha256=%s" % (len(raw2), hashlib.sha256(raw2).hexdigest()))
d2 = json.loads(raw2.decode("utf-8"))
i2 = d2 if isinstance(d2, list) else d2.get("memories", [])
print("条目数:", len(i2))
for it in i2:
    print("  有 source_role?", "source_role" in it)
    print("  source =", repr(it.get("source")))
    print("  content =", repr(it.get("content", ""))[:70])

print()
print("=" * 72)
print("FACT-3  代码缺省值")
print("=" * 72)
ms = os.path.join(SRC, "M3_reflection_executor", "MemorySystem.py")
txt = open(ms, encoding="utf-8", newline="").read()
print("MemorySystem.py bytes=%d" % len(txt.encode()))
n = 0
for i, line in enumerate(txt.splitlines(), 1):
    if "source_role" in line:
        n += 1
        print("  L%d: %s" % (i, line.strip()))
print("source_role 出现次数:", n)
print("其中带 'user' 缺省值的行:",
      sum(1 for l in txt.splitlines() if "source_role" in l and "'user'" in l))
