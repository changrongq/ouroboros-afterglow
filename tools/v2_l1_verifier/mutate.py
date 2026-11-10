# -*- coding: utf-8 -*-
"""变异测试：故意破坏解析器，确认测试会失败。

凌翼与钳星反复强调：
  "会失败的检查，最怕的不是失败，是没响。"

做法：对 l1_parser.py 源码做字符串替换生成变异副本，
      用同一套预期跑一遍。
      若变异后仍全通过 => 测试恒真、无效。
"""
import sys, os, shutil, tempfile, subprocess
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "l1_parser.py"), "rb").read().decode("utf-8")

MUTATIONS = [
    # 2026-11-10：原「放宽 V1_TYPES」变异无效——v1 分支硬编码 otype>=0x80，
    # 不读 V1_TYPES。改为直接改硬编码判定。
    ("放宽 v1 N3：高位类型不再拒绝",
     "if otype >= 0x80:",
     "if False:"),
    ("v2 保留类型 0x80 被误放行",
     "if otype in RESERVED_TYPES:",
     "if False:"),
    ("N5 白名单误含保留 TAG 0x8B",
     "0x86: [0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8C],",
     "0x86: [0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8B, 0x8C],"),
    ("取消 TOTAL_LEN 校验", "if total_len != L:", "if False:"),
    ("取消 FIELD_COUNT 校验", "if fcnt != len(fields):", "if False:"),
    # 2026-11-10：MAGIC 在文件中有 2 处（分派器 + 专用入口），
    # 必须全部替换才能模拟「取消 MAGIC 校验」
    ("取消 MAGIC 校验（两处全改）", "if raw[:8] != MAGIC:", "if False:"),
    ("取消 RESERVED 校验", "if reserved != 0x00:", "if False:"),
    ("取消专用入口版本自检", "if fv != expected:", "if False:"),
    ("取消字段 TAG 顺序校验", "if got_tags != TAGS[otype]:", "if False:"),
    ("取消规定字段数校验", "if len(fields) != spec:", "if False:"),
    ("v2 白名单加入 v1 引用类型", "if otype in (0x01, 0x02, 0x03):", "if False:"),
]


def run_with(parser_path):
    tmp = tempfile.mkdtemp(prefix="mut_")
    for f in ["expected.py", "vec6.py", "run_a16.py"]:
        shutil.copy(os.path.join(HERE, f), tmp)
    shutil.copy(parser_path, os.path.join(tmp, "l1_parser.py"))
    r = subprocess.run([sys.executable, "run_a16.py"],
                       capture_output=True, text=True, encoding="utf-8",
                       cwd=tmp, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    shutil.rmtree(tmp, ignore_errors=True)
    for line in r.stdout.split("\n"):
        if "合计" in line:
            t = line.split()
            try:
                return int(t[t.index("通过") + 1]), int(t[t.index("失败") + 1])
            except Exception:
                pass
    return None, r.stdout[-300:]


print("=== 基线（未变异）===")
bp, bf = run_with(os.path.join(HERE, "l1_parser.py"))
print(f"  通过 {bp}  失败 {bf}")

print("\n=== 变异 ===")
caught_all = True
mut_file = os.path.join(tempfile.gettempdir(), "_mut_l1_parser.py")
for desc, old, new in MUTATIONS:
    if old not in SRC:
        print(f"  ⚠ 锚点未找到: {desc}")
        caught_all = False
        continue
    open(mut_file, "wb").write(SRC.replace(old, new).encode("utf-8"))
    p, f = run_with(mut_file)
    if not isinstance(f, int):
        print(f"  ✅ 被捕获(运行异常) {desc}")
        continue
    if f > 0:
        print(f"  ✅ 被捕获 {desc}: 通过 {p} 失败 {f}")
    else:
        print(f"  ❌ 未捕获! {desc}: 通过 {p} 失败 {f}")
        caught_all = False

print("\n=== 结论 ===")
print(f"  全部变异均被捕获: {caught_all}")
print("  ⇒ " + ("测试有效：破坏解析器会让它失败。" if caught_all
                 else "存在未捕获的变异，测试有盲区（须补用例或修解析器）。"))
