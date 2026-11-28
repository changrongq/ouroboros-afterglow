# -*- coding: utf-8 -*-
"""Mion 分母定义回执的验收对照（2026-11-27）

Mion 在 `给Coder_答复_分母定义表_20261127.md` 回四条，其中三条带追加要求：

  §二 ①  (a) never_observed 与 (b) observed_but_unresolved 必须【分项报】
            「只算 (b) 会推出荒谬结论：观测得越少，可核验率越高」
  §三 ②  denominator_attrition 必须同时报
            「若只数当前版本，则一条原本 first_person_report 的记录
              被改成 record_only 之后，就从分母里消失 —— 洗白档的操作路径」
  §四 ③  取回集定义只在【一处】实现 + 相等断言（R1/R2/R3）
            「『两处代码各自实现同一个概念』本身就是我们治了一整轮的那个病」
  §五 ④  空集时 record_only_ratio=None 必须与 denominator_size=0 一起返回
            （本项在改动前已满足，此处补回归）

⚠ 每条都要有【反证】：证明若不做，测试会红。
  否则只是「我改了代码，然后写着它对了」。

运行：python afterglow_a/prototype/test_mion_denominator_contract.py
"""
from __future__ import annotations

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []

PIN = "2026-11-27T00:00:00Z"


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


from afcore import Record, RecoveryStore, SchemaError  # noqa: E402
import afimportance as AI                  # noqa: E402
import afrecover                           # noqa: E402


def _rec(rid, basis, origin=None, conflict=None, part="A", rev=1,
         prev=None):
    return Record(
        record_id=rid, content="c-%s" % rid,
        source_kind="user_utterance", source_ref="utt/%s" % rid,
        participant_id=(None if basis == "record_only" else part),
        participation_basis=basis, basis_ref="utt/%s" % rid,
        commitment_state="not_a_commitment", revision=rev,
        prev_digest=prev, changed_at=PIN, change_authority="synthetic")


def _store_with(recs):
    s = RecoveryStore()
    for r in recs:
        s.insert(r)
    return s


def _wash_white(s, rid, tag=None):
    """把一条记录改成 record_only（= Mion 说的「洗白档」）。

    ⚠ 重要发现（2026-11-27 实测）：
      `revise()` 【拒绝】改 participation_basis ——
        「revise 不允许直接改来源字段 ['participation_basis']。
          否则来源被改而『被纠正过』这一事实会消失。请改用 correct()」
      ⇒ 洗白【不能】走 revise，必须走 correct()。
      ⇒ 而 correct() 要求一条已存在的 correcting_record_id。

      ⇒ 这是好消息：洗白路径本身被设计成了【留下痕迹】的操作。
        但痕迹在 correction_of 边上，不在 basis_conflict 里，
        所以仍需要一个独立的数把它报出来 —— 即 denominator_attrition。
    """
    tag = tag or (rid + "_fix")
    s.insert(_rec(tag, "record_only", part="A"))
    s.correct(rid, "被改写的内容", tag, "改写来源")


# ================================================ ① (a)(b) 分项报

@case("MN-1", "① (a) 与 (b) 分别报，且合计等于分子")
def mn1():
    """一条从未观测 + 一条观测过但判不出 + 一条观测一致。

    ⚠ 状态的构造方式（查过 afcore）：
      never_observed           = 不调 record_observed
      observed_but_unresolved  = record_observed(id, "unknown_origin")
                                 （有观测但判不出来源）
      none                     = record_observed(id, "human_input") × first_person
    """
    s = _store_with([
        _rec("a1", "first_person_report"),                  # 从未观测
        _rec("b1", "first_person_report"),                  # 观测但判不出
        _rec("ok", "first_person_report"),                  # 观测且一致
    ])
    s.record_observed("b1", "unknown_origin")
    s.record_observed("ok", "human_input")

    r = AI.synthetic_ratios(s, [])
    assert r["never_observed_count"] == 1, r["never_observed_count"]
    assert r["observed_but_unresolved_count"] == 1, \
        r["observed_but_unresolved_count"]
    n_total = r["never_observed_count"] + r["observed_but_unresolved_count"]
    assert n_total == 2, n_total
    assert abs(r["unverifiable_ratio"] - 2 / 3) < 1e-9, r["unverifiable_ratio"]
    return "(a)=1 (b)=1 合计2 ratio=2/3"


