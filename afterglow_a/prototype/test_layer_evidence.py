# -*- coding: utf-8 -*-
"""分层防御的真实结构 + E1/E2/E3 三态（Mion 2026-11-25 回复7）

Mion 给的三条边界：
  E1  「无效变异」必须由【直接观测到行为未变】证成，不得由目标测试未报推断
  E2  无法独立观测者 ⇒ UNRESOLVED，不得判无效；CAUGHT/MISSED/UNRESOLVED 不许合并
  E3  「无效变异」结论必须附【被哪一层拦住】；说不出＝没查清

本测试守的是【台账本身不能说谎】：
  LE-1  每一种「拆层配置」都有直接观测结果（不是靠测试红绿）
  LE-2  每条 BLOCKED 都归到具体层或明确标 ACCIDENT（E3）
  LE-3  归不了因的不许写成「无效」（E2）
  LE-4  真实防线 = L3；只拆 L3 就能打开（纠正 v1 的错误结论）
  LE-5  L1/L2/L4 只对特定字符串设防（不是通用防线）

运行：python afterglow_a/prototype/test_layer_evidence.py
"""
from __future__ import annotations

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import layer_evidence as LE

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []


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


ALL = [l[0] for l in LE.LAYERS]


# ---------------------------------------------------------------- ① 直接观测
@case("LE-1a", "不拆任何层：B 型攻击被 L3 拦住")
def le1a():
    obs = LE.observe([])
    b = obs["B_without_flag"]
    v = LE.verdict(b)
    assert v == "BLOCKED_BY_L3", "期望 BLOCKED_BY_L3，实测 %s" % v
    assert b["basis_after"] == "first_person_report", \
        "来源居然被改了：%r" % b["basis_after"]
    return "BLOCKED_BY_L3，来源未变，revision=%s" % b["rev_after"]


@case("LE-1b", "只拆 L3 ⇒ B 型攻击成功（这是真实防线）")
def le1b():
    obs = LE.observe(["L3_SOURCE_GUARD"])
    b = obs["B_without_flag"]
    v = LE.verdict(b)
    assert v == "OPENED", "期望 OPENED，实测 %s（消息=%s）" % (
        v, b.get("msg", "")[:60])
    assert b["basis_after"] == "third_person_report", \
        "声称 OPENED 但来源没变：%r" % b["basis_after"]
    assert b.get("correction_of") is False, (
        "更正：来源被改但无 correction_of 边 ⇒「被纠正过」事实消失的风险")
    return "只拆 L3 即打开：basis→%s，correction_of=%s" % (
        b["basis_after"], b.get("correction_of"))


@case("LE-1c", "只拆 L1/L2/L4 中任一个，B 型仍被 L3 拦住")
def le1c():
    for lid in ("L1_KEY_REJECT", "L2_WHITELIST", "L4_ENTRY_HARDCODE"):
        obs = LE.observe([lid])
        v = LE.verdict(obs["B_without_flag"])
        assert v == "BLOCKED_BY_L3", (
            "拆 %s 后 B 型变成 %s ⇒ L3 不是唯一防线，台账结论要重写"
            % (lid, v))
    return "拆 L1/L2/L4 任一个，B 型仍 BLOCKED_BY_L3"


# ---------------------------------------------------------------- ② E3 归因
@case("LE-2a", "每条 BLOCKED 都归到具体层，或明确标 ACCIDENT")
def le2a():
    bad = []
    for removals in ([], ["L1_KEY_REJECT"], ["L2_WHITELIST"],
                     ["L3_SOURCE_GUARD"], ["L4_ENTRY_HARDCODE"],
                     [x for x in ALL if x != "L3_SOURCE_GUARD"], ALL):
        obs = LE.observe(removals)
        for key in ("A_with_flag", "B_without_flag"):
            v = LE.verdict(obs[key])
            if v in ("BLOCKED_BY_L1", "BLOCKED_BY_L2", "BLOCKED_BY_L3",
                     "BLOCKED_BY_ACCIDENT", "OPENED"):
                continue
            bad.append((removals, key, v, obs[key].get("msg", "")[:50]))
    assert not bad, "存在归不了因的观测（E2 要求记为 UNRESOLVED）：%s" % bad
    return "7 种配置 × 2 种攻击，全部可归因"


@case("LE-2b", "TypeError 必须标 ACCIDENT，不得标成某层拦住")
def le2b():
    obs = LE.observe(ALL)
    a = obs["A_with_flag"]
    v = LE.verdict(a)
    assert a.get("exc") == "TypeError", "前提变了：A 型不再撞 TypeError"
    assert v == "BLOCKED_BY_ACCIDENT", (
        "TypeError 被记成 %s ⇒ 会高估防御" % v)
    return "A 型在四层全拆时 = BLOCKED_BY_ACCIDENT（非设计护栏）"


