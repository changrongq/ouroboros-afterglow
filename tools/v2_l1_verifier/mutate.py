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


# 允许的子进程退出码（与 run_a16.py 的四档一致）
EXIT_OK, EXIT_FAIL, EXIT_SKIP, EXIT_EVIDENCE = 0, 1, 2, 3

# 【知微 ZBR-02 修正 2026-11-11】
#   原实现只检查 `total >= 30` 与 `len(results) == total`。
#   ⇒ 过滤掉本轮新补的 6 个必需用例后 total=38，仍 >= 30，
#     于是 mutate 照报「基线健康」「12 KILLED」，exit 0。
#   ⇒ 实测确认：这是真的（见下方 REQUIRED_CASE_IDS 的来历）。
#
#   现在改为：与一组【独立登记的必需用例 ID】逐一比对。
#   ⇒ 不采用「把 30 改成 44」的做法：重复一项顶替缺失一项时，
#     数量仍相等，照样漏。
#   ⇒ 必需集合单独列在这里，不从 run_a16 的用例表反推——
#     否则「用例表被删」和「必需集合被删」会一起消失，检查又白做。
REQUIRED_CASE_IDS = (
    # --- 向量类（来自 B_24 固定证据）---
    "TV2-01", "TV2-02", "TV2-05", "TV2-06", "TV2-07", "TV2-N5", "TV2-OTHER",
    "NEG-01", "NEG-02", "NEG-03", "NEG-04", "NEG-05", "NEG-06",
    "NEG-07", "NEG-08", "NEG-09", "NEG-10",
    "NEG-11", "X2", "X2b",
    # --- 构造类（结构/长度/字段数）---
    "C-TRUNC-SHORT", "C-TRUNC-FIELD", "C-TRAILING", "C-EMPTY-FIELDS",
    "C-DUP-RULE", "C-FCNT-MISMATCH", "C-MAGIC-ONLY", "C-V2-TYPE01",
    "C-WIDTH-EPOCH", "C-DOMAIN-GRANTKIND", "C-NESTED-TLEN",
    # --- 第三轮 6 项值/长度/最小值反例（知微 上一轮原始反例，必须常驻）---
    "C-NESTED-TYPE", "C-LEN-EVENTID", "C-LEN-OBSERVED",
    "C-MIN-EPOCH", "C-MIN-SEQ", "C-MIN-RECEIPTSEQ",
    # --- 合法正例（防误伤）---
    "TV2-81", "TV2-82", "TV2-83", "TV2-84", "TV2-85", "TV2-87",
    "V1-ATTEMPT-REF-OK",
)

# 允许的判定取值（第四类 OBSERVED_PENDING_RULING 必须显式保留）
ALLOWED_VERDICTS = ("PASS", "FAIL", "SKIP", "OBSERVED_PENDING_RULING")