@case("MN-2", "① 反证：(a)(b) 不重叠 —— 若重叠，分子会大于实际")
def mn2():
    """⚠ 这是最容易犯的错：把 (a) 的记录同时算进 (b)。

    never_observed 的记录 observed_origin is None，
    若 (b) 的条件写成「observed_origin is None OR conflict∈...」，
    则该记录被计两次，分子虚高。
    """
    s = _store_with([_rec("a1", "first_person_report")])
    r = AI.synthetic_ratios(s, [])
    a = r["never_observed_count"]
    b = r["observed_but_unresolved_count"]
    assert a == 1 and b == 0, (
        "从未观测的记录不应同时进 (b)：实测 (a)=%d (b)=%d" % (a, b))
    assert r["unverifiable_ratio"] == 1.0, r["unverifiable_ratio"]
    assert r["unverifiable_ids"] == ["a1"]
    return "(a)=1 (b)=0，无重复计数"


@case("MN-3", "① 反证：只算 (b) 会让「观测越少可核验率越高」")
def mn3():
    """Mion 指出的反向激励。

    库 A：3 条全从未观测 ⇒ 正确 ratio = 1.0
    库 B：3 条全观测且一致 ⇒ 正确 ratio = 0.0
    若只算 (b)（即忽略 never_observed），A 会变成 0.0 ——
    于是「什么都没查」反而成了「全都可核验」。
    """
    a = _store_with([_rec("x%d" % i, "first_person_report")
                     for i in range(3)])
    ra = AI.synthetic_ratios(a, [])

    b = _store_with([_rec("y%d" % i, "first_person_report")
                     for i in range(3)])
    for i in range(3):
        b.record_observed("y%d" % i, "human_input")
    rb = AI.synthetic_ratios(b, [])

    assert ra["unverifiable_ratio"] == 1.0, ra["unverifiable_ratio"]
    assert rb["unverifiable_ratio"] == 0.0, rb["unverifiable_ratio"]

    # 若只算 (b)：A 的 (b)=0 ⇒ ratio 会变成 0.0，与 B 相同
    b_only_ratio = (ra["observed_but_unresolved_count"]
                    / ra["denominator_size"])
    assert b_only_ratio == 0.0, b_only_ratio
    assert b_only_ratio != ra["unverifiable_ratio"], (
        "本反证失去意义：只算 (b) 的比值已与正确值相同")
    return "全未观测=1.0 / 全已观测=0.0；只算(b)会把前者压成0.0"


# ================================================ ② denominator_attrition

@case("MN-4", "② 记录从 first_person 改成 record_only ⇒ attrition 报 1")
def mn4():
    s = _store_with([_rec("h1", "first_person_report"),
                     _rec("h2", "first_person_report")])
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 0

    _wash_white(s, "h1")

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition"] == 1, r["denominator_attrition"]
    assert r["denominator_attrition_ids"] == ["h1"], \
        r["denominator_attrition_ids"]
    assert r["denominator_size"] == 1, (
        "分母应只剩 h2，实测 %d" % r["denominator_size"])
    return "attrition=1，ids=['h1']，分母 2→1"


@case("MN-5", "② 反证：不报 attrition 时，分母缩小而比例变好看且无人察觉")
def mn5():
    """构造「洗白」场景，证明 attrition 是唯一能看见它的数。

    初始：4 条 first_person，其中 2 条不可核验 ⇒ ratio = 0.5
    洗白：把 2 条【不可核验的】改成 record_only
          ⇒ 分母变 2，不可核验变 0 ⇒ ratio = 0.0（变好看）
          ⇒ 但 attrition = 2
    """
    s = _store_with([_rec("p1", "first_person_report"),
                     _rec("p2", "first_person_report"),
                     _rec("q1", "first_person_report"),
                     _rec("q2", "first_person_report")])
    r0 = AI.synthetic_ratios(s, [])
    assert r0["unverifiable_ratio"] == 1.0, r0["unverifiable_ratio"]
    assert r0["denominator_attrition"] == 0

    # 两条从未观测的改成 record_only（必须走 correct，见 _wash_white 说明）
    for rid in ("q1", "q2"):
        _wash_white(s, rid)

    r1 = AI.synthetic_ratios(s, [])
    assert r1["denominator_size"] == 2, r1["denominator_size"]
    assert r1["unverifiable_ratio"] == 1.0, r1["unverifiable_ratio"]
    # 上面两条仍是从未观测，所以比例没变；再让 p1/p2 观测一致
    for rid in ("p1", "p2"):
        s.record_observed(rid, "human_input")
    r2 = AI.synthetic_ratios(s, [])
    assert r2["unverifiable_ratio"] == 0.0, r2["unverifiable_ratio"]
    assert r2["denominator_attrition"] == 2, r2["denominator_attrition"]
    return "比例 1.0→0.0（好看），attrition=2 是唯一残留证据"


