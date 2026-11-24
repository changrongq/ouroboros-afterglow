# -*- coding: utf-8 -*-
"""
变异验证：门禁测试能不能被真的打破？

目的：证明 test_recovery_gate.py 的 10 条不是「怎么写都过」。
做法：把实现里每一处关键判断逐个破坏（mutate），
      确认【对应测试真的会失败】。

判据：
  CAUGHT      破坏后至少一条测试失败 —— 测试确实在守这件事
  MISSED      破坏后全部通过 —— 测试没守住（必须修测试）
  NOT_EXECUTED 破坏后测试根本没跑到 —— 假绿，最危险

运行：python afterglow_a/prototype/test_mutations_gate.py
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO_FILES = ("afcore.py", "afrecover.py")
# 变异验证必须跑【全部】守护测试。
# 之前只列了 test_recovery_gate / test_p1_p5，导致 Z61 新门禁的变异
# 全部 MISSED —— 不是门禁没守住，是守护它的测试没被跑。
TEST_FILES = ("test_recovery_gate.py", "test_p1_p5.py", "test_z61_gaps.py",
              "test_observed_channel.py")


def _harden_stdio():
    for name in ("stdout", "stderr"):
        st = getattr(sys, name, None)
        if st is None:
            continue
        try:
            st.reconfigure(encoding="utf-8")
        except Exception:
            try:
                st.reconfigure(errors="backslashreplace")
            except Exception:
                pass


_harden_stdio()


# ---------------------------------------------------------------- 变异定义
# 每条：(id, 说明, 目标文件, 原文, 替换为)
# 原文必须精确匹配一次，否则算 INVALID（变异没生效，不算数）

MUTATIONS = [
    # ---- 门禁核心：完整性失败是否阻断资格
    (
        "M1", "把 integrity_failed 的阻断删掉（失败也不影响资格）",
        "afrecover.py",
        '    if integ["status"] == "failed":\n'
        '        reasons.append("integrity_failed")\n'
        '    elif integ["status"] != "verified":\n'
        '        reasons.append("integrity_not_checked")',
        '    pass  # MUTANT: 完整性结果不参与资格判断',
    ),
    (
        "M2", "只删 failed 分支，未检查仍阻断",
        "afrecover.py",
        '    if integ["status"] == "failed":\n'
        '        reasons.append("integrity_failed")\n'
        '    elif integ["status"] != "verified":\n'
        '        reasons.append("integrity_not_checked")',
        '    if integ["status"] != "verified":\n'
        '        reasons.append("integrity_not_checked")',
    ),
    (
        "M3", "把 not_checked 当通过（默认为通过）",
        "afrecover.py",
        '    elif integ["status"] != "verified":\n'
        '        reasons.append("integrity_not_checked")',
        '    elif False:\n        reasons.append("integrity_not_checked")',
    ),
    # ---- 快照失效
    (
        "M4", "删掉 stale_check 阻断（旧检查结果可沿用）",
        "afrecover.py",
        '    if stale:\n        reasons.append("stale_check")',
        '    if False:\n        reasons.append("stale_check")',
    ),
    # ---- 登记身份
    (
        "M5", "删掉登记独立性阻断",
        "afrecover.py",
        '    if reg["present"] and not reg["independent"]:\n'
        '        reasons.append("registration_not_independent")',
        '    if False:\n        reasons.append("registration_not_independent")',
    ),
    (
        "M6", "让 check_registration 永远判独立",
        "afrecover.py",
        '    independent = (\n'
        '        reg.get("independent_of_write") == "yes"\n'
        '        and reg.get("before_exposure") == "yes"\n'
        '        and not problems\n    )',
        '    independent = True  # MUTANT',
    ),
    # ---- 空期望集
    (
        "M7", "删掉 no_expected_ids 阻断",
        "afrecover.py",
        '    elif not detail.get("expected"):\n'
        '        # 期望集为空列表时，集合关系无意义（任何 retrieved 都会 disjoint）\n'
        '        reasons.append("no_expected_ids")',
        '    elif False:\n        reasons.append("no_expected_ids")',
    ),
    # ---- 串轴：让完整性污染 match_kind
    (
        "M8", "让完整性失败改写 match_kind（两轴串了）",
        "afrecover.py",
        '        "match_kind": kind,',
        '        "match_kind": (None if integ["status"] == "failed" else kind),',
    ),
    # ---- not_run 重回枚举
    (
        "M9", "not_run 重新进入 MATCH_KINDS",
        "afcore.py",
        'MATCH_KINDS = {"exact", "superset", "subset", "disjoint"}',
        'MATCH_KINDS = {"exact", "superset", "subset", "disjoint", "not_run"}',
    ),
    (
        "M10", "未执行时返回字符串 not_run",
        "afrecover.py",
        '    if not ran or expected is None:\n'
        '        return None, {',
        '    if not ran or expected is None:\n'
        '        return "not_run", {',
    ),
    # ---- content_digest
    (
        "M11", "内容摘要缺字段时按缺省填充而不是报错",
        "afcore.py",
        '    missing = [k for k in CONTENT_DIGEST_FIELDS if k not in record]\n'
        '    if missing:\n'
        '        raise SchemaError(',
        '    missing = []\n'
        '    if missing:\n'
        '        raise SchemaError(',
    ),
    (
        "M12", "让 changed_at 混进内容摘要投影",
        "afcore.py",
        '    "relation",       # relation 是内容的一部分（指向谁、为何指向）\n)',
        '    "relation",       # relation 是内容的一部分（指向谁、为何指向）\n'
        '    "changed_at",\n)',
    ),
    # ---- 外部锚定
    (
        "M13", "声称外部锚定已建立",
        "afrecover.py",
        '        "trusted_chain_anchor": "not_established",',
        '        "trusted_chain_anchor": "established",',
    ),
    (
        "M14", "把工程结果标成科学结果",
        "afrecover.py",
        '        "is_scientific_result": False,',
        '        "is_scientific_result": True,',
    ),
    # ---- snapshot_token
    (
        "M15", "snapshot_token 忽略 live 侧",
        "afcore.py",
        '        for rid in sorted(self._live):\n'
        '            cur = self._live[rid]\n'
        '            parts.append([rid + "\\x00live",\n'
        '                          json.dumps(cur.to_dict(), sort_keys=True,\n'
        '                                     ensure_ascii=False,\n'
        '                                     separators=(",", ":"))])',
        '        pass  # MUTANT: 不纳入 live 侧',
    ),
    # Z61-02（知微 2026-11-24 §4）：快照必须覆盖历史实际内容
    (
        "M15b", "snapshot_token 只取历史条数不看内容（Z61-02 原缺陷形态）",
        "afcore.py",
        '            ver_parts = []\n'
        '            for d in hist:\n'
        '                ver_parts.append(json.dumps(\n'
        '                    d, sort_keys=True, ensure_ascii=False,\n'
        '                    separators=(",", ":")))\n'
        '            parts.append([rid, ver_parts])',
        '            parts.append([rid, len(hist)])  # MUTANT: 只看条数',
    ),
    # Z61-01（知微 2026-11-24 §3）：默认必须比较本次检查的快照
    (
        "M17", "G6 只在外部传 expected_snapshot 时生效（Z61-01 原缺陷形态）",
        "afrecover.py",
        '        if checked_tok is not None and now_tok != checked_tok:',
        '        if False and checked_tok is not None and now_tok != checked_tok:',
    ),
    # Z61-04（知微 2026-11-24 §6）：failed 不得被 stale 覆盖
    (
        "M18", "stale 时无条件改写状态（Z61-04 原缺陷形态）",
        "afrecover.py",
        '            if integ["status"] == "failed":',
        '            if False:',
    ),
    # Z61-03（知微 2026-11-24 §5）：登记身份空值必须判不合格
    (
        "M19", "不校验 registered_by/rev 的空白（Z61-03 原缺陷形态）",
        "afrecover.py",
        '        elif not v.strip():\n'
        '            problems.append("%s 为空或纯空白（须给出实际取值）" % k)',
        '        elif False:\n'
        '            problems.append("%s 为空或纯空白（须给出实际取值）" % k)',
    ),
    (
        "M20", "registered_by 非字符串类型被放行（Z61-03 变形）",
        "afrecover.py",
        '        elif not isinstance(v, str):\n'
        '            problems.append("%s 类型为 %s（须为字符串）" % (k, type(v).__name__))',
        '        elif False:\n'
        '            problems.append("%s 类型为 %s（须为字符串）" % (k, type(v).__name__))',
    ),
    # ---- 完整性检查：空范围当通过
    (
        "M16", "空检查范围当作 verified",
        "afrecover.py",
        '    ids = sorted(set(record_ids))\n'
        '    if not ids:\n'
        '        return {\n'
        '            "status": "not_checked",',
        '    ids = sorted(set(record_ids))\n'
        '    if not ids:\n'
        '        return {\n'
        '            "status": "verified",',
    ),
    # ---- Mion 2026-11-24 回复2 / 回复3 的四项改造
    (
        "M21", "conflict_summary 从返回结构删掉（Mion 第 0 项）",
        "afrecover.py",
        '        "conflict_summary": conflict,',
        '        # MUTANT: 不返回冲突摘要',
    ),
    (
        "M22", "「未观测」返回成 none 而非 observed_absent（Mion 第 0 项核心）",
        "afrecover.py",
        '        if val is None:\n'
        '            # 字段缺失 = 从未计算过 ⇒ 不得当作 none\n'
        '            buckets.setdefault("observed_absent", []).append(rid)',
        '        if val is None:\n'
        '            buckets.setdefault("none", []).append(rid)  # MUTANT',
    ),
    (
        "M23", "去掉 record_observed 的时序约束（Mion 第 2 项·批量补洞）",
        "afcore.py",
        '        if cur.revision != 1:',
        '        if False:  # MUTANT: 允许事后补观测',
    ),
    (
        "M26", "允许 Record 构造器填 observed_origin（Mion 第 1 项）",
        "afcore.py",
        '        if rec.observed_origin is not None or rec.basis_conflict is not None:',
        '        if False:  # MUTANT',
    ),
]


# ---------------------------------------------------------------- 执行

def run_tests(tmpdir):
    """在临时副本里跑两个测试文件，返回 (rc, 输出, 是否真的执行了)。"""
    outs = []
    any_executed = False
    rcs = []

    for tf in TEST_FILES:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.run(
            [sys.executable, os.path.join(tmpdir, tf)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=tmpdir, env=env, timeout=300)
        out = (p.stdout or "") + (p.stderr or "")
        outs.append("--- %s (rc=%d) ---\n%s" % (tf, p.returncode, out))
        rcs.append(p.returncode)

        # 「真的执行了」的判据：输出里出现 case 级结果行
        if re.search(r"\[(PASS|FAIL)\]", out):
            any_executed = True

    return rcs, "\n".join(outs), any_executed


def copy_proto(tmpdir):
    for f in PROTO_FILES + TEST_FILES:
        src = os.path.join(HERE, f)
        shutil.copy2(src, os.path.join(tmpdir, f))
    # 测试依赖 reports 目录
    os.makedirs(os.path.join(tmpdir, "reports"), exist_ok=True)
    # test_p1_p5.py 依赖 synthetic/ 数据夹具；缺了会让基线不绿，
    # 那时变异结果没有意义。必须一并复制。
    syn_src = os.path.join(HERE, "synthetic")
    syn_dst = os.path.join(tmpdir, "synthetic")
    if os.path.isdir(syn_src):
        shutil.copytree(syn_src, syn_dst, dirs_exist_ok=True)
        return True
    return False


def apply_mutation(tmpdir, target, old, new):
    path = os.path.join(tmpdir, target)
    src = open(path, encoding="utf-8").read()
    n = src.count(old)
    if n != 1:
        return False, "锚点出现 %d 次（应为 1）" % n
    open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
    return True, "ok"


def main():
    print("=" * 78)
    print("变异验证 · 恢复资格门禁测试是否真的会亮红灯")
    print("=" * 78)
    print()

    # ---- 基线：未变异时必须全绿
    with tempfile.TemporaryDirectory() as td:
        copy_proto(td)
        rcs, out, executed = run_tests(td)
        baseline_ok = all(rc == 0 for rc in rcs)
        print("[基线] rc=%s  executed=%s  → %s"
              % (rcs, executed, "全绿" if baseline_ok else "非全绿"))
        if not baseline_ok:
            print(out[-3000:])
            print("!! 基线不绿，变异结果无意义。先修基线。")
            return 1
    print()

    rows = []
    for mid, desc, target, old, new in MUTATIONS:
        with tempfile.TemporaryDirectory() as td:
            copy_proto(td)
            ok, note = apply_mutation(td, target, old, new)
            if not ok:
                rows.append((mid, desc, "INVALID", note))
                print("  [INVALID] %-4s %s — %s" % (mid, desc, note))
                continue

            try:
                rcs, out, executed = run_tests(td)
            except subprocess.TimeoutExpired:
                rows.append((mid, desc, "TIMEOUT", "测试超时"))
                print("  [TIMEOUT] %-4s %s" % (mid, desc))
                continue

            if not executed:
                status = "NOT_EXECUTED"
                evid = "没有任何 case 级结果行（测试没跑到）"
            elif any(rc != 0 for rc in rcs):
                status = "CAUGHT"
                fails = re.findall(r"\[FAIL\]\s+(\S+)\s+([^\n]*)", out)
                if fails:
                    evid = "失败用例：%s" % (
                        "; ".join("%s %s" % (a, b.strip()[:32])
                                  for a, b in fails[:3]),)
                elif re.search(r"ERR ", out):
                    evid = "测试崩溃（也算被抓住）"
                else:
                    evid = "rc=%s 非零" % (rcs,)
            else:
                status = "MISSED"
                evid = "全部通过 —— 该变异没被任何测试拦住"

            rows.append((mid, desc, status, evid))
            print("  [%-12s] %-4s %s" % (status, mid, desc))
            if status != "CAUGHT":
                print("              %s" % evid)

    print()
    print("=" * 78)
    counts = {}
    for _, _, st, _ in rows:
        counts[st] = counts.get(st, 0) + 1
    for st in ("CAUGHT", "MISSED", "INVALID", "NOT_EXECUTED", "TIMEOUT"):
        if st in counts:
            print("  %-13s %d" % (st, counts[st]))
    print("=" * 78)

    bad = counts.get("MISSED", 0) + counts.get("INVALID", 0) + \
        counts.get("NOT_EXECUTED", 0) + counts.get("TIMEOUT", 0)
    verdict = "PASS" if bad == 0 else "FAIL"
    print("  判定：%s（共 %d 个变异）" % (verdict, len(rows)))

    out_dir = os.path.join(HERE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "mutations_gate_result.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump({"verdict": verdict, "counts": counts,
                   "rows": [{"id": a, "desc": b, "status": c, "evidence": d}
                            for a, b, c, d in rows]},
                  f, ensure_ascii=False, indent=2)
    print("  结果已写入 reports/mutations_gate_result.json")

    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
