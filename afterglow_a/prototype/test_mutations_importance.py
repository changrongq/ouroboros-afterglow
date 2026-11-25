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
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = "afimportance.py"
TEST_FILE = "test_importance_a3b3.py"

# 每条 = (id, 说明, 原文, 替换为)
MUTATIONS = [
    (
        "I1", "B1 排除条件被删掉（model_generation 不再被排除）",
        '        if ("R_MODEL_GENERATION" in active\n'
        '                and rec.get("observed_origin") == "model_generation"):',
        '        if False:  # MUTANT: B1 失效',
    ),
    (
        "I2", "B1 排除条件放宽（只排 first_person × model_generation）",
        '        if ("R_MODEL_GENERATION" in active\n'
        '                and rec.get("observed_origin") == "model_generation"):',
        '        if ("R_MODEL_GENERATION" in active\n'
        '                and rec.get("observed_origin") == "model_generation"\n'
        '                and rec.get("participation_basis")\n'
        '                    == "first_person_report"):  # MUTANT',
    ),
    (
        "I3", "exclude 参数被忽略（关闭规则无效 ⇒ 变异无法生效）",
        '    active = rules - off',
        '    active = rules  # MUTANT: 忽略 exclude',
    ),
    (
        "I4", "空分母判据失效（NOT_EVALUABLE 变 EVALUATED）",
        '    if ("R_EMPTY_DENOMINATOR" in active) and denom_size == 0:',
        '    if False:  # MUTANT: C2 失效',
    ),
    (
        "I5", "空分母仍返回全部候选（不是空集）",
        '            "candidates": set(),',
        '            "candidates": candidates,  # MUTANT: 空分母返回非空集',
    ),
    (
        "I6", "合成事件流不校验 record_id 真实存在",
        '        if store.get(rid) is None:',
        '        if False:  # MUTANT: 不校验存在性',
    ),
    (
        "I7", "合成事件流不拒绝完全重复事件",
        '        if key in seen_events:',
        '        if False:  # MUTANT: 允许重复事件',
    ),
    (
        "I8", "未知规则被静默忽略",
        '    if unknown_off:\n'
        '        raise SchemaError("exclude 含未知规则：%s" % sorted(unknown_off))',
        '    # MUTANT: 未知规则直接忽略',
    ),
    (
        "I9", "NOT_EVALUABLE 分支不标 MEASURED_ON_SYNTHETIC_ONLY",
        '            "measurement_scope": (SYNTHETIC_PREFIX if trace is not None\n'
        '                                  else "NOT_MEASURED"),\n'
        '            "note": ("分母为 0 ⇒ NOT_EVALUABLE。"',
        '            "measurement_scope": "NOT_MEASURED",  # MUTANT\n'
        '            "note": ("分母为 0 ⇒ NOT_EVALUABLE。"',
    ),
    (
        "I9b", "EVALUATED 分支不标 MEASURED_ON_SYNTHETIC_ONLY",
        '        "measurement_scope": (SYNTHETIC_PREFIX if trace is not None\n'
        '                              else "NOT_MEASURED"),\n'
        '        "note": ("候选资格集合 = 未被已声明规则排除的记录。"',
        '        "measurement_scope": "NOT_MEASURED",  # MUTANT\n'
        '        "note": ("候选资格集合 = 未被已声明规则排除的记录。"',
    ),
    (
        "I10", "空分母比例返回 0 而不是 None",
        '            "unverifiable_ratio": None,',
        '            "unverifiable_ratio": 0.0,  # MUTANT',
    ),
    (
        "I11", "B3 排除只看路径不看值（改成读 basis_conflict 而非 observed_origin）",
        '                and rec.get("observed_origin") == "model_generation"):',
        '                and rec.get("basis_conflict")\n'
        '                    == "asserted_contradicts_observed"):  # MUTANT',
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
# ⚠ 记录【是否为 None】的布尔值，而不只是值本身 ——
#   因为 None 与 0.0 在 JSON 里都能序列化，
#   只比值的化会被一起读成「差不多」。
def _empty_ratios():
    r = AI.synthetic_ratios(mk_empty_denom(), [])
    return {"unv": r["unverifiable_ratio"],
            "ro": r["record_only_ratio"],
            "unv_is_none": r["unverifiable_ratio"] is None,
            "ro_is_none": r["record_only_ratio"] is None}
out["empty_ratios"] = safe(_empty_ratios)

# V10 · record_only × model_generation（I11 会在此暴露：看 origin 还是看 conflict）
out["ro_model"] = safe(lambda: {
    "basis_conflict": mk_record_only_model().get("ro2")["basis_conflict"],
    "has_ro2": "ro2" in AI.importance_candidates(
        mk_record_only_model(), trace=[])["candidates"]})

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
    for mid, desc, old, new in MUTATIONS:
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

            if changed is None:
                status = "UNRESOLVED"
                evid = "E2：无法独立观测（%s）" % detail
            elif not changed:
                status = "UNRESOLVED"
                evid = ("直接观测：行为【未变】（%s）⇒ 该变异无效，"
                        "不得据此判断言强弱（M1）" % (detail or "无差异"))
            elif rc != 0:
                status = "CAUGHT"
                fails = [l.strip() for l in out.splitlines()
                         if "[FAIL]" in l or "[ERR ]" in l]
                evid = "行为已变（%s）；失败用例 %d 条：%s" % (
                    detail[:100], len(fails),
                    fails[0][:70] if fails else "（见输出）")
            else:
                status = "MISSED"
                evid = "行为已变（%s），但目标测试全绿 ⇒ 真漏洞" % detail[:100]

            rows.append((mid, desc, status, evid))
            print("  [%-11s] %-4s %s" % (status, mid, desc))
            print("               %s" % evid)

    print()
    print("=" * 84)
    counts = {}
    for _, _, st, _ in rows:
        counts[st] = counts.get(st, 0) + 1
    for st in ("CAUGHT", "UNRESOLVED", "MISSED", "INVALID"):
        if st in counts:
            print("  %-12s %d" % (st, counts[st]))
    print("=" * 84)

    bad = counts.get("MISSED", 0) + counts.get("INVALID", 0)
    verdict = "PASS" if bad == 0 else "FAIL"
    print("  判定：%s（共 %d 个变异）" % (verdict, len(rows)))
    if counts.get("UNRESOLVED", 0):
        print("  ⚠ UNRESOLVED %d 条：变异未改变可观测行为，不计入 CAUGHT，")
        print("    也不计入 MISSED —— 三态不合并（E2）。")

    out_dir = os.path.join(HERE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "mutations_importance_result.json"),
              "w", encoding="utf-8", newline="\n") as f:
        json.dump({"verdict": verdict, "counts": counts,
                   "rows": [{"id": a, "desc": b, "status": c, "evidence": d}
                            for a, b, c, d in rows]},
                  f, ensure_ascii=False, indent=2)
    print("  结果已写入 reports/mutations_importance_result.json")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