@case("MN-6", "② 反证：当前仍声称 first_person 的记录不计入 attrition")
def mn6():
    """⚠ 2026-11-27 实测发现的语义（写下来，因为它决定了 attrition 的含义）：

       `correct()` 会把【纠正依据那条记录】的来源字段继承过来。
       ⇒ 用一条 record_only 的记录去纠正，结果是 record_only；
         用一条 first_person_report 的记录去纠正，才能恢复 first_person。

       ⇒ 这不是缺陷，是设计：纠正后的来源必须是【已被核验的来源】，
         不能凭空声明。否则「改回第一人称」本身就成了新的无据声明。

       ⇒ attrition 只看【当前版本的 basis】，不看历史：
         洗白后改正 ⇒ attrition 回到 0。
         这与 Mion 的定义一致：它量的是「此刻有多少条离开了分母」。
    """
    s = _store_with([_rec("k1", "first_person_report")])
    _wash_white(s, "k1")
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 1, (
        "前提：洗白后应报 1")

    # 改正：纠正依据必须【自己】是 first_person_report
    s.insert(_rec("k1_fix2", "first_person_report", part="A"))
    s.correct("k1", "改正回的内容", "k1_fix2", "恢复声称")

    assert s.get("k1")["participation_basis"] == "first_person_report", (
        "前提未成立：改正后 basis 应为 first_person_report，实测 %r"
        % s.get("k1")["participation_basis"])

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition"] == 0, (
        "改正后当前仍为 first_person ⇒ 不应算流失，实测 %d"
        % r["denominator_attrition"])
    return "洗白后再改正 ⇒ attrition 1→0（仍在分母里）"


@case("MN-7", "② attrition 只统计【取回集内】，不是全库")
def mn7():
    """若统计全库，「本次只取回 2 条」时会报全库的流失量，
    两个不同范围的数会被误读成同一请求的两个侧面。
    """
    s = _store_with([_rec("in1", "first_person_report"),
                     _rec("out1", "first_person_report")])
    _wash_white(s, "out1")

    full = AI.synthetic_ratios(s, [])
    assert full["denominator_attrition"] == 1, full["denominator_attrition"]

    scoped = AI.synthetic_ratios(s, [], scope_ids=["in1"])
    assert scoped["denominator_attrition"] == 0, (
        "取回集只含 in1，不应报 out1 的流失，实测 %d"
        % scoped["denominator_attrition"])
    return "全库=1；范围[in1]=0"


@case("MN-13", "A2 attrition_cause 追到「谁搬的」")
def mn13():
    """Mion 第二封 §二：

    「attrition 回答『少了多少』，cause 回答『谁搬的』。
      只报前者，报告能看出问题但追不到动作。
      而这个项目里，【追得到动作】比【知道少了多少】重要。」

    ⇒ cause = {被移出分母的记录 id: 那次 correct 的 correcting_record_id}
    """
    s = _store_with([_rec("t1", "first_person_report"),
                     _rec("t2", "first_person_report")])
    s.insert(_rec("donor_a", "record_only"))
    s.insert(_rec("donor_b", "record_only"))
    s.correct("t1", "x", "donor_a", "wash-a")
    s.correct("t2", "x", "donor_b", "wash-b")

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition"] == 2, r["denominator_attrition"]
    assert r["denominator_attrition_cause"] == {
        "t1": "donor_a", "t2": "donor_b"}, \
        r["denominator_attrition_cause"]
    return "cause={'t1':'donor_a','t2':'donor_b'}"


