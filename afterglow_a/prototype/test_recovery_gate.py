# -*- coding: utf-8 -*-
"""
AfterGlow-A 最小原型 · 恢复资格门禁回归测试
凌翼裁定 2026-11-24 §三 要求覆盖的七条场景

运行：python afterglow_a/prototype/test_recovery_gate.py
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import afcore
from afcore import (Record, RecoveryStore, SchemaError, MATCH_KINDS,
                    canonical_digest, content_digest, HISTORY_OPERATIONS,
                    CONTENT_DIGEST_FIELDS, CONTENT_DIGEST_EXCLUDED)
from afrecover import (classify_match, verify_recovery, check_integrity,
                       check_registration, REGISTRATION_FIELDS)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []


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

PIN = "2026-11-24T00:00:00Z"


def case(cid, name):
    def deco(fn):
        def run():
            try:
                detail = fn()
                RESULTS.append((cid, name, True, detail))
                print("  [PASS] %s %s — %s" % (cid, name, detail))
            except AssertionError as e:
                RESULTS.append((cid, name, False, str(e)))
                print("  [FAIL] %s %s — %s" % (cid, name, e))
            except Exception as e:
                RESULTS.append((cid, name, False, repr(e)))
                print("  [ERR ] %s %s — %s" % (cid, name, e))
                traceback.print_exc()
        run.cid = cid
        return run
    return deco


# ---------------------------------------------------------------- 夹具

def mk_store(record_id="syn-g1", content="港口检修记录", source_ref="utt/g1",
             changed_at=PIN):
    st = RecoveryStore()
    st.insert(Record(
        record_id=record_id, content=content,
        source_kind="user_utterance", source_ref=source_ref,
        participant_id=None, participation_basis="first_person_report",
        basis_ref=source_ref, commitment_state="not_a_commitment",
        revision=1, prev_digest=None,
        changed_at=changed_at, change_authority="synthetic-fixture",
    ))
    return st


def good_registration(**over):
    """正确的独立性声明：独立于写入且早于观察。"""
    reg = {
        "registered_by": "ops-observer",
        "registered_at": "2026-11-20T00:00:00Z",
        "registered_rev": "cd-v1",
        "independent_of_write": "yes",
        "before_exposure": "yes",
    }
    reg.update(over)
    return reg


def tamper_history(store, record_id="syn-g1", which=1):
    """破坏历史中第 which 版的摘要，模拟篡改。"""
    hist = store._history[record_id]
    idx = min(which, len(hist) - 1)
    for k in list(hist[idx].keys()):
        if "digest" in k.lower() and k != "prev_digest":
            hist[idx][k] = "0" * 64
            return True
    return False


# ================================================================ 场景 1
@case("RG-1", "原样保存的历史跨时刻再次校验，摘要一致")
def rg1():
    # 原样恢复：同一份字段、同一 changed_at，跨秒重算
    st = mk_store()
    orig = [r["this_digest"] for r in st.history("syn-g1")]

    time.sleep(1.1)
    rec = st.get("syn-g1")
    again = canonical_digest({k: v for k, v in rec.items()
                              if k != "this_digest"})
    assert again == orig[0], (
        "原样记录重算摘要不一致：%s ≠ %s" % (again[:12], orig[0][:12]))

    # 且链校验仍通过
    ok, msgs = st.verify_chain("syn-g1")
    assert ok, "原样历史链校验失败：%s" % (msgs,)
    return "跨秒重算一致 %s，链校验 True" % again[:12]


# ================================================================ 场景 2
@case("RG-2", "同内容不同时刻重建：record_digest 不同，content_digest 相同")
def rg2():
    st_a = mk_store(changed_at="2026-11-24T00:00:00Z")
    st_b = mk_store(changed_at="2026-11-24T09:99:99Z".replace("99", "30"))

    a = st_a.get("syn-g1")
    b = st_b.get("syn-g1")

    rd_a = canonical_digest({k: v for k, v in a.items() if k != "this_digest"})
    rd_b = canonical_digest({k: v for k, v in b.items() if k != "this_digest"})
    assert rd_a != rd_b, (
        "不同 changed_at 却得到同一 record_digest —— 说明时间戳未进摘要")

    cd_a = content_digest(a)
    cd_b = content_digest(b)
    assert cd_a == cd_b, (
        "同内容却得到不同 content_digest：%s ≠ %s" % (cd_a, cd_b))

    # 内容变了则 content_digest 必变
    c = copy.deepcopy(a)
    c["content"] = "港口检修记录（改）"
    assert content_digest(c) != cd_a, "内容变了但 content_digest 未变"

    return "record_digest 不同(%s/%s)，content_digest 相同(%s)" % (
        rd_a[:8], rd_b[:8], cd_a[:16])


# ================================================================ 场景 3
@case("RG-3", "历史字段或链指针遭破坏，校验明确失败")
def rg3():
    # 3a. 破坏摘要字段
    st = mk_store()
    assert tamper_history(st, "syn-g1", 0), "未能定位摘要字段"
    ok, msgs = st.verify_chain("syn-g1")
    assert ok is False, "破坏摘要后链校验仍 True"
    assert any("摘要不符" in m for m in msgs), "未报摘要不符：%s" % (msgs,)

    # 3b. 破坏 prev_digest 指针（多加一版）
    st2 = mk_store()
    st2.revise("syn-g1", {"content": "第二版"}, reason="t")
    hist = st2._history["syn-g1"]
    hist[-1]["prev_digest"] = "f" * 64
    ok2, msgs2 = st2.verify_chain("syn-g1")
    assert ok2 is False, "破坏链指针后仍 True"
    assert any("prev_digest" in m for m in msgs2), "未报链指针问题：%s" % (msgs2,)

    return "摘要破坏→%d 条问题；指针破坏→%d 条问题" % (len(msgs), len(msgs2))


# ================================================================ 场景 4
@case("RG-4", "取回集合 exact 但链校验失败 ⇒ 资格必须拒绝")
def rg4():
    st = mk_store()
    # 先确认正常情况下 eligible
    rep_ok = verify_recovery(st, "q1", lambda r: True, ["syn-g1"],
                             registration=good_registration())
    assert rep_ok["match_kind"] == "exact", "前置：应为 exact"
    assert rep_ok["integrity_status"] == "verified", \
        "前置：完整性应 verified，实为 %s" % rep_ok["integrity_status"]
    assert rep_ok["recovery_eligible"] is True, \
        "前置：健康库应 eligible，实为 %s (%s)" % (
            rep_ok["recovery_eligible"], rep_ok["ineligible_reasons"])

    # 注入篡改
    assert tamper_history(st, "syn-g1", 0)
    rep = verify_recovery(st, "q1", lambda r: True, ["syn-g1"],
                          registration=good_registration())

    # 集合关系仍是 exact（它是纯集合语义，不该被污染）
    assert rep["match_kind"] == "exact", (
        "串轴：match_kind 被完整性污染成 %r" % (rep["match_kind"],))
    # 但完整性失败
    assert rep["integrity_status"] == "failed", (
        "完整性应为 failed，实为 %s" % rep["integrity_status"])
    assert rep["integrity_detail"], "failure 必须带原因"
    # 资格必须拒绝
    assert rep["recovery_eligible"] is False, "exact + 链失败却仍 eligible"
    assert "integrity_failed" in rep["ineligible_reasons"], \
        "拒绝原因缺 integrity_failed：%s" % (rep["ineligible_reasons"],)

    return "exact 仍 exact，integrity=failed，eligible=False（原因 %s）" % (
        ",".join(rep["ineligible_reasons"]),)


# ================================================================ 场景 5
@case("RG-5", "取回集合 exact 但未执行完整性检查 ⇒ 资格必须拒绝")
def rg5():
    st = mk_store()

    # 5a. 显式关闭检查
    rep = verify_recovery(st, "q2", lambda r: True, ["syn-g1"],
                          registration=good_registration(),
                          run_integrity_check=False)
    assert rep["match_kind"] == "exact"
    assert rep["integrity_status"] == "not_checked", (
        "关闭检查后状态应为 not_checked，实为 %s" % rep["integrity_status"])
    assert rep["recovery_eligible"] is False, \
        "未检查却给了恢复资格（这正是裁定禁止的默认为通过）"
    assert "integrity_not_checked" in rep["ineligible_reasons"], \
        "拒绝原因缺 integrity_not_checked：%s" % (rep["ineligible_reasons"],)

    # 5b. 检查范围为空（取回集为空）
    rep2 = verify_recovery(st, "q3", lambda r: False, [],
                           registration=good_registration())
    assert rep2["integrity_status"] == "not_checked", (
        "空范围应为 not_checked，实为 %s" % rep2["integrity_status"])
    assert rep2["recovery_eligible"] is False, "空范围却给了资格"

    # 5c. 取回非空但期望集为空列表 ⇒ 必须报 no_expected_ids。
    #     这一条 5b 掩盖不住：这里 retrieved 非空，完整性检查会真的跑起来
    #     并 verified，于是「拒绝」只能来自 no_expected_ids 本身。
    rep3 = verify_recovery(st, "q3b", lambda r: True, [],
                           registration=good_registration())
    assert rep3["retrieved_ids"], "前置：取回集应非空"
    assert rep3["integrity_status"] == "verified", (
        "前置：此场景完整性应 verified，实为 %s（否则测不到 no_expected_ids）"
        % rep3["integrity_status"])
    # 空期望集是任何非空集的真子集 ⇒ superset，不是 disjoint。
    # （我第一版把这里写成 disjoint，是自己算错了；set() < {x} 成立。
    #   superset 同样说明「集合关系照算，但资格必须拒」。）
    assert rep3["match_kind"] == "superset", (
        "空期望集对非空取回应为 superset，实为 %r" % (rep3["match_kind"],))
    assert rep3["recovery_eligible"] is False, (
        "期望集为空却给了资格（聚合关系无意义）")
    assert "no_expected_ids" in rep3["ineligible_reasons"], (
        "拒绝原因缺 no_expected_ids：%s" % (rep3["ineligible_reasons"],))

    return "关闭检查⇒拒绝；空范围⇒拒绝；非空取回+空期望⇒no_expected_ids 拒绝"


# ================================================================ 场景 6
@case("RG-6", "链局部自洽但缺外部锚定，不得声称独立真实性")
def rg6():
    st = mk_store()
    rep = verify_recovery(st, "q4", lambda r: True, ["syn-g1"],
                          registration=good_registration())
    # 即使一切通过
    assert rep["recovery_eligible"] is True
    assert rep["integrity_status"] == "verified"

    # 仍不得声称外部锚定 / 科学结果
    #
    # ⚠ 凌翼裁定 2026-11-25 事项 B：
    #   「该限制应在设计文档、状态登记和对外报告中明确，
    #     不得仅用 is_scientific_result=False 代替完整的声明。」
    # ⇒ 本用例原先只断言顶层 trusted_chain_anchor == "not_established"。
    #   那是一个【值】，不是一个【声明】：读者无法从中得知缺的是哪一类证据。
    # ⇒ 现改为断言 scope_declaration 的逐项内容。
    decl = rep["scope_declaration"]
    assert decl["trusted_chain_anchor"] == "NOT_ESTABLISHED", (
        "链通过却声称外部锚定已建立：%r" % (decl["trusted_chain_anchor"],))
    assert decl["trusted_anchor_scope"] == "OUT_OF_SCOPE_FOR_PROTOTYPE", (
        "锚点范围未声明为原型外：%r" % (decl["trusted_anchor_scope"],))
    assert rep["is_scientific_result"] is False, "被标成科学结果"
    assert rep["engineering_only"] is True

    # 工程级限定验收（事项 A）
    assert decl["recovery_gate_status"] == "VERIFIED_ENGINEERING_SYNTHETIC", (
        "工程验收档位未如实登记：%r" % (decl["recovery_gate_status"],))
    assert decl["recovery_gate_evidence"] == "SELF_TEST_REPORTED", (
        "证据来源未登记为自测：%r" % (decl["recovery_gate_evidence"],))

    # 未建立的独立证据必须逐项列出（不得合并为一个 False 了事）
    for k in ("independent_recomputation", "real_history_validation",
              "external_source_attestation"):
        assert decl[k] in ("NOT_ESTABLISHED", "NOT_PERFORMED"), (
            "%s 未如实登记：%r" % (k, decl[k]))

    # 已知边界三条必须都在
    limits = " ".join(decl["known_limits"])
    for token in ("registration_may_be_absent", "eligible_neq_exact",
                  "not_atomic"):
        assert token in limits, "已知边界缺 %s：%s" % (token, limits)

    # 且字段确实存在（不是靠缺省缺失蒙过去）
    for k in ("integrity_status", "integrity_detail", "integrity_scope",
              "recovery_eligible", "expected_ids_registration",
              "scope_declaration"):
        assert k in rep, "报告缺字段 %s" % k

    return "eligible=True，但声明 3 项 NOT_ESTABLISHED + 3 条已知边界"


# ================================================================ 场景 7
@case("RG-7", "检查后被消费前对象被替换 ⇒ 不得沿用旧检查结果")
def rg7():
    st = mk_store()
    tok_before = st.snapshot_token()

    # 用「检查时快照」去做恢复验证，但中途库被改
    st.revise("syn-g1", {"content": "检查之后偷改"}, reason="race")

    rep = verify_recovery(st, "q5", lambda r: True, ["syn-g1"],
                          registration=good_registration(),
                          expected_snapshot=tok_before)

    assert rep["recovery_eligible"] is False, \
        "快照已变却仍给资格（旧结论被沿用了）"
    assert "stale_check" in rep["ineligible_reasons"], \
        "拒绝原因缺 stale_check：%s" % (rep["ineligible_reasons"],)
    assert rep["integrity_status"] == "not_checked", (
        "快照失效后状态应为 not_checked，实为 %s" % rep["integrity_status"])

    # 附带确认：snapshot_token 对写入敏感
    tok_after = st.snapshot_token()
    assert tok_after != tok_before, "写入后快照未变，snapshot_token 失效"

    return "写入后快照变，eligible=False（stale_check）"


# ================================================================ 附加 A/B
@case("RG-8", "登记身份：独立且早于观察才允许 eligible")
def rg8():
    st = mk_store()

    # 8a. 未提供登记 ⇒ 不因缺失而拒绝，但报告 present=False
    rep_none = verify_recovery(st, "q6", lambda r: True, ["syn-g1"])
    assert rep_none["expected_ids_registration"]["present"] is False
    # 缺失登记本身不阻断资格（回归兼容），但必须可见
    assert rep_none["recovery_eligible"] is True, \
        "未提供登记不应阻断（当前契约），实为 %s" % (
            rep_none["ineligible_reasons"],)

    # 8b. 提供了但独立=false ⇒ 必须拒绝
    rep_bad = verify_recovery(
        st, "q7", lambda r: True, ["syn-g1"],
        registration=good_registration(independent_of_write="no"))
    assert rep_bad["recovery_eligible"] is False, \
        "非独立登记却给了资格"
    assert "registration_not_independent" in rep_bad["ineligible_reasons"]

    # 8c. before_exposure=no 同样拒绝
    rep_late = verify_recovery(
        st, "q8", lambda r: True, ["syn-g1"],
        registration=good_registration(before_exposure="no"))
    assert rep_late["recovery_eligible"] is False, \
        "事后回填期望集却给了资格"

    # 8d. 字段缺失 ⇒ 登记无效
    partial = good_registration()
    del partial["registered_rev"]
    chk = check_registration(partial)
    assert chk["independent"] is False, "缺字段仍判独立"
    assert any("缺少登记字段" in p for p in chk["problems"]), \
        "未报缺字段：%s" % (chk["problems"],)

    # 8e. 非法 yes/no 值
    bad_val = check_registration(good_registration(independent_of_write="true"))
    assert bad_val["independent"] is False, "非法 yes/no 值仍判独立"

    return "独立=no/事后=no/缺字段/非法值 四种均被拒"


@case("RG-9", "content_digest 投影：缺字段报错，不按缺省填充")
def rg9():
    st = mk_store()
    rec = st.get("syn-g1")

    # 正常可用
    cd = content_digest(rec)
    assert cd.startswith("cd-v1:"), "缺版本前缀：%r" % cd[:12]

    # 缺字段 ⇒ 报错（而不是算出一个看似合理的值）
    for victim in ("content", "record_id", "source_kind"):
        broken = copy.deepcopy(rec)
        del broken[victim]
        try:
            content_digest(broken)
        except SchemaError as e:
            assert "缺字段" in str(e), "报错信息未说明缺字段：%s" % e
        else:
            raise AssertionError("缺 %s 却算出了摘要（缺省填充被允许）" % victim)

    # 排除字段确实不进入摘要
    leaked = [k for k in CONTENT_DIGEST_EXCLUDED if k in CONTENT_DIGEST_FIELDS]
    assert not leaked, "排除字段混入投影表：%s" % (leaked,)

    for k in ("changed_at", "revision", "prev_digest", "change_authority"):
        assert k not in CONTENT_DIGEST_FIELDS, "%s 不应进入内容摘要" % k

    return "cd-v1 前缀正常；缺 3 类字段均报错；排除表无泄漏"


@case("RG-10", "三种操作语义在闭集内且互不相同")
def rg10():
    assert HISTORY_OPERATIONS == {
        "restore_verbatim", "rebuild_from_content", "migrate_history"}, \
        "操作闭集不符：%s" % (HISTORY_OPERATIONS,)

    # 原样恢复 vs 内容重建：对 record_digest 的影响不同
    st = mk_store(changed_at=PIN)
    a = st.get("syn-g1")
    rd1 = canonical_digest({k: v for k, v in a.items() if k != "this_digest"})

    rebuilt = copy.deepcopy(a)
    rebuilt["changed_at"] = "2026-11-25T12:00:00Z"
    rd2 = canonical_digest({k: v for k, v in rebuilt.items()
                            if k != "this_digest"})

    assert rd1 != rd2, "内容重建后 record_digest 未变（应不同）"
    assert content_digest(a) == content_digest(rebuilt), \
        "内容重建后 content_digest 变了（应相同）"

    return "操作三值齐备；重建改 record_digest 不改 content_digest"


# ---------------------------------------------------------------- main

def main():
    print("=" * 74)
    print("恢复资格门禁回归 · 凌翼裁定 2026-11-24 §三")
    print("=" * 74)
    print()

    groups = [
        ("RG-1  原样保存跨时刻", [rg1]),
        ("RG-2  同内容不同时刻重建", [rg2]),
        ("RG-3  历史/链指针破坏", [rg3]),
        ("RG-4  exact + 链失败", [rg4]),
        ("RG-5  exact + 未检查", [rg5]),
        ("RG-6  链自洽但无外部锚定", [rg6]),
        ("RG-7  检查后对象被替换", [rg7]),
        ("RG-8  登记身份独立性", [rg8]),
        ("RG-9  content_digest 投影", [rg9]),
        ("RG-10 三种操作区分", [rg10]),
    ]

    for gname, fns in groups:
        print("[%s]" % gname)
        for fn in fns:
            fn()
        print()

    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print("=" * 74)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 74)

    out_dir = os.path.join(HERE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "recovery_gate_result.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({
            "baseline": "凌翼裁定 2026-11-24",
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "results": [{"id": a, "name": b, "ok": c, "detail": d}
                        for a, b, c, d in RESULTS],
        }, f, ensure_ascii=False, indent=2)
    print("结果已写入 %s" % out)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
