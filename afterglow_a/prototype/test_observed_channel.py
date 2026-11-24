# -*- coding: utf-8 -*-
"""Mion 观测通道改造 · 回归测试

覆盖 Mion 2026-11-24 回复2 / 回复3 的全部可执行要求：
  第 0 项  conflict_summary 进返回结构，第一个值 observed_absent
  第 1 项  basis_conflict 四值 + observed_origin（只经 record_observed）
  第 2 项  record_observed 时序约束（revision==1 且未被 revise/correct）
  第 3 项  unverifiable_ratio 作为独立一栏

运行：python afterglow_a/prototype/test_observed_channel.py
"""
from __future__ import annotations

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import afcore
from afcore import (Record, RecoveryStore, SchemaError,
                    OBSERVED_ORIGINS, BASIS_CONFLICTS)
from afrecover import verify_recovery, summarize_conflicts

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


def mk(rid="r1", basis="first_person_report", kind="user_utterance",
       ref="u/1"):
    s = RecoveryStore()
    s.insert(Record(
        record_id=rid, content="内容", source_kind=kind,
        source_ref=ref, participant_id=None,
        participation_basis=basis, basis_ref=ref,
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    return s


def good_reg():
    return {"registered_by": "obs", "registered_at": "2026-11-20T00:00:00Z",
            "registered_rev": "cd-v1",
            "independent_of_write": "yes", "before_exposure": "yes"}


# ======================================================== 第 0 项
@case("OC-0a", "conflict_summary 必须随 verify_recovery 结果返回")
def oc0a():
    s = mk()
    rep = verify_recovery(s, "q", lambda r: True, ["r1"],
                          registration=good_reg())
    assert "conflict_summary" in rep, "返回结构里没有 conflict_summary"
    cs = rep["conflict_summary"]
    for k in ("basis_conflict", "affected_ids", "detail"):
        assert k in cs, "conflict_summary 缺键 %s" % k
    return "返回结构含 conflict_summary（3 键齐全）"


@case("OC-0b", "未观测 ⇒ observed_absent，不得是 none")
def oc0b():
    s = mk()
    rep = verify_recovery(s, "q", lambda r: True, ["r1"],
                          registration=good_reg())
    v = rep["conflict_summary"]["basis_conflict"]
    assert v == "observed_absent", "未观测却报 %r" % (v,)
    assert v != "none", "把「没观测」读成了「没冲突」"
    return "observed_absent"


@case("OC-0c", "取回集为空 ⇒ observed_absent 且 ratio=None（不是 0）")
def oc0c():
    s = mk()
    rep = verify_recovery(s, "q", lambda r: False, [],
                          registration=good_reg())
    cs = rep["conflict_summary"]
    assert cs["basis_conflict"] == "observed_absent", cs["basis_conflict"]
    assert cs["unverifiable_ratio"] is None, (
        "空集 ratio 应为 None，实为 %r（0 会被读成「全部可判定」）"
        % (cs["unverifiable_ratio"],))
    return "observed_absent + ratio=None"


@case("OC-0d", "conflict 不影响 recovery_eligible（激励约束）")
def oc0d():
    s = mk()
    # 制造一个明确冲突
    s.record_observed("r1", "model_generation")
    rep = verify_recovery(s, "q", lambda r: True, ["r1"],
                          registration=good_reg())
    assert rep["conflict_summary"]["basis_conflict"] == \
        "asserted_contradicts_observed", rep["conflict_summary"]
    assert rep["recovery_eligible"] is True, (
        "冲突拉低了资格 ⇒ 系统会学会不标冲突")
    assert "conflict" not in "".join(rep["ineligible_reasons"]), \
        "冲突泄漏进了 ineligible_reasons"
    return "冲突但 eligible=True，且未进 ineligible_reasons"


# ======================================================== 第 1 项
@case("OC-1a", "OBSERVED_ORIGINS / BASIS_CONFLICTS 闭集正确")
def oc1a():
    assert OBSERVED_ORIGINS == {"system_dispatch", "model_generation",
                                "human_input", "unknown_origin"}, \
        sorted(OBSERVED_ORIGINS)
    assert BASIS_CONFLICTS == {"none", "asserted_contradicts_observed",
                               "observed_absent", "observed_unresolved"}, \
        sorted(BASIS_CONFLICTS)
    # 与 UNKNOWN_REASONS 不重名（Mion：元数不同，不能复用）
    inter = BASIS_CONFLICTS & afcore.UNKNOWN_REASONS
    assert not inter, "与 UNKNOWN_REASONS 重名：%s" % (inter,)
    return "四值闭集正确，且与 UNKNOWN_REASONS 无重名"


@case("OC-1b", "observed_origin 不在闭集内 ⇒ 报错")
def oc1b():
    s = mk()
    for bad in ("model_created", "system", "", None, 123):
        try:
            s.record_observed("r1", bad)
        except SchemaError as e:
            assert "不在闭集内" in str(e), str(e)
        else:
            raise AssertionError("非法值 %r 被接受" % (bad,))
    return "5 种非法值全部被拒"


@case("OC-1c", "不得经 Record 构造器填写 observed_origin")
def oc1c():
    s = RecoveryStore()
    try:
        s.insert(Record(
            record_id="r9", content="c", source_kind="user_utterance",
            source_ref="u/9", participant_id=None,
            participation_basis="first_person_report", basis_ref="u/9",
            commitment_state="not_a_commitment", revision=1, prev_digest=None,
            changed_at=PIN, change_authority="f",
            observed_origin="system_dispatch"))
    except SchemaError as e:
        assert "不得经 Record 构造写入" in str(e), str(e)
        return "被拒"
    raise AssertionError("构造器能填 observed_origin")


@case("OC-1d", "revise 不得修改 observed_origin / basis_conflict")
def oc1d():
    s = mk()
    s.record_observed("r1", "system_dispatch")
    for f in ("observed_origin", "basis_conflict"):
        try:
            s.revise("r1", {f: "human_input"}, reason="t")
        except SchemaError as e:
            assert f in str(e), str(e)
        else:
            raise AssertionError("revise 改掉了 %s" % f)
    return "两个字段都不在白名单内"


@case("OC-1e", "伪亲历：声称亲历但系统看到模型生成 ⇒ 冲突")
def oc1e():
    s = mk(basis="first_person_report", kind="model_echo")
    s.record_observed("r1", "model_generation")
    g = s.get("r1")
    assert g["basis_conflict"] == "asserted_contradicts_observed", \
        g["basis_conflict"]
    return "asserted_contradicts_observed"


@case("OC-1f", "声称亲历但系统看到派发 ⇒ 也判冲突")
def oc1f():
    s = mk(basis="first_person_report", kind="system_generated")
    s.record_observed("r1", "system_dispatch")
    g = s.get("r1")
    assert g["basis_conflict"] == "asserted_contradicts_observed", \
        ("系统派发的内容声称第一人称亲历，应判冲突；实为 %r"
         % (g["basis_conflict"],))
    return "asserted_contradicts_observed"


@case("OC-1g", "声称亲历且系统看到人类输入 ⇒ none")
def oc1g():
    s = mk(basis="first_person_report", kind="user_utterance")
    s.record_observed("r1", "human_input")
    assert s.get("r1")["basis_conflict"] == "none"
    return "none"


@case("OC-1h", "observed_origin=unknown_origin ⇒ observed_unresolved")
def oc1h():
    s = mk(basis="first_person_report")
    s.record_observed("r1", "unknown_origin")
    assert s.get("r1")["basis_conflict"] == "observed_unresolved", \
        "有观测但判不出，不得读成 none"
    return "observed_unresolved"


# ======================================================== 第 2 项
@case("OC-2a", "revise 之后 record_observed 必须被拒（防事后补观测）")
def oc2a():
    s = mk()
    s.revise("r1", {"content": "改"}, reason="t")
    try:
        s.record_observed("r1", "system_dispatch")
    except SchemaError as e:
        assert "第 2 版" in str(e) or "晚于内容写入" in str(e), str(e)
        return "被拒"
    raise AssertionError("事后补观测被接受了")


@case("OC-2b", "correct 之后 record_observed 必须被拒")
def oc2b():
    s = mk()
    s.insert(Record(
        record_id="basis", content="依据", source_kind="third_party",
        source_ref="doc/C", participant_id=None,
        participation_basis="record_only", basis_ref="doc/C",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="f"))
    s.correct("r1", "更正后", "basis", reason="证据")
    try:
        s.record_observed("r1", "system_dispatch")
    except SchemaError:
        return "被拒"
    raise AssertionError("correct 之后补观测被接受")


@case("OC-2c", "观测是一次性的，重复调用必须被拒")
def oc2c():
    s = mk()
    s.record_observed("r1", "system_dispatch")
    try:
        s.record_observed("r1", "human_input")
    except SchemaError as e:
        assert "一次性" in str(e) or "不得覆盖" in str(e), str(e)
        return "被拒"
    raise AssertionError("观测可被覆盖")


@case("OC-2d", "批量补观测：第二至 N 条必须全部失败")
def oc2d():
    """Mion 指出的那个洞：「一个脚本能给全部历史刷上观测」。"""
    s = RecoveryStore()
    for i in range(1, 6):
        s.insert(Record(
            record_id="b%d" % i, content="c", source_kind="model_echo",
            source_ref="g/%d" % i, participant_id=None,
            participation_basis="first_person_report", basis_ref="g/%d" % i,
            commitment_state="not_a_commitment", revision=1, prev_digest=None,
            changed_at=PIN, change_authority="f"))
    # 先给它们全部 revise 过（模拟「历史记录」）
    for i in range(1, 6):
        s.revise("b%d" % i, {"content": "改过"}, reason="历史")

    ok = 0
    for i in range(1, 6):
        try:
            s.record_observed("b%d" % i, "system_dispatch")
            ok += 1
        except SchemaError:
            pass
    assert ok == 0, "批量补观测成功 %d 条（应为 0）" % ok
    return "5 条历史记录全部拒绝补观测"


# ======================================================== 第 3 项
@case("OC-3a", "unverifiable_ratio 是独立一栏，且不进合格率")
def oc3a():
    s = RecoveryStore()
    # 3 条：1 条可判定(none)，2 条不可判定(未观测)
    for i, basis in enumerate(["first_person_report"] * 3, 1):
        s.insert(Record(
            record_id="u%d" % i, content="c", source_kind="user_utterance",
            source_ref="u/%d" % i, participant_id=None,
            participation_basis=basis, basis_ref="u/%d" % i,
            commitment_state="not_a_commitment", revision=1, prev_digest=None,
            changed_at=PIN, change_authority="f"))
    s.record_observed("u1", "human_input")   # 可判定 → none

    cs = summarize_conflicts(s, ["u1", "u2", "u3"])
    assert cs["unverifiable_ratio"] is not None, "ratio 未计算"
    assert abs(cs["unverifiable_ratio"] - 2.0 / 3.0) < 1e-9, \
        "ratio 应为 2/3，实为 %r" % (cs["unverifiable_ratio"],)
    assert len(cs["unverifiable_ids"]) == 2, cs["unverifiable_ids"]
    assert "不是伪亲历率" in cs["unverifiable_note"], cs["unverifiable_note"]

    # 它不得出现在 eligible 的计算里
    rep = verify_recovery(s, "q", lambda r: True, ["u1", "u2", "u3"],
                          registration=good_reg())
    assert "unverifiable_ratio" not in rep["ineligible_reasons"]
    assert rep["conflict_summary"]["unverifiable_ratio"] is not None
    return "ratio=2/3，且未进 ineligible_reasons"


@case("OC-3b", "全部可判定 ⇒ ratio=0（不是 None）")
def oc3b():
    s = mk()
    s.record_observed("r1", "human_input")
    cs = summarize_conflicts(s, ["r1"])
    assert cs["unverifiable_ratio"] == 0.0, cs["unverifiable_ratio"]
    assert cs["basis_conflict"] == "none"
    return "ratio=0.0，basis_conflict=none"


@case("OC-3c", "未指定范围 ⇒ ratio=None（不可计算 ≠ 0）")
def oc3c():
    s = mk()
    cs = summarize_conflicts(s, None)
    assert cs["unverifiable_ratio"] is None, cs["unverifiable_ratio"]
    return "None"


# ======================================================== 第 4 项（Mion 回复4）
@case("OC-4a", "观测已进链（Mion 回复4 §二·链外问题）")
def oc4a():
    s = mk(basis="first_person_report", kind="model_echo")
    assert s.observed_chained("r1") is False, "前置：未观测不应有链"
    s.record_observed("r1", "model_generation")
    assert s.observed_chained("r1") is True, (
        "观测未进链 ⇒ 观测字段是唯一不受校验的字段")
    chain = s.observed_chain("r1")
    assert len(chain) == 1, len(chain)
    for k in ("record_id", "asserted", "observed", "basis_conflict",
              "pseudo_first_person", "at", "prev", "digest"):
        assert k in chain[0], "链条目缺键 %s" % k
    return "进链成功，8 键齐全"


@case("OC-4b", "篡改观测链必须被发现")
def oc4b():
    s = mk(basis="first_person_report", kind="model_echo")
    s.record_observed("r1", "model_generation")
    ok, _ = s.verify_observed_chain("r1")
    assert ok, "前置：正常链应自洽"

    # 篡改冲突值
    s._observed_chain["r1"][0]["basis_conflict"] = "none"
    ok2, msgs = s.verify_observed_chain("r1")
    assert ok2 is False, "改观测链里的冲突值未被发现"
    assert any("摘要不符" in m for m in msgs), msgs
    return "改 basis_conflict 会被检出"


@case("OC-4c", "snapshot_token 必须覆盖观测链")
def oc4c():
    s = mk()
    t0 = s.snapshot_token()
    s.record_observed("r1", "model_generation")
    t1 = s.snapshot_token()
    assert t0 != t1, "record_observed 未改变 snapshot_token"
    # 直接篡改链
    s._observed_chain["r1"][0]["basis_conflict"] = "none"
    t2 = s.snapshot_token()
    assert t1 != t2, "篡改观测链未改变 snapshot_token"
    return "观测与篡改都改变 token"


@case("OC-4d", "record_only × model_generation ⇒ none（弱断言不被违反）")
def oc4d():
    s = mk(basis="record_only", kind="model_echo")
    s.record_observed("r1", "model_generation")
    v = s.get("r1")["basis_conflict"]
    assert v == "none", (
        "record_only 断言「不指向任何陈述者」，模型生成不违反它；实为 %r" % (v,))
    return "none"


@case("OC-4e", "third_person_report × model_generation ⇒ 冲突（断言与观测相反）")
def oc4e():
    s = mk(basis="third_person_report", kind="model_echo")
    s.record_observed("r1", "model_generation")
    v = s.get("r1")["basis_conflict"]
    assert v == "asserted_contradicts_observed", v
    return "asserted_contradicts_observed"


@case("OC-4f", "pseudo_first_person 是派生标记，不是第五个值")
def oc4f():
    # 伪亲历：first + model_generation
    a = mk(basis="first_person_report", kind="model_echo")
    a.record_observed("r1", "model_generation")
    assert a.get("r1")["basis_conflict"] == "asserted_contradicts_observed"
    assert a.pseudo_first_person("r1") is True

    # 冲突但非伪亲历：first + system_dispatch
    b = mk(basis="first_person_report", kind="system_generated")
    b.record_observed("r1", "system_dispatch")
    assert b.get("r1")["basis_conflict"] == "asserted_contradicts_observed"
    assert b.pseudo_first_person("r1") is False, (
        "非伪亲历也能冲突 —— 证明伪亲历是冲突的真子集")
    # 枚举仍是四值
    assert len(BASIS_CONFLICTS) == 4, len(BASIS_CONFLICTS)
    return "冲突 ⊋ 伪亲历，枚举仍 4 值"


@case("OC-4g", "record_only_ratio 是行为漏洞度量，单独一栏")
def oc4g():
    s = RecoveryStore()
    for i, basis in enumerate(["record_only", "record_only",
                               "first_person_report"], 1):
        s.insert(Record(
            record_id="q%d" % i, content="c", source_kind="model_echo",
            source_ref="g/%d" % i, participant_id=None,
            participation_basis=basis, basis_ref="g/%d" % i,
            commitment_state="not_a_commitment", revision=1, prev_digest=None,
            changed_at=PIN, change_authority="f"))
    cs = summarize_conflicts(s, ["q1", "q2", "q3"])
    assert cs["record_only_ratio"] is not None
    assert abs(cs["record_only_ratio"] - 2.0 / 3.0) < 1e-9, \
        cs["record_only_ratio"]
    assert "分母被抽空" in cs["record_only_note"], cs["record_only_note"]
    # 不进 ineligible_reasons
    rep = verify_recovery(s, "q", lambda r: True, ["q1", "q2", "q3"],
                          registration=good_reg())
    assert "record_only_ratio" not in rep["ineligible_reasons"]
    return "ratio=2/3，独立一栏"


@case("OC-4h", "observed_chained 进返回结构")
def oc4h():
    s = mk(basis="first_person_report", kind="model_echo")
    s.record_observed("r1", "model_generation")
    cs = summarize_conflicts(s, ["r1"])
    assert cs["observed_chained_ids"] == ["r1"], cs["observed_chained_ids"]
    assert cs["observed_unchained_ids"] == [], cs["observed_unchained_ids"]

    # 未观测的记录应出现在 unchained 里
    s2 = mk()
    cs2 = summarize_conflicts(s2, ["r1"])
    assert cs2["observed_chained_ids"] == []
    assert cs2["observed_unchained_ids"] == ["r1"]
    return "chained / unchained 分开列"


# ======================================================== 汇总
def main():
    print("=" * 78)
    print("观测通道改造回归 · 据 Mion 2026-11-24 回复2 / 回复3 / 回复4")
    print("=" * 78)
    print()

    groups = [
        ("第 0 项 · conflict_summary 进返回结构",
         [oc0a, oc0b, oc0c, oc0d]),
        ("第 1 项 · basis_conflict 四值 + observed_origin",
         [oc1a, oc1b, oc1c, oc1d, oc1e, oc1f, oc1g, oc1h]),
        ("第 2 项 · record_observed 时序约束",
         [oc2a, oc2b, oc2c, oc2d]),
        ("第 3 项 · unverifiable_ratio 独立一栏",
         [oc3a, oc3b, oc3c]),
        ("第 4 项 · 观测进链 + 判定表修正 + 派生标记（Mion 回复4）",
         [oc4a, oc4b, oc4c, oc4d, oc4e, oc4f, oc4g, oc4h]),
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

    out = os.path.join(HERE, "reports", "observed_channel_result.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({
            "baseline": "Mion 2026-11-24 回复2 / 回复3",
            "total": total, "passed": passed, "failed": total - passed,
            "results": [{"id": a, "name": b, "ok": c, "detail": d}
                        for a, b, c, d in RESULTS],
        }, f, ensure_ascii=False, indent=2)
    print("结果已写入 reports/observed_channel_result.json")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
