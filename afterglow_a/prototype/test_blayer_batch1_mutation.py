# -*- coding: utf-8 -*-
"""B 层第一批 · 变异验证 —— 证明 8 条测试【真的会变红】

绑定：v0.4 (9031df2)

做法：对每条断言，注入对应的实现错误（monkeypatch），
      断言该测试必须失败。若某个变异下测试仍然绿，说明那条测试没有分辨力。

⚠ 这不是"再跑一遍测试"。这是【反证测试本身有效】。
   上一轮的教训：把"没写断言"当成"测试通过"。
   本文件对每条 T 都给出至少一个变异。
"""
from __future__ import annotations

import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bfjudge as BJ
import lbjudge as LB
import test_blayer_batch1 as T

OUT = []


def _run_one(name):
    """跑单条测试函数，返回 True=通过 / False=失败。"""
    fn = getattr(T, name)
    T.RESULTS.clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return bool(T.RESULTS and T.RESULTS[0][2]), (T.RESULTS[0][3] if T.RESULTS else "")


def mutate(cid, desc, patch, unpatch, test_name):
    """注入变异 → 断言该测试变红 → 还原。"""
    patch()
    try:
        ok, detail = _run_one(test_name)
    finally:
        unpatch()
    # 变异生效后测试必须【失败】
    passed = (ok is False)
    OUT.append((cid, desc, test_name, passed, detail))
    print("  [%s] %s | 变异：%s | 测试 %s %s"
          % ("OK  " if passed else "MISS", cid, desc, test_name,
             "翻红" if ok is False else "仍然绿（无分辨力）"))
    return passed


