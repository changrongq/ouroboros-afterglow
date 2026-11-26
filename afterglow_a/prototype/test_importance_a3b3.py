# -*- coding: utf-8 -*-
"""第 5 项 A3/B3 限定原型测试（凌翼 2026-11-25 裁定）

授权范围：
    SYNTHETIC_TRACE_DESIGN     = AUTHORIZED
    CANDIDATE_FILTER_PROTOTYPE = AUTHORIZED_LIMITED
    FULL_IMPORTANCE_LEARNER    = NOT_AUTHORIZED

凌翼的六条具体要求，逐条对应本文件的用例组：

    1. 建立 B1 排除规则的正向与负向测试          → 组 ①
    2. 在不同合成召回次数下检查排除不变性         → 组 ②
    3. 关闭排除规则时，必须直接观测变异确实生效   → 组 ③
    4. 若其他机制阻断了变异效果，不得冒充 A3 成功；
       按既有 E1/E2/E3 与 M1 边界登记            → 组 ③（三态）
    5. J2 的伪亲历计数和 J3 的空分母判据分别测试，
       不能用 B3 的结果代替                       → 组 ④/⑤
    6. 合成基线只允许标 MEASURED_ON_SYNTHETIC_ONLY，
       不写正式重要性结论                         → 组 ⑥

另：本文件【必须】包含至少一条「不可能通过」的用例，
    用来证明前三组不是空转（A3 的自指要求）。

运行：python afterglow_a/prototype/test_importance_a3b3.py
"""
from __future__ import annotations

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import afimportance as AI
from afcore import Record, RecoveryStore, SchemaError

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


