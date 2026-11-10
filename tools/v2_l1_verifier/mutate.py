# -*- coding: utf-8 -*-
"""变异测试（ZFP-01B 修正版）

除原有"故意破坏解析器看测试会不会失败"外，本版新增三条硬约束：

1. 【基线门禁】未变异的解析器必须完整通过，否则整个变异测试
   直接判 INFRA_ERROR，不进入变异阶段。
2. 【三态分类】每个变异归为：
     MUTANT_KILLED     —— 变异体被测试检出（期望）
     MUTANT_SURVIVED   —— 变异体仍全通过（测试盲区）
     INFRA_ERROR       —— 子进程启动/解析失败等基础设施问题
   不再把"跑不起来"记成"被捕获"。
3. 【退出码】只有全部 MUTANT_KILLED 才返回 0；存在 SURVIVED 或
   INFRA_ERROR 均返回非零。

用法：
  python mutate.py
"""
import sys, os, shutil, tempfile, subprocess
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "l1_parser.py"), "rb").read().decode("utf-8")

MUTATIONS = [
    ("放宽 v1 高位类型拒绝", "if otype >= 0x80:", "if False:"),
    ("v2 保留类型 0x80 被误放行", "if otype in RESERVED_TYPES:", "if False:"),
    ("N5 白名单误含保留 TAG 0x8B",
     "0x86: [0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8C],",
     "0x86: [0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8B, 0x8C],"),
    ("取消 TOTAL_LEN 校验", "if total_len != L:", "if False:"),
    ("取消字段数一致性校验", "if fcnt != len(fields):", "if False:"),
    ("取消 MAGIC 校验", "if raw[:8] != MAGIC:", "if False:"),
    ("取消 RESERVED 校验", "if reserved != 0x00:", "if False:"),
    ("取消专用入口版本自检", "if fv != expected:", "if False:"),
    ("取消字段 TAG 顺序校验", "if got_tags != TAGS[otype]:", "if False:"),
    ("取消规定字段数校验", "if len(fields) != spec:", "if False:"),
    ("v2 白名单加入 v1 引用类型", "if otype in (0x01, 0x02, 0x03):", "if False:"),
    # 新增：取消值约束检查（ZFP-03 修正后应被检出）
    ("取消字段值约束检查", "    _check_values(otype, fields, entry)", "    pass"),
]


def _copy_fixture(dst, parser_src_path):
    for f in ["expected.py", "vec6.py", "run_a16.py"]:
        shutil.copy(os.path.join(HERE, f), dst)
    shutil.copy(parser_src_path, os.path.join(dst, "l1_parser.py"))
    # 证据目录若存在，一并复制，保证 runner 能定位 B_24
    ev = os.path.join(HERE, "evidence")
    if os.path.isdir(ev):
        shutil.copytree(ev, os.path.join(dst, "evidence"))
    else:
        # 回退：把 reports 路径下的 B24 复制到工作目录 evidence/
        name = "阶段B_24_v2规范向量与负向实例_Coder_20261110.md"
        cand = os.path.abspath(os.path.join(HERE, "..", "..", "reports", "review_history", name))
        if os.path.exists(cand):
            os.makedirs(os.path.join(dst, "evidence"))
            shutil.copy(cand, os.path.join(dst, "evidence", name))


def run_fixture(parser_path):
    """在隔离目录跑 run_a16.py，返回 (status, pass_n, fail_n, skip_n, raw)。"""
    tmp = tempfile.mkdtemp(prefix="mut_")
    try:
        _copy_fixture(tmp, parser_path)
        r = subprocess.run([sys.executable, "run_a16.py", "--json"],
                           capture_output=True, text=True, encoding="utf-8",
                           cwd=tmp, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if r.returncode not in (0, 1, 2, 3):
            return "INFRA_ERROR", None, None, None, (r.stdout + r.stderr)[-400:]
        # 解析 JSON
        import json
        try:
            data = json.loads(r.stdout)
        except Exception:
            return "INFRA_ERROR", None, None, None, r.stdout[-400:]
        s = data["summary"]
        return "OK", s["pass"], s["fail"], s["skip"], ""
    except Exception as e:
        return "INFRA_ERROR", None, None, None, f"{type(e).__name__}: {e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print("=== 基线门禁（未变异的解析器必须完整通过）===")
    st, p, f, s, raw = run_fixture(os.path.join(HERE, "l1_parser.py"))
    if st != "OK" or f != 0 or s != 0:
        print(f"  ❌ 基线未通过: status={st} pass={p} fail={f} skip={s}")
        if raw:
            print(f"  原始输出: {raw}")
        print("\n[结论] INFRA_ERROR：基线不健康，变异结果不可解释。")
        print("  ⇒ 不进入变异阶段，退出码 3")
        return 3
    print(f"  ✅ 基线 pass={p} fail={f} skip={s}")
    base_pass = p

    print("\n=== 变异 ===")
    killed = survived = infra = 0
    rows = []
    mut_file = os.path.join(tempfile.gettempdir(), "_mut_l1_parser.py")
    for desc, old, new in MUTATIONS:
        if old not in SRC:
            rows.append((desc, "INFRA_ERROR", f"锚点未找到: {old[:30]}"))
            infra += 1
            continue
        open(mut_file, "wb").write(SRC.replace(old, new).encode("utf-8"))
        st, p2, f2, s2, raw2 = run_fixture(mut_file)
        if st != "OK":
            rows.append((desc, "INFRA_ERROR", raw2[:80]))
            infra += 1
        elif f2 > 0:
            rows.append((desc, "MUTANT_KILLED", f"fail={f2}"))
            killed += 1
        else:
            rows.append((desc, "MUTANT_SURVIVED", f"pass={p2} fail=0"))
            survived += 1

    for desc, verdict, info in rows:
        icon = {"MUTANT_KILLED": "✅", "MUTANT_SURVIVED": "❌",
                "INFRA_ERROR": "⚠"}[verdict]
        print(f"  {icon} {verdict:<16} {desc}: {info}")

    total = len(MUTATIONS)
    print(f"\n=== 汇总 ===")
    print(f"  基线通过 {base_pass}")
    print(f"  变异 {total}：KILLED {killed}  SURVIVED {survived}  INFRA_ERROR {infra}")
    ok = (killed == total and survived == 0 and infra == 0)
    print(f"  全部 KILLED: {ok}")

    if infra > 0:
        print("\n[exit 3] 存在 INFRA_ERROR，结果不可解释")
        return 3
    if survived > 0:
        print("\n[exit 2] 存在 MUTANT_SURVIVED（测试盲区）")
        return 2
    print("\n[exit 0] 全部变异被检出，且基线健康")
    return 0


if __name__ == "__main__":
    sys.exit(main())
