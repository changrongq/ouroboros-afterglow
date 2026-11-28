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

    # ---------------- T-11：新增一个未登记的生产调用点（E-25-1 必须红）
    #   做真实的文件写入再还原 —— 这是 E-25 要抓的那件事本身。
    probe = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "_e25_probe_prod.py")

    def patch_t11():
        with io.open(probe, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "# 临时探针：模拟一个【新增的生产调用点】\n"
                "import lbjudge\n\n\n"
                "def some_new_production_path():\n"
                "    return lbjudge.judge_mechanism(\n"
                "        r_a='BLUE', r_b='RED',\n"
                "        pathway_registered_and_controlled=False,\n"
                "        drift_control_explains=False,\n"
                "        readout_has_resolution=True)\n"
            )

    def unpatch_t11():
        if os.path.exists(probe):
            os.remove(probe)
    mutate("M-11", "新增一个未登记的生产调用点", patch_t11, unpatch_t11, "t11")

    # ---------------- T-11 第二变异：扫描器返回空（断言会因「无对象」而红）
    orig_cov = LB.check_call_site_coverage

    def patch_t11b():
        LB.check_call_site_coverage = lambda repo_root=None: {
            "ok": True, "hits": [], "missing_from_registry": [],
            "exemptions_applied": [], "registered_functions": []}
    mutate("M-11b", "扫描器返回空（空扫描让断言永远绿）", patch_t11b,
           lambda: setattr(LB, "check_call_site_coverage", orig_cov), "t11")

    # ---------------- T-11 第三变异：造一条过期豁免（列了不存在的豁免）
    orig_exempt = LB.CALL_SITE_EXEMPTIONS

    def patch_t11c():
        LB.CALL_SITE_EXEMPTIONS = list(orig_exempt) + [
            ("lbjudge.py", "no_such_function_exists", "过期豁免")]
    mutate("M-11c", "造一条过期豁免", patch_t11c,
           lambda: setattr(LB, "CALL_SITE_EXEMPTIONS", orig_exempt), "t11")

    # ---------------- T-12：三字段两两成立而第三项矛盾（E-24-2）
    def patch_t12():
        def bad_inv(result):
            # 错误：只查前两项，不查 reason
            if (result.get("EXCLUDED") is None) != bool(
                    result.get("excluded_undetermined")):
                raise ValueError("E-24-2 violated")
        LB.check_e21_invariant = bad_inv
    mutate("M-12", "不变量漏查 reason（允许两两成立而第三项矛盾）", patch_t12,
           lambda: setattr(LB, "check_e21_invariant", _orig_inv), "t12")

    # ---------------- T-12 第二变异：两种措辞合并成同一句（E-24-3）
    orig_wording = LB.wording_for

    def patch_t12b():
        LB.wording_for = lambda reason, n_unexcluded=0: "无法判定是否已排除"
    mutate("M-12b", "两种判不出措辞合并成同一句", patch_t12b,
           lambda: setattr(LB, "wording_for", orig_wording), "t12")

    # ---------------- T-12 第三变异：evaluate_excluded 出口漏 excluded_undetermined
    orig_branch = LB._excl_branch

    def patch_t12c():
        def bad_branch(*a, **kw):
            r = orig_branch(*a, **kw)
            r.pop("excluded_undetermined", None)
            return r
        LB._excl_branch = bad_branch
    mutate("M-12c", "evaluate_excluded 出口漏第三字段", patch_t12c,
           lambda: setattr(LB, "_excl_branch", orig_branch), "t12")

    # ---------------- T-13：BINDING 指向一个不存在的文档（E-27 那次事故本身）
    import check_binding_docs as CBD
    orig_binding = list(CBD.BINDING_DOCS)

    def patch_t13():
        CBD.BINDING_DOCS.append(
            ("伪造", "____this_doc_never_existed____.md"))
    mutate("M-13", "BINDING 列入一份从未存在的文档（E-27 事故复现）",
           patch_t13,
           lambda: setattr(CBD, "BINDING_DOCS", list(orig_binding)), "t13")

    # ---------------- T-13 第二变异：清单变空（断言无对象，必须红）
    def patch_t13b():
        CBD.BINDING_DOCS = []
    mutate("M-13b", "BINDING 清单变空", patch_t13b,
           lambda: setattr(CBD, "BINDING_DOCS", list(orig_binding)), "t13")

    # ---------------- T-13 第三变异：head_blob 恒返回假 sha（扫描失效）
    orig_head_blob = CBD.head_blob

    def patch_t13c():
        CBD.head_blob = lambda rel, repo_root=None: "0" * 40
    mutate("M-13c", "head_blob 恒返回假 sha", patch_t13c,
           lambda: setattr(CBD, "head_blob", orig_head_blob), "t13")

    # ================================================================
    # 勘误007 的两条：Q1 逐文件放行 / 四出口汇一个点
    # ================================================================

    # ---------------- M-14：把测试豁免改回「按模式」（Q1 的原始缺陷）
    orig_test_exempt = list(LB.TEST_FILE_EXEMPTIONS)

    def patch_t11e():
        # 模拟「按模式放行」的实现：往豁免表里塞一条 glob 模式
        LB.TEST_FILE_EXEMPTIONS = orig_test_exempt + [
            ("afterglow_a/prototype/test_*.py", "按模式放行（错误做法）")]
    mutate("M-14", "测试豁免改回按模式（Q1 原始缺陷）", patch_t11e,
           lambda: setattr(LB, "TEST_FILE_EXEMPTIONS", list(orig_test_exempt)),
           "t11")

    # ---------------- M-14b：造一条过期测试豁免（列了扫不到的文件）
    def patch_t11f():
        LB.TEST_FILE_EXEMPTIONS = orig_test_exempt + [
            ("afterglow_a/prototype/test_no_such_file.py", "过期")]
    mutate("M-14b", "造一条过期测试豁免", patch_t11f,
           lambda: setattr(LB, "TEST_FILE_EXEMPTIONS", list(orig_test_exempt)),
           "t11")

    # ---------------- M-14c：新增一个未登记的测试文件并让它调用
    #   ⚠ 这是 Q1 真正的攻击场景：新测试文件自动被放行 = 没人看过它。
    probe_test = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "_t_no_such_test_probe.py")

    def patch_t11g():
        with io.open(probe_test, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "# 临时探针：一个未登记进 TEST_FILE_EXEMPTIONS 的测试文件\n"
                "import lbjudge\n\n\n"
                "def probe():\n"
                "    return lbjudge.judge_mechanism(\n"
                "        r_a=1, r_b=2,\n"
                "        pathway_registered_and_controlled=False,\n"
                "        drift_control_explains=False,\n"
                "        readout_has_resolution=True)\n"
            )

    def unpatch_t11g():
        if os.path.exists(probe_test):
            os.remove(probe_test)
    mutate("M-14c", "新增未登记的测试文件（按模式会放过它）",
           patch_t11g, unpatch_t11g, "t11")

    # ---------------- M-15：结构修复倒退 —— 把 _pack_excluded 改成漏字段
    #   ⚠ 勘误007 之前，「漏第三字段」只能靠断言抓；
    #      现在唯一产出点被改了，应当仍然红（断言仍需要作为第二道）。
    orig_pack = LB._pack_excluded

    def patch_t12d():
        def bad_pack(excluded, reason, remaining):
            d = orig_pack(excluded, reason, remaining)
            d.pop("excluded_undetermined", None)
            return d
        LB._pack_excluded = bad_pack
    mutate("M-15", "唯一产出点漏第三字段（结构修复被破坏）", patch_t12d,
           lambda: setattr(LB, "_pack_excluded", orig_pack), "t12")

    # ---------------- M-16：扫描器漏扫某个文件（自制检查器失效）
    #   ⚠ 这是 Mion 2026-11-28 §三 要求的那条：
    #      「凡自制检查器，必须有一条【它自己会失效】的断言」。
    #      探针文件含真实调用，扫描器却不命中它 ⇒ T-11 ②b 必须红。
    #   ⇒ 若这条抓不住，说明我的自失效断言只是摆设。
    orig_scan_calls = LB.scan_judge_mechanism_calls

    def patch_t16():
        def bad_scan(repo_root=None):
            # 错误：悄悄跳过文件名里带 probe 的文件
            return [h for h in orig_scan_calls(repo_root)
                    if "probe" not in h[0]]
        LB.scan_judge_mechanism_calls = bad_scan
    mutate("M-16", "扫描器漏扫探针文件（自失效断言必须红）", patch_t16,
           lambda: setattr(LB, "scan_judge_mechanism_calls", orig_scan_calls),
           "t11")

    # ---------------- M-16b：扫描器对所有文件都漏扫（更彻底）
    def patch_t16b():
        LB.scan_judge_mechanism_calls = lambda repo_root=None: []
    mutate("M-16b", "扫描器返回空（彻底失效）", patch_t16b,
           lambda: setattr(LB, "scan_judge_mechanism_calls", orig_scan_calls),
           "t11")

    # ---------------- M-17：把前置条件改回 assert（违反 C-3）
    #   ⚠ Mion 0173c69 §三 的第三类：【文档】不能单独红，
    #      所以必须用 raise 而不是 assert —— 否则它会被计入通过数。
    t_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "test_blayer_batch1.py")

    def patch_t17():
        with io.open(t_path, encoding="utf-8") as fh:
            src = fh.read()
        old = (
            '    if not cov["hits"]:              # 前置条件；不计数、不单独作为防线\n'
            '        raise RuntimeError(\n'
            '            "前置条件不成立：扫描结果为空。"\n'
            '            "注意本条不是断言 —— 若它先于下面两条触发，说明扫描器坏了。")\n'
        )
        new = (
            '    assert cov["hits"], "E-25-1 violated: 扫描结果为空，断言无对象"\n'
        )
        with io.open(t_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src.replace(old, new, 1))

    def unpatch_t17():
        with io.open(t_path, encoding="utf-8") as fh:
            src = fh.read()
        old = (
            '    assert cov["hits"], "E-25-1 violated: 扫描结果为空，断言无对象"\n'
        )
        new = (
            '    if not cov["hits"]:              # 前置条件；不计数、不单独作为防线\n'
            '        raise RuntimeError(\n'
            '            "前置条件不成立：扫描结果为空。"\n'
            '            "注意本条不是断言 —— 若它先于下面两条触发，说明扫描器坏了。")\n'
        )
        with io.open(t_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src.replace(old, new, 1))
    mutate("M-17", "前置条件改回 assert（被蕴含项混入通过数）", patch_t17,
           unpatch_t17, "t14")

    # ================================================================
    # v0.5（2df4517）的三条
    # ================================================================

    # ---------------- M-18：BINDING 退回六份（v0.5 §〇 要求只有一份）
    orig_binding_list = list(CBD.BINDING_DOCS)

    def patch_t13d():
        CBD.BINDING_DOCS.extend(list(CBD.SUPERSEDED_DOCS))
    mutate("M-18", "BINDING 退回六份（v0.5 要求只有一份）", patch_t13d,
           lambda: setattr(CBD, "BINDING_DOCS", list(orig_binding_list)),
           "t13")

    # ---------------- M-18b：旧版被从仓库删掉（应保留）
    orig_superseded = list(CBD.SUPERSEDED_DOCS)

    def patch_t13e():
        CBD.SUPERSEDED_DOCS.append(
            ("伪造旧版", "____no_such_old_version____.md"))
    mutate("M-18b", "旧版文件在仓库里不存在", patch_t13e,
           lambda: setattr(CBD, "SUPERSEDED_DOCS", list(orig_superseded)),
           "t13")

    # ---------------- M-19：撤销记录被清空（删了没留痕）
    orig_withdrawn = list(LB.WITHDRAWN)

    def patch_t15():
        LB.WITHDRAWN = []
    mutate("M-19", "撤销记录被清空（删了没留痕）", patch_t15,
           lambda: setattr(LB, "WITHDRAWN", list(orig_withdrawn)), "t15")

    # ---------------- M-19b：撤销条目又塞回 NOT_CHECKED
    def patch_t15b():
        LB.NOT_CHECKED = list(LB.NOT_CHECKED) + [
            ("SCAN 表外的新调用点", "（错误：已撤销的条目塞回 NOT_CHECKED）")]
    _orig_nc = list(LB.NOT_CHECKED)
    mutate("M-19b", "撤销条目又出现在 NOT_CHECKED 里", patch_t15b,
           lambda: setattr(LB, "NOT_CHECKED", list(_orig_nc)), "t15")

    # ---------------- M-19c：撤销记录缺「被什么覆盖」
    def patch_t15c():
        LB.WITHDRAWN = [(n, w, "") for n, w, _c in orig_withdrawn]
    mutate("M-19c", "撤销记录缺「被什么覆盖」", patch_t15c,
           lambda: setattr(LB, "WITHDRAWN", list(orig_withdrawn)), "t15")

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
