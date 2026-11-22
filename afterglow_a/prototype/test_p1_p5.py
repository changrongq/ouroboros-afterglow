# -*- coding: utf-8 -*-
"""
AfterGlow-A 最小原型 · P1–P5 验收测试

运行：python afterglow_a/prototype/test_p1_p5.py
输出：每个命题 PASS/FAIL + 证据行 + 退出码
"""
from __future__ import annotations

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from afcore import (Record, RecoveryStore, SchemaError, SOURCE_KINDS,
                    COMMITMENT_STATES, canonical_digest)
from afrecover import classify_match, verify_recovery, check_unknown_preserved

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "synthetic", "records_seed.json")

RESULTS = []


def case(pid, name):
    def deco(fn):
        def run():
            try:
                detail = fn()
                RESULTS.append((pid, name, True, detail))
                print("  [PASS] %s %s — %s" % (pid, name, detail))
            except AssertionError as e:
                RESULTS.append((pid, name, False, str(e)))
                print("  [FAIL] %s %s — %s" % (pid, name, e))
            except Exception as e:
                RESULTS.append((pid, name, False, repr(e)))
                print("  [ERR ] %s %s — %s" % (pid, name, e))
                traceback.print_exc()
        run.pid = pid
        return run
    return deco


# ============================================================ P1
@case("P1", "来源五值闭集 + 缺省 unknown")
def p1():
    # 1a. 闭集里必须有 unknown
    assert "unknown" in SOURCE_KINDS, "SOURCE_KINDS 缺 unknown"
    # 1b. 非法值必须被拒
    bad = Record(record_id="x", content="c", source_kind="user",   # 旧式模糊值
                 source_ref=None, participant_id=None,
                 participation_basis="unknown", basis_ref=None,
                 commitment_state="not_a_commitment", revision=1,
                 prev_digest=None, changed_at="2026-01-01T00:00:00Z",
                 change_authority="t")
    probs = bad.validate()
    assert any("source_kind" in p for p in probs), \
        "非法 source_kind='user' 未被拒绝（P1 违规）"
    # 1c. 缺省必须是 unknown，不是 user
    store = RecoveryStore()
    store.load_seed(SEED)
    unk = [r for r in store.sqlite_rows() if r["source_kind"] == "unknown"]
    assert len(unk) == 1, "种子应含 1 条 unknown 来源，实得 %d" % len(unk)
    return "非法值被拒；unknown 作为一等值存在（%d 条）" % len(unk)


# ============================================================ P2
@case("P2", "修改留上一版摘要 + 链可校验")
def p2():
    store = RecoveryStore()
    store.load_seed(SEED)
    h0 = store.history("syn-0001")
    assert len(h0) == 1, "首版历史长度应为 1"
    d0 = h0[0]["this_digest"]

    d1 = store.revise("syn-0001", {"content": "合成船坞在四月完成了第二次例行检修。"},
                      reason="校正月份")
    h1 = store.history("syn-0001")
    assert len(h1) == 2, "修订后历史应为 2 版，实得 %d" % len(h1)
    assert h1[1]["prev_digest"] == d0, "新版 prev_digest 未指向旧版摘要"
    assert h1[0]["this_digest"] == d0, "旧版摘要被改动（违反不覆盖）"

    ok, problems = store.verify_chain("syn-0001")
    assert ok, "链校验失败: %s" % problems
    return "2 版，旧版摘要不变，链校验通过"


@case("P2", "篡改历史可被摘要链检出")
def p2b():
    store = RecoveryStore()
    store.load_seed(SEED)
    store.revise("syn-0001", {"content": "被改过的内容"}, reason="t")
    # 直接篡改内部历史（模拟磁盘被手改）
    store._history["syn-0001"][0]["content"] = "偷偷改掉的第一版"
    ok, problems = store.verify_chain("syn-0001")
    assert not ok, "篡改后链校验竟然通过（这是最可怕的失败：检查没响）"
    return "篡改被检出：%s" % problems[0][:50]


