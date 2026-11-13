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
#   原实现只检查 `total >= 30` 与 `len(results) == total`，
#   于是过滤掉 6 个必需用例后 total=38 仍 >= 30，照报「基线健康」。
#   ⇒ 改为与【独立登记的必需用例 ID】逐一比对。
#
# 【知微 ZB32-01 修正 2026-11-12】
#   这些常量原定义在本文件，而 a16_result_check.py 又从本文件导入，
#   当本文件也要调用 a16_result_check 时会循环导入。
#   ⇒ 现抽到 a16_cases.py（纯数据、无副作用），两个文件都从那里导入。
#   ⇒ 【单点定义仍然保持】：改集合只改 a16_cases.py 一处。
from a16_cases import (REQUIRED_CASE_IDS, ALLOWED_VERDICTS,
                       PENDING_VERDICT)

# 结果完整性共用校验（与独立验收器同一实现，见 a16_result_check 的三层说明）
import a16_result_check as _ARC


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

    # 3~6) 分类判定【全部】交给 _classify_from_doc 单一实现
    #   【知微 ZB33-01 修正后重构 2026-11-13】
    #     原来这段在本函数里、自检里各写一份 ⇒ 删掉一边另一边察觉不到。
    #     现在只有 _classify_from_doc 一处；本函数只负责取字节/起进程/解析。
    status, reason = _classify_from_doc(data, rc)
    if status == "INFRA_ERROR":
        return {**base, **common, "status": status, "reason": reason}
    if status == "MUTANT_KILLED":
        return {**base, **common, "status": status,
                "fail": int(reason.split("=")[-1]),
                "recount_fail": int(reason.split("=")[-1])}
    return {**base, **common, "status": status}


