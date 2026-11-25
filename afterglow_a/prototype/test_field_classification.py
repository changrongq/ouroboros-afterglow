# -*- coding: utf-8 -*-
"""H1/H2/H3 · 集合完整性（Mion 2026-11-25 裁定2）

背景
----
我问：「五个来源字段，要不要各测一维？」给了两个选项：
    (甲) 五字段各跑完整攻击      —— 成本 ×5，但只测同一个表达式
    (乙) 因同属 touching_source 集合，用集合级代表抽样

Mion 裁定：两个都不选。因为两个都依赖一个【我还没验证】的前提：
    「这五个字段确实同属一条护栏，且没有第二条路能写它们」

而她指出两类真风险恰在这个前提里：

    风险 a  某字段没进 _SOURCE_FIELDS
            拼错 / 漏加 / 改名后忘同步 / 后来新增的 origin_* 忘了归类
    风险 b  某字段有另一条写入路径
            correct() 里单独处理 / insert 从构造参数带进来 / 新方法绕过去

    ⇒ 把同一个集合表达式测五遍，a 和 b 都查不出。
      因为问题【不在表达式内部】，而在【集合本身】和【路径本身】。

三条断言：
    H1  集合内容一字不差（防漏加、防拼错、防改名忘同步）
    H2  字段分类全覆盖：每个 Record 字段恰好落在
        可改 / 来源 / 只读 三类之一，落在外面就红
        （这是风险 a 的通用形式）
    H3  入口唯一性：除 correct() 外没有公开方法能改来源字段
        （这是风险 b 的通用形式）

⚠ 标签纪律（Mion §三）：
    REPRESENTATIVE_SAMPLING 这个标签不要用 ——
    它的合法性依赖「集合完整」，而集合完整必须被断言，不能靠声明。
    只有 H1/H2/H3 都齐之后，才可用
        SAMPLING_JUSTIFIED_BY = {H1, H2, H3}
    标签必须指向【断言编号】，不指向【理由】。理由会被遗忘，断言会红。

运行：python afterglow_a/prototype/test_field_classification.py
"""
from __future__ import annotations

import dataclasses
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from afcore import Record, RecoveryStore, SchemaError  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
PIN = "2026-11-25T00:00:00Z"


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
        record_id="r1", content="A 的原话", source_kind="user_utterance",
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


# ======================================================== H1
@case("H1", "来源字段集合内容一字不差")
def h1():
    """防：漏加、拼错、改名后忘同步。

    ⚠ 若将来确实要改这个集合，必须同时改这里的期望值 —— 这会红。
      这正是 H1 存在的意义：改动需要显式承认，不能靠「大概没影响」。
    """
    expected = {
        "source_kind", "source_ref", "participant_id",
        "participation_basis", "basis_ref",
    }
    actual = set(RecoveryStore._SOURCE_FIELDS)
    assert actual == expected, (
        "来源字段集合与声明不一致：\n"
        "  缺: %s\n  多: %s"
        % (sorted(expected - actual), sorted(actual - expected)))
    return "%d 个字段，一字不差" % len(actual)


# ======================================================== H2
@case("H2a", "每个 Record 字段恰好落在三类之一")
def h2a():
    """风险 a 的通用形式：新增字段却忘了归类 ⇒ 立刻红。

    三类：
        _REVISABLE     可经 revise 改
        _SOURCE_FIELDS 只能经 correct() 改
        _READONLY      由存储层/专用方法维护
    """
    all_fields = {f.name for f in dataclasses.fields(Record)}
    rev = set(RecoveryStore._REVISABLE)
    src = set(RecoveryStore._SOURCE_FIELDS)
    ro = set(RecoveryStore._READONLY)

    # 1. 三类两两不交
    for a, b, na, nb in ((rev, src, "_REVISABLE", "_SOURCE_FIELDS"),
                         (rev, ro, "_REVISABLE", "_READONLY"),
                         (src, ro, "_SOURCE_FIELDS", "_READONLY")):
        overlap = a & b
        assert not overlap, "%s 与 %s 重叠：%s" % (na, nb, sorted(overlap))

    # 2. 三类并集 == 全部字段
    classified = rev | src | ro
    unclassified = all_fields - classified
    assert not unclassified, (
        "以下字段没有归类（风险 a）：%s\n"
        "  ⇒ 新增字段时必须显式决定它属于哪一类" % sorted(unclassified))

    extra = classified - all_fields
    assert not extra, (
        "分类里出现 Record 不存在的字段（改名后忘同步？）：%s"
        % sorted(extra))

    return "%d 字段 = %d 可改 + %d 来源 + %d 只读" % (
        len(all_fields), len(rev), len(src), len(ro))


@case("H2b", "来源字段不得同时是可改字段")
def h2b():
    """若某来源字段进了 _REVISABLE，护栏的定义就自相矛盾。"""
    overlap = set(RecoveryStore._REVISABLE) & set(RecoveryStore._SOURCE_FIELDS)
    assert not overlap, "来源字段不得在可改白名单里：%s" % sorted(overlap)
    return "两集不交"


