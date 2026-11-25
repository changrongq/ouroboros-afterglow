# -*- coding: utf-8 -*-
"""第 4 项 · 原始来源层分离（Mion 2026-11-24 §二）

Mion 给的三条硬约束：
  ① origin_* 不进 revise 白名单（否则成了第二个自报）
  ② current_basis_* 只能由 correct() 写（否则来源被改而「被纠正过」消失）
  ③ 「被纠正过」判据是 origin ≠ current，不是 revision > 1

运行：python afterglow_a/prototype/test_origin_layer.py
"""
from __future__ import annotations

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import afcore
from afcore import Record, RecoveryStore, SchemaError

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
PIN = "2026-11-24T00:00:00Z"


def _harden():
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


_harden()


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


def mk():
    s = RecoveryStore()
    s.insert(Record(
        record_id="r1", content="A 说的原话", source_kind="user_utterance",
        source_ref="utt/A", participant_id="A",
        participation_basis="first_person_report", basis_ref="utt/A",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    s.insert(Record(
        record_id="basis", content="B 依据 C 的更正",
        source_kind="third_party", source_ref="doc/C", participant_id="C",
        participation_basis="third_person_report", basis_ref="doc/C",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    return s


# ======================================================== ①
@case("OL-1a", "insert 时自动写入 origin_* 五字段")
def ol1a():
    s = mk()
    g = s.get("r1")
    pairs = [("origin_source_kind", "user_utterance"),
             ("origin_source_ref", "utt/A"),
             ("origin_participant_id", "A"),
             ("origin_participation_basis", "first_person_report"),
             ("origin_basis_ref", "utt/A")]
    for k, v in pairs:
        assert g.get(k) == v, "%s = %r，应为 %r" % (k, g.get(k), v)
    return "五字段与建时 source 一致"


@case("OL-1b", "origin_* 不在 revise 白名单")
def ol1b():
    bad = [f for f in RecoveryStore._REVISABLE if f.startswith("origin_")]
    assert not bad, "白名单含 %s" % bad
    return "白名单无 origin_*"


@case("OL-1c", "revise 改 origin_* 必须被拒")
def ol1c():
    s = mk()
    for f in ("origin_source_kind", "origin_source_ref",
              "origin_participant_id", "origin_participation_basis",
              "origin_basis_ref"):
        try:
            s.revise("r1", {f: "hijacked"}, reason="t")
        except SchemaError:
            continue
        raise AssertionError("revise 改掉了 %s" % f)
    return "五个字段全部被拒"


# ======================================================== ②
@case("OL-2a", "revise 不得直接改来源字段（否则被纠正过这件事会消失）")
def ol2a():
    s = mk()
    for f, v in (("source_kind", "third_party"),
                 ("source_ref", "hijacked"),
                 ("participant_id", "X"),
                 ("participation_basis", "record_only"),
                 ("basis_ref", "hijacked")):
        try:
            s.revise("r1", {f: v}, reason="偷偷改来源")
        except SchemaError as e:
            assert "来源字段" in str(e) or "correct" in str(e), str(e)
            continue
        raise AssertionError("revise 直接改掉了 %s" % f)
    return "五个来源字段全部被拒"


@case("OL-2b", "correct() 可以改来源（它是唯一合法路径）")
def ol2b():
    s = mk()
    s.correct("r1", "依据 C 更正后", "basis", reason="证据")
    g = s.get("r1")
    assert g["source_ref"] == "doc/C", g["source_ref"]
    assert g["source_kind"] == "third_party", g["source_kind"]
    return "current 已改为纠正依据"


@case("OL-2c", "correct() 之后 origin_* 保持原值不动")
def ol2c():
    s = mk()
    s.correct("r1", "依据 C 更正后", "basis", reason="证据")
    g = s.get("r1")
    assert g["origin_source_ref"] == "utt/A", g["origin_source_ref"]
    assert g["origin_participant_id"] == "A", g["origin_participant_id"]
    assert g["origin_source_kind"] == "user_utterance"
    return "origin 仍是 utt/A / A / user_utterance"


# ======================================================== ③
@case("OL-3a", "只 revise 不改来源 ⇒ was_corrected = False")
def ol3a():
    s = mk()
    s.revise("r1", {"content": "普通修订"}, reason="t")
    assert s.get("r1")["revision"] > 1, "前置：revision 应 >1"
    assert s.was_corrected("r1") is False, (
        "revision>1 不等于被纠正过；was_corrected 应为 False")
    return "revision=2 但 was_corrected=False"


@case("OL-3b", "correct 之后 ⇒ was_corrected = True")
def ol3b():
    s = mk()
    s.correct("r1", "更正后", "basis", reason="证据")
    assert s.was_corrected("r1") is True
    return "True"


@case("OL-3c", "was_corrected 是 origin ≠ current，不是 revision > 1")
def ol3c():
    s1 = mk()
    s1.revise("r1", {"content": "改"}, reason="t")     # revision 2，未纠正
    s2 = mk()
    s2.correct("r1", "改", "basis", reason="证据")     # revision 2，已纠正
    assert s1.get("r1")["revision"] == s2.get("r1")["revision"] == 2, \
        "两条 revision 都应是 2"
    assert s1.was_corrected("r1") is False
    assert s2.was_corrected("r1") is True
    return "同 revision，was_corrected 不同 ⇒ 判据确实是 origin≠current"


# ======================================================== ④
@case("OL-4a", "origin_of 并列给出原始与当前")
def ol4a():
    s = mk()
    s.correct("r1", "更正后", "basis", reason="证据")
    o = s.origin_of("r1")
    for k in ("origin_source_kind", "origin_source_ref",
              "origin_participant_id", "origin_participation_basis",
              "origin_basis_ref", "current_source_kind", "current_source_ref",
              "current_participant_id", "current_participation_basis",
              "current_basis_ref", "was_corrected"):
        assert k in o, "origin_of 缺 %s" % k
    assert o["origin_source_ref"] == "utt/A"
    assert o["current_source_ref"] == "doc/C"
    assert o["was_corrected"] is True
    return "11 键齐全，origin/current 并列"


@case("OL-4b", "C 被污染时，回退的路还在（Mion 说原设计下无解）")
def ol4b():
    s = mk()
    # 模拟 C 本身被污染
    s.revise("basis", {"content": "C 也是错的"}, reason="模拟污染")
    s.correct("r1", "依据被污染的 C 更正", "basis", reason="证据")
    o = s.origin_of("r1")
    assert o["origin_source_ref"] == "utt/A", (
        "C 被污染后原始来源应仍可查")
    assert o["current_source_ref"] == "doc/C"
    assert o["was_corrected"] is True
    return "origin=utt/A 仍在，current=doc/C ⇒ 可回退"


@case("OL-4c", "origin 层在链内（第 1 版摘要覆盖它）")
def ol4c():
    s = mk()
    hist = s.history("r1")
    assert "origin_source_ref" in hist[0], (
        "第 1 版历史里没有 origin 字段 ⇒ 它不在内容摘要覆盖范围")
    # 篡改历史里的 origin ⇒ 链应断
    hist2 = s._history["r1"]
    hist2[0]["origin_source_ref"] = "tampered"
    ok, msgs = s.verify_chain("r1")
    assert ok is False, "篡改 origin 后链仍 True"
    return "origin 被第 1 版摘要覆盖，篡改会断链"


# ======================================================== ⑤
# Mion 2026-11-25 回复6 §三：_via_correct 曾是调用方可自塞的 changes 键
#
# ⚠ 设计要点（A3：断言必须能失败）：
#   这里断言的不是「错误消息里有没有 _via_correct 这个词」——
#   那是措辞检查，实现改一句话就会误报/漏报。
#   要守的机制是：**调用方无法借 revise 改掉来源字段**。
#   所以正确断言 = 尝试之后【来源字段没变】，且【没有任何 correction_of 边】。
#   纵深防御（不在白名单也会拦）会让消息变化，但机制结果不变 ⇒ 断言仍绿，
#   这是对的：只要机制守住了，从哪条路拦下的不算事。
@case("OL-5a", "revise 无法借 _via_correct 改掉来源字段")
def ol5a():
    s = mk()
    before = dict(s.get("r1"))
    try:
        s.revise("r1", {"participation_basis": "third_person_report",
                        "_via_correct": True})
    except SchemaError:
        pass
    after = dict(s.get("r1"))
    assert after["participation_basis"] == "first_person_report", (
        "来源字段被改了：%r ⇒ 护栏失效"
        % after["participation_basis"])
    assert after["revision"] == before["revision"], (
        "被拒之后 revision 仍被抬高 ⇒ 先写后验")
    assert not any(r.get("relation_type") == "correction_of"
                   for r in after["relation"]), \
        "无 correction_of 却改了来源 ⇒「被纠正过」这一事实会消失"
    return "来源未变（%s），revision=%d，无 correction_of" % (
        after["participation_basis"], after["revision"])


@case("OL-5b", "即便直调 _revise_impl，也改不了来源字段")
def ol5b():
    s = mk()
    try:
        s._revise_impl("r1",
                       {"participation_basis": "third_person_report",
                        "_via_correct": True},
                       "", None, via_correct=True)
    except SchemaError:
        pass
    after = dict(s.get("r1"))
    assert after["participation_basis"] == "first_person_report", (
        "私有入口 + via_correct=True 把来源改掉了：%r"
        % after["participation_basis"])
    return "私有入口亦改不了来源（%s）" % after["participation_basis"]


@case("OL-5c", "correct() 仍能改来源（护栏未误伤正路）")
def ol5c():
    s = mk()
    s.correct("r1", "更正后", "basis", reason="证据")
    g = s.get("r1")
    assert g["participation_basis"] == "third_person_report", (
        "correct() 未把来源改指向纠正依据")
    assert any(r.get("relation_type") == "correction_of"
               for r in g["relation"]), "correct() 未加 correction_of 边"
    assert s.was_corrected("r1") is True
    return "correct() 正路通畅，且留下 correction_of"


@case("OL-5d", "反证：绕过尝试后记录逐字段未变")
def ol5d():
    s = mk()
    before = dict(s.get("r1"))
    try:
        s.revise("r1", {"participation_basis": "third_person_report",
                        "_via_correct": True})
    except SchemaError:
        pass
    after = dict(s.get("r1"))
    diff = {k: (before.get(k), after.get(k))
            for k in set(before) | set(after)
            if before.get(k) != after.get(k)}
    assert not diff, "被拒之后记录变了：%s" % diff
    return "零差异（%d 字段全等）" % len(before)


# ======================================================== 汇总
def main():
    print("=" * 78)
    print("第 4 项 · 原始来源层分离（Mion 2026-11-24 §二）")
    print("=" * 78)
    print()

    groups = [
        ("① origin_* 建时写入且不可改", [ol1a, ol1b, ol1c]),
        ("② current_basis_* 只能由 correct() 写", [ol2a, ol2b, ol2c]),
        ("③ 「被纠正过」判据 = origin ≠ current", [ol3a, ol3b, ol3c]),
        ("④ origin_of 并列与可追溯性", [ol4a, ol4b, ol4c]),
        ("⑤ _via_correct 不可由调用方传入（Mion 回复6 §三）",
         [ol5a, ol5b, ol5c, ol5d]),
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

    out = os.path.join(HERE, "reports", "origin_layer_result.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"baseline": "Mion 2026-11-24 §二 第 4 项",
                   "total": total, "passed": passed,
                   "failed": total - passed,
                   "results": [{"id": a, "name": b, "ok": c, "detail": d}
                               for a, b, c, d in RESULTS]},
                  f, ensure_ascii=False, indent=2)
    print("结果已写入 reports/origin_layer_result.json")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