def run_fixture(parser_path):
    """在隔离目录跑 run_a16.py，返回 dict。

    【ZRV-01 修正 2026-11-11】
      原实现只把"不在 0/1/2/3 内"的退出码当 INFRA_ERROR，
      且只要 JSON 能读就返回 OK —— 【不采纳 exit 3，也不读 evidence_ok】。
      于是"证据身份失败"在变异工具这一层被吞掉，仍报"基线健康"。

      现改为：退出码 + meta.evidence_ok + summary + 用例覆盖【四项都须成立】。
    """
    import json
    base = {"status": None, "reason": "", "exit": None,
            "pass": None, "fail": None, "skip": None,
            "evidence_ok": None, "total": None, "raw": ""}

    tmp = tempfile.mkdtemp(prefix="mut_")
    try:
        _copy_fixture(tmp, parser_path)
        r = subprocess.run([sys.executable, "run_a16.py", "--json"],
                           capture_output=True, text=True, encoding="utf-8",
                           cwd=tmp, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        rc, out, err = r.returncode, r.stdout, r.stderr
    except Exception as e:
        return {**base, "status": "INFRA_ERROR",
                "reason": f"{type(e).__name__}: {e}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 1) 退出码必须在已知四档内
    if rc not in (EXIT_OK, EXIT_FAIL, EXIT_SKIP, EXIT_EVIDENCE):
        return {**base, "status": "INFRA_ERROR", "exit": rc,
                "reason": f"未知退出码 {rc}", "raw": (out + err)[-400:]}

    # 2) JSON 必须可解析且结构完整
    try:
        data = json.loads(out)
        s, meta, results = data["summary"], data["meta"], data["results"]
        p_, f_, s_, t_ = s["pass"], s["fail"], s["skip"], s["total"]
        ev_ok = meta["evidence_ok"]
    except Exception as e:
        return {**base, "status": "INFRA_ERROR", "exit": rc,
                "reason": f"JSON 结构不完整: {type(e).__name__}: {e}",
                "raw": out[-400:]}

    common = {"exit": rc, "pass": p_, "fail": f_, "skip": s_,
              "evidence_ok": ev_ok, "total": t_}

    # 3) 证据身份失败必须先判 INFRA_ERROR，不能被 fail>0 掩盖成"变异被检出"
    if rc == EXIT_EVIDENCE or ev_ok is not True:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": f"证据身份失败 exit={rc} evidence_ok={ev_ok}"}

    # 4) SKIP 不得算 OK
    if rc == EXIT_SKIP or (s_ or 0) > 0:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": f"存在 SKIP {s_} 项（必需输入缺失）"}

    # 5) 用例覆盖完整性 —— 按【已登记的必需 ID 集合】校验，不按数量
    if not isinstance(t_, int) or len(results) != t_:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": f"summary.total={t_} 与 len(results)={len(results)} 不符"}

    got_ids = []
    bad_verdicts = []
    for r_ in results:
        cid = r_.get("id")
        v = r_.get("verdict")
        if cid is None:
            return {**base, **common, "status": "INFRA_ERROR",
                    "reason": "存在缺少 id 的结果项"}
        got_ids.append(cid)
        if v not in ALLOWED_VERDICTS:
            bad_verdicts.append("%s=%s" % (cid, v))

    if bad_verdicts:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": "出现未登记判定值: " + ", ".join(bad_verdicts[:6])}

    dup = sorted({i for i in got_ids if got_ids.count(i) > 1})
    if dup:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": "用例 ID 重复: " + ", ".join(dup[:6])}

    got_set = set(got_ids)
    need_set = set(REQUIRED_CASE_IDS)
    missing_ids = sorted(need_set - got_set)
    extra_ids = sorted(got_set - need_set)
    if missing_ids:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": "缺少已登记必需用例: " + ", ".join(missing_ids[:8])}
    if extra_ids:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": "出现未登记用例: " + ", ".join(extra_ids[:8])}

    # 6) 计数守恒：total 必须等于四类之和（含 pending）
    pend_ = s_.get("pending") if isinstance(s_, dict) else None
    if pend_ is None:
        # 兼容旧 runner 不带 pending 字段：用 results 现算，
        #   但【仍要求】它和 pass+fail+skip 凑得上，否则说明 summary 不完整。
        pend_ = sum(1 for r_ in results
                    if r_.get("verdict") == "OBSERVED_PENDING_RULING")
        common["pending"] = pend_
        common["pending_from"] = "recount"
    else:
        common["pending"] = pend_
        common["pending_from"] = "summary"

    if (p_ or 0) + (f_ or 0) + (s_ or 0) + (pend_ or 0) != t_:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": "计数不守恒 pass=%s+fail=%s+skip=%s+pending=%s != total=%s"
                          % (p_, f_, s_, pend_, t_)}

    # 7) 退出码与计数自洽
    if rc == EXIT_FAIL and (f_ or 0) == 0:
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": "exit=1 但 fail=0，不自洽"}
    if rc == EXIT_OK and ((f_ or 0) != 0 or (s_ or 0) != 0):
        return {**base, **common, "status": "INFRA_ERROR",
                "reason": f"exit=0 但 fail={f_} skip={s_}，不自洽"}

    return {**base, **common, "status": "OK"}


def main():
    print("=== 基线门禁（未变异的解析器必须完整通过）===")
    b = run_fixture(os.path.join(HERE, "l1_parser.py"))
    print(f"  status={b['status']} exit={b['exit']} "
          f"pass={b['pass']} fail={b['fail']} skip={b['skip']} "
          f"evidence_ok={b['evidence_ok']} total={b['total']}")
    # 【ZRV-01】基线必须：OK + pass>0 + fail=0 + skip=0 + 证据身份成立
    if (b["status"] != "OK" or not b["pass"] or b["fail"] != 0
            or b["skip"] != 0 or b["evidence_ok"] is not True):
        print(f"  ❌ 基线未通过: {b['reason'] or '条件不满足'}")
        if b.get("raw"):
            print(f"  原始输出: {b['raw']}")
        print("\n[结论] INFRA_ERROR：基线不健康，变异结果不可解释。")
        print("  ⇒ 不进入变异阶段，退出码 3")
        return 3
    print(f"  ✅ 基线健康 pass={b['pass']}")

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
        m = run_fixture(mut_file)
        # 【ZRV-01】先判基础设施问题，再看 fail>0
        if m["status"] != "OK":
            rows.append((desc, "INFRA_ERROR", m["reason"][:90]))
            infra += 1
        elif (m["fail"] or 0) > 0:
            rows.append((desc, "MUTANT_KILLED", f"fail={m['fail']}"))
            killed += 1
        else:
            rows.append((desc, "MUTANT_SURVIVED",
                         f"pass={m['pass']} fail=0"))
            survived += 1

    for desc, verdict, info in rows:
        icon = {"MUTANT_KILLED": "✅", "MUTANT_SURVIVED": "❌",
                "INFRA_ERROR": "⚠"}[verdict]
        print(f"  {icon} {verdict:<16} {desc}: {info}")

    total = len(MUTATIONS)
    print(f"\n=== 汇总 ===")
    print(f"  基线通过 {b['pass']}")
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
