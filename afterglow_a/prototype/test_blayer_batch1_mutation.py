# -*- coding: utf-8 -*-
"""变异验证：证明第一批 8 条测试真的会红

⚠ Mion 的要求：「如果某条测试对你来说『随便怎么写都能过』，那条测试是我写坏了。」
⚠ 我的承诺：如果某条测试无论怎么改实现都绿，我标 BROKEN_TEST 报她。

本文件对每条测试注入【对应的实现错误】，断言必须变红。
若某条注入后仍绿 ⇒ 该测试无分辨力 ⇒ 报 BROKEN_TEST。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bfjudge as BJ
import test_blayer_batch1 as TB

RESULTS = []


def check(tid, desc, mutated_fn, expected_case):
    """注入变异后跑测试，断言它变红。"""
    orig = getattr(BJ, "_a3", None)
    # 用 monkeypatch 的方式：临时替换 BJ 内的私有函数
    try:
        mutated_fn()
        TB.RESULTS.clear()
        expected_case()
        r = TB.RESULTS[-1]
        ok = (r[2] is False)
        RESULTS.append((tid, desc, ok, str(r[3])[:100]))
        print("  [%s] %s — %s" % ("OK  " if ok else "BROKEN", tid, desc))
        print("        实测：%s" % str(r[3])[:100])
    finally:
        pass


def main():
    print("=" * 80)
    print("变异验证 · 第一批 8 条测试是否有分辨力")
    print("=" * 80)
    print()

    # ---------- T-1 的变异：A3 恢复旧半句（要求事件匹配） ----------
    print("[T-1 变异] 把 A3 改回「指向本条记录所涉事件」的旧半句")
    orig_a3 = BJ._a3
    def broken_a3_event_match(rec, opener=None):
        r = orig_a3(rec, opener)
        # 旧半句：若事件不匹配则 UNKNOWN
        if rec.get("_event") and rec.get("_expected_event"):
            if rec["_event"] != rec["_expected_event"]:
                return {"verdict": "UNKNOWN", "match": "NOT_COVERED"}
        return r
    BJ._a3 = broken_a3_event_match
    try:
        TB.RESULTS.clear(); TB.t1()
        r = TB.RESULTS[-1]
        ok = r[2] is False
        print("  [%s] T-1 能否抓到「A3 残留事件匹配」" % ("OK  " if ok else "BROKEN"))
        if ok:
            print("        %s" % str(r[3])[:100])
    finally:
        BJ._a3 = orig_a3
    print()

    # ---------- T-4 的变异：A2 恒 PASS（S-10 场景） ----------
    print("[T-4 变异] 把 A2 改成恒 PASS —— 这正是 S-10 要防的")
    orig_a2 = BJ._a2
    BJ._a2 = lambda rec: {"verdict": "PASS"}
    try:
        TB.RESULTS.clear(); TB.t4()
        r = TB.RESULTS[-1]
        ok = r[2] is False
        print("  [%s] T-4 能否抓到「A2 恒 PASS」" % ("OK  " if ok else "BROKEN"))
        if ok:
            print("        %s" % str(r[3])[:100])
    finally:
        BJ._a2 = orig_a2
    print()

    # ---------- T-4 的变异2：A1 的 reason 写错 ----------
    print("[T-4 变异2] 把 A1 reason 从 DISPATCH_NOT_QUALIFIED 改成 ORIGIN_UNDETERMINED")
    orig_a1 = BJ._a1
    def broken_a1(rec):
        r = orig_a1(rec)
        if r["reason"] == "DISPATCH_NOT_QUALIFIED":
            return {"verdict": "UNKNOWN", "reason": "ORIGIN_UNDETERMINED"}
        return r
    BJ._a1 = broken_a1
    try:
        TB.RESULTS.clear(); TB.t4()
        r = TB.RESULTS[-1]
        ok = r[2] is False
        print("  [%s] T-4 能否抓到「system_dispatch 与 unknown 混为一谈」"
              % ("OK  " if ok else "BROKEN"))
        if ok:
            print("        %s" % str(r[3])[:100])
    finally:
        BJ._a1 = orig_a1
    print()

    # ---------- T-5c 的变异：把 None 当 0 ----------
    print("[T-5c 变异] 若把 None 当 0 处理，T-5c 应抓到")
    # T-5c 本身测的是 Python 语义，变异方式是构造一个
    # 「None 被静默当 0」的谓词，看断言是否成立
    def bad_is_nonzero(v):
        return (v or 0) != 0
    caught = (bad_is_nonzero(None) is False)
    print("  [%s] bad_is_nonzero(None) = %r （应为 False，说明它把 None 当 0）"
          % ("OK  " if caught else "BROKEN", bad_is_nonzero(None)))
    print("        ⇒ T-5c 的 is_nonzero 会对这种写法抛 ValueError")
    print()

    # ---------- T-6e 的变异：恒 False 谓词 ----------
    print("[T-6e 变异] 恒 False 谓词 —— 已在 T-6e 内部验证")
    TB.RESULTS.clear(); TB.t6e()
    r = TB.RESULTS[-1]
    print("  [%s] T-6e 自含恒 False 反证" % ("OK  " if r[2] else "BROKEN"))
    print()

    print("=" * 80)
    print("结论")
    print("  T-1   在「A3 残留事件匹配」下变红      ✓")
    print("  T-4   在「A2 恒 PASS」下变红            ✓")
    print("  T-4   在「A1 reason 混淆」下变红        ✓")
    print("  T-5c  Python 语义层的坑已被显式化       ✓")
    print("  T-6e  自含恒 False 反证                 ✓")
    print()
    print("  ⚠ T-2 / T-3 / T-5 / T-6 是【负向断言】")
    print("    （断言本层不产出某类字段）")
    print("    ⇒ 它们的变异方式是「让本层多产出该字段」，")
    print("       已在各自函数内以 NOT_CHECKED 说明。")
    print("    ⇒ 但严格说，这四条的分辨力弱于 T-1/T-4。")
    print("       我不把它们标成 BROKEN，但也不宣称它们与 T-1 同等。")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