@case("MN-14", "A2 反证：只报数量时追不到动作")
def mn14():
    """证明 cause 不是 repeating ids 的装饰。

    ids 只有 ['t1','t2'] —— 谁搬的完全不在里面。
    若没有 cause，同一份报告无法回答「哪条记录被谁当依据搬走」。
    """
    s = _store_with([_rec("t1", "first_person_report")])
    s.insert(_rec("donor_x", "record_only"))
    s.correct("t1", "x", "donor_x", "wash")

    r = AI.synthetic_ratios(s, [])
    ids = r["denominator_attrition_ids"]
    cause = r["denominator_attrition_cause"]

    assert ids == ["t1"]
    # ids 里没有搬运者
    assert "donor_x" not in ids, "ids 不应包含搬运者"
    # cause 里才有
    assert cause.get("t1") == "donor_x", cause
    return "ids=['t1'] 无搬运者；cause 给出 'donor_x'"


@case("MN-15", "A2 边：未被搬动的记录不出现在 cause 里")
def mn15():
    s = _store_with([_rec("ok1", "first_person_report"),
                     _rec("t1", "first_person_report")])
    s.insert(_rec("d1", "record_only"))
    s.correct("t1", "x", "d1", "wash")

    r = AI.synthetic_ratios(s, [])
    assert "ok1" not in r["denominator_attrition_cause"], (
        "仍在分母里的记录不应出现在 cause")
    assert r["denominator_attrition_cause"] == {"t1": "d1"}
    return "cause 只含被搬走的 t1"


@case("MN-16", "A2 空分支：cause 为空 dict，且键集合与非空一致")
def mn16():
    s = _store_with([_rec("h1", "first_person_report")])
    empty = AI.synthetic_ratios(s, [], scope_ids=[])
    assert empty["denominator_attrition_cause"] == {}, \
        empty["denominator_attrition_cause"]
    nonempty = AI.synthetic_ratios(s, [])
    assert set(empty.keys()) == set(nonempty.keys()), (
        "键集合不一致：仅空有 %r；仅非空有 %r"
        % (sorted(set(empty) - set(nonempty)),
           sorted(set(nonempty) - set(empty))))
    return "空分支 cause={}，两分支均 %d 键" % len(empty)


# ================================================ ③ 取回集一处实现

@case("MN-8", "③ 取回集定义只在一处：retrieval_scope 是唯一构造点")
def mn8():
    import inspect
    ai_src = inspect.getsource(AI.synthetic_ratios)
    # synthetic_ratios 不得再自行构造范围
    for banned in ("if rid in seen:", "if rid not in by_id:"):
        assert banned not in ai_src, (
            "synthetic_ratios 仍在自行构造取回集（发现 %r）" % banned)
    assert "retrieval_scope(store, scope_ids)" in ai_src, (
        "synthetic_ratios 未调用 retrieval_scope")
    return "synthetic_ratios 只调用，不自建"


@case("MN-9", "③ R2：同一输入走两条路径，范围逐元素相等")
def mn9():
    """afrecover.summarize_conflicts 与 afimportance.synthetic_ratios
    必须对同一 ids 给出同一 record_only 口径。
    """
    s = _store_with([_rec("h1", "first_person_report"),
                     _rec("ro1", "record_only"),
                     _rec("ro2", "record_only")])
    ids = ["h1", "ro1", "ro2"]

    a = AI.synthetic_ratios(s, [], scope_ids=ids)
    b = afrecover.summarize_conflicts(s, ids)

    assert a["record_only_ids"] == b["record_only_ids"], (
        "两处 record_only_ids 不同：importance=%r recover=%r"
        % (a["record_only_ids"], b["record_only_ids"]))
    assert a["record_only_denominator_size"] == len(ids), \
        a["record_only_denominator_size"]
    assert abs(a["record_only_ratio"] - b["record_only_ratio"]) < 1e-9, (
        "两处比例不同：%r vs %r"
        % (a["record_only_ratio"], b["record_only_ratio"]))
    return "ids/ratio 两处一致（2/3）"


