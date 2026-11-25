# -*- coding: utf-8 -*-
"""分层证据台账 v2（Mion 2026-11-25 回复7 E1/E2/E3）

为什么有 v2
-----------
v1 的探针只测【一种攻击】：往 changes 里塞 "_via_correct": True。
于是台账里出现了三个假象：

  1. 「四层全拆 → BLOCKED」——
     其实是 `_via_correct` 被放行后进到 `Record(**merged)`，
     撞上 `TypeError: __init__() got an unexpected keyword argument`。
     **这是构造函数不接受多余键的副产品，不是设计上的护栏。**

  2. 「只留 L3 → BLOCKED」—— 同样是 TypeError，不是 L3 拦下的。

  3. 由此得出「必须四层同时拆才打得穿」——**这个结论是错的。**

真因：v1 只测了「塞那个字符串」这一条路。
换一条路（不塞该字符串，直接改来源）就能看出，
真正在守「改来源必须走 correct()」的，只有 L3_SOURCE_GUARD 一层。

Mion 回复7 E1 的要求正是这个：
    必须独立打出【被变异点的实际结果】，不能来自目标测试的红绿。

被变异点是「护栏」，不是「某个特定攻击字符串」。
所以本文件用两种攻击分别观测：

    A 型  往 changes 里塞 "_via_correct": True
          —— 只对 L1/L2/L4 的字符串检查有效
    B 型  不塞，直接改 participation_basis
          —— 只对 L3 的来源字段护栏有效

判据不写成「测试是否红」，写成【外部状态是否被改变】：
    SUCCEEDED                → 漏洞真被打开
    BLOCKED_BY_Lx            → 被第 x 层拦住（归因明确，满足 E3）
    BLOCKED_BY_ACCIDENT      → 被非设计因素挡住（TypeError 等）⇒ 不算防御
    UNRESOLVED               → 归不了因（E2：不许判「无效」）

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

# ---------------------------------------------------------------- 层定义
LAYERS = [
    ("L1_KEY_REJECT",
     "显式拒收 changes 里的 _via_correct 键",
     '        if "_via_correct" in changes:\n'
     '            raise SchemaError(\n'
     '                "changes 不得包含保留键 _via_correct。"\n'
     '                "「是否纠正流程」由调用哪个方法来决定，不由调用方传入。")',
     '        # MUTANT: 拆掉 L1'),
    ("L2_WHITELIST",
     "白名单 _REVISABLE 不含 _via_correct",
     '        illegal = set(changes) - self._REVISABLE',
     '        illegal = set(changes) - self._REVISABLE - {"_via_correct"}  # MUTANT'),
    ("L3_SOURCE_GUARD",
     "来源字段护栏：非 correct 流程不得改来源",
     '        if touching_source and not via_correct:',
     '        if False:  # MUTANT: 拆掉 L3'),
    ("L4_ENTRY_HARDCODE",
     "公开入口硬编码 via_correct=False",
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

def run_case(changes):
    s = mk()
    try:
        s.revise("r1", dict(changes))
    except Exception as e:
        return {"result": "BLOCKED", "exc": type(e).__name__,
                "msg": str(e)[:110],
                "basis_after": s.get("r1")["participation_basis"],
                "rev_after": s.get("r1")["revision"]}
    g = s.get("r1")
    return {"result": "SUCCEEDED", "exc": None, "msg": "",
            "basis_after": g["participation_basis"],
            "rev_after": g["revision"],
            "correction_of": any(r.get("relation_type") == "correction_of"
                                 for r in g["relation"])}

out = {
    "A_with_flag": run_case({"participation_basis": "third_person_report",
                             "_via_correct": True}),
    "B_without_flag": run_case({"participation_basis": "third_person_report"}),
}
print("PROBE_JSON " + json.dumps(out, ensure_ascii=False))
'''


def observe(removals):
    td = tempfile.mkdtemp()
    try:
        shutil.copy2(os.path.join(HERE, "afcore.py"),
                     os.path.join(td, "afcore.py"))
        p = os.path.join(td, "afcore.py")
        s = open(p, encoding="utf-8").read()
        for lid in removals:
            layer = next(l for l in LAYERS if l[0] == lid)
            if s.count(layer[2]) != 1:
                return {"error": "%s 锚点出现 %d 次" % (lid, s.count(layer[2]))}
            s = s.replace(layer[2], layer[3], 1)
        open(p, "w", encoding="utf-8", newline="\n").write(s)
        open(os.path.join(td, "probe.py"), "w", encoding="utf-8").write(PROBE)
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, os.path.join(td, "probe.py")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=td, env=env, timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
        for line in out.splitlines():
            if line.startswith("PROBE_JSON "):
                return json.loads(line[len("PROBE_JSON "):])
        return {"error": out[-300:]}
    finally:
        shutil.rmtree(td, ignore_errors=True)


def verdict(cell):
    """把一条观测定性。看的是【外部状态】，不是测试红绿。"""
    if cell.get("result") == "SUCCEEDED":
        return "OPENED"
    exc = cell.get("exc") or ""
    msg = cell.get("msg", "")
    if "不得包含保留键" in msg:
        return "BLOCKED_BY_L1"
    if "不允许变更字段" in msg and "_via_correct" in msg:
        return "BLOCKED_BY_L2"
    if "不允许直接改来源字段" in msg:
        return "BLOCKED_BY_L3"
    if exc == "TypeError":
        return "BLOCKED_BY_ACCIDENT"
    return "UNRESOLVED"


def main():
    all_ids = [l[0] for l in LAYERS]

    combos = [("（不拆）", [])]
    for lid, desc, _, _ in LAYERS:
        combos.append(("只拆 " + lid, [lid]))
    combos.append(("只留 L3_SOURCE_GUARD",
                   [x for x in all_ids if x != "L3_SOURCE_GUARD"]))
    combos.append(("只留 L3 + L1",
                   [x for x in all_ids
                    if x not in ("L3_SOURCE_GUARD", "L1_KEY_REJECT")]))
    combos.append(("四层全拆", all_ids))

    rows = []
    for label, removals in combos:
        obs = observe(removals)
        if "error" in obs:
            rows.append({"label": label, "removed": removals,
                         "error": obs["error"]})
            continue
        a = dict(obs["A_with_flag"])
        b = dict(obs["B_without_flag"])
        a["verdict"] = verdict(a)
        b["verdict"] = verdict(b)
        rows.append({"label": label, "removed": removals,
                     "A_with_flag": a, "B_without_flag": b})

    print("=" * 106)
    print("分层证据台账 v2（Mion 2026-11-25 回复7 E1/E2/E3）")
    print("  A 型 = 塞 _via_correct（针对 L1/L2/L4 的字符串检查）")
    print("  B 型 = 只改来源、不塞（只针对 L3 的来源护栏）")
    print("=" * 106)
    print()
    print("  %-24s | %-24s | %-24s"
          % ("拆掉的层", "A 塞 _via_correct", "B 只改来源"))
    print("  " + "-" * 102)
    for r in rows:
        if "error" in r:
            print("  %-24s | ERROR %s" % (r["label"], r["error"]))
            continue
        print("  %-24s | %-24s | %-24s"
              % (r["label"], r["A_with_flag"]["verdict"],
                 r["B_without_flag"]["verdict"]))
    print()

    print("=" * 106)
    print("结论（这是 v1 说错的地方，以本次实测为准）")
    print("=" * 106)
    print()

    b_open = [r for r in rows
              if r.get("B_without_flag", {}).get("result") == "SUCCEEDED"]
    print("  B 型被打开的配置：")
    for r in b_open:
        print("    ! %s" % r["label"])
    print()
    print("  ⇒ 真正守住「改来源必须走 correct()」的只有 L3_SOURCE_GUARD。")
    print("  ⇒ L1/L2/L4 只对 `_via_correct` 这个【特定字符串】设防；")
    print("     攻击者不写这个字符串，三层全部不起作用。")
    print()
    print("  ⇒ 四层全拆时出现 TypeError，是 `Record(**merged)` 不接受")
    print("     多余键的副产品 —— 不是设计上的护栏。")
    print("     把它记成「拦住」会高估防御，记成「无效变异」会低估缺口。")
    print()
    print("  ⇒ v1 那句「必须四层同时拆才打得穿」是错的：")
    print("     只拆 L3 就打得穿（B 型）。我当时只测了 A 型，看不出来。")
    print("=" * 106)

    out = os.path.join(HERE, "reports", "layer_evidence.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"rows": rows}, f, ensure_ascii=False, indent=2)
    print("  台账已写入 reports/layer_evidence.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