def _run_and_validate_baseline():
    """跑一次未变异解析器，用【第 2 层】validate() 判定基线是否健康。

    为什么要单独跑一次：
      run_fixture 返回的是【变异结论】（KILLED / SURVIVED / INFRA_ERROR），
      对基线而言"无 FAIL"正是理应如此 —— 所以不能拿它的 status 当健康判据。
      ⇒ 基线需要的是【结构完整 + 全部 PASS + 无 PENDING】，
        这正是 a16_result_check.validate() 的第 2 层。
      ⇒ 两个入口（独立验收器 / 本文件的基线门）用同一个判据，不各写一套。
    """
    import json
    tmp = tempfile.mkdtemp(prefix="mut_base_")
    try:
        _copy_fixture(tmp, os.path.join(HERE, "l1_parser.py"))
        r = subprocess.run([sys.executable, "run_a16.py", "--json"],
                           capture_output=True, text=True, encoding="utf-8",
                           cwd=tmp,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        try:
            doc = json.loads(r.stdout)
        except Exception as e:
            return False, ["基线 JSON 不可解析: %s: %s"
                           % (type(e).__name__, e)], {}
        ok, problems, info = _ARC.validate(doc)
        if r.returncode != 0 and ok:
            problems = list(problems) + [
                "基线五项均成立但 runner 退出码非零 (exit=%d)" % r.returncode]
            ok = False
        return ok, problems, info
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _classify_from_doc(doc, rc):
    """【单一实现】从 (JSON 文档, 退出码) 得出变异分类。

    【为什么必须抽出来（2026-11-13 修正）】
      我第一版把这段逻辑在 run_fixture 里写了一份，
      又在自检里【复刻了一份】。
      实测：把 run_fixture 里的 5b 约束删掉，自检依然报"四条全部符合" ——
      因为自检跑的是自己那一份。这正是「抄两份、改一边」。
      ⇒ 现在只有这一处实现；run_fixture 调它，自检也调它。
      ⇒ 改动它，两条路径同时改变，自检才可能真的察觉回退。

    返回 (status, reason)。
    """
    s = doc.get("summary") or {}
    if rc not in (EXIT_OK, EXIT_FAIL, EXIT_SKIP, EXIT_EVIDENCE):
        return "INFRA_ERROR", "未知退出码 %s" % rc
    meta = doc.get("meta") or {}
    if rc == EXIT_EVIDENCE or meta.get("evidence_ok") is not True:
        return "INFRA_ERROR", "证据身份失败 exit=%s evidence_ok=%s" % (
            rc, meta.get("evidence_ok"))
    if rc == EXIT_SKIP or (s.get("skip") or 0) > 0:
        return "INFRA_ERROR", "存在 SKIP %s 项（必需输入缺失）" % s.get("skip")

    ok_st, problems, info = _ARC.validate_structure(doc)
    if not ok_st:
        return "INFRA_ERROR", "结果结构不完整/自相矛盾: " + "; ".join(problems[:4])

    f = (info or {}).get("recomputed", {}).get("FAIL", 0)
    sk = (info or {}).get("recomputed", {}).get("SKIP", 0)

    # 【知微 ZB33-01】退出码与逐项结果一致性
    #   ⇒ 按【逐项重算值】比对，不按 summary 自报值
    #   ⇒ 不能把非零退出一概当基础设施失败：exit=1 且有真实 FAIL 仍应 KILLED
    if rc == EXIT_FAIL and f == 0:
        return "INFRA_ERROR", "exit=1 但逐项重算 FAIL=0，退出码与结果矛盾"
    if rc == EXIT_OK and (f != 0 or sk != 0):
        return "INFRA_ERROR", (
            "exit=0 但逐项重算 FAIL=%d SKIP=%d，退出码与结果矛盾" % (f, sk))

    if f > 0:
        return "MUTANT_KILLED", "fail=%d" % f
    return "MUTANT_SURVIVED", "recount FAIL=0"


def _selfcheck_classification():
    """【ZB33-01 常驻对照】调用【同一个】_classify_from_doc 验四条对照。

    ⇒ 不再复刻逻辑：直接测生产路径。
      这样若 _classify_from_doc 被改动（例如删掉退出码一致性约束），
      自检就会跟着失败 —— 而不是各自漂移。
    """
    notes = []
    ok = True

    def mk_real(n_fail):
        ids = list(REQUIRED_CASE_IDS)
        res = [{"id": cid, "verdict": ("FAIL" if i < n_fail else "PASS")}
               for i, cid in enumerate(ids)]
        return {
            "meta": {"evidence_ok": True, "evidence_detail": "self-check",
                     "evidence_path": "self-check", "unknown_vectors": []},
            "results": res,
            "summary": {"total": len(ids), "pass": len(ids) - n_fail,
                        "fail": n_fail, "skip": 0, "pending": 0,
                        "conserved": True},
        }

    cases = [
        ("exit=1 但逐项 FAIL=0", mk_real(0), EXIT_FAIL, "INFRA_ERROR"),
        ("exit=0 但逐项 FAIL>0", mk_real(1), EXIT_OK, "INFRA_ERROR"),
        ("exit=1 且 FAIL>0（正常 KILLED）", mk_real(1), EXIT_FAIL, "MUTANT_KILLED"),
        ("exit=0 且 FAIL=0（正常 SURVIVED）", mk_real(0), EXIT_OK, "MUTANT_SURVIVED"),
    ]
    for name, doc, rc, want in cases:
        got, _why = _classify_from_doc(doc, rc)
        good = got == want
        if not good:
            ok = False
            notes.append("%s：得到 %s，期望 %s" % (name, got, want))
        else:
            notes.append("%s → %s" % (name, got))
    return ok, notes


def main():
    print("=== 分类判据自检（ZB33-01 常驻对照）===")
    sc_ok, sc_notes = _selfcheck_classification()
    for n in sc_notes:
        print("  " + ("✅ " if sc_ok else "   ") + n)
    if not sc_ok:
        print("\n[结论] INFRA_ERROR：变异分类判据自检失败，结果不可解释。")
        print("  ⇒ 退出码 3")
        return 3
    print("  ✅ 四条对照全部符合")

    print("\n=== 基线门禁（未变异的解析器必须完整通过）===")
    b = run_fixture(os.path.join(HERE, "l1_parser.py"))
    print(f"  status={b['status']} exit={b['exit']} "
          f"pass={b['pass']} fail={b['fail']} skip={b['skip']} "
          f"evidence_ok={b['evidence_ok']} total={b['total']}")

    # 【知微 ZB32-01】基线判定必须用【第 2 层】= 结构完整 + 全部 PASS。
    #   ⇒ run_fixture 现在返回的是【变异结论】：
    #       MUTANT_SURVIVED 表示"逐项无 FAIL"，这对**基线**恰是正确结果；
    #       若直接要求 status == "OK" 会把健康基线判成失败。
    #   ⇒ 所以基线不靠 run_fixture 的 status，而是重新读一次 JSON 用 validate()。
    #     两个入口共用同一个第 2 层判据，避免"基线自己写一套"。
    ok_base, base_problems, base_info = _run_and_validate_baseline()
    if not ok_base:
        print("  ❌ 基线未通过：")
        for p in base_problems[:6]:
            print("     -", p)
        print("\n[结论] INFRA_ERROR：基线不健康，变异结果不可解释。")
        print("  ⇒ 不进入变异阶段，退出码 3")
        return 3
    print(f"  ✅ 基线健康 pass={base_info['recomputed']['PASS']}")

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
        # 【知微 ZB32-01】run_fixture 现在直接给出三类结论：
        #   MUTANT_KILLED  —— 结构完整 且【逐项重算】FAIL>0
        #   MUTANT_SURVIVED—— 结构完整 且 逐项重算 FAIL=0
        #   INFRA_ERROR    —— 基础设施失败 或【结构矛盾】
        #   ⇒ main 只做分派，不再自己用 m["fail"]>0 重新判一次
        #     （那正是旧逻辑把矛盾证据当 KILLED 的地方）。
        if m["status"] == "MUTANT_KILLED":
            rows.append((desc, "MUTANT_KILLED",
                         f"fail={m.get('recount_fail', m.get('fail'))}"))
            killed += 1
        elif m["status"] == "MUTANT_SURVIVED":
            rows.append((desc, "MUTANT_SURVIVED",
                         f"pass={m['pass']} fail=0"))
            survived += 1
        else:
            rows.append((desc, "INFRA_ERROR", (m["reason"] or "")[:90]))
            infra += 1

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