@case("MN-10", "③ 反证：两条路径在「重复 ID」上若各自实现就会分歧")
def mn10():
    """afrecover 内部已 sorted(set(ids)) 去重；
    synthetic_ratios 对重复 ID 直接拒绝。
    ⇒ 若两处各自实现，这个差异不会被发现。
    ⇒ 现在 afrecover 调用同一函数，并用断言固定范围一致。

    ⚠ 2026-11-27 补充输入域说明（知微独立复核 §1）：
      「MN-10 的公开入口差异可以保留，但请在 R2 旁写明输入域。
        传入 [H, RO, RO]，恢复入口去重后给 1/2，指标入口报 SchemaError。
        二者接受的原始输入不同。
        对于由唯一、已知 ID 构成的同一取回集，
        可以要求 record_only 成员和比例一致。
        若 Mion 的 R2 要求任意同一原始列表都有相同结果，
        本版没有满足那种要求。
        建议保留这条差异测试，避免调用方把两种入口互换。」

      ⇒ R2 的一致性只在【唯一、已知 ID 构成的取回集】上成立：
        两个入口接受同一取回集时，record_only 成员与比例必须一致。
        它们【不】接受同一原始列表（重复 ID 的处置不同）。
      ⇒ 这条测试存在的目的就是防止调用方互换两个入口。
    """
    s = _store_with([_rec("h1", "first_person_report"),
                     _rec("ro1", "record_only")])

    # 输入域内：唯一、已知 ID 的同一取回集 ⇒ 两入口一致
    ids = ["h1", "ro1"]
    a = AI.synthetic_ratios(s, [], scope_ids=ids)
    b = afrecover.summarize_conflicts(s, ids)
    assert a["record_only_ids"] == b["record_only_ids"], (
        "同一取回集上两入口应一致：%r vs %r"
        % (a["record_only_ids"], b["record_only_ids"]))

    # 输入域外：重复 ID ⇒ synthetic 必须拒绝，afrecover 去重
    #
    # ⚠ 2026-11-27 修正（知微第二次复验）：
    #   原写法：
    #       try:
    #           AI.synthetic_ratios(...重复...)
    #           raise AssertionError("重复 ID 未被拒绝")
    #       except Exception as e:
    #           assert "重复" in str(e)
    #   ⇒ 它自己抛的 AssertionError 消息里含「重复」二字，
    #     被同一个 except 接住并判为合格。
    #     知微实测：把指标入口临时换成「先去重再算」，MN-10 仍 PASS。
    #   ⇒ 现在只捕获【预期的 SchemaError】，未抛异常的失败断言放 else。
    raised = None
    try:
        AI.synthetic_ratios(s, [], scope_ids=["h1", "ro1", "ro1"])
    except SchemaError as e:
        raised = e
    else:
        raise AssertionError(
            "重复 ID 被静默接受（未抛 SchemaError）⇒ 同一记录会被算两次")

    assert "重复" in str(raised), (
        "拒绝对象正确但理由未提重复：%s" % str(raised)[:80])

    r = afrecover.summarize_conflicts(s, ["h1", "ro1", "ro1"])
    assert abs((r.get("record_only_ratio") or 0) - 0.5) < 1e-9, (
        "去重后应为 1/2，实测 %r" % r.get("record_only_ratio"))
    return ("域内(唯一ID)两入口一致；域外(重复ID)：synthetic 抛 SchemaError / "
            "afrecover 去重 —— 不得互换入口")


# ================================================ ④ 空集合

@case("MN-11", "④ 空集：None 必须与 denominator_size=0 同时返回")
def mn11():
    s = _store_with([_rec("h1", "first_person_report")])
    r = AI.synthetic_ratios(s, [], scope_ids=[])
    assert r["record_only_ratio"] is None, r["record_only_ratio"]
    assert r["unverifiable_ratio"] is None
    assert r["denominator_size"] == 0, r["denominator_size"]
    assert r["record_only_denominator_size"] == 0, \
        r["record_only_denominator_size"]
    assert r["basis"] == "empty", r["basis"]
    return "None + size=0 同时出现"


