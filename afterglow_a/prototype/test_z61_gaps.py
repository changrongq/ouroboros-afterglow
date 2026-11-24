# -*- coding: utf-8 -*-
"""Z61 四项回归测试 · 知微 2026-11-24 独立复核所指的四个缺口

每个用例都直接构造知微描述的现象，并断言【修复后的正确行为】。
修复前的行为已在 repro_z61*.py 中记录，此处断言的是反方向。

运行：python afterglow_a/prototype/test_z61_gaps.py
"""
from __future__ import annotations

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import afcore
import afrecover
from afcore import Record, RecoveryStore
from afrecover import verify_recovery, check_registration, check_integrity

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
PIN = "2026-11-24T00:00:00Z"


def _harden_stdio():
    for n in ("stdout", "stderr"):
        s = getattr(sys, n, None)
        if s is None:
            continue
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            try:
                s.reconfigure(errors="backslashreplace")
            except Exception:
                pass


_harden_stdio()


def case(cid, name):
    def deco(fn):
        def run():
            try:
                d = fn()
                RESULTS.append((cid, name, True, d))
                print("  [PASS] %s %s — %s" % (cid, name, d))
            except AssertionError as e:
                RESULTS.append((cid, name, False, str(e)))
                print("  [FAIL] %s %s — %s" % (cid, name, e))
            except Exception as e:
                RESULTS.append((cid, name, False, repr(e)))
                print("  [ERR ] %s %s — %s" % (cid, name, e))
                traceback.print_exc()
        return run
    return deco