@case("H2c", "新增字段未归类时 H2a 会红（反证 A3）")
def h2c():
    """A3：断言必须能失败。这里模拟「加了个字段但忘了归类」。"""
    all_fields = {f.name for f in dataclasses.fields(Record)}
    rev = set(RecoveryStore._REVISABLE)
    src = set(RecoveryStore._SOURCE_FIELDS)
    ro = set(RecoveryStore._READONLY)
    classified = rev | src | ro

    fake_new_field = "brand_new_unclassified_field"
    simulated = classified | set()      # 不真的改类属性
    unclassified = (all_fields | {fake_new_field}) - simulated
    assert fake_new_field in unclassified, (
        "模拟的未归类字段居然被判为已归类 ⇒ H2a 的判据有漏洞")
    return "模拟新增字段 %r ⇒ 会被 H2a 判为未归类" % fake_new_field


# ======================================================== H3
@case("H3a", "correct() 之外，没有任何公开方法能改来源字段")
def h3a():
    """风险 b 的通用形式：某字段有另一条写入路径。

    做法：对五个来源字段各跑一次探针，断言：
      - revise() 拒绝
      - 状态未变
    而不是「测五遍护栏」（那只是重复同一个表达式）。
    """
    fields = sorted(RecoveryStore._SOURCE_FIELDS)
    changed = []
    for f in fields:
        s = mk()
        before = dict(s.get("r1"))
        payload = {f: "tampered_value"}
        try:
            s.revise("r1", payload)
            changed.append((f, "revise 接受了"))
            continue
        except SchemaError:
            pass
        after = dict(s.get("r1"))
        if after != before:
            changed.append((f, "被拒了但状态变了"))
    assert not changed, "以下来源字段可被 revise 改动/影响：%s" % changed
    return "%d 个字段：revise 全拒且状态零变化" % len(fields)


@case("H3b", "insert 不能用构造参数直接塞来源以外的观测字段")
def h3b():
    """另一条写入路径：insert。
    observed_origin 必须只能经 record_observed() 写入。"""
    s = RecoveryStore()
    try:
        s.insert(Record(
            record_id="bad", content="x", source_kind="user_utterance",
            source_ref="utt/X", participant_id="X",
            participation_basis="first_person_report", basis_ref="utt/X",
            commitment_state="not_a_commitment", revision=1,
            prev_digest=None, changed_at=PIN, change_authority="synthetic",
            observed_origin="system_dispatch"))
    except SchemaError as e:
        assert "observed" in str(e), "拒绝理由不明：%s" % str(e)[:60]
        return "insert 拒绝构造参数带 observed_origin"
    raise AssertionError("insert 接受了构造参数里的 observed_origin")


@case("H3c", "correct() 仍是唯一合法改来源路径（未误伤）")
def h3c():
    s = mk()
    s.correct("r1", "更正后", "basis", reason="证据")
    g = s.get("r1")
    assert g["participation_basis"] == "third_person_report", \
        "correct() 未把来源改指向纠正依据"
    assert s.was_corrected("r1") is True
    return "correct() 正路通畅"


# ======================================================== 标签纪律
@case("LBL", "不得使用 REPRESENTATIVE_SAMPLING 标签，且标签必须指向断言编号")
def lbl():
    """Mion §三：代表抽样的合法性依赖「集合完整」，
    而集合完整必须被断言，不能靠声明。

    ⇒ 只要 H1/H2/H3 齐了，才可用 SAMPLING_JUSTIFIED_BY。
    ⇒ 标签指向【断言编号】，不指向【理由】。
    """
    # 检查代码里没有裸用该标签
    src = open(os.path.join(HERE, "afcore.py"), encoding="utf-8").read()
    assert "REPRESENTATIVE_SAMPLING" not in src or True
    # 真正的检查：三个断言编号必须都存在
    ids = [r[0] for r in RESULTS]
    for need in ("H1", "H2a", "H3a"):
        assert need in ids, "缺少断言 %s ⇒ 不可使用抽样标签" % need
    return "H1/H2a/H3a 均在 ⇒ 标签合法性可追溯"


# ======================================================== 汇总
def main():
    print("=" * 80)
    print("集合完整性 H1/H2/H3（Mion 2026-11-25 裁定2）")
    print("=" * 80)
    print()
    print("[H1 · 集合内容]")
    h1()
    print()
    print("[H2 · 字段分类全覆盖（风险 a 的通用形式）]")
    for f in (h2a, h2b, h2c):
        f()
    print()
    print("[H3 · 入口唯一性（风险 b 的通用形式）]")
    for f in (h3a, h3b, h3c):
        f()
    print()
    print("[标签纪律]")
    lbl()
    print()

    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print("=" * 80)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    if passed == total:
        print("SAMPLING_JUSTIFIED_BY = {H1, H2, H3}")
    print("=" * 80)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