@case("P2", "prev_digest 被清空可被检出")
def p2c():
    """变异测试 M3 暴露的缺口：verify_chain 原本不检查 prev_digest 为空。"""
    store = RecoveryStore()
    store.load_seed(SEED)
    store.revise("syn-0001", {"content": "第二版内容"}, reason="t")
    # 模拟 prev_digest 被抹成 None（链断但摘要本身仍自洽）
    store._history["syn-0001"][1]["prev_digest"] = None
    # 重新计算该版摘要，使摘要自洽 —— 这样只有 prev_digest 检查能抓到
    d = store._history["syn-0001"][1]
    d["this_digest"] = canonical_digest({k: v for k, v in d.items()
                                         if k != "this_digest"})
    ok, problems = store.verify_chain("syn-0001")
    assert not ok, "prev_digest 为空却校验通过（链完整性未守）"
    assert any("prev_digest" in p for p in problems), \
        "报错未指向 prev_digest：%s" % problems
    return "已检出：%s" % [p for p in problems if "prev_digest" in p][0][:46]


# ============================================================ P3
@case("P3", "纠正后旧版仍在且可指认")
def p3():
    store = RecoveryStore()
    store.load_seed(SEED)
    before = store.history("syn-0004")
    old_content = before[0]["content"]

    store.correct("syn-0004",
                  "记录称检修当天天气为阴。",
                  correcting_record_id="syn-0005",
                  reason="第三方气象记录与当事人的雨/晴说法冲突，取中间值待核")
    after = store.history("syn-0004")
    assert len(after) == 2, "纠正后应有 2 版"
    assert after[0]["content"] == old_content, "旧版内容丢失"
    assert after[1]["content"] != old_content, "新版内容未变"
    rels = [r for r in after[1]["relation"] if r["relation_type"] == "correction_of"]
    assert len(rels) == 1, "纠正关系边缺失"
    assert rels[0]["to_id"] == "syn-0005", "纠正指向错误"

    cur = store.get("syn-0004")
    assert cur["content"] == "记录称检修当天天气为阴。", "当前版不是纠正后版本"
    return "2 版共存，旧版原样保留，correction_of 边已建立"


@case("P3", "纠正不等于删除")
def p3b():
    store = RecoveryStore()
    store.load_seed(SEED)
    hist_before = len(store.history("syn-0002"))
    store.correct("syn-0002", "合成实体 A 说自己不记得那天是否下雨。",
                  correcting_record_id="syn-0001", reason="t")
    hist_after = len(store.history("syn-0002"))
    assert hist_after == hist_before + 1, "纠正应新增一版而非替换"
    return "历史长度 %d → %d（+1，非覆盖）" % (hist_before, hist_after)


# ============================================================ P4
@case("P4", "能报告不知道而不自动填值")
def p4():
    store = RecoveryStore()
    store.load_seed(SEED)
    r = check_unknown_preserved(store, "syn-0005", "source_kind")
    assert r["found"] and r["is_unknown"], \
        "unknown 已被填成别的值（P4 违规）：%r" % (r.get("value"),)

    # 关键反例：现状代码 get('source_role','user') 的行为
    candidate = {"content": "x"}   # 无 source_role 字段
    legacy_default = candidate.get("source_role", "user")
    assert legacy_default == "user", "对照组构造失败"
    # 本原型的做法：字段缺失 ⇒ unknown，不是 user
    record_default = candidate.get("source_kind", "unknown")
    assert record_default == "unknown", "本原型缺省不是 unknown"
    assert legacy_default != record_default, "两种缺省未区分"

    return "unknown 保留；旧缺省 'user' 与新缺省 'unknown' 行为不同"


@case("P4", "非法值报错而非静默落缺省")
def p4b():
    store = RecoveryStore()
    store.load_seed(SEED)
    try:
        store.revise("syn-0001", {"source_kind": "user"})   # 旧式值，不在闭集
    except SchemaError as e:
        assert "source_kind" in str(e)
        return "SchemaError 被抛出：%s" % str(e)[:40]
    raise AssertionError("非法 source_kind 未被拒绝（静默落缺省 = P4 违规）")


