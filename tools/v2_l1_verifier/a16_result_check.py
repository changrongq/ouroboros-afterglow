# -*- coding: utf-8 -*-
"""A16 结果的完整性校验 —— 单一实现，供两个入口共用。

存在理由（知微 ZB31-02）：
  原 check_a16_acceptance.py 判定 ALL_REQUIRED_CASES 的条件是
      npass == len(res) and len(res) > 0
  ⇒ 只证明「返回的每一条都 PASS」，
    不证明「该在的都在、没有重复、没有多出来的」。
  实测三个反例全部被误判为通过：
    ① 把三个 B1 用例改名（实际不存在），总数不变 → 仍报 PASS
    ② 用重复 X2 顶替 B1-v1-into-v2             → 仍报 PASS
    ③ summary.total 报 48 而 results 只 47 条   → 仍报守恒
  ⇒ 而 mutate.py 已经有完整的同类校验，只是没人共用。
  ⇒ 本模块把那套校验提取出来，两个入口都调它，避免「一处修好、另一处仍宽」。

设计原则：
  · 只依赖传入的 JSON 对象，不读文件、不起子进程 ⇒ 便于单独测。
  · 返回 (ok, problems, info)，problems 是【具体字符串列表】，便于定位。
  · 计数【一律由 results 重算】，不采信 summary 自报。
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 必需用例 ID 与允许判定值从 mutate.py 单点引入。
#   ⇒ 不在这里再抄一份：抄两份就会有一天只改一边。
#   ⇒ 若 mutate.py 不可导入，则明确失败，而不是静默放宽。
try:
    from mutate import REQUIRED_CASE_IDS, ALLOWED_VERDICTS
except Exception as e:  # pragma: no cover
    REQUIRED_CASE_IDS = None
    ALLOWED_VERDICTS = None
    _IMPORT_ERR = e
else:
    _IMPORT_ERR = None


def validate(doc):
    """校验 run_a16.py --json 的输出。

    返回 (ok: bool, problems: list[str], info: dict)
    """
    problems = []

    if _IMPORT_ERR is not None:
        return False, ["无法导入 mutate.REQUIRED_CASE_IDS: %r" % (_IMPORT_ERR,)], {}

    if not isinstance(doc, dict):
        return False, ["JSON 顶层不是对象"], {}

    for key in ("meta", "results", "summary"):
        if key not in doc:
            problems.append("缺少顶层字段 %r" % key)
    if problems:
        return False, problems, {}

    meta, results, summary = doc["meta"], doc["results"], doc["summary"]

    if not isinstance(results, list) or not results:
        return False, ["results 不是非空列表"], {}

    # ---- 1) 每条结果的 id 与 verdict ----
    ids = []
    for i, r in enumerate(results):
        if not isinstance(r, dict):
            problems.append("results[%d] 不是对象" % i)
            continue
        cid = r.get("id")
        v = r.get("verdict")
        if not isinstance(cid, str) or not cid:
            problems.append("results[%d] 缺少 id" % i)
            continue
        ids.append(cid)
        if v not in ALLOWED_VERDICTS:
            problems.append("用例 %s 的 verdict=%r 不在允许集合 %s"
                            % (cid, v, list(ALLOWED_VERDICTS)))

    # ---- 2) ID 唯一性 ----
    seen, dups = set(), set()
    for cid in ids:
        if cid in seen:
            dups.add(cid)
        seen.add(cid)
    if dups:
        problems.append("用例 ID 重复: %s" % ", ".join(sorted(dups)[:8]))

    # ---- 3) 必需 ID 完整性 / 未登记 ID ----
    need = set(REQUIRED_CASE_IDS)
    got = set(ids)
    missing = sorted(need - got)
    extra = sorted(got - need)
    if missing:
        problems.append("缺少已登记必需用例 (%d): %s"
                        % (len(missing), ", ".join(missing[:8])))
    if extra:
        problems.append("出现未登记用例 (%d): %s"
                        % (len(extra), ", ".join(extra[:8])))

    # ---- 4) 每条必须 PASS（裁定后不允许待定）----
    nonpass = [r.get("id") for r in results
               if isinstance(r, dict) and r.get("verdict") != "PASS"]
    if nonpass:
        problems.append("非 PASS 用例 (%d): %s"
                        % (len(nonpass), ", ".join(str(x) for x in nonpass[:8])))

    # ---- 5) 计数一律由 results 重算，不采信 summary 自报 ----
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0, "OBSERVED_PENDING_RULING": 0}
    for r in results:
        if isinstance(r, dict):
            v = r.get("verdict")
            if v in counts:
                counts[v] += 1
    recomputed_total = len(results)

    for key, calc in (("total", recomputed_total),
                      ("pass", counts["PASS"]),
                      ("fail", counts["FAIL"]),
                      ("skip", counts["SKIP"]),
                      ("pending", counts["OBSERVED_PENDING_RULING"])):
        claimed = summary.get(key)
        if claimed != calc:
            problems.append("summary.%s=%r 与 results 重算值 %d 不符"
                            % (key, claimed, calc))

    # ---- 6) summary.conserved 不得与自己矛盾 ----
    if summary.get("conserved") is True:
        s_total = summary.get("total")
        s_sum = sum(summary.get(k) or 0
                    for k in ("pass", "fail", "skip", "pending"))
        if s_total != s_sum:
            problems.append("summary.conserved=True 但 %r != %r+%r+%r+%r"
                            % (s_total, summary.get("pass"), summary.get("fail"),
                               summary.get("skip"), summary.get("pending")))

    # ---- 7) 证据身份 ----
    if meta.get("evidence_ok") is not True:
        problems.append("evidence_ok != True (%r)" % (meta.get("evidence_ok"),))

    info = {
        "n_results": len(results),
        "recomputed": counts,
        "recomputed_total": recomputed_total,
        "required_count": len(REQUIRED_CASE_IDS),
    }
    return (len(problems) == 0), problems, info