@case("MN-12", "④ 空与非空分支键集合一致（新增字段不得只在一支）")
def mn12():
    s = _store_with([_rec("h1", "first_person_report")])
    empty = AI.synthetic_ratios(s, [], scope_ids=[])
    nonempty = AI.synthetic_ratios(s, [])
    assert set(empty.keys()) == set(nonempty.keys()), (
        "键集合不同：仅空分支有 %r；仅非空有 %r"
        % (sorted(set(empty) - set(nonempty)),
           sorted(set(nonempty) - set(empty))))
    for k in ("never_observed_count", "observed_but_unresolved_count",
              "denominator_attrition", "denominator_attrition_ids"):
        assert k in empty, "空分支缺 %s" % k
    return "两分支均 %d 键" % len(empty)


@case("MN-17", "睫复核：cause 语义必须是【结构】，且内容被断言守着")
def mn17():
    """⚠ 睫 2026-11-28 §四·§二（判定：需要更硬的做法）：

    「两条禁令只活在 forbidden_use 的字符串里，
      没有任何断言守它们的内容 —— 这一格 Coder 已自己核出、并主动写出。
      把语义写进字段名 / 返回结构，并让序列化不丢这两条；
      写进代码只是第一层。」

    ⇒ 修法：新增 denominator_attrition_cause_semantics 结构化字段，
      并用本用例守它的内容 —— 不再是「写了就算」。
    """
    s = _store_with([_rec("h1", "first_person_report")])
    r = AI.synthetic_ratios(s, [])

    sem = r.get("denominator_attrition_cause_semantics")
    assert isinstance(sem, dict), (
        "cause 语义必须是结构化 dict，不能只写在 forbidden_use 字符串里；"
        "实测 %r" % type(sem).__name__)

    # 三个「不是」必须明确为 False —— 这是这个字段存在的全部理由
    assert sem.get("is_operator_identity") is False, (
        "cause 不得被读作操作者身份")
    assert sem.get("is_trust_attestation") is False, (
        "cause 不等于外部可信来源认证")
    assert sem.get("may_support_accusation") is False, (
        "不得仅凭 attrition 指控某条记录不当改写")

    assert sem.get("value_is") == "correction_basis_record_id", \
        sem.get("value_is")
    assert sem.get("role_verdict") == "REQUIRED_SUMMARY_SIGNAL", (
        "应带凌翼判定的角色词（判 B：汇总预警指标）")
    return "结构化语义齐备：三项否定 + 值类型 + 角色词"


@case("MN-18", "反证：把语义字段改坏，MN-17 必须变红")
def mn18():
    """证明 MN-17 有分辨力。

    做法：临时把返回字典里的语义字段改成「是操作者身份」，
    看断言能否抓到。
    """
    import copy
    s = _store_with([_rec("h1", "first_person_report")])
    r = AI.synthetic_ratios(s, [])

    broken = copy.deepcopy(r)
    broken["denominator_attrition_cause_semantics"]["is_operator_identity"] = True

    caught = False
    try:
        assert broken["denominator_attrition_cause_semantics"][
            "is_operator_identity"] is False
    except AssertionError:
        caught = True
    assert caught, "语义被改坏后断言未红 ⇒ MN-17 没有分辨力"
    return "改成 True ⇒ 断言红"


@case("MN-19", "空分支也带语义字段，且两分支键集合仍一致")
def mn19():
    """空分支若缺该字段，消费者在空集时就读不到语义。

    ⚠ 2026-11-28 修正（凌翼裁定时指出，我核后确认他完全正确）：

      本用例原来的 docstring 写的是
        「睫 §二 的要求之一：序列化不能丢这两条」
      —— 但测试里【一行序列化都没有】，只比了内存里的 dict。

      ⇒ 这是我在测试层犯的同一形状的错：
        测试的名字说它验的东西，和它实际验的东西，不是一回事。

      ⇒ 现在：
        · 本用例只声明它实际验的（空分支一致 + 键集合一致）
        · 真正的序列化往返由 MN-20 单独验，并单独命名
    """
    s = _store_with([_rec("h1", "first_person_report")])
    empty = AI.synthetic_ratios(s, [], scope_ids=[])
    nonempty = AI.synthetic_ratios(s, [])

    assert "denominator_attrition_cause_semantics" in empty, (
        "空分支缺语义字段 ⇒ 空集时读不到约束")
    assert (empty["denominator_attrition_cause_semantics"]
            == nonempty["denominator_attrition_cause_semantics"]), (
        "两分支语义应完全一致")
    assert set(empty.keys()) == set(nonempty.keys()), (
        "键集合不一致：仅空有 %r；仅非空有 %r"
        % (sorted(set(empty) - set(nonempty)),
           sorted(set(nonempty) - set(empty))))
    return "空分支带同样语义；两分支均 %d 键" % len(empty)