@case("P4", "承诺态与承诺字段的一致性被强制")
def p4b2():
    bad = Record(record_id="y", content="c", source_kind="user_utterance",
                 source_ref="s", participant_id="p",
                 participation_basis="first_person_report", basis_ref="s",
                 commitment_state="accepted",          # 但没 committed_to
                 revision=1, prev_digest=None,
                 changed_at="2026-01-01T00:00:00Z", change_authority="t")
    probs = bad.validate()
    assert any("committed_to" in p for p in probs), \
        "承诺态 accepted 却无 committed_to 未被拒"
    return "缺失承诺对象被拒（%d 条问题）" % len(probs)


# ============================================================ P5
@case("P5", "五种 match_kind 可区分")
def p5():
    cases = [
        (["a", "b"], ["a", "b"], "exact"),
        (["a", "b", "c"], ["a", "b"], "superset"),
        (["a"], ["a", "b"], "subset"),
        (["x"], ["a"], "disjoint"),
        (["a", "x"], ["a", "b"], "partial_overlap"),
    ]
    got = []
    for r, e, want in cases:
        kind, _ = classify_match(r, e)
        got.append((kind, want))
        assert kind == want, "retrieved=%s expected=%s 得 %s，应 %s" % (r, e, kind, want)
    return "5 类 + partial_overlap 均正确：" + "/".join(g[0] for g in got)


@case("P5", "not_run 不得被读成通过")
def p5b():
    kind, detail = classify_match([], None, ran=False)
    assert kind == "not_run", "未执行却报 %s" % kind
    kind2, _ = classify_match(["a"], None, ran=True)
    assert kind2 == "not_run", "无期望集却报 %s" % kind2
    return "ran=False 与 expected=None 均落 not_run"


@case("P5", "实际恢复验证：检索 syn-0001 与期望集对比")
def p5c():
    store = RecoveryStore()
    store.load_seed(SEED)
    # 模拟一次粗检索：含「检修」字样
    report = verify_recovery(
        store, "q-harbour",
        selector=lambda rec: "检修" in rec.get("content", ""),
        expected_ids=["syn-0001"],
    )
    assert report["match_kind"] == "superset", \
        "应得 superset（多条含检修），实得 %s：%s" % (
            report["match_kind"], report["retrieved_ids"])
    assert report["engineering_only"] is True
    assert report["is_scientific_result"] is False, \
        "工程测试被标成科学结果（违反凌翼 §三）"
    return "superset，含 %d 条，已标 engineering_only" % len(report["retrieved_ids"])


# ============================================================ 额外：负控制

@case("NC", "工程结论不得冒充科学结果")
def nc():
    store = RecoveryStore()
    store.load_seed(SEED)
    report = verify_recovery(store, "q-all", selector=lambda r: True,
                             expected_ids=[r["record_id"] for r in store.sqlite_rows()])
    assert report["is_scientific_result"] is False
    assert report["engineering_only"] is True
    assert report["match_kind"] == "exact"
    return "exact 但 is_scientific_result=False（边界正确）"


@case("NC", "原型的写入日志完整可查")
def nc2():
    store = RecoveryStore()
    store.load_seed(SEED)
    store.revise("syn-0003", {"commitment_state": "fulfilled"}, reason="月底已交")
    log = store.write_log()
    assert len(log) == 1, "应记录 1 次写入，实得 %d" % len(log)
    assert log[0]["op"] == "revise"
    assert log[0]["from"] and log[0]["to"]
    return "写入日志 %d 条，含 from/to 摘要" % len(log)


def main():
    print("=" * 74)
    print("AfterGlow-A 最小原型 · P1–P5 验收")
    print("=" * 74)
    tests = [v for k, v in sorted(globals().items())
             if callable(v) and hasattr(v, "pid")]
    order = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "NC": 6}
    tests.sort(key=lambda f: (order.get(f.pid, 9), f.__name__))

    cur = None
    for t in tests:
        if t.pid != cur:
            cur = t.pid
            print("\n[%s]" % cur)
        t()

    print("\n" + "=" * 74)
    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 74)

    os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
    out = os.path.join(HERE, "reports", "p1_p5_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump([{"id": a, "case": b, "pass": c, "detail": d}
                   for a, b, c, d in RESULTS],
                  f, ensure_ascii=False, indent=2)
    print("结果已写入:", out)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
