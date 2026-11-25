# -*- coding: utf-8 -*-
"""分层证据台账 v3（Mion 2026-11-25 裁定：F1/F2 + 纵深≠冗余 + G1/G2/G3）

修订史
------
v1  只测 A 型攻击 ⇒ 把 TypeError 误当成「拦住」⇒ 得出「必须四层同时拆」（错）
v2  分 A/B 两型 ⇒ 发现只有 L3 是真实防线
v3（本版）Mion 裁定后加三条：

    F1  每一层必须对【它声称覆盖的输入维度】各有一份独立观测，
        而「它声称覆盖哪些维度」必须先写下来。
        ⇒ 不写下来，就无法判断覆盖率，只能事后解释。

    F2  「换一种攻击路径」是 F1 的一个实例，不是 F1 本身。
        F1 要求的是【输入空间的抽样清单】，不是「再随便试一个」。

    G1  ACCIDENT（碰巧挡住）不得计入任何防御层，也不得计入 CAUGHT。
    G2  ACCIDENT 必须单列，并写明：它挡住的不是攻击，是攻击者的笔误。
    G3  若某条路径【只】被 ACCIDENT 挡住，该路径状态为 OPENED。

纵深 ≠ 冗余（Mion §二）
---------------------
    拦住【同一个输入】的多数层 = 冗余（REDUNDANCY）
    拦住【不同输入维度】的多层   = 纵深（COVERAGE）

    台账必须分开记：
        纵深主力        → BLOCKED_BY_Lx
        冗余覆盖        → COVERED_REDUNDANTLY_BY_Lx,Ly

用法：
    python layer_evidence.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 输入维度（F1）
#
# Mion F1：「它声称覆盖哪些维度」必须先写下来。
# ⇒ 这里就是那份清单。新增层必须先在此处声明它打算覆盖哪些维度。
#
# 每个维度 = (维度标识, 说明, 构造的 changes)
#   changes 就是攻击载荷。dimension 是「攻击面」，不是「攻击字符串」。

DIMENSIONS = [
    ("D1_FLAG_LEAK",
     "调用方在 changes 里塞内部标志 _via_correct，企图伪装成纠正流程",
     {"participation_basis": "third_person_report", "_via_correct": True}),
    ("D2_DIRECT_SOURCE_EDIT",
     "调用方不塞任何标志，直接要求改来源字段（participation_basis）",
     {"participation_basis": "third_person_report"}),
    ("D3_SOURCE_VIA_SOURCE_KIND",
     "绕开 participation_basis，改另一个来源字段 source_kind",
     {"source_kind": "third_party"}),
    ("D4_SOURCE_VIA_REF",
     "改来源引用 source_ref（同样的护栏应当覆盖）",
     {"source_ref": "doc/X"}),
]

# ---------------------------------------------------------------- 层定义（含声明维度）
#
# 每层 = (层标识, 说明, 声明覆盖的维度列表, 锚点原文, 替换为)
#
# ⚠ 声明维度 = 这一层【声称】自己拦哪些维度。
#   F1 要求：对它声称的每一条，都必须有一份独立观测。
#   若实测发现它其实拦不了某条 ⇒ 声明不实，必须显式标出。

LAYERS = [
    ("L1_KEY_REJECT",
     "显式拒收 changes 里的 _via_correct 键",
     ["D1_FLAG_LEAK"],
     '        if "_via_correct" in changes:\n'
     '            raise SchemaError(\n'
     '                "changes 不得包含保留键 _via_correct。"\n'
     '                "「是否纠正流程」由调用哪个方法来决定，不由调用方传入。")',
     '        # MUTANT: 拆掉 L1'),
    # ⚠ 2026-11-25（Mion 裁定2 H2 之后）：白名单行改过，本层锚点随之更新。
    #
    #   原先：`illegal = set(changes) - self._REVISABLE`
    #         —— 一行同时管「字段是否在白名单」与「来源字段是否被允许」。
    #   现在：来源字段移出 _REVISABLE，白名单行拆成两句：
    #            allowed = self._correctable() if via_correct else set(self._REVISABLE)
    #            illegal = set(changes) - allowed
    #         再往下还有一道独立的来源护栏 `if touching_source and not via_correct:`。
    #
    #   ⇒ 这两道【机制不同】（字段集 vs 流程判断），实测（diag_which.py）：
    #        拆白名单句 → D2 仍 BLOCKED（来源护栏拦）
    #        拆护栏句   → D2 仍 BLOCKED（白名单拦）
    #        两句都拆   → D2 OPENED
    #     所以它们对来源维度是【纵深 COVERAGE】，不是冗余。
    #
    #   ⚠ 变异体必须【只打一处机制】，否则「只留这一层」会变成「其实留了两层」。
    #     第一版把 allowed 改成 _correctable()（对所有 changes 都放行），
    #     结果连来源字段也一起放行 —— 于是「只留 L2」实测拦住的其实是 L3，
    #     台账把它误记成冗余。变异体只放行 _via_correct：
    #
    #   ⚠ 第二版仍有问题：只给 else 分支加 `{"_via_correct"}`。
    #     但 L4 的变异体会让 via_correct 变成 True（读 changes 里的标志），
    #     于是走 _correctable() 分支 —— 那里没有 _via_correct，
    #     照样被拦。两个变异体互相抵消，实测仍报「不允许变更字段」。
    #   ⇒ 现在给【两个分支】都放行 _via_correct，确保这一层真的被拆掉。
    ("L2_WHITELIST",
     "白名单：_via_correct 不属于任何一类合法字段",
     ["D1_FLAG_LEAK"],
     '        allowed = self._correctable() if via_correct else set(self._REVISABLE)',
     '        allowed = (self._correctable() | {"_via_correct"} if via_correct\n'
     '                   else set(self._REVISABLE) | {"_via_correct"})  # MUTANT'),
    ("L3_SOURCE_GUARD",
     "来源字段护栏：非 correct 流程不得改来源（与 L2 白名单机制不同）",
     ["D2_DIRECT_SOURCE_EDIT", "D3_SOURCE_VIA_SOURCE_KIND",
      "D4_SOURCE_VIA_REF"],
     '        if touching_source and not via_correct:',
     '        if False:  # MUTANT: 拆掉 L3'),
    # ⚠ L3 单独拆掉时 D2 仍被白名单拦（纵深，非冗余）。
    #   要观测「来源维度的真实纵深」，必须同时拆 L2+L3 ——
    #   这在 main() 的「只留这一层」矩阵里已经覆盖（D2 的 solo_guards
    #   会列出 L2 与 L3 两层，判为纵深/冗余由层数决定）。
    ("L4_ENTRY_HARDCODE",
     "公开入口硬编码 via_correct=False",
     ["D1_FLAG_LEAK"],
     '        return self._revise_impl(record_id, changes, reason, authority,\n'
     '                                 via_correct=False)',
     '        return self._revise_impl(record_id, changes, reason, authority,\n'
     '                                 via_correct=bool(\n'
     '                                     changes.get("_via_correct")))  # MUTANT'),
]

PROBE = r'''# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from afcore import Record, RecoveryStore
PIN = "2026-11-25T00:00:00Z"

def mk():
    s = RecoveryStore()
    s.insert(Record(record_id="r1", content="A 的原话",
        source_kind="user_utterance", source_ref="utt/A", participant_id="A",
        participation_basis="first_person_report", basis_ref="utt/A",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    return s

BASE = {"source_kind": "user_utterance", "source_ref": "utt/A",
        "participant_id": "A", "participation_basis": "first_person_report",
        "basis_ref": "utt/A"}

def run_case(payload):
    s = mk()
    try:
        s.revise("r1", dict(payload))
    except Exception as e:
        g = s.get("r1")
        return {"result": "BLOCKED", "exc": type(e).__name__,
                "msg": str(e)[:140],
                "state": {k: g[k] for k in BASE},
                "rev_after": g["revision"]}
    g = s.get("r1")
    return {"result": "SUCCEEDED", "exc": None, "msg": "",
            "state": {k: g[k] for k in BASE},
            "rev_after": g["revision"],
            "correction_of": any(r.get("relation_type") == "correction_of"
                                 for r in g["relation"])}

payloads = json.loads(sys.argv[1])
out = {}
for name, pl in payloads.items():
    out[name] = run_case(pl)
print("PROBE_JSON " + json.dumps({"results": out, "base": BASE},
                                ensure_ascii=False))
'''


def observe(removals):
    """拆掉指定层，对【全部维度】各跑一次探针。

    层定义支持两种形态：
        4 元组 (id, desc, dims, anchor, repl)        —— 单锚
        5 元组同上，但 anchor/repl 可含 "\\n---\\n" 分隔的多段（组合层）
    """
    td = tempfile.mkdtemp()
    try:
        shutil.copy2(os.path.join(HERE, "afcore.py"),
                     os.path.join(td, "afcore.py"))
        p = os.path.join(td, "afcore.py")
        s = open(p, encoding="utf-8").read()
        for lid in removals:
            layer = next(l for l in LAYERS if l[0] == lid)
            anchor, repl = layer[3], layer[4]
            if "\n---\n" in anchor or "\n---\n" in repl:
                anchors = anchor.split("\n---\n")
                repls = repl.split("\n---\n")
                if len(anchors) != len(repls):
                    return {"error": "%s 组合段数不齐" % lid}
            else:
                anchors, repls = [anchor], [repl]
            for i, a in enumerate(anchors):
                if s.count(a) != 1:
                    return {"error": "%s 第 %d 段锚点出现 %d 次" % (
                        lid, i + 1, s.count(a))}
                s = s.replace(a, repls[i], 1)
        open(p, "w", encoding="utf-8", newline="\n").write(s)
        open(os.path.join(td, "probe.py"), "w", encoding="utf-8").write(PROBE)
        payloads = {d[0]: d[2] for d in DIMENSIONS}
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(
            [sys.executable, os.path.join(td, "probe.py"),
             json.dumps(payloads, ensure_ascii=False)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=td, env=env, timeout=180)
        out = (r.stdout or "") + (r.stderr or "")
        for line in out.splitlines():
            if line.startswith("PROBE_JSON "):
                data = json.loads(line[len("PROBE_JSON "):])
                return data
        return {"error": out[-400:]}
    finally:
        shutil.rmtree(td, ignore_errors=True)


def classify(cell, base):
    """把一条观测定性。G1/G2/G3：ACCIDENT 不算任何防御。"""
    if cell.get("result") == "SUCCEEDED":
        return {"verdict": "OPENED", "blocker": None, "accident": False}
    exc = cell.get("exc") or ""
    msg = cell.get("msg", "")
    if "不得包含保留键" in msg:
        return {"verdict": "BLOCKED_BY_L1", "blocker": "L1_KEY_REJECT",
                "accident": False}
    if "不允许变更字段" in msg and "_via_correct" in msg:
        return {"verdict": "BLOCKED_BY_L2", "blocker": "L2_WHITELIST",
                "accident": False}
    if "不允许直接改来源字段" in msg:
        return {"verdict": "BLOCKED_BY_L3", "blocker": "L3_SOURCE_GUARD",
                "accident": False}
    if exc == "TypeError":
        return {"verdict": "ACCIDENT", "blocker": None, "accident": True}
    return {"verdict": "UNRESOLVED", "blocker": None, "accident": False}


def build_rows():
    all_ids = [l[0] for l in LAYERS]
    configs = [("（不拆）", [])]
    for lid in all_ids:
        configs.append(("只拆 " + lid, [lid]))
    configs.append(("四层全拆", all_ids))

    rows = []
    for label, removals in configs:
        obs = observe(removals)
        if "error" in obs:
            rows.append({"label": label, "removed": removals,
                         "error": obs["error"]})
            continue
        base = obs.get("base", {})
        cells = {}
        for dim in DIMENSIONS:
            d_id = dim[0]
            raw = obs["results"].get(d_id, {})
            if not raw:
                cells[d_id] = {"verdict": "UNRESOLVED", "blocker": None,
                               "accident": False, "state": {}}
                continue
            c = classify(raw, base)
            c["state"] = raw.get("state", {})
            c["msg"] = (raw.get("msg") or "")[:100]
            c["exc"] = raw.get("exc")
            cells[d_id] = c
        rows.append({"label": label, "removed": removals, "cells": cells,
                     "base": base})
    return rows


def dim_reference_class(row, dim_id):
    """在「不拆」基准下，这个维度实际由哪一层拦住（G3 的关键）。"""
    c = row["cells"].get(dim_id, {})
    v = c.get("verdict")
    if v == "OPENED":
        return None                 # 基准下就没拦住 ⇒ 该维度无防线
    if v == "ACCIDENT":
        return "ACCIDENT"           # 只被巧合挡住 ⇒ G3 视为 OPENED
    if v.startswith("BLOCKED_BY_"):
        return c.get("blocker")
    return None


def main():
    rows = build_rows()
    base_row = rows[0]

    # ---- F1：每层对它声称的维度，必须有独立观测
    print("=" * 108)
    print("F1 · 每层对其【声称覆盖】的维度，逐条观测")
    print("  台账不只看「有没有拦住」，看【声称的维度是否真的拦住】")
    print("=" * 108)
    print()

    claims = []
    for lid, desc, dims, anchor, repl in LAYERS:
        print("  %s — %s" % (lid, desc))
        print("    声称覆盖维度: %s" % (", ".join(dims) or "（无声明）"))
        for d_id in dims:
            # 拆掉本层，看该维度是否变成 OPENED
            removals = [lid]
            obs = observe(removals)
            if "error" in obs:
                claims.append((lid, d_id, "ERROR", obs["error"][:50]))
                print("      %-26s ERROR %s" % (d_id, obs["error"][:40]))
                continue
            raw = obs["results"].get(d_id, {})
            c = classify(raw, obs.get("base", {}))
            v = c["verdict"]
            if v == "OPENED":
                note = "拆掉本层即打开 ⇒ 本层是该维度的主力（纵深）"
                claims.append((lid, d_id, "PRIMARY", note))
            elif v == "ACCIDENT":
                note = "拆掉本层后仅剩 ACCIDENT ⇒ G3：该维度实为 OPENED"
                claims.append((lid, d_id, "ACCIDENT_ONLY", note))
            elif v.startswith("BLOCKED_BY_"):
                other = c.get("blocker")
                note = "拆掉本层仍被 %s 拦住 ⇒ 冗余（非纵深）" % other
                claims.append((lid, d_id, "REDUNDANT", note))
            else:
                note = "归不了因（E2）"
                claims.append((lid, d_id, "UNRESOLVED", note))
            print("      %-26s %-16s %s" % (d_id, v, note))
        print()

    # ---- 纵深 vs 冗余（Mion §二）
    print("=" * 108)
    print("纵深 ≠ 冗余 · 每个维度实际由谁拦住（基准「不拆」配置）")
    print("=" * 108)
    print()
    ref = {}
    for dim in DIMENSIONS:
        d_id, d_desc, _ = dim
        who = dim_reference_class(base_row, d_id)
        # 「独力拦住」的正确判据（Mion §二 纵深 vs 冗余）：
        #   只保留这一层、其余全拆 ⇒ 该维度仍被【它自己】拦住。
        # ⚠ 不是「只保留这一层时 OPENED」——那是反的。
        #   第一版写反了，得出「D1 没有独力守卫」的错误结论。
        all_ids = [l[0] for l in LAYERS]
        solo_guards = []
        for keep in all_ids:
            removals = [x for x in all_ids if x != keep]
            obs = observe(removals)
            if "error" in obs:
                continue
            c = classify(obs["results"].get(d_id, {}), obs.get("base", {}))
            if (c["verdict"].startswith("BLOCKED_BY_")
                    and c.get("blocker") == keep):
                solo_guards.append(keep)
        ref[d_id] = {"primary": who, "solo_guards": solo_guards}
        kind = "冗余 REDUNDANCY" if len(solo_guards) >= 2 else (
            "纵深 COVERAGE" if len(solo_guards) == 1 else "无独力守卫")
        print("  %-26s 基准拦住者=%-20s 独力守卫=%s" % (
            d_id, who or "（无）",
            ", ".join(solo_guards) or "（无）"))
        print("      ⇒ %s（可独力拦住的层数=%d）"
              % (kind, len(solo_guards)))
    print()
    print("  ⚠ 术语（Mion §二）：")
    print("     纵深 = 每层拦【不同的】输入维度 ⇒ 覆盖率相加")
    print("     冗余 = 多层拦【同一个】输入维度 ⇒ 少一层覆盖率不减")
    print("     冗余不是没用：它让「删掉一层」不立刻退化成「零防御」。")
    print("     但冗余不能拿来支撑「防御完好」。")
    print()
    print("  注：基准下 D1 的拦住者是 %s，但 L1 与 L2 互为冗余；"
          % (dim_reference_class(base_row, "D1_FLAG_LEAK") or "（无）"))
    print("      若两者都被拆（四层全拆），D1 只剩 ACCIDENT ⇒ 按 G3 记 OPENED。")
    print()

    # ---- G1/G2/G3
    print("=" * 108)
    print("G1/G2/G3 · ACCIDENT 不得计入防御")
    print("=" * 108)
    print()
    accidents = []
    for r in rows:
        if "error" in r:
            continue
        for d_id, c in r["cells"].items():
            if c.get("verdict") == "ACCIDENT":
                accidents.append((r["label"], d_id, c.get("exc")))
    if accidents:
        print("  观测到 ACCIDENT 的位置：")
        for label, d_id, exc in accidents:
            print("    %-24s %-26s %s" % (label, d_id, exc))
        print()
        print("  G2：ACCIDENT 挡住的不是攻击，是攻击者的笔误。")
        print("  G1：上述位置【不计入】任何防御层，也不计入 CAUGHT。")
        print("  G3：若某维度【只】被 ACCIDENT 挡住 ⇒ 该维度状态记为 OPENED。")
    else:
        print("  本配置组合下未观测到 ACCIDENT。")
        print("  ⚠ 但 G1/G2/G3 仍需由测试守住（构造一条只有 ACCIDENT 的路径）。")
    print()

    # ---- 四层全拆的最终判定（G3 口径）
    full = rows[-1]
    print("=" * 108)
    print("四层全拆 · 按 G3 口径的最终状态（ACCIDENT 视同 OPENED）")
    print("=" * 108)
    print()
    for dim in DIMENSIONS:
        d_id = dim[0]
        c = full["cells"].get(d_id, {})
        v = c.get("verdict")
        eff = "OPENED" if v == "ACCIDENT" else v
        print("  %-26s 原始=%-16s 按 G3=%s" % (d_id, v, eff))
    print()
    print("  ⇒ 凡是按 G3 变成 OPENED 的维度，说明它【没有真正的防线】。")
    print()

    out = os.path.join(HERE, "reports", "layer_evidence.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    payload = {
        "dimensions": [{"id": d[0], "desc": d[1]} for d in DIMENSIONS],
        "layer_claims": [{"id": l[0], "desc": l[1], "claims": l[2]}
                         for l in LAYERS],
        "claims_verified": [
            {"layer": a, "dimension": b, "kind": c, "note": d}
            for a, b, c, d in claims],
        "dimension_reference": ref,
        "accidents": [{"config": a, "dimension": b, "exc": c}
                      for a, b, c in accidents],
        "rows": rows,
    }
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("  台账已写入 reports/layer_evidence.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