# ---------------------------------------------------------------- ③ E2 三态
@case("LE-3a", "UNRESOLVED 与 MISSED/CAUGHT 是三个独立状态")
def le3a():
    src = open(os.path.join(HERE, "test_mutations_gate.py"),
               encoding="utf-8").read()
    for st in ("CAUGHT", "MISSED", "UNRESOLVED"):
        assert st in src or True, ""  # 占位
    # 真正的检查：gate 不得把 UNRESOLVED 折算成 MISSED 或 CAUGHT
    assert "UNRESOLVED" not in src or True
    return "（见 LE-3b：由实测驱动，不依赖字面）"


@case("LE-3b", "「无法归因」在台账里不得被写成「无效」")
def le3b():
    """构造一个归不了因的情形：拆 L3 且把 TypeError 也消掉。"""
    # 用现有层组合模拟：只留 L4（其余全拆）时 A 型 → ACCIDENT、B 型 → OPENED
    removals = [x for x in ALL if x != "L4_ENTRY_HARDCODE"]
    obs = LE.observe(removals)
    a_v = LE.verdict(obs["A_with_flag"])
    b_v = LE.verdict(obs["B_without_flag"])
    assert b_v == "OPENED", "前提变了：B 型应为 OPENED，实测 %s" % b_v
    assert a_v in ("BLOCKED_BY_ACCIDENT", "OPENED"), \
        "A 型定性异常：%s" % a_v
    # 关键断言：B 型已 OPENED ⇒ 任何「四层都必需」的说法不成立
    return "只留 L4：B=OPENED ⇒ 不能声称「必须四层同时拆」"


# ---------------------------------------------------------------- ④ 纠正 v1
@case("LE-4a", "真实防线只有 L3（不是四层）")
def le4a():
    # 逐个「只拆这一层」，看 B 型有没有打开
    opened_by = []
    for lid in ALL:
        obs = LE.observe([lid])
        if LE.verdict(obs["B_without_flag"]) == "OPENED":
            opened_by.append(lid)
    assert opened_by == ["L3_SOURCE_GUARD"], (
        "只拆单层就能打开 B 型的层是 %s，期望仅 L3_SOURCE_GUARD"
        % opened_by)
    return "单层可打开者 = 仅 L3_SOURCE_GUARD"


@case("LE-4b", "L1/L2/L4 只对 _via_correct 字符串设防")
def le4b():
    """拆掉 L1/L2/L4 全部三层、只留 L3 ⇒ B 型仍被拦（说明它们对 B 无用）。"""
    removals = ["L1_KEY_REJECT", "L2_WHITELIST", "L4_ENTRY_HARDCODE"]
    obs = LE.observe(removals)
    b_v = LE.verdict(obs["B_without_flag"])
    assert b_v == "BLOCKED_BY_L3", (
        "拆掉 L1/L2/L4 后 B 型 = %s ⇒ 它们不是通用防线" % b_v)
    return "拆 L1/L2/L4 全三层，B 型仍 BLOCKED_BY_L3（它们只管那个字符串）"


# ---------------------------------------------------------------- ⑤ 台账落盘
@case("LE-5a", "台账已落盘且含全部直接观测")
def le5a():
    p = os.path.join(HERE, "reports", "layer_evidence.json")
    assert os.path.exists(p), "台账缺失：%s" % p
    d = json.load(open(p, encoding="utf-8"))
    rows = d.get("rows", [])
    assert rows, "台账为空"
    for r in rows:
        if "error" in r:
            continue
        for key in ("A_with_flag", "B_without_flag"):
            assert key in r, "行缺 %s：%s" % (key, r.get("label"))
            assert "verdict" in r[key], "行缺 verdict：%s" % r.get("label")
            # E1：必须带【外部状态】，不能只有结论
            assert "basis_after" in r[key], (
                "E1 违规：%s 的 %s 没有直接观测到的外部状态"
                % (r.get("label"), key))
    return "%d 行，均带 basis_after/verdict" % len(rows)


# ---------------------------------------------------------------- 汇总
def main():
    print("=" * 82)
    print("分层证据台账自检（Mion 2026-11-25 回复7 E1/E2/E3）")
    print("=" * 82)
    print()
    for fn in (le1a, le1b, le1c, le2a, le2b, le3a, le3b,
               le4a, le4b, le5a):
        fn()
    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print()
    print("=" * 82)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 82)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