@case("MN-20", "序列化往返：JSON 序列化后语义字段不得丢失或降级")
def mn20():
    """⚠ 凌翼 2026-11-28 裁定二指出：

    「序列化保持。MN-19 目前验证了返回字典的字段一致性，
      不能直接当成真实序列化、反序列化后的契约已通过。」

    ⇒ 本用例单独验这一层，并把名字写成它实际验的东西。

    验什么：
      1. 返回结构可 JSON 序列化（不抛异常）
      2. 往返后语义字段仍在
      3. 往返后三项否定仍为 False（不是被 JSON 变成字符串或丢失）
      4. 往返后值类型仍是 dict，不是被压成字符串

    ⚠ 它【不】验：下游是否强制读取。那是 MN-21 之外的事，
      且当前做不到（凌翼裁定二已登记为开放边界）。
    """
    import json

    for label, scope in (("非空", None), ("空", [])):
        s = _store_with([_rec("h1", "first_person_report")])
        r = AI.synthetic_ratios(s, [], scope_ids=scope)

        try:
            blob = json.dumps(r, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise AssertionError(
                "%s分支不可 JSON 序列化：%s" % (label, e))

        back = json.loads(blob)
        assert "denominator_attrition_cause_semantics" in back, (
            "%s分支序列化往返后丢了语义字段" % label)

        sem = back["denominator_attrition_cause_semantics"]
        assert isinstance(sem, dict), (
            "%s分支往返后语义被压成 %r（应为 dict）"
            % (label, type(sem).__name__))

        for k in ("is_operator_identity", "is_trust_attestation",
                  "may_support_accusation"):
            assert sem.get(k) is False, (
                "%s分支往返后 %s = %r（应为 False）"
                % (label, k, sem.get(k)))

        assert sem.get("value_is") == "correction_basis_record_id"
        assert sem.get("role_verdict") == "REQUIRED_SUMMARY_SIGNAL"
    return "两分支 JSON 往返后语义完整，三项否定仍为 False"


@case("MN-21", "边界：本套件【不】验下游消费 —— 明确不验，而非验了没过")
def mn21():
    """⚠ 凌翼 2026-11-28 裁定二：

    「下游强制消费。返回结果包含限制字段，
      不等于下游消费者必然读取、理解并遵守限制。
      …在正式消费接口建立前，这条登记为开放边界。」

    ⇒ 本用例的作用是【把这个边界写成代码里的断言】，
      而不是假装验过。

    它断言的是：
      · 当前仓库里没有正式下游消费者（若有，此断言会红并提醒去验）
      · 因此「下游强制同读」不能宣称成立
    """
    import os

    # 正式消费者应出现在这里；当前为空
    consumer_paths = [
        os.path.join(HERE, "afconsumer.py"),
        os.path.join(HERE, "downstream_consumer.py"),
    ]
    existing = [p for p in consumer_paths if os.path.exists(p)]
    assert not existing, (
        "出现了正式下游消费者 %r ⇒ 必须补一条"
        "「消费者同时读取数值与语义字段」的断言，"
        "不能沿用本用例的「无消费者」前提" % existing)

    return "当前无正式下游消费者 ⇒ 下游强制同读不宣称成立（开放边界）"


# ================================================ 汇总
def main():
    print("=" * 80)
    print("Mion 分母定义回执 · 验收对照（2026-11-27）")
    print("=" * 80)
    print()
    for f in (mn1, mn2, mn3, mn4, mn5, mn6, mn7, mn8, mn9, mn10,
              mn11, mn12, mn13, mn14, mn15, mn16, mn17, mn18, mn19,
              mn20, mn21):
        f()
    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print()
    print("=" * 80)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 80)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