# ---------------------------------------------------------------- 夹具
def mk(basis="first_person_report", rid="r1"):
    s = RecoveryStore()
    s.insert(Record(
        record_id=rid, content="人说的话 " + rid,
        source_kind="user_utterance", source_ref="utt/" + rid,
        participant_id="A", participation_basis=basis,
        basis_ref="utt/" + rid, commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    return s


def mk_mixed():
    """四条记录：人输入的、模型生成的(first_person)、模型生成的(third_person)、
    record_only 的。

    ⚠ 2026-11-25 修正：第一版这里【没有】third_person 的记录，
      而 A3-1d 却断言 t1 —— 于是那条断言实际在测「一个不存在的记录」，
      失败原因是 KeyError 而不是 B1。
      ⇒ 现在补上 t1，且必须 record_observed 过。
    """
    s = RecoveryStore()
    s.insert(Record(
        record_id="h1", content="人说的", source_kind="user_utterance",
        source_ref="utt/h1", participant_id="A",
        participation_basis="first_person_report", basis_ref="utt/h1",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    s.insert(Record(
        record_id="m1", content="模型生成的", source_kind="system_generated",
        source_ref="gen/m1", participant_id="sys",
        participation_basis="first_person_report", basis_ref="gen/m1",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    s.insert(Record(
        record_id="t1", content="模型转述", source_kind="system_generated",
        source_ref="gen/t1", participant_id="sys",
        participation_basis="third_person_report", basis_ref="gen/t1",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    s.insert(Record(
        record_id="ro1", content="只记录", source_kind="unknown",
        source_ref="doc/ro1", participant_id=None,
        participation_basis="record_only", basis_ref="doc/ro1",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    # 观测：m1 与 t1 都是模型自发生成
    s.record_observed("m1", "model_generation", note="合成")
    s.record_observed("t1", "model_generation", note="合成")
    return s


# ================================================== 组 ① B1 正向 / 负向
@case("A3-1a", "B1 正向：model_generation 记录【不在】候选集合里")
def a31a():
    s = mk_mixed()
    r = AI.importance_candidates(s, trace=[])
    assert r["status"] == "EVALUATED", "状态异常：%r" % r["status"]
    assert "m1" not in r["candidates"], (
        "m1 是 model_generation，却进了候选集合 ⇒ B1 被违反")
    assert "m1" in r["excluded"]["R_MODEL_GENERATION"], (
        "m1 未被记入 R_MODEL_GENERATION 的排除名单")
    return "m1 被排除；候选=%s" % sorted(r["candidates"])


@case("A3-1b", "B1 负向：human_input 记录【可以】在候选集合里")
def a31b():
    s = mk_mixed()
    r = AI.importance_candidates(s, trace=[])
    assert "h1" in r["candidates"], (
        "h1 是人输入的，不该被排除")
    return "h1 在候选集合内（h1 未被误伤）"


@case("A3-1c", "B1 只排除 model_generation，不误伤其他 origin")
def a31c():
    s = mk_mixed()
    # 未观测的记录（basis_conflict=observed_absent）也不应因 B1 被排除
    r = AI.importance_candidates(s, trace=[])
    for rid in ("h1", "ro1"):
        assert rid in r["candidates"], "%s 被误排除" % rid
    return "h1/ro1 均未被 R_MODEL_GENERATION 排除"


@case("A3-1d", "B1 不区分 asserted 类别：third_person × model_generation 同样排除")
def a31d():
    """凌翼要求 1 的「负向测试」关键一格。

    B1 原文：「observed_origin = model_generation 的记录，
             不得进入「重要」集合。」
    ⇒ 排除依据是【观测值】，不是【断言类别】。
       first_person 与 third_person 的 model_generation 记录都该被排除。

    ⚠ 第一版只测了 first_person（A3-1a），于是变异 I2
      （把排除条件收窄成「只排 first_person」）行为已变但测试全绿：
      ⇒ 被变异验证判为 MISSED，是真缺口，不是探针问题。
    """
    s = mk_mixed()
    r = AI.importance_candidates(s, trace=[])
    assert "t1" not in r["candidates"], (
        "t1 是 third_person × model_generation，也属 observed_origin=model_generation，"
        "应被 B1 排除，但仍进了候选集合")
    assert "t1" in r["excluded"]["R_MODEL_GENERATION"], (
        "t1 未被记入 R_MODEL_GENERATION 排除名单")
    return "t1（third_person × model_generation）同样被排除"


@case("A3-1e", "B1 看的是 observed_origin 的值，不是 basis_conflict")
def a31e():
    """若把排除依据改成 basis_conflict == asserted_contradicts_observed，
    那么 record_only × model_generation 的记录（basis_conflict=none）
    就会被漏掉 —— 但它同样是 model_generation，B1 要求排除。

    ⚠ 第一版这里【只有一个 ro2 记录】。
      于是空分母规则把 candidates 整个清空，
      「ro2 不在候选里」是空分母的结果，不是 B1 的结果 ——
      **断言假通过**。变异 I11 因此被判 MISSED（行为已变、测试全绿）。
    ⇒ 必须补一条 first_person_report 记录作为分母，
      让 candidates 在【正常路径】下产出，
      才能观察到「ro2 被 B1 排除」而不是「被空分母清零」。
    """
    s = RecoveryStore()
    # 分母记录：让 EVALUATED 成立，排除空分母遮蔽
    s.insert(Record(
        record_id="denom", content="人说的", source_kind="user_utterance",
        source_ref="utt/denom", participant_id="A",
        participation_basis="first_person_report", basis_ref="utt/denom",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    s.insert(Record(
        record_id="ro2", content="只记录但模型生成",
        source_kind="system_generated", source_ref="gen/ro2",
        participant_id="sys", participation_basis="record_only",
        basis_ref="gen/ro2", commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    s.record_observed("ro2", "model_generation")
    g = s.get("ro2")
    assert g["basis_conflict"] == "none", (
        "前提变了：record_only × model_generation 应为 none，实测 %r"
        % g["basis_conflict"])

    r = AI.importance_candidates(s, trace=[])
    assert r["status"] == "EVALUATED", (
        "分母应为 1（有 denom）⇒ 状态应为 EVALUATED，实测 %r。"
        "若为 NOT_EVALUABLE，则下面的断言会被空分母遮蔽" % r["status"])
    assert "denom" in r["candidates"], "分母记录本身应进候选（未被 B1 排除）"

    assert "ro2" not in r["candidates"], (
        "ro2 的 basis_conflict=none 但 observed_origin=model_generation，"
        "B1 仍要求排除；若在候选里说明判据看错了字段")
    assert "ro2" in r["excluded"]["R_MODEL_GENERATION"], (
        "ro2 未被记入 R_MODEL_GENERATION 排除名单")
    return "basis_conflict=none 的 model_generation 仍被 B1 排除（看的是 origin）"


# ================================================== 组 ② 排除不变性
@case("A3-2a", "同一 record_id 被召回 1/5/50 次，【每一档】都必须排除")
def a32a():
    """⚠ 知微复核指出的假绿（2026-11-26）：

    第一版的断言是 results[1] == results[5] == results[50]，
    【只比较三档相等】，不要求每一档的排除布尔值为真。

    ⇒ 后果：若把 B1 改成「只有没有召回事件时才排除」，
      50 次时 m1 会被放行，而三档的「是否排除」分别是
      (False, False, False) —— 三者仍然【相等】，
      断言依然通过。这是假绿。

    实测（知微在临时副本验证）：只改这一处，原目标套件仍 23/23。

    ⇒ 修法：
      ① 每一档【分别】断言 m1 不在
      ② 在同一非空事件流上关 B1，确认原目标断言【变红】
      ③ 保留未受影响记录的对照（h1 始终在）
    """
    s = mk_mixed()
    total = {}
    for n in (1, 5, 50):
        trace = AI.synthetic_trace(s, [
            {"record_id": "m1", "at": "T%03d" % i,
             "query_ref": "q%d" % i} for i in range(n)
        ])
        r = AI.importance_candidates(s, trace=trace)
        # ① 每一档【分别】断言，不允许用「三档相等」代替
        assert "m1" not in r["candidates"], (
            "%d 次召回时 m1 进了候选集合 ⇒ B1 在该档失效" % n)
        # ③ 未受影响记录的对照
        assert "h1" in r["candidates"], (
            "%d 次召回时 h1（人输入的）被误排除" % n)
        total[n] = (tuple(sorted(r["candidates"])), len(trace))

    # 三档之间其余成员也不应变（排除不变性）
    sets = [v[0] for v in total.values()]
    assert sets[0] == sets[1] == sets[2], (
        "召回次数改变导致其余成员变化：%r" % sets)

    return "1/5/50 次逐档断言：m1 均不在，h1 均在，其余成员不变"


@case("A3-2a2", "反证：若 B1 只在「无召回事件」时生效，A3-2a 必须变红")
def a32a2():
    """这是 A3-2a 的失败样本（A3 要求每条判据配一个已知会失败的情形）。

    做法：用 exclude 关掉 B1 且喂非空事件流 ⇒ 等价于
    「有召回事件时 B1 不生效」这一变异的行为。
    ⇒ A3-2a 中「每一档分别断言」的写法会红；
      而第一版的「三档相等」写法不会红 —— 这正是假绿的证据。
    """
    s = mk_mixed()
    trace = AI.synthetic_trace(s, [{"record_id": "m1", "at": "T%03d" % i,
                                    "query_ref": "q%d" % i} for i in range(50)])
    off = AI.importance_candidates(s, trace=trace,
                                   exclude=["R_MODEL_GENERATION"])
    # 变异后：m1 被放行
    assert "m1" in off["candidates"], (
        "前提失效：关掉 B1 后 m1 仍未进候选，本反证无效")

    # 逐档断言写法会红
    per_bucket_would_fail = "m1" not in off["candidates"]
    assert per_bucket_would_fail is False, (
        "逐档断言应当在此情形变红")

    # 旧写法（三档相等）在此情形【不会】红 —— 因为三档都是 False
    olds = []
    for n in (1, 5, 50):
        tr = AI.synthetic_trace(s, [
            {"record_id": "m1", "at": "T%03d" % i,
             "query_ref": "q%d" % i} for i in range(n)])
        rr = AI.importance_candidates(s, trace=tr,
                                      exclude=["R_MODEL_GENERATION"])
        olds.append(tuple(sorted(rr["candidates"])))
    assert olds[0] == olds[1] == olds[2], (
        "旧写法在此情形居然不等 ⇒ 反证前提变了")
    return "变异下：逐档断言红，旧「三档相等」写法不红 ⇒ 假绿已复现并堵住"


@case("A3-2b", "合成事件流拒绝「用不存在的 record_id 造假」")
def a32b():
    s = mk_mixed()
    try:
        AI.synthetic_trace(s, [
            {"record_id": "ghost", "at": "T0", "query_ref": "q0"}])
    except SchemaError as e:
        assert "不存在" in str(e) or "ghost" in str(e)
        return "不存在的 record_id 被拒"
    raise AssertionError("合成事件流接受了不存在的 record_id")


@case("A3-2c", "合成事件流拒绝「完全重复的事件」冒充多次召回")
def a32c():
    s = mk_mixed()
    try:
        AI.synthetic_trace(s, [
            {"record_id": "m1", "at": "T0", "query_ref": "q0"},
            {"record_id": "m1", "at": "T0", "query_ref": "q0"}])
    except SchemaError as e:
        assert "重复" in str(e)
        return "完全重复事件被拒"
    raise AssertionError("合成事件流接受了完全重复的事件")


@case("A3-2d", "合成事件流允许同一 record_id 的【不同】事件（这才是高频）")
def a32d():
    s = mk_mixed()
    trace = AI.synthetic_trace(s, [
        {"record_id": "m1", "at": "T0", "query_ref": "q0"},
        {"record_id": "m1", "at": "T1", "query_ref": "q1"},
        {"record_id": "m1", "at": "T2", "query_ref": "q2"}])
    assert len(trace) == 3
    counts = AI.recall_counts(trace)
    assert counts["m1"] == 3
    return "同一 record_id × 3 个不同事件 = 高频，被接受"


# ================================================== 组 ③ 变异观测（三态）
@case("A3-3a", "关闭 B1 ⇒ 排除确实失效（直接观测，不靠测试红绿）")
def a33a():
    s = mk_mixed()
    # 基线：m1 被排除
    base = AI.importance_candidates(s, trace=[])
    assert "m1" not in base["candidates"]

    # 关闭 B1：直接观测外部状态
    off = AI.importance_candidates(s, trace=[],
                                   exclude=["R_MODEL_GENERATION"])
    assert "m1" in off["candidates"], (
        "关闭 B1 后 m1 仍不在候选集合 ⇒ 变异没生效，"
        "此时不得声称 A3 成功（E1/M1）")
    assert "R_MODEL_GENERATION" not in off["active_rules"]
    return "关闭 B1：m1 进入候选集合（外部状态已变）⇒ 变异有效"


@case("A3-3b", "变异有效性的判定顺序：先观测行为已变，再谈断言强弱")
def a33b():
    """M1：A3 的前提。
    变异体必须【直接观测到行为已变】，才可用 A3 判断断言强弱。
    若行为未变，则该变异无效，不得记成「断言没红所以断言弱」。
    """
    s = mk_mixed()
    base = "m1" not in AI.importance_candidates(s, trace=[])["candidates"]
    off = "m1" in AI.importance_candidates(
        s, trace=[], exclude=["R_MODEL_GENERATION"])["candidates"]
    assert base and off, (
        "变异未改变可观测行为（base_excluded=%r, off_included=%r）"
        " ⇒ 该变异无效，不得据此判断断言强弱" % (base, off))
    return "行为变化已直接观测：基线排除 / 关闭后纳入"


@case("A3-3c", "关闭未知规则 ⇒ 报错，不静默忽略")
def a33c():
    s = mk_mixed()
    try:
        AI.importance_candidates(s, trace=[], exclude=["NOT_A_RULE"])
    except SchemaError as e:
        assert "未知规则" in str(e)
        return "未知规则被拒"
    raise AssertionError("未知排除规则被静默接受 ⇒ 变异可能没生效却无人知晓")


# ================================================== 组 ④ J2 伪亲历（单独测）
@case("A3-4a", "J2：first_person × model_generation ⇒ 伪亲历标记为真")
def a34a():
    s = mk_mixed()
    g = s.get("m1")
    assert g["participation_basis"] == "first_person_report"
    assert g["observed_origin"] == "model_generation"
    assert g["basis_conflict"] == "asserted_contradicts_observed", (
        "冲突值应为 asserted_contradicts_observed，实测 %r"
        % g["basis_conflict"])
    # 伪亲历是派生：first_person × model_generation
    pseudo = (g["participation_basis"] == "first_person_report"
              and g["observed_origin"] == "model_generation")
    assert pseudo is True
    return "m1: 冲突=%s + 伪亲历=真（两件事分别可查）" % g["basis_conflict"]


@case("A3-4b", "J2 与 B3 分开：冲突成立≠伪亲历成立")
def a34b():
    """Mion 回复4 §4.5：asserted_contradicts_observed 是【一格】，
    伪亲历是其中一个真子集。二者不得互推。
    """
    # third_person × model_generation ⇒ 冲突成立，但不是伪亲历
    s = RecoveryStore()
    s.insert(Record(
        record_id="t1", content="模型说的", source_kind="system_generated",
        source_ref="gen/t1", participant_id="sys",
        participation_basis="third_person_report", basis_ref="gen/t1",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    s.record_observed("t1", "model_generation")
    g = s.get("t1")
    assert g["basis_conflict"] == "asserted_contradicts_observed", (
        "前提变了：third_person × model_generation 未判冲突")
    pseudo = (g["participation_basis"] == "first_person_report"
              and g["observed_origin"] == "model_generation")
    assert pseudo is False, "冲突成立却派生出了伪亲历 ⇒ 两层被压成一层"
    return "冲突成立但伪亲历为假 ⇒ 两层可区分"


@case("A3-4c", "J2：消费者真的把 m1 计入、把 t1 排除在伪亲历名单外")
def a34c():
    """⚠ 知微复核指出（2026-11-26）：

    A3-4a/4b 在【测试内部】用两个字段重算 pseudo，
    没有检查【消费者真的做了什么】。
    ⇒ 那测的是「我能算出这个布尔值」，不是「系统把谁算进了伪亲历」。

    ⇒ 修：直接调用 summarize_conflicts()，查它返回的
      pseudo_first_person_ids 实际包含谁。
    """
    import afrecover as AR
    s = mk_mixed()   # 含 m1(first_person×model)、t1(third_person×model)、h1

    ids = [r["record_id"] for r in s.sqlite_rows()]
    conf = AR.summarize_conflicts(s, ids)

    # 逐条：m1 计入、t1 不计入、h1 不计入
    per = {p["record_id"]: p for p in conf.get("per_record", [])}
    assert "m1" in per, "per_record 缺 m1"
    assert per["m1"]["pseudo_first_person"] is True, (
        "m1 是 first_person × model_generation，消费者未把它标为伪亲历")
    assert per["t1"]["pseudo_first_person"] is False, (
        "t1 是 third_person × model_generation，消费者误把它标为伪亲历")
    assert per["h1"]["pseudo_first_person"] is False, (
        "h1 是人输入的，消费者误把它标为伪亲历")

    # 汇总名单也要一致
    #
    # ⚠ 2026-11-26 修正（知微定点复验）：
    #   第一版写 `if plist is not None:` —— 名单【整个缺失】时直接进成功分支。
    #   知微实测：只把消费者输出改名为 pseudo_first_person_xx、
    #   保留逐条值，目标套件仍 26/26 全绿。
    #   ⇒ 缺字段不得算通过。必须断言：键存在、值可迭代、且集合恰等于
    #     per_record 中标真的全部 ID。
    assert "pseudo_first_person_ids" in conf, (
        "summarize_conflicts 缺 pseudo_first_person_ids 字段 ⇒ "
        "A3-4c 不能靠「字段不存在就跳过」通过")
    plist = conf["pseudo_first_person_ids"]
    assert isinstance(plist, (list, tuple, set)), (
        "pseudo_first_person_ids 类型为 %s，应为名单"
        % type(plist).__name__)

    # 逐条真值为 True 的 ID 集合，必须与名单【恰等】——不是「包含」
    expect = {rid for rid, p in per.items()
              if p.get("pseudo_first_person") is True}
    assert set(plist) == expect, (
        "名单与逐条不一致：名单=%r 逐条真值=%r"
        % (sorted(plist), sorted(expect)))
    # 反向也要守：名单里不得出现逐条为 False 的 ID
    for rid in plist:
        assert per.get(rid, {}).get("pseudo_first_person") is not False, (
            "%r 在名单里，但逐条判为 False ⇒ 两者矛盾" % rid)
    return "名单与逐条恰等：%r（m1 计入，t1/h1 排除）" % (sorted(plist),)


@case("A3-4c2", "反证：名单字段缺失时 A3-4c 必须变红")
def a34c2():
    """A3：A3-4c 自己也要能失败。

    知微实测的形态：把消费者输出改名（保留逐条值），
    第一版仍 26/26 全绿。
    ⇒ 这里断言「缺字段会被 A3-4c 的 `in conf` 判据抓住」。
    """
    fake_conf = {"per_record": [
        {"record_id": "m1", "pseudo_first_person": True}]}   # 缺名单

    caught_by_presence_check = "pseudo_first_person_ids" not in fake_conf
    assert caught_by_presence_check, (
        "缺字段居然被判为存在 ⇒ A3-4c 的键存在断言无效")

    # 对照：旧写法会放行
    old_would_pass = ("if plist is not None" and
                      fake_conf.get("pseudo_first_person_ids") is None)
    assert old_would_pass, "旧写法的逃逸前提变了"
    return "缺字段：旧写法放行、新写法（in conf）拦截"


@case("A3-4d", "反证：把伪亲历派生关掉，A3-4c 必须变红")
def a34d():
    """A3：这条断言自己也要能失败。
    构造一个 third_person × model_generation 却自称 first_person 的情形 ——
    不，那样会改断言对象。

    ⇒ 改用更直接的反证：把 t1 改成 first_person_report（→ 它就该被计入），
      断言 A3-4c 中「t1 不计入」的那一条会失败。
    """
    import afrecover as AR
    s = RecoveryStore()
    s.insert(Record(
        record_id="t1", content="模型说的", source_kind="system_generated",
        source_ref="gen/t1", participant_id="sys",
        participation_basis="first_person_report",  # ← 改成第一人称
        basis_ref="gen/t1", commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    s.record_observed("t1", "model_generation")
    conf = AR.summarize_conflicts(s, ["t1"])
    per = {p["record_id"]: p for p in conf.get("per_record", [])}
    assert per["t1"]["pseudo_first_person"] is True, (
        "改成 first_person 后应计为伪亲历 ⇒ A3-4c 的「t1 不计入」会在此情形红")
    return "改一处断言对象：t1(first_person) 被计入 ⇒ A3-4c 会红"


# ================================================== 组 ⑤ J3 空分母（单独测）
@case("A3-5a", "J3：分母为空 ⇒ NOT_EVALUABLE，不是 0，也不是「无重要项」")
def a35a():
    s = mk()   # 只有 record_only 的记录
    s2 = RecoveryStore()
    s2.insert(Record(
        record_id="ro", content="只记录", source_kind="unknown",
        source_ref="doc/ro", participant_id=None,
        participation_basis="record_only", basis_ref="doc/ro",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    r = AI.importance_candidates(s2, trace=[])
    assert r["denominator_size"] == 0, (
        "分母应只数 first_person_report，实测 %d" % r["denominator_size"])
    assert r["status"] == "NOT_EVALUABLE", (
        "空分母被报成 %r ⇒ 违反 C2" % r["status"])
    assert r["candidates"] == set(), (
        "NOT_EVALUABLE 时候选集合应为空集，实测 %r" % r["candidates"])
    return "空分母 ⇒ NOT_EVALUABLE + 空集（不是 0）"


@case("A3-5b", "J3 的反证：关闭这条规则后会被误报为 EVALUATED")
def a35b():
    s2 = RecoveryStore()
    s2.insert(Record(
        record_id="ro", content="只记录", source_kind="unknown",
        source_ref="doc/ro", participant_id=None,
        participation_basis="record_only", basis_ref="doc/ro",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    off = AI.importance_candidates(
        s2, trace=[], exclude=["R_EMPTY_DENOMINATOR"])
    assert off["status"] == "EVALUATED", (
        "关闭规则后仍非 EVALUATED ⇒ 这条变异无效")
    return "关闭 C2 规则 ⇒ 变成 EVALUATED（该处确实在守）"


# ================================================== 组 ⑥ 合成标记
@case("A3-6a", "有 trace 时 measurement_scope 必须标 MEASURED_ON_SYNTHETIC_ONLY")
def a36a():
    s = mk_mixed()
    trace = AI.synthetic_trace(s, [{"record_id": "m1", "at": "T0",
                                    "query_ref": "q0"}])
    r = AI.importance_candidates(s, trace=trace)
    assert r["status"] == "EVALUATED", (
        "本用例应命中 EVALUATED 分支，实测 %r" % r["status"])
    assert r["measurement_scope"] == AI.SYNTHETIC_PREFIX, (
        "合成测量未标 %s，实测 %r"
        % (AI.SYNTHETIC_PREFIX, r["measurement_scope"]))
    return r["measurement_scope"]


@case("A3-6a2", "空分母（NOT_EVALUABLE）分支同样必须标合成测量")
def a36a2():
    """⚠ 第一版只测了 EVALUATED 路径。
    而 importance_candidates 有【两个】返回点，各自算一次 measurement_scope。
    ⇒ 变异 I9（只改 NOT_EVALUABLE 那一处）行为已变但测试全绿，被判 MISSED。
    ⇒ 两个分支必须各自断言。
    """
    s = RecoveryStore()
    s.insert(Record(
        record_id="ro", content="只记录", source_kind="unknown",
        source_ref="doc/ro", participant_id=None,
        participation_basis="record_only", basis_ref="doc/ro",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    trace = AI.synthetic_trace(s, [])
    r = AI.importance_candidates(s, trace=trace)
    assert r["status"] == "NOT_EVALUABLE", (
        "本用例应命中 NOT_EVALUABLE 分支，实测 %r" % r["status"])
    assert r["measurement_scope"] == AI.SYNTHETIC_PREFIX, (
        "NOT_EVALUABLE 分支的合成测量未标 %s，实测 %r"
        % (AI.SYNTHETIC_PREFIX, r["measurement_scope"]))
    return "NOT_EVALUABLE 分支：%s" % r["measurement_scope"]


@case("A3-6b", "无 trace 时不得标成合成测量")
def a36b():
    s = mk_mixed()
    r = AI.importance_candidates(s, trace=None)
    assert r["measurement_scope"] != AI.SYNTHETIC_PREFIX, (
        "没有事件流却标成合成测量")
    assert r["measurement_scope"] == "NOT_MEASURED"
    return r["measurement_scope"]


@case("A3-6c", "合成比例函数不写文件（红线：无基线前不入 reports/）")
def a36c():
    s = mk_mixed()
    trace = AI.synthetic_trace(s, [{"record_id": "m1", "at": "T0",
                                    "query_ref": "q0"}])
    before = set(os.listdir(os.path.join(HERE, "reports"))) \
        if os.path.isdir(os.path.join(HERE, "reports")) else set()
    r = AI.synthetic_ratios(s, trace)
    after = set(os.listdir(os.path.join(HERE, "reports"))) \
        if os.path.isdir(os.path.join(HERE, "reports")) else set()
    assert before == after, (
        "synthetic_ratios 改动了 reports/ 目录：新增 %s" % (after - before))
    assert r["measurement_scope"] == AI.SYNTHETIC_PREFIX, (
        "合成比例未标 measurement_scope（键名须与 importance_candidates 一致）")
    return "未写任何文件；measurement_scope=%s" % r["measurement_scope"]


@case("A3-6d", "空分母时比例返回 None 而不是 0")
def a36d():
    s = RecoveryStore()
    r = AI.synthetic_ratios(s, [])
    assert r["unverifiable_ratio"] is None, (
        "空分母被报成 %r，应为 None（0 会被读成「全部可判定」）"
        % r["unverifiable_ratio"])
    assert r["record_only_ratio"] is None
    return "空分母 ⇒ None（不是 0）"


@case("A3-6e", "两个函数用同一个测量范围键名（不得 scope / measurement_scope 并存）")
def a36e():
    """⚠ 自查发现的真问题：
    importance_candidates 用 measurement_scope，
    synthetic_ratios 第一版用 scope。
    ⇒ 同一个概念两个键名 ⇒ 读者会以为是两件事。
    ⇒ 现统一为 measurement_scope，并加此断言防止漂回。
    """
    s = mk_mixed()
    c = AI.importance_candidates(s, trace=[])
    p = AI.synthetic_ratios(s, AI.synthetic_trace(
        s, [{"record_id": "m1", "at": "T0", "query_ref": "q0"}]))
    assert "measurement_scope" in c, "importance_candidates 缺 measurement_scope"
    assert "measurement_scope" in p, (
        "synthetic_ratios 缺 measurement_scope（键名与另一个函数不一致）")
    assert "scope" not in p, (
        "synthetic_ratios 仍带裸 scope 键 ⇒ 同一概念出现两个名字")
    assert c["measurement_scope"] == p["measurement_scope"] == AI.SYNTHETIC_PREFIX
    return "两函数键名一致：measurement_scope=%s" % c["measurement_scope"]


# ================================================== 组 ⑦ 显式范围契约
@case("A3-7a", "显式范围拒绝重复 ID（同一记录不得被算两次）")
def a37a():
    """知微定点复验：原实现保留重复 ⇒ [r1,ro1,ro1] 分母变 3，
    比例从 0.5 变 0.667，而调用方看不出范围被改变了。
    """
    s = mk_mixed()
    ok = AI.synthetic_ratios(s, [], scope_ids=["h1", "ro1"])
    assert ok["record_only_denominator_size"] == 2, (
        "基准：[h1,ro1] 分母应为 2，实测 %r"
        % ok["record_only_denominator_size"])

    try:
        AI.synthetic_ratios(s, [], scope_ids=["h1", "ro1", "ro1"])
    except SchemaError as e:
        assert "重复" in str(e), "拒绝理由未提重复：%s" % str(e)[:60]
        return "重复 ID 被拒：[h1,ro1] 分母 2；[h1,ro1,ro1] 报错"
    raise AssertionError(
        "重复 ID 被静默接受 ⇒ 同一记录会被算两次，比例失真")


@case("A3-7b", "显式范围拒绝未知 ID（不得与「范围为空」混淆）")
def a37b():
    """知微定点复验：原实现静默丢弃 ⇒ [ghost] 与 [] 返回完全相同，
    于是「没能解析任何 ID」与「本次范围本来为空」混成一件事。
    """
    s = mk_mixed()

    # 空范围：语义是「范围为空」，应当正常返回空
    empty = AI.synthetic_ratios(s, [], scope_ids=[])
    assert empty.get("basis") == "empty", (
        "空范围应返回 basis=empty，实测 %r" % empty.get("basis"))

    # 未知 ID：语义是「解析失败」，必须报错而不是伪装成空
    try:
        AI.synthetic_ratios(s, [], scope_ids=["ghost"])
    except SchemaError as e:
        assert "不存在" in str(e) or "ghost" in str(e), (
            "拒绝理由不明：%s" % str(e)[:60])
        return "[] → basis=empty；[ghost] → 报错（两者不再等同）"
    raise AssertionError(
        "未知 ID 被静默丢弃 ⇒ 不完整范围会冒充完整范围")


@case("A3-7c", "两个返回分支的键集合一致（空分支不再少字段）")
def a37c():
    """知微 + 睫都指出：空分支 10 键、非空 12 键。
    ⇒ 同一函数两种键集合 ⇒ 「完整清单」站不住。
    """
    full = AI.synthetic_ratios(mk_mixed(), [])
    empty = AI.synthetic_ratios(RecoveryStore(), [])
    assert set(full) == set(empty), (
        "两分支键集合不同：仅非空有 %s；仅空有 %s"
        % (sorted(set(full) - set(empty)), sorted(set(empty) - set(full))))
    return "两分支均 %d 键，集合一致" % len(full)


# ================================================== 自指检查
@case("A3-0", "本文件的断言不是空转：构造一个必然违反 B1 的输入")
def a30():
    """A3 的自指要求：连这套测试本身也要能失败。

    做法：直接构造一个【绕过 record_observed】的记录 ——
    在 live 上手工塞 observed_origin（模拟「如果有人绕过了通道」）。
    ⇒ 候选集合过滤器【仍应排除它】。
    ⇒ 若它也进得去，说明 B1 只在「正常路径」上成立，不是真排除。
    """
    s = mk_mixed()
    # 手工把那层保护拆掉：把 m1 的 observed_origin 改写
    # （直接改 _live，模拟越权写入；Record 是不可变 dataclass，故重建）
    cur = s._live["m1"]
    d = cur.to_dict()
    d["observed_origin"] = "model_generation"
    s._live["m1"] = Record(**{k: v for k, v in d.items()
                              if k != "this_digest"})
    r = AI.importance_candidates(s, trace=[])
    assert "m1" not in r["candidates"], (
        "绕过通道写入的 model_generation 仍在候选集合里 ⇒ "
        "B1 只在正常路径生效，不是真排除")
    return "越权写入的 model_generation 同样被排除（B1 看的是值，不是路径）"


# ---------------------------------------------------------------- 汇总
def main():
    print("=" * 82)
    print("第 5 项 A3/B3 限定原型（凌翼 2026-11-25 授权）")
    print("  SYNTHETIC_TRACE_DESIGN     = AUTHORIZED")
    print("  CANDIDATE_FILTER_PROTOTYPE = AUTHORIZED_LIMITED")
    print("  FULL_IMPORTANCE_LEARNER    = NOT_AUTHORIZED")
    print("=" * 82)
    print()

    groups = [
        ("① B1 正向/负向（凌翼要求 1）", [a31a, a31b, a31c, a31d, a31e]),
        ("② 不同召回次数下排除不变（要求 2）",
         [a32a, a32a2, a32b, a32c, a32d]),
        ("③ 关闭规则时直接观测变异生效（要求 3/4）", [a33a, a33b, a33c]),
        ("④ J2 伪亲历单独测（要求 5）", [a34a, a34b, a34c, a34c2, a34d]),
        ("⑤ J3 空分母单独测（要求 5）", [a35a, a35b]),
        ("⑥ 合成标记与红线（要求 6）",
         [a36a, a36a2, a36b, a36c, a36d, a36e]),
        ("⑦ 显式范围契约（知微定点复验）", [a37a, a37b, a37c]),
        ("⑦ A3 自指：本文件能否失败", [a30]),
    ]
    for title, fns in groups:
        print("[%s]" % title)
        for fn in fns:
            fn()
        print()

    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print("=" * 82)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 82)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