def mk(rid="syn-z", content="原始内容"):
    s = RecoveryStore()
    s.insert(Record(
        record_id=rid, content=content, source_kind="user_utterance",
        source_ref="utt/z", participant_id=None,
        participation_basis="first_person_report", basis_ref="utt/z",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic-fixture"))
    return s


def good_reg(**over):
    d = {"registered_by": "ops-observer", "registered_at": "2026-11-20T00:00:00Z",
         "registered_rev": "cd-v1",
         "independent_of_write": "yes", "before_exposure": "yes"}
    d.update(over)
    return d


def tamper_history_summary(s, rid="syn-z", idx=0):
    h = s._history[rid]
    for k in list(h[idx]):
        if "digest" in k.lower() and k != "prev_digest":
            h[idx][k] = "0" * 64
            return True
    return False


# ============================================================ Z61-01
@case("Z61-01", "G6 默认消费本次检查快照：检查中途被改必须拒绝")
def z61_01():
    s = mk()
    orig = afrecover.check_integrity

    def patched(store, record_ids=None):
        r = orig(store, record_ids)
        # 真实检查已完成，返回给主入口前改库
        if "syn-z" in store._live:
            store.revise("syn-z", {"content": "中途偷改"}, reason="mid-race")
        return r

    afrecover.check_integrity = patched
    try:
        rep = verify_recovery(s, "q", lambda r: True, ["syn-z"],
                              registration=good_reg())
    finally:
        afrecover.check_integrity = orig

    assert rep["recovery_eligible"] is False, (
        "检查中途被改却仍 eligible（Z61-01 未修）")
    assert "stale_check" in rep["ineligible_reasons"], (
        "缺 stale_check：%s" % (rep["ineligible_reasons"],))
    return "eligible=False, reasons=%s" % (rep["ineligible_reasons"],)


@case("Z61-01b", "G6 默认生效：不传 expected_snapshot 也能检出")
def z61_01b():
    # 断言结构而非字符串：
    # 必须存在【无条件的】checked_tok 比较，且它不在 expected_snapshot 分支里。
    # （expected_snapshot 的比较作为额外前提【允许】存在，那不是缺陷。）
    import inspect
    src = inspect.getsource(verify_recovery)

    assert "checked_tok" in src, "实现中找不到 checked_tok"
    assert "checked_tok = (integ.get(\"scope\") or {}).get(\"snapshot\")" in src, \
        "未从本次检查结果取快照"

    # 逐行检查：checked_tok 的比较行不能带 expected_snapshot 条件
    checked_lines = [l.strip() for l in src.splitlines()
                     if "checked_tok" in l and "!=" in l]
    assert checked_lines, "找不到 checked_tok 的比较行"
    bad = [l for l in checked_lines
           if "expected_snapshot" in l or "if False" in l]
    assert not bad, "checked_tok 的比较仍受外部参数约束：%s" % (bad,)

    # 实证：check_integrity 的 scope.snapshot 非空且被消费
    s = mk()
    ci = check_integrity(s, ["syn-z"])
    assert ci["scope"]["snapshot"] is not None, "check_integrity 未返回快照"

    # 真正的行为验证：不传 expected_snapshot，但检查后库变了 —— 必须被拒
    orig = afrecover.check_integrity

    def patched(store, record_ids=None):
        r = orig(store, record_ids)
        if "syn-z" in store._live:
            store.revise("syn-z", {"content": "无外部令牌时被改"}, reason="r")
        return r

    afrecover.check_integrity = patched
    try:
        rep = verify_recovery(s, "q", lambda r: True, ["syn-z"],
                              registration=good_reg())
    finally:
        afrecover.check_integrity = orig

    assert rep["recovery_eligible"] is False, (
        "未传 expected_snapshot 时检查后改动未被检出")
    return "无条件比较 checked_tok；不传令牌也能检出"


# ============================================================ Z61-02
@case("Z61-02", "快照覆盖历史实际内容：只改历史也必须改变令牌")
def z61_02():
    s = mk()
    s.revise("syn-z", {"content": "第二版"}, reason="r")
    tok_before = s.snapshot_token()
    ok_before, _ = s.verify_chain("syn-z")
    assert ok_before, "前置：改前链应通过"

    # 只改历史第 1 版正文，不动 live，不改长度
    s._history["syn-z"][0]["content"] = "被篡改的历史"
    tok_after = s.snapshot_token()
    ok_after, msgs = s.verify_chain("syn-z")

    assert not ok_after, "前置：改后链应失败"
    assert tok_before != tok_after, (
        "历史正文被改但令牌未变（Z61-02 未修）")
    # 不把 token 值写进 detail：
    #   changed_at 精确到秒，同一次运行内的 token 跨进程不可复算。
    #   写进报告会让每次跑都产生一份「看似不同」的产物 ——
    #   这正是第二封函里讲的那件事，测试自己也该遵守。
    return "历史正文改动后令牌改变，链校验 False"


@case("Z61-02b", "快照覆盖摘要串本身：改 this_digest 也改变令牌")
def z61_02b():
    s = mk()
    tok0 = s.snapshot_token()
    s._history["syn-z"][0]["this_digest"] = "f" * 64
    tok1 = s.snapshot_token()
    assert tok0 != tok1, "摘要串被改但令牌未变"
    return "改 this_digest ⇒ token 变"


@case("Z61-02c", "快照覆盖链指针：改 prev_digest 也改变令牌")
def z61_02c():
    s = mk()
    s.revise("syn-z", {"content": "v2"}, reason="r")
    tok0 = s.snapshot_token()
    s._history["syn-z"][1]["prev_digest"] = "e" * 64
    tok1 = s.snapshot_token()
    assert tok0 != tok1, "prev_digest 被改但令牌未变"
    return "改 prev_digest ⇒ token 变"


@case("Z61-02d", "快照仍对正常写入敏感（不误伤）")
def z61_02d():
    s = mk()
    t0 = s.snapshot_token()
    s.revise("syn-z", {"content": "v2"}, reason="r")
    t1 = s.snapshot_token()
    assert t0 != t1, "正常 revise 后令牌未变"
    # 同内容同历史的两库应同令牌
    assert mk().snapshot_token() == mk().snapshot_token(), \
        "同内容两库令牌不同（令牌不确定）"
    return "正常写入变，同内容稳定"


@case("Z61-02e", "只改 live 不改 history：令牌必须变")
def z61_02e():
    """M15 变异（删掉 live 侧投影）的守护用例。

    正常 API 做不到「只改 live」——revise 会同时写 history 与 live。
    因此这里直接改 _live，模拟「检查后当前版对象被替换、历史未变」，
    这正是 live 侧投影唯一能覆盖的窗口。
    """
    s = mk()
    tok0 = s.snapshot_token()

    # 只替换 _live 中的对象，不动 _history
    cur = s._live["syn-z"]
    d = cur.to_dict()
    d["content"] = "被单独替换的当前版"
    from afcore import Record as _R
    s._live["syn-z"] = _R(**{k: v for k, v in d.items()
                             if k != "this_digest"})

    tok1 = s.snapshot_token()
    assert tok0 != tok1, (
        "只改 live 未改 history，令牌却未变 ⇒ live 侧未被覆盖")
    return "只改 live ⇒ token 变"


# ============================================================ Z61-03
@case("Z61-03", "登记身份空值必须判不合格")
def z61_03():
    bad_cases = [
        ("registered_by=''", good_reg(registered_by="")),
        ("registered_rev=''", good_reg(registered_rev="")),
        ("registered_by=None", good_reg(registered_by=None)),
        ("registered_rev=None", good_reg(registered_rev=None)),
        ("registered_by 纯空白", good_reg(registered_by="   ")),
        ("registered_rev 纯空白", good_reg(registered_rev="\t \n")),
        ("两个都空", good_reg(registered_by="", registered_rev="")),
        ("registered_by=123（非字符串）", good_reg(registered_by=123)),
        ("registered_rev=3.14（非字符串）", good_reg(registered_rev=3.14)),
        ("registered_by=True（bool）", good_reg(registered_by=True)),
        ("registered_rev=[]（list）", good_reg(registered_rev=[])),
    ]
    leaks = []
    for desc, r in bad_cases:
        chk = check_registration(r)
        if chk["independent"]:
            leaks.append(desc)
    assert not leaks, "以下情形仍被判独立：%s" % (leaks,)

    # 正向：齐全时应判独立
    ok = check_registration(good_reg())
    assert ok["independent"] is True, "齐全登记被误判不合格"
    return "%d 种非法值全部拒绝；齐全时通过" % len(bad_cases)


@case("Z61-03b", "空身份登记进入门禁后必须拒绝资格")
def z61_03b():
    s = mk()
    rep = verify_recovery(s, "q", lambda r: True, ["syn-z"],
                          registration=good_reg(registered_by=""))
    assert rep["recovery_eligible"] is False, "空登记人却给了资格"
    assert "registration_not_independent" in rep["ineligible_reasons"], \
        "原因码缺 registration_not_independent：%s" % (
            rep["ineligible_reasons"],)
    return "eligible=False，原因含 registration_not_independent"


@case("Z61-03c", "未提供登记仍不阻断（兼容路径不变）")
def z61_03c():
    s = mk()
    rep = verify_recovery(s, "q", lambda r: True, ["syn-z"])
    assert rep["expected_ids_registration"]["present"] is False
    assert rep["recovery_eligible"] is True, (
        "未提供登记不应阻断（与原 RG-8 兼容路径一致）")
    return "present=False 但不阻断"


# ============================================================ Z61-04
@case("Z61-04", "链已失败 + 过期令牌：failed 不得被覆盖成 not_checked")
def z61_04():
    s = mk()
    tok = s.snapshot_token()
    assert tamper_history_summary(s, "syn-z", 0)
    ok, _ = s.verify_chain("syn-z")
    assert not ok, "前置：链应失败"

    # 让令牌过期
    s.revise("syn-z", {"content": "使令牌失效"}, reason="r")

    rep = verify_recovery(s, "q", lambda r: True, ["syn-z"],
                          registration=good_reg(), expected_snapshot=tok)

    assert rep["integrity_status"] == "failed", (
        "failed 被覆盖成 %s（Z61-04 未修）" % rep["integrity_status"])
    assert "integrity_failed" in rep["ineligible_reasons"], (
        "原因码缺 integrity_failed：%s" % (rep["ineligible_reasons"],))
    assert "stale_check" in rep["ineligible_reasons"], (
        "原因码缺 stale_check：%s" % (rep["ineligible_reasons"],))
    return "status=failed，reasons=%s" % (rep["ineligible_reasons"],)


@case("Z61-04b", "未失败 + 过期令牌：仍应降级为 not_checked")
def z61_04b():
    s = mk()
    tok = s.snapshot_token()
    s.revise("syn-z", {"content": "改动"}, reason="r")
    rep = verify_recovery(s, "q", lambda r: True, ["syn-z"],
                          registration=good_reg(), expected_snapshot=tok)
    assert rep["integrity_status"] == "not_checked", (
        "未失败时快照失效应降级 not_checked，实为 %s"
        % rep["integrity_status"])
    assert "stale_check" in rep["ineligible_reasons"]
    return "status=not_checked，含 stale_check"


@case("Z61-04c", "健康库 + 正确令牌：不应误报 stale")
def z61_04c():
    s = mk()
    tok = s.snapshot_token()
    rep = verify_recovery(s, "q", lambda r: True, ["syn-z"],
                          registration=good_reg(), expected_snapshot=tok)
    assert rep["integrity_status"] == "verified", (
        "健康库被误判 %s" % rep["integrity_status"])
    assert "stale_check" not in rep["ineligible_reasons"], (
        "健康库误报 stale_check：%s" % (rep["ineligible_reasons"],))
    assert rep["recovery_eligible"] is True
    return "verified 且 eligible，无 stale_check"


# ============================================================ 汇总
def main():
    print("=" * 78)
    print("Z61 四项回归 · 知微 2026-11-24 独立复核所指缺口")
    print("=" * 78)
    print()

    groups = [
        ("Z61-01 · G6 默认消费本次检查快照", [z61_01, z61_01b]),
        ("Z61-02 · 快照覆盖历史实际内容", [z61_02, z61_02b, z61_02c,
                                          z61_02d, z61_02e]),
        ("Z61-03 · 登记身份空值约束", [z61_03, z61_03b, z61_03c]),
        ("Z61-04 · failed 不得被 stale 覆盖", [z61_04, z61_04b, z61_04c]),
    ]
    for g, fns in groups:
        print("[%s]" % g)
        for fn in fns:
            fn()
        print()

    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print("=" * 78)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 78)

    out_dir = os.path.join(HERE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "z61_gaps_result.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump({
            "baseline": "知微 2026-11-24 独立复核",
            "total": total, "passed": passed, "failed": total - passed,
            "results": [{"id": a, "name": b, "ok": c, "detail": d}
                        for a, b, c, d in RESULTS],
        }, f, ensure_ascii=False, indent=2)
    print("结果已写入 reports/z61_gaps_result.json")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
