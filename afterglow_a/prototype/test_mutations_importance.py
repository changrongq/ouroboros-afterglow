# -*- coding: utf-8 -*-
"""第 5 项变异验证（凌翼裁定要求 3 / 4）

要求 3：关闭排除规则时，必须【直接观测】变异确实生效。
要求 4：若其他机制阻断了变异效果，不得冒充 A3 成功；
        按既有 E1/E2/E3 与 M1 边界登记。

本文件对 afimportance.py 逐处破坏，然后：
  ① 先【直接观测】候选集合是否真的变化（E1/M1）
  ② 再看目标测试是否红（A3）
  ③ 若观测到行为未变 ⇒ 记 UNRESOLVED，不记 MISSED

三态：CAUGHT / UNRESOLVED / MISSED —— 不许合并。

运行：python afterglow_a/prototype/test_mutations_importance.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = "afimportance.py"
TEST_FILE = "test_importance_a3b3.py"

#: 六类失败状态。⚠ 与 classify_evidence() 共用同一出处，
#:   不允许测试文件另抄一份（知微 2026-11-27 第 3 条）。
FAIL_STATES = ("MISSED", "INVALID", "TEST_DID_NOT_RUN", "TEST_CRASHED",
               "TARGET_ERRORED", "NOT_ATTRIBUTABLE")


def classify_evidence(rows, expected_ids=None):
    """证据状态判定 —— **真实驱动与测试共用同一个函数**。

    ⚠ 2026-11-27 抽出（知微第 3 条）：
      原实现把判定写在 main() 里，而 test_evidence_state.py
      另写了一份 classify 去「测它」。
      ⇒ 两份实现，测的和跑的不是同一个东西。
      ⇒ 知微实测：在真实驱动里删掉 TARGET_ERRORED，ES 仍 8/8。
      ⇒ 现在抽成本函数，main() 与测试都调它。

    规则（知微 2026-11-27 给定，互斥）：
      1. 有失败 ⇒ EVIDENCE_FAIL（有失败又有未决时失败优先，两类明细均保留）
      2. 无失败但有 UNRESOLVED，或应跑项缺失 ⇒ EVIDENCE_PARTIAL
      3. 预期清单非空、唯一、明细按 ID 一一对应、全 CAUGHT ⇒ EVIDENCE_COMPLETE

    ⚠ 第 3 条的身份核对（知微第 1 条）：
      不能用 len(rows) == len(MUTATIONS) 判完备 ——
      15 行、14 个不同 ID（末项被换成 I1 的副本）时，
      两个长度都等于 15，判据会放过。
      ⇒ 必须固定独立预期 ID 清单，逐个核对。

    返回 (verdict, exit_code, counts, detail)
    """
    counts = {}
    for _, _, st, _ in rows:
        counts[st] = counts.get(st, 0) + 1

    fail_detail = {st: counts.get(st, 0) for st in FAIL_STATES
                   if counts.get(st, 0)}
    n_fail_total = sum(fail_detail.values())
    n_unresolved = counts.get("UNRESOLVED", 0)

    got_ids = [r[0] for r in rows]
    detail = {"fail_detail": fail_detail, "n_unresolved": n_unresolved}

    if expected_ids is None:
        # 未提供预期清单 ⇒ 只能做「非空 + 唯一」的最低检查
        #
        # ⚠ 2026-11-27 修正（知微定点复验）：
        #   「未提供预期清单的降级模式也能 COMPLETE。
        #     若 COMPLETE 承诺『完整且与有效登记一一对应』，
        #     缺预期时至多 PARTIAL。」
        #   ⇒ 降级模式改为：可以判 PARTIAL，不判 COMPLETE。
        manifest_ok = False
        detail.update({"manifest_ok": manifest_ok,
                       "manifest_check": "DEGRADED_NO_EXPECTED_LIST",
                       "note": ("未提供预期清单 ⇒ 无法核对身份 ⇒ 至多 PARTIAL"
                                "（知微 2026-11-27）")})
    else:
        exp = list(expected_ids)
        exp_set, got_set = set(exp), set(got_ids)
        missing = sorted(exp_set - got_set)
        unexpected = sorted(got_set - exp_set)
        duplicated = sorted({i for i in got_ids if got_ids.count(i) > 1})
        # ⚠ 预期清单自身也要唯一（知微 2026-11-27）：
        #   「预期清单有重复、明细无重复时（预期 16 行、实得 15 行）仍 COMPLETE」
        #   ⇒ 预期重复 + 明细不重复 = 数量对不上，但集合相等，旧判据放过。
        exp_duplicated = sorted({i for i in exp if exp.count(i) > 1})
        manifest_ok = (bool(exp) and not missing and not unexpected
                       and not duplicated and not exp_duplicated)
        detail.update({"manifest_ok": manifest_ok,
                       "manifest_check": "STRICT_EXPECTED_LIST",
                       "expected_n": len(exp), "got_n": len(got_ids),
                       "missing": missing, "unexpected": unexpected,
                       "duplicated": duplicated,
                       "expected_duplicated": exp_duplicated})

    all_caught = bool(got_ids) and all(st == "CAUGHT"
                                       for _, _, st, _ in rows)

    if n_fail_total:
        verdict, exit_code = "EVIDENCE_FAIL", 1
    elif n_unresolved or not manifest_ok or not all_caught:
        verdict, exit_code = "EVIDENCE_PARTIAL", 2
    else:
        verdict, exit_code = "EVIDENCE_COMPLETE", 0

    detail["all_caught"] = all_caught
    return verdict, exit_code, counts, detail


def parse_case_results(out):
    """解析目标测试的实际 case 级结果：{case_id: "PASS"|"FAIL"|"ERR"}。

    ⚠ 知微定点复验指出：只数 [FAIL] 文本无法归因。
      必须解析出【哪个 case】红了，才能判断是否为目标 case。
    格式来自各套测试的输出行：
        [PASS] A3-1a 说明 — 结果
        [FAIL] A3-1a 说明 — 原因
        [ERR ] A3-1a 说明 — 异常
    """
    res = {}
    pat = re.compile(r"\[(PASS|FAIL|ERR)\s*\]\s+([A-Za-z0-9][A-Za-z0-9\-_]*)\s")
    for line in out.splitlines():
        m = pat.search(line)
        if not m:
            continue
        state, cid = m.group(1), m.group(2)
        # 同一 case 出现多次时，取最严重的
        rank = {"PASS": 0, "FAIL": 1, "ERR": 2}
        if cid not in res or rank[state] > rank[res[cid]]:
            res[cid] = state
    return res


# 每条 = (id, 说明, 原文, 替换为, 目标 case ID 集合)
#
# ⚠ 2026-11-26 新增第五项（知微定点复验）：
#   原实现只数 [FAIL] 文本，【不核 case ID】。
#   知微实测：对实际改变排除结果的 I1，用「只有无关 A3-6e 红」的输出替身，
#   得到 CAUGHT / PASS / exit 0。
#   ⇒ 必须为每个变异声明【可归因的目标 case】，
#      并解析实际 case 结果，只有目标 case 真的红了才算 CAUGHT。

MUTATIONS = [
    (
        "I1", "B1 排除条件被删掉（model_generation 不再被排除）",
        '        if ("R_MODEL_GENERATION" in active\n'
        '                and rec.get("observed_origin") == "model_generation"):',
        '        if False:  # MUTANT: B1 失效',
        {"A3-1a", "A3-1c", "A3-1d", "A3-1e"},
    ),
    (
        "I2", "B1 排除条件放宽（只排 first_person × model_generation）",
        '        if ("R_MODEL_GENERATION" in active\n'
        '                and rec.get("observed_origin") == "model_generation"):',
        '        if ("R_MODEL_GENERATION" in active\n'
        '                and rec.get("observed_origin") == "model_generation"\n'
        '                and rec.get("participation_basis")\n'
        '                    == "first_person_report"):  # MUTANT',
        {"A3-1d", "A3-1e"},
    ),
    (
        "I3", "exclude 参数被忽略（关闭规则无效 ⇒ 变异无法生效）",
        '    active = rules - off',
        '    active = rules  # MUTANT: 忽略 exclude',
        {"A3-3a", "A3-3b", "A3-2a2"},
    ),
    (
        "I4", "空分母判据失效（NOT_EVALUABLE 变 EVALUATED）",
        '    if ("R_EMPTY_DENOMINATOR" in active) and denom_size == 0:',
        '    if False:  # MUTANT: C2 失效',
        {"A3-5a"},
    ),
    (
        "I5", "空分母仍返回全部候选（不是空集）",
        '            "candidates": set(),',
        '            "candidates": candidates,  # MUTANT: 空分母返回非空集',
        {"A3-5a"},
    ),
    (
        "I6", "合成事件流不校验 record_id 真实存在",
        '        if store.get(rid) is None:\n'
        '            raise SchemaError(',
        '        if False:  # MUTANT: 不校验存在性\n'
        '            raise SchemaError(',
        {"A3-2b"},
    ),
    (
        "I7", "合成事件流不拒绝完全重复事件",
        '        if key in seen_events:',
        '        if False:  # MUTANT: 允许重复事件',
        {"A3-2c"},
    ),
    (
        "I8", "未知规则被静默忽略",
        '    if unknown_off:\n'
        '        raise SchemaError("exclude 含未知规则：%s" % sorted(unknown_off))',
        '    # MUTANT: 未知规则直接忽略',
        {"A3-3c"},
    ),
    (
        "I9", "NOT_EVALUABLE 分支不标 MEASURED_ON_SYNTHETIC_ONLY",
        '            "measurement_scope": (SYNTHETIC_PREFIX if trace is not None\n'
        '                                  else "NOT_MEASURED"),\n'
        '            "allowed_use": ("可用于断言「本批次不可评估」（status 字段）；"',
        '            "measurement_scope": "NOT_MEASURED",  # MUTANT\n'
        '            "allowed_use": ("可用于断言「本批次不可评估」（status 字段）；"',
        {"A3-6a2"},
    ),
    (
        "I9b", "EVALUATED 分支不标 MEASURED_ON_SYNTHETIC_ONLY",
        '        "measurement_scope": (SYNTHETIC_PREFIX if trace is not None\n'
        '                              else "NOT_MEASURED"),\n'
        '        "allowed_use": ("可用于断言「某记录未被已声明规则排除」；"',
        '        "measurement_scope": "NOT_MEASURED",  # MUTANT\n'
        '        "allowed_use": ("可用于断言「某记录未被已声明规则排除」；"',
        {"A3-6a", "A3-6e"},
    ),
    (
        "I10", "空分母比例返回 0 而不是 None",
        '            "unverifiable_ratio": None,\n'
        '            "record_only_ratio": None,',
        '            "unverifiable_ratio": 0.0,  # MUTANT\n'
        '            "record_only_ratio": 0.0,   # MUTANT',
        {"A3-6d"},
    ),
    (
        "I11", "B3 排除只看路径不看值（改成读 basis_conflict 而非 observed_origin）",
        '                and rec.get("observed_origin") == "model_generation"):',
        '                and rec.get("basis_conflict")\n'
        '                    == "asserted_contradicts_observed"):  # MUTANT',
        {"A3-1e"},
    ),
    # ⚠ 2026-11-26 新增（知微定点复验 §「显式范围会改变样本总体却不告知」）
    (
        "I12", "显式范围允许重复 ID（同一记录被算两次）",
        '            if rid in seen:\n'
        '                dup.append(rid)\n'
        '                continue',
        '            if False:  # MUTANT: 允许重复 ID\n'
        '                dup.append(rid)\n'
        '                continue',
        {"A3-7a"},
    ),
    (
        "I13", "显式范围静默丢弃未知 ID（保留 continue，不登记 unknown）",
        # ⚠ 2026-11-27 重做（知微复验）：
        #   原变异体把【整段 if 判断】改成 False，
        #   于是 `continue` 也不再执行，后面的 by_id[rid] 抛 KeyError('ghost')。
        #   ⇒ 它实现的是「崩溃」，不是注释所说的「静默丢弃」。
        #   ⇒ 该格的 CAUGHT 是异常冒充断言，作废。
        #
        #   真正的「静默丢弃」= 仍然跳过这条 ID（continue 保留），
        #   只是不把它记进 unknown 列表。
        '            if rid not in by_id:\n'
        '                unknown.append(rid)\n'
        '                continue',
        '            if rid not in by_id:\n'
        '                continue  # MUTANT: 静默丢弃（不登记 unknown）',
        {"A3-7b"},
    ),
    (
        "I14", "不可核验率不再计入「从未观测」（知微 2026-11-27 要求防回归）",
        '        if r.get("observed_origin") is None            # 从未观测\n'
        '        or r.get("basis_conflict") in ("observed_absent", "observed_unresolved")',
        '        if r.get("basis_conflict") in ("observed_absent", "observed_unresolved")'
        '  # MUTANT: 去掉「从未观测」这一项',
        {"A3-7d"},
    ),
]

PROBE = r'''# -*- coding: utf-8 -*-
# 直接观测：候选集合到底变没变（不参考任何测试红绿）
#
# 注意：本段整体是一个 r''' + "'''" + r''' 字符串，
# 内部不能出现连续三个单引号，故此处用 # 注释而非 docstring。
#
# 第一版只观测三个场景（base / b1_off / empty_denom），
# 于是所有「不改变这三个场景」的变异都被判 UNRESOLVED ——
# 那不是变异无效，是【探针覆盖面不足】。
# 这正是 Mion F1 说的：「按维度各验一次」，不是「验一个场景」。
#
# 现在按【被变异点声称影响的维度】分场景观测（V1–V9）。
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from afcore import Record, RecoveryStore
import afimportance as AI

PIN = "2026-11-25T00:00:00Z"

def mk_mixed():
    s = RecoveryStore()
    s.insert(Record(record_id="h1", content="人说的",
        source_kind="user_utterance", source_ref="utt/h1", participant_id="A",
        participation_basis="first_person_report", basis_ref="utt/h1",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    s.insert(Record(record_id="m1", content="模型生成的",
        source_kind="system_generated", source_ref="gen/m1",
        participant_id="sys", participation_basis="first_person_report",
        basis_ref="gen/m1", commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    s.insert(Record(record_id="t1", content="模型转述",
        source_kind="system_generated", source_ref="gen/t1",
        participant_id="sys", participation_basis="third_person_report",
        basis_ref="gen/t1", commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    # ⚠ 2026-11-26 补：探针夹具原缺 ro1，
    #   于是 scope_contract 里 ["h1","ro1"] 报「不存在 ro1」而不是正常返回，
    #   I12/I13 因此无法归因（探针缺口，不是代码问题）。
    s.insert(Record(record_id="ro1", content="只记录",
        source_kind="unknown", source_ref="doc/ro1", participant_id=None,
        participation_basis="record_only", basis_ref="doc/ro1",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    s.record_observed("m1", "model_generation", note="probe")
    s.record_observed("t1", "model_generation", note="probe")
    return s

def mk_empty_denom():
    s = RecoveryStore()
    s.insert(Record(record_id="ro", content="只记录", source_kind="unknown",
        source_ref="doc/ro", participant_id=None,
        participation_basis="record_only", basis_ref="doc/ro",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    return s

def mk_record_only_model():
    """record_only × model_generation：basis_conflict=none 但 origin 是模型

    ⚠ 必须【同时】含一条 first_person_report 记录作为分母，
      否则空分母规则会把 candidates 清空，
      于是「ro2 是否被 B1 排除」这个差异被完全遮住 ——
      这正是凌翼裁定第 4 条说的「其他机制阻断了变异效果，
      不得冒充 A3 成功」。探针必须先排除这种遮蔽。
    """
    s = RecoveryStore()
    s.insert(Record(record_id="p1", content="人说的",
        source_kind="user_utterance", source_ref="utt/p1",
        participant_id="A", participation_basis="first_person_report",
        basis_ref="utt/p1", commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    s.insert(Record(record_id="ro2", content="只记录但模型生成",
        source_kind="system_generated", source_ref="gen/ro2",
        participant_id="sys", participation_basis="record_only",
        basis_ref="gen/ro2", commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    s.record_observed("ro2", "model_generation")
    return s

def safe(fn):
    try:
        return fn()
    except Exception as e:
        return {"_exc": type(e).__name__, "_msg": str(e)[:110]}

out = {}

# V1 · B1 对 first_person 的排除（基本盘）
out["b1_first_person"] = safe(lambda: {
    "cand": sorted(AI.importance_candidates(mk_mixed(), trace=[])["candidates"])})

# V2 · B1 对 third_person 的排除（I11 会在此暴露：按 basis_conflict 判）
out["b1_third_person"] = safe(lambda: {
    "has_t1": "t1" in AI.importance_candidates(
        mk_mixed(), trace=[])["candidates"]})

# V3 · exclude 参数是否生效
out["exclude_works"] = safe(lambda: {
    "on": "m1" in AI.importance_candidates(mk_mixed(), trace=[])["candidates"],
    "off": "m1" in AI.importance_candidates(
        mk_mixed(), trace=[], exclude=["R_MODEL_GENERATION"])["candidates"]})

# V4 · 空分母判据（含 measurement_scope —— I9 会在此暴露）
#
# ⚠ 第一版只记录 status 与候选数，没记录空分母分支的 measurement_scope。
#   于是 I9（把该分支的合成标记改成 NOT_MEASURED）行为已变但探针看不见。
#   ⇒ 现在把该分支的 scope 也纳入观测。
def _empty_denom():
    s = mk_empty_denom()
    tr = AI.synthetic_trace(s, [])   # 空事件流也是 trace，应为合成测量
    r = AI.importance_candidates(s, trace=tr)
    return {"status": r["status"],
            "n_cand": len(r["candidates"]),
            "scope": r["measurement_scope"],
            "scope_is_synthetic": r["measurement_scope"] == AI.SYNTHETIC_PREFIX}
out["empty_denom"] = safe(_empty_denom)

# V5 · 未知规则是否报错（I8 会在此暴露）
def _unknown_rule():
    try:
        AI.importance_candidates(mk_mixed(), trace=[], exclude=["NOT_A_RULE"])
        return {"rejected": False}
    except Exception as e:
        return {"rejected": True, "type": type(e).__name__}
out["unknown_rule"] = safe(_unknown_rule)

# V6 · 合成事件流：不存在的 record_id（I6 会在此暴露）
def _ghost():
    try:
        AI.synthetic_trace(mk_mixed(), [
            {"record_id": "ghost", "at": "T0", "query_ref": "q0"}])
        return {"rejected": False}
    except Exception as e:
        return {"rejected": True, "type": type(e).__name__}
out["ghost_id"] = safe(_ghost)

# V7 · 合成事件流：完全重复事件（I7 会在此暴露）
def _dup():
    try:
        AI.synthetic_trace(mk_mixed(), [
            {"record_id": "m1", "at": "T0", "query_ref": "q0"},
            {"record_id": "m1", "at": "T0", "query_ref": "q0"}])
        return {"rejected": False}
    except Exception as e:
        return {"rejected": True, "type": type(e).__name__}
out["dup_event"] = safe(_dup)

# V8 · 合成标记（I9 会在此暴露）
#
# ⚠ 第一版这里只比较了 with_trace / no_trace 两个值的【存在】，
#   而 I9 的变异体是把 with_trace 那分支整个删掉 ——
#   若 no_trace 本来就等于 "NOT_MEASURED"，两者都变成同一个值时
#   只有【显式比较期望字符串】才能发现。故这里直接记录两个字面值。
def _scope():
    s = mk_mixed()
    tr = AI.synthetic_trace(s, [{"record_id": "m1", "at": "T0",
                                 "query_ref": "q0"}])
    return {"with_trace": AI.importance_candidates(
                s, trace=tr)["measurement_scope"],
            "no_trace": AI.importance_candidates(
                s, trace=None)["measurement_scope"],
            "with_trace_is_synthetic": (
                AI.importance_candidates(s, trace=tr)["measurement_scope"]
                == AI.SYNTHETIC_PREFIX)}
out["scope"] = safe(_scope)

# V9 · 空分母比例（I10 会在此暴露）
#
# ⚠ 必须用【真正为空】的 store。
#   2026-11-26 修正后，空分母分支的条件是 `n == 0 and m == 0`
#   （n = first_person 数，m = 取回集大小）。
#   而 mk_empty_denom() 里有一条 record_only ⇒ m == 1 ⇒ 走不到该分支。
#   ⇒ 第一版此处用的夹具已不适用，改用空 store。
def _empty_ratios():
    s = RecoveryStore()          # 真·空库
    r = AI.synthetic_ratios(s, [])
    return {"unv": r["unverifiable_ratio"],
            "ro": r["record_only_ratio"],
            "unv_is_none": r["unverifiable_ratio"] is None,
            "ro_is_none": r["record_only_ratio"] is None,
            "basis": r.get("basis")}
out["empty_ratios"] = safe(_empty_ratios)

# V10 · record_only × model_generation（I11 会在此暴露：看 origin 还是看 conflict）
out["ro_model"] = safe(lambda: {
    "basis_conflict": mk_record_only_model().get("ro2")["basis_conflict"],
    "has_ro2": "ro2" in AI.importance_candidates(
        mk_record_only_model(), trace=[])["candidates"]})

# V11 · 显式范围契约（I12/I13 会在此暴露）
#
# ⚠ 2026-11-26 新增（知微定点复验 §「显式范围会改变样本总体却不告知」）：
#   重复 ID 与未知 ID 的处理必须可观测，否则这两个变异无法归因。
def _scope_contract():
    s = mk_mixed()
    out2 = {}
    # 基准：正常显式范围
    try:
        r = AI.synthetic_ratios(s, [], scope_ids=["h1", "ro1"])
        out2["normal"] = {"denom": r["record_only_denominator_size"],
                          "ro": r["record_only_ratio"]}
    except Exception as e:
        out2["normal"] = {"_exc": type(e).__name__}
    # 重复 ID
    try:
        r = AI.synthetic_ratios(s, [], scope_ids=["h1", "ro1", "ro1"])
        out2["dup"] = {"accepted": True,
                       "denom": r["record_only_denominator_size"],
                       "ro": r["record_only_ratio"]}
    except Exception as e:
        out2["dup"] = {"accepted": False, "exc": type(e).__name__}
    # 未知 ID
    try:
        r = AI.synthetic_ratios(s, [], scope_ids=["ghost"])
        out2["unknown"] = {"accepted": True, "basis": r.get("basis")}
    except Exception as e:
        out2["unknown"] = {"accepted": False, "exc": type(e).__name__}
    # 空范围（对照组）
    try:
        r = AI.synthetic_ratios(s, [], scope_ids=[])
        out2["empty"] = {"accepted": True, "basis": r.get("basis")}
    except Exception as e:
        out2["empty"] = {"accepted": False, "exc": type(e).__name__}
    return out2
out["scope_contract"] = safe(_scope_contract)

# V12 · 不可核验率对「从未观测」的计入（I14 会在此暴露）
#
# ⚠ 2026-11-27 新增（知微复验：「尚缺防回归断言」）：
#   固定单条未观测记录时，unverifiable_ratio 必须为 1.0，
#   否则「从未观测」这一项被删掉也不会红。
def _unverifiable_single():
    s = RecoveryStore()
    s.insert(Record(record_id="r1", content="x",
        source_kind="user_utterance", source_ref="utt/r1",
        participant_id="A", participation_basis="first_person_report",
        basis_ref="utt/r1", commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    r = AI.synthetic_ratios(s, [])
    out2 = {"ratio": r["unverifiable_ratio"],
            "ids": r["unverifiable_ids"],
            "denom": r["denominator_size"]}
    # 对照：已观测且一致
    s2 = RecoveryStore()
    s2.insert(Record(record_id="r1", content="x",
        source_kind="user_utterance", source_ref="utt/r1",
        participant_id="A", participation_basis="first_person_report",
        basis_ref="utt/r1", commitment_state="not_a_commitment",
        revision=1, prev_digest=None, changed_at=PIN,
        change_authority="synthetic"))
    s2.record_observed("r1", "human_input")
    r2 = AI.synthetic_ratios(s2, [])
    out2["observed_ratio"] = r2["unverifiable_ratio"]
    out2["observed_ids"] = r2["unverifiable_ids"]
    return out2
out["unverifiable_single"] = safe(_unverifiable_single)

print("PROBE_JSON " + json.dumps(out, ensure_ascii=False))
'''


def copy_all(td):
    for f in ("afcore.py", "afrecover.py", TARGET, TEST_FILE):
        shutil.copy2(os.path.join(HERE, f), os.path.join(td, f))
    os.makedirs(os.path.join(td, "reports"), exist_ok=True)
    syn = os.path.join(HERE, "synthetic")
    if os.path.isdir(syn):
        shutil.copytree(syn, os.path.join(td, "synthetic"),
                        dirs_exist_ok=True)


def apply_mut(td, old, new):
    p = os.path.join(td, TARGET)
    src = open(p, encoding="utf-8").read()
    n = src.count(old)
    if n != 1:
        return False, "锚点出现 %d 次（应为 1）" % n
    open(p, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
    return True, "ok"


def observe(td):
    """E1/M1：直接观测候选集合的实际状态。"""
    with open(os.path.join(td, "probe_imp.py"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(PROBE)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, os.path.join(td, "probe_imp.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=td, env=env, timeout=180)
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.splitlines():
        if line.startswith("PROBE_JSON "):
            return json.loads(line[len("PROBE_JSON "):])
    return {"parse_error": out[-300:]}


def run_target_test(td):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, os.path.join(td, TEST_FILE)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=td, env=env, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def behavior_changed(base, mut):
    """比较两次直接观测，判断外部状态是否真的变了。

    ⚠ F1：观测必须覆盖【被变异点声称影响的维度】。
      探针场景见 PROBE 里的 V1–V9。
    """
    if not base or not mut:
        return None, "探针无输出"
    if base.get("parse_error") or mut.get("parse_error"):
        return None, "探针输出不可解析"
    diffs = []
    for key in sorted(set(base) | set(mut)):
        b = base.get(key, "<缺失>")
        m = mut.get(key, "<缺失>")
        if b != m:
            diffs.append("%s: %s → %s" % (
                key, json.dumps(b, ensure_ascii=False)[:70],
                json.dumps(m, ensure_ascii=False)[:70]))
    return (len(diffs) > 0), "; ".join(diffs)


def main():
    print("=" * 84)
    print("第 5 项变异验证（凌翼要求 3/4）")
    print("  先直接观测行为是否改变（E1/M1），再看目标测试是否红（A3）")
    print("  三态：CAUGHT / UNRESOLVED / MISSED —— 不许合并")
    print("=" * 84)
    print()

    # 基线
    with tempfile.TemporaryDirectory() as td:
        copy_all(td)
        rc, out = run_target_test(td)
        if rc != 0:
            print("!! 基线不绿，变异结果无意义")
            print(out[-2000:])
            return 1
        base_obs = observe(td)
        print("[基线] 目标测试 rc=0；直接观测 = %s" % json.dumps(
            base_obs, ensure_ascii=False))
        print()

    rows = []
    for mid, desc, old, new, target_cases in MUTATIONS:
        with tempfile.TemporaryDirectory() as td:
            copy_all(td)
            ok, note = apply_mut(td, old, new)
            if not ok:
                rows.append((mid, desc, "INVALID", note))
                print("  [INVALID   ] %-4s %s — %s" % (mid, desc, note))
                continue

            mut_obs = observe(td)
            changed, detail = behavior_changed(base_obs, mut_obs)
            rc, out = run_target_test(td)

            # ⚠ 2026-11-26 第二次修正（知微定点复验）：
            #
            # 第一版：rc != 0 一律 CAUGHT。
            # 第二版：数 [FAIL] 文本，仍【不核 case ID】。
            #   知微实测：对真正改变排除结果的 I1，
            #   用「只有无关 A3-6e 红」的输出替身 ⇒ CAUGHT / PASS / exit 0。
            #   「目标 A3-1a 抛异常 + 无关 A3-6e 红」同样被放过。
            #
            # ⇒ 现在：每个变异声明 target_cases，
            #   解析实际 case 结果，只有【目标 case 真的红了】才算 CAUGHT。
            #
            # ⚠ 2026-11-27 第三次修正（知微复验）：
            #   前一版把 FAIL 与 ERR 一起算入 hit。
            #   知微实测：目标 A3-1a 抛异常 + 无关 A3-6e 断言失败
            #            ⇒ 仍 CAUGHT / PASS / exit 0。
            #   而她同时指出：I13 的原日志就是 0 FAIL / 1 ERR
            #   （KeyError('ghost')）——
            #   ⇒ 那一格 CAUGHT 是【异常】冒充了【断言捕获】。
            #
            #   ⇒ 现在只有 FAIL 算断言捕获；
            #      目标只有 ERR 时单列 TARGET_ERRORED，不算 CAUGHT。
            case_results = parse_case_results(out)

            # 目标 case 中【断言失败】的（这才是「按目标断言捕获」）
            hit_fail = sorted(tc for tc in target_cases
                              if case_results.get(tc) == "FAIL")
            # 目标 case 中【抛异常】的（单列，不算捕获）
            hit_err = sorted(tc for tc in target_cases
                             if case_results.get(tc) == "ERR")

            n_case = len(case_results)
            n_fail = sum(1 for v in case_results.values() if v == "FAIL")
            n_err = sum(1 for v in case_results.values() if v == "ERR")
            unrelated = sorted(tc for tc, v in case_results.items()
                               if v in ("FAIL", "ERR") and tc not in target_cases)

            if changed is None:
                status = "UNRESOLVED"
                evid = "E2：无法独立观测（%s）" % detail
            elif not changed:
                status = "UNRESOLVED"
                evid = ("直接观测：行为【未变】（%s）⇒ 该变异无效，"
                        "不得据此判断言强弱（M1）" % (detail or "无差异"))
            elif n_case == 0:
                status = "TEST_DID_NOT_RUN"
                evid = ("行为已变（%s），但目标测试【零用例输出】"
                        "（rc=%s）⇒ 不得记 CAUGHT" % (detail[:60], rc))
            elif hit_fail:
                # 目标 case【按断言】失败 —— 这才是「按目标断言捕获」
                if rc == 0:
                    status = "MISSED"
                    evid = ("目标 case %s 断言失败，但退出码 0 ⇒ 测试自身判定有误"
                            % hit_fail)
                else:
                    status = "CAUGHT"
                    evid = ("行为已变；目标 case 断言失败：%s"
                            "（全库 %d FAIL / %d ERR）%s"
                            % (", ".join(hit_fail), n_fail, n_err,
                               ("；另有无关红：%s" % unrelated) if unrelated else ""))
            elif hit_err:
                # 目标 case【抛异常】—— 变异可能打穿了，但没有断言守住它
                status = "TARGET_ERRORED"
                evid = ("行为已变；目标 case %s 抛异常（非断言失败）"
                        "⇒ 不构成「按目标断言捕获」。"
                        "多半是变异体写错（改坏了语法/引用），需重做变异。"
                        % (", ".join(hit_err),))
            elif n_fail == 0 and n_err == 0:
                status = "MISSED"
                evid = ("行为已变（%s），但【无任何 case 红】"
                        "⇒ 真漏洞（目标 %s 未被守住）"
                        % (detail[:60], sorted(target_cases)))
            elif unrelated:
                status = "NOT_ATTRIBUTABLE"
                evid = ("行为已变（%s），但红的是【无关 case】%s，"
                        "目标 %s 全绿 ⇒ 无法归因到本变异"
                        % (detail[:60], unrelated, sorted(target_cases)))
            else:
                status = "TEST_CRASHED"
                evid = ("行为已变（%s），目标 case 有 ERR：%s"
                        "（无 FAIL，按异常单列）"
                        % (detail[:60],
                           sorted(tc for tc, v in case_results.items()
                                  if v == "ERR")))

            rows.append((mid, desc, status, evid))
            print("  [%-11s] %-4s %s" % (status, mid, desc))
            print("               %s" % evid)

    print()
    print("=" * 84)
    counts = {}
    for _, _, st, _ in rows:
        counts[st] = counts.get(st, 0) + 1
    # ⚠ 2026-11-27 修正（知微复验）：
    #   原汇总只印 6 个状态，TARGET_ERRORED 不在其中
    #   ⇒ JSON 有数、终端看不见。现全部列出。
    for st in ("CAUGHT", "UNRESOLVED", "MISSED", "INVALID",
               "TEST_DID_NOT_RUN", "TEST_CRASHED", "TARGET_ERRORED",
               "NOT_ATTRIBUTABLE"):
        if st in counts:
            print("  %-18s %d" % (st, counts[st]))
    print("=" * 84)

    # ---- 证据状态三态（判定逻辑已抽到模块级 classify_evidence）
    #
    # ⚠ 2026-11-27 第二次修正（知微定点复验）：
    #   第一次改成 `expected_ids = [m[0] for m in MUTATIONS]` ——
    #   预期没有从 rows 反推，但【预期与执行计划仍同源】。
    #   知微实测：给真实 main 的可执行列表仅去掉 I14（不补副本），
    #              14 项照常真跑 ⇒ COMPLETE / 0，missing=[]。
    #   ⇒ 现在改用【独立登记的清单】（mutation_manifest.py），
    #     它与 MUTATIONS 不是同一个对象。
    #     ⇒ 执行列表删了一项而登记仍有它 ⇒ missing 列出 ⇒ PARTIAL。
    from mutation_manifest import REGISTERED_MUTATION_IDS
    verdict, exit_code, counts2, detail = classify_evidence(
        rows, list(REGISTERED_MUTATION_IDS))
    fail_detail = detail["fail_detail"]
    n_unresolved = detail["n_unresolved"]

    # 额外核对：执行计划与登记清单是否一致（不一致不是失败，是登记没跟上）
    plan_ids = [m[0] for m in MUTATIONS]
    plan_vs_manifest_msgs = []
    if sorted(plan_ids) != sorted(REGISTERED_MUTATION_IDS):
        only_plan = sorted(set(plan_ids) - set(REGISTERED_MUTATION_IDS))
        only_mani = sorted(set(REGISTERED_MUTATION_IDS) - set(plan_ids))
        plan_vs_manifest_msgs.append(
            "执行计划与登记清单不一致：仅计划有 %s；仅登记有 %s"
            % (only_plan, only_mani))

    print("  证据状态：%s（共 %d 个变异）" % (verdict, len(rows)))
    for m in plan_vs_manifest_msgs:
        print("  ⚠ 登记核对：%s" % m)
        print("    ⇒ 执行计划与登记清单不同步 ⇒ 证据不完整，不签 COMPLETE。")
    if fail_detail:
        print("    失败明细：%s" % fail_detail)
    if n_unresolved:
        print("  ⚠ UNRESOLVED %d 条：变异未改变可观测行为/无法观测，" % n_unresolved)
        print("    ⇒ 证据不完整（EVIDENCE_PARTIAL），不签全项 PASS。")
    if counts.get("TARGET_ERRORED", 0):
        print("  ⚠ TARGET_ERRORED %d 条：目标 case 抛异常而非断言失败" %
              counts["TARGET_ERRORED"])
        print("    ⇒ 不构成「按目标断言捕获」，计入失败。")
    if counts.get("NOT_ATTRIBUTABLE", 0):
        print("  ⚠ NOT_ATTRIBUTABLE %d 条：行为变了但红的不是目标 case" %
              counts["NOT_ATTRIBUTABLE"])
        print("    ⇒ 不能归因到本变异，计入失败。")
    print("  退出码：%d（COMPLETE=0 / FAIL=1 / PARTIAL=2）" % exit_code)

    out_dir = os.path.join(HERE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "mutations_importance_result.json"),
              "w", encoding="utf-8", newline="\n") as f:
        json.dump({"verdict": verdict,
                   "exit_code": exit_code,
                   "counts": counts,
                   # detail 已含 fail_detail / n_unresolved / manifest_ok /
                   # manifest_check / missing / unexpected / duplicated /
                   # all_caught —— 直接展开，不再重复引用局部变量
                   **detail,
                   "rows": [{"id": a, "desc": b, "status": c, "evidence": d}
                            for a, b, c, d in rows]},
                  f, ensure_ascii=False, indent=2)
    print("  结果已写入 reports/mutations_importance_result.json")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