def main():
    print("=" * 80)
    print("变异验证 —— 每条测试注入实现错误后必须变红")
    print("=" * 80)
    print()

    # ---------------- T-1：A3 空引用判 FAIL（v0.3 旧行为）+ 缺 multi_ref
    orig_a3 = BJ._a3

    def patch_t1():
        def bad_a3(rec, opener=None):
            d = orig_a3(rec, opener)
            d.pop("multi_ref", None)   # 删除 multi_ref ⇒ T-1 断言失败
            return d
        BJ._a3 = bad_a3
    mutate("M-1a", "A3 返回值缺 multi_ref", patch_t1,
           lambda: setattr(BJ, "_a3", orig_a3), "t1")

    def patch_t1b():
        def bad_a3(rec, opener=None):
            d = orig_a3(rec, opener)
            d["match"] = "MATCHED"     # 谎称做了事件匹配
            return d
        BJ._a3 = bad_a3
    mutate("M-1b", "A3.match 谎称 MATCHED", patch_t1b,
           lambda: setattr(BJ, "_a3", orig_a3), "t1")

    # ---------------- T-2：delta=0 判成 SUPPORTED / B4 写成 ESTABLISHED
    orig_judge = LB.judge_impact

    def patch_t2():
        def bad(obs, excluded, **kw):
            d = orig_judge(obs, excluded, **kw)
            if d["B3-OBS"]["delta"] == 0:
                d["B3-CLAIM"] = "SUPPORTED"   # delta=0 当成有影响
                d["B4"] = "ESTABLISHED"
            return d
        LB.judge_impact = bad
    mutate("M-2", "delta=0 判 SUPPORTED/ESTABLISHED", patch_t2,
           lambda: setattr(LB, "judge_impact", orig_judge), "t2")

    # ---------------- T-3：MECH 无视通路控制
    orig_mech = LB.judge_mechanism

    def patch_t3():
        def bad(r_a, r_b, pathway_registered_and_controlled, **kw):
            # 错误：只看差值，不看通路
            m = "NOT_DETECTED" if r_a == r_b else "DETECTED"
            return {"MECH": m, "scope": LB._scope("r", "f", "o"), "reasons": []}
        LB.judge_mechanism = bad
    mutate("M-3", "MECH 无视通路受控（有差值就 DETECTED）", patch_t3,
           lambda: setattr(LB, "judge_mechanism", orig_mech), "t3")

    # ---------------- T-4：A2 恒 PASS（只断言 admitted 会漏）
    orig_a2 = BJ._a2

    def patch_t4():
        BJ._a2 = lambda rec: {"verdict": "PASS"}
    mutate("M-4a", "A2 恒 PASS", patch_t4,
           lambda: setattr(BJ, "_a2", orig_a2), "t4")

    def patch_t4b():
        def bad_a1(rec):
            d = _orig_a1(rec)
            if d["reason"] == "DISPATCH_NOT_QUALIFIED":
                d["reason"] = "ORIGIN_UNDETERMINED"  # 混了「不合格」与「不知道」
            return d
        _orig_a1 = BJ._a1
        BJ._a1 = bad_a1
    _saved_a1 = BJ._a1
    mutate("M-4b", "A1 把 DISPATCH 写成 UNDETERMINED", patch_t4b,
           lambda: setattr(BJ, "_a1", _saved_a1), "t4")

    # ---------------- T-5：readout_valid=false 时给出 delta 并判 NOT_DETECTED
    def patch_t5():
        def bad(obs, excluded, **kw):
            if not obs.get("readout_valid"):
                # 错误：忽略 readout_valid，直接按 delta 判
                d = {"B3-OBS": {"delta": 0, "delivered": True,
                                "readout_valid": False},
                     "B3-CLAIM": "NOT_DETECTED", "B4": "INDETERMINATE",
                     "scope": LB._scope("r", "f", "o")}
                return d
            return orig_judge(obs, excluded, **kw)
        LB.judge_impact = bad
    mutate("M-5", "readout_valid=false 仍判 NOT_DETECTED", patch_t5,
           lambda: setattr(LB, "judge_impact", orig_judge), "t5")

    # ---------------- T-5c：D-1 校验失效（不拒绝 null）
    orig_check = LB._check_delta_contract

    def patch_t5c():
        LB._check_delta_contract = lambda delta, readout_valid: None
    mutate("M-5c", "去掉 D-1/D-2 校验（null 可进比较）", patch_t5c,
           lambda: setattr(LB, "_check_delta_contract", orig_check), "t5c")

    # ---------------- T-6：空跑重现也判 EXCLUDED=True
    orig_excl = LB.evaluate_excluded

    def patch_t6():
        def bad(negative_control_reproduced, alternative_terms,
                excluded_terms, positive_control_ok):
            # 错误：只看正对照，不看空跑与清单
            return {"EXCLUDED": bool(positive_control_ok),
                    "remaining": [], "reason": "BAD"}
        LB.evaluate_excluded = bad
    mutate("M-6", "空跑重现也判 EXCLUDED=True", patch_t6,
           lambda: setattr(LB, "evaluate_excluded", orig_excl), "t6")

    # ---------------- T-6e：EXCLUDED 恒 False（T-6 全绿也测不出来）
    def patch_t6e():
        def bad(**kw):
            return {"EXCLUDED": False, "remaining": [], "reason": "ALWAYS_FALSE"}
        LB.evaluate_excluded = bad
    mutate("M-6e", "EXCLUDED 恒 False", patch_t6e,
           lambda: setattr(LB, "evaluate_excluded", orig_excl), "t6e")

    # ---------------- T-7：回到上一版行为（空清单 → TRUE）
    def patch_t7():
        def bad(negative_control_reproduced, alternative_terms,
                excluded_terms, positive_control_ok):
            # 上一版 6b4e3e5 的实现：空清单 ⇒ TRUE
            if not positive_control_ok:
                return {"EXCLUDED": False, "INDETERMINATE": False,
                        "remaining": list(alternative_terms),
                        "reason": "POSITIVE_CONTROL_FAILED"}
            if negative_control_reproduced:
                return {"EXCLUDED": False, "INDETERMINATE": False,
                        "remaining": list(alternative_terms),
                        "reason": "NEGATIVE_CONTROL_REPRODUCED_DRIFT"}
            if not alternative_terms:
                return {"EXCLUDED": True, "INDETERMINATE": False,
                        "remaining": [], "reason": "NO_ALTERNATIVES_REGISTERED"}
            return orig_excl(negative_control_reproduced, alternative_terms,
                             excluded_terms, positive_control_ok)
        LB.evaluate_excluded = bad
    mutate("M-7", "空清单判 TRUE（回到上一版行为）", patch_t7,
           lambda: setattr(LB, "evaluate_excluded", orig_excl), "t7")

    # ---------------- T-8：DETECTED 变得可达（删掉通路检查）
    def patch_t8():
        def bad(r_a, r_b, pathway_registered_and_controlled, **kw):
            # 错误：删掉通路受控检查 ⇒ 有差值就 DETECTED
            m = "NOT_DETECTED" if r_a == r_b else "DETECTED"
            return {"MECH": m, "scope": LB._scope("r", "f", "o"), "reasons": []}
        LB.judge_mechanism = bad
    mutate("M-8", "删掉通路受控检查 ⇒ DETECTED 可达", patch_t8,
           lambda: setattr(LB, "judge_mechanism", orig_mech), "t8")

    # ---------------- T-8 第二变异：只改扫描表的某一路径可达
    #   （验 T-8 的断言不只依赖「r_A != r_B 那一条」）
    orig_scan = LB.scan_stage_call_sites

    def patch_t8b():
        def bad_scan():
            return {"results": [("伪造入口", "DETECTED")],
                    "detected_reachable": True}
        LB.scan_stage_call_sites = bad_scan
    mutate("M-8b", "扫描表报告某入口 DETECTED", patch_t8b,
           lambda: setattr(LB, "scan_stage_call_sites", orig_scan), "t8")

    # ---------------- T-8 第三变异：把 DETECTED 从枚举里删掉（E-19-1）
    orig_mech_set = LB.MECH

    def patch_t8c():
        LB.MECH = {"NOT_DETECTED", "INDETERMINATE"}
    mutate("M-8c", "从枚举里删掉 DETECTED（E-19-1）", patch_t8c,
           lambda: setattr(LB, "MECH", orig_mech_set), "t8")

    # ---------------- T-8 第四变异：覆盖不标 PARTIAL（E-22-3 沉默）
    def patch_t8d():
        def bad_scan():
            return {"results": [("x", "INDETERMINATE")],
                    "detected_reachable": False,
                    "coverage": "EXHAUSTIVE"}   # 无依据却声称穷尽
        LB.scan_stage_call_sites = bad_scan
    mutate("M-8d", "无依据却声称穷尽覆盖（E-22-3 沉默的反面）", patch_t8d,
           lambda: setattr(LB, "scan_stage_call_sites", orig_scan), "t8")

    # ---------------- T-9：pathway=True 退回旧行为（返回 INDETERMINATE 不抛）
    def patch_t9():
        def bad(r_a, r_b, pathway_registered_and_controlled, **kw):
            return {"MECH": "INDETERMINATE",
                    "scope": LB._scope("r", "f", "o"),
                    "reasons": ["PATHWAY_NOT_CONTROLLED"]}
        LB.judge_mechanism = bad
    mutate("M-9", "pathway=True 静默返回 INDETERMINATE（不抛）", patch_t9,
           lambda: setattr(LB, "judge_mechanism", orig_mech), "t9")

    # ---------------- T-9 第二变异：抛 ValueError 而非 UnsupportedPremise
    def patch_t9b():
        class WrongErr(ValueError):
            pass

        def bad(r_a, r_b, pathway_registered_and_controlled, **kw):
            if pathway_registered_and_controlled:
                raise WrongErr("pathway not supported")
            return orig_mech(r_a, r_b, pathway_registered_and_controlled, **kw)
        LB.judge_mechanism = bad
        LB.UnsupportedPremise = WrongErr   # 让 except LB.UnsupportedPremise 也命中
    _saved_up = LB.UnsupportedPremise
    mutate("M-9b", "pathway=True 抛 ValueError 子类", patch_t9b,
           lambda: (setattr(LB, "judge_mechanism", orig_mech),
                    setattr(LB, "UnsupportedPremise", _saved_up)), "t9")

    # ---------------- T-10：单向不变量（None ⇒ flag=True，但反向不成立）
    def patch_t10():
        # 错误：允许 flag=True 而 value=False
        def bad_inv(result):
            if result.get("EXCLUDED") is None and result.get("INDETERMINATE") is not True:
                raise ValueError("E-21-1 violated")
        LB.check_e21_invariant = bad_inv
    _orig_inv = LB.check_e21_invariant
    mutate("M-10", "不变量改成单向（允许 False + flag=True）", patch_t10,
           lambda: setattr(LB, "check_e21_invariant", _orig_inv), "t10")

    # ---------------- T-10 第二变异：往 lbjudge.py 注入布尔化消费
    #   ⚠ 这需要临时改源码，故用文件内容替换 + 还原。
    lb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "lbjudge.py")

    def patch_t10b():
        with io.open(lb_path, encoding="utf-8") as fh:
            src = fh.read()
        # 在 _branch_unreachable 之前插入一个真实（非注释）的布尔化消费
        marker = "def _branch_unreachable("
        inject = (
            "def _e21_bad_consumer(excluded):\n"
            "    if excluded:\n"
            "        return 'whatever'\n"
            "    return None\n\n\n"
        )
        with io.open(lb_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src.replace(marker, inject + marker, 1))

    def unpatch_t10b():
        with io.open(lb_path, encoding="utf-8") as fh:
            src = fh.read()
        inject = (
            "def _e21_bad_consumer(excluded):\n"
            "    if excluded:\n"
            "        return 'whatever'\n"
            "    return None\n\n\n"
        )
        with io.open(lb_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src.replace(inject, "", 1))
    mutate("M-10b", "往 lbjudge.py 注入真实 `if excluded:`", patch_t10b,
           unpatch_t10b, "t10")

    # ---------------- 汇总
    total = len(OUT)
    ok = sum(1 for r in OUT if r[3])
    print()
    print("=" * 80)
    print("变异总数 %d  被抓住 %d  漏网 %d" % (total, ok, total - ok))
    print("=" * 80)
    if ok != total:
        print("\n⚠ 以下变异未被抓住（对应测试无分辨力）：")
        for cid, desc, tname, passed, detail in OUT:
            if not passed:
                print("  %s | %s | 测试 %s" % (cid, desc, tname))
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
