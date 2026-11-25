# -*- coding: utf-8 -*-
"""分层证据台账自检（Mion 2026-11-25 裁定：F1/F2 + 纵深≠冗余 + G1/G2/G3）

Mion 给的条款：
  F1  每层必须对【它声称覆盖的输入维度】各有一份独立观测，
      而「声称覆盖哪些维度」必须先写下来。
  F2  「换一条攻击路径」是 F1 的实例，不是 F1 本身。
      F1 要的是【输入空间的抽样清单】。
  G1  ACCIDENT 不得计入任何防御层，也不得计入 CAUGHT。
  G2  ACCIDENT 必须单列，并写明它挡住的不是攻击，是攻击者的笔误。
  G3  若某条路径【只】被 ACCIDENT 挡住，该路径状态为 OPENED。

本测试守的是【台账不能说谎】：
  LAY-1  每个维度都有直接观测（E1）
  LAY-2  每层声称的维度都有一条独立观测结论（F1）
  LAY-3  实测与声明不符时必须标出，不得沉默（F1）
  LAY-4  纵深与冗余分开记（Mion §二）
  LAY-5  ACCIDENT 单列、不计入防御（G1/G2）
  LAY-6  只有 ACCIDENT 拦住的维度判 OPENED（G3）
  LAY-7  台账落盘且带外部状态（E1）

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
ALL_LAYERS = [l[0] for l in LE.LAYERS]
ALL_DIMS = [d[0] for d in LE.DIMENSIONS]


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


# ---------------------------------------------------------------- LAY-1
@case("LAY-1a", "每个声明维度都有直接观测（不依赖目标测试）")
def lay1a():
    obs = LE.observe([])
    assert "results" in obs, "探针无输出：%s" % str(obs)[:120]
    missing = [d for d in ALL_DIMS if d not in obs["results"]]
    assert not missing, "维度未观测：%s" % missing
    for d in ALL_DIMS:
        cell = obs["results"][d]
        assert "state" in cell, (
            "E1 违规：维度 %s 没有外部状态" % d)
    return "%d 个维度全部有 state" % len(ALL_DIMS)


@case("LAY-1b", "观测到的是外部状态，不是测试红绿")
def lay1b():
    obs = LE.observe([])
    # 直接观测到的必须是记录字段值
    st = obs["results"]["D2_DIRECT_SOURCE_EDIT"]["state"]
    assert st["participation_basis"] == "first_person_report", (
        "未拆任何层时来源应未变，实测 %r" % st["participation_basis"])
    return "未拆：basis=first_person_report（来源未变）"


# ---------------------------------------------------------------- LAY-2/3
@case("LAY-2a", "每层【声称】的每个维度，都有独立的拆层观测结论")
def lay2a():
    bad = []
    for lid, desc, dims, anchor, repl in LE.LAYERS:
        assert isinstance(dims, list) and dims, (
            "F1：%s 没有声明覆盖维度 ⇒ 无法判断覆盖率" % lid)
        for d in dims:
            assert d in ALL_DIMS, (
                "F1：%s 声称覆盖不存在的维度 %s" % (lid, d))
            obs = LE.observe([lid])
            if "error" in obs:
                bad.append((lid, d, obs["error"]))
                continue
            cell = obs["results"].get(d)
            if not cell:
                bad.append((lid, d, "无观测"))
                continue
            v = LE.classify(cell, obs.get("base", {}))["verdict"]
            if v not in ("OPENED", "ACCIDENT", "BLOCKED_BY_L1",
                         "BLOCKED_BY_L2", "BLOCKED_BY_L3"):
                bad.append((lid, d, v))
    assert not bad, "声称维度缺少可用观测：%s" % bad
    total = sum(len(l[2]) for l in LE.LAYERS)
    return "%d 条声明 × 独立拆层观测，全部有结论" % total


@case("LAY-3a", "实测与声明不符时，必须能被识别（不得沉默）")
def lay3a():
    """F1 的核心：声明了就必须对得上。

    ⚠ 「独力守卫」的正确定义（Mion §二 之后定死的）：
        只保留这一层、其余全拆 ⇒ 该维度仍被【它自己】拦住。
      而不是：
        拆掉这一层 ⇒ 该维度 OPENED。
      后者要求「该维度只有一层在守」，把冗余层全判成失败 —— 那是错的。

    第一版用的是后者，LAY-4b 因此跑出 0 条并误判「D1 没有独力守卫」。
    """
    all_ids = [l[0] for l in LE.LAYERS]
    solo = {}
    for d in ALL_DIMS:
        guards = []
        for keep in all_ids:
            removals = [x for x in all_ids if x != keep]
            obs = LE.observe(removals)
            if "error" in obs:
                continue
            c = LE.classify(obs["results"][d], obs.get("base", {}))
            if (c["verdict"].startswith("BLOCKED_BY_")
                    and c.get("blocker") == keep):
                guards.append(keep)
        solo[d] = guards

    no_guard = [d for d, g in solo.items() if not g]
    assert not no_guard, (
        "以下维度没有任何独力守卫（要么真无防线，要么判据又反了）：%s"
        % no_guard)
    return "；".join("%s=%s" % (d, len(g)) for d, g in solo.items()) + " 层"


# ---------------------------------------------------------------- LAY-4
@case("LAY-4a", "D2/D3/D4 有独力守卫（不假定只有 L3）")
def lay4a():
    """⚠ 第一版断言「拆掉 L3 ⇒ D2/D3/D4 全部 OPENED」。
    那是假定「来源维度只有一层在守」。

    2026-11-25 重分类后，来源字段移出白名单，
    白名单句与来源护栏句【机制不同、各能独立守住】⇒ 这是纵深。
    因此「拆 L3 就打开」不再成立 —— 不是防线变弱，是防线多了一层。

    ⇒ 断言改为「外部状态」：这三个维度都必须有至少一层能独力拦住，
      且必须能说出是哪一层（E3）。
    """
    all_ids = [l[0] for l in LE.LAYERS]
    result = {}
    for d in ("D2_DIRECT_SOURCE_EDIT", "D3_SOURCE_VIA_SOURCE_KIND",
              "D4_SOURCE_VIA_REF"):
        guards = []
        for keep in all_ids:
            removals = [x for x in all_ids if x != keep]
            obs = LE.observe(removals)
            if "error" in obs:
                continue
            c = LE.classify(obs["results"][d], obs.get("base", {}))
            if (c["verdict"].startswith("BLOCKED_BY_")
                    and c.get("blocker") == keep):
                guards.append(keep)
        assert guards, "%s 没有任何独力守卫 ⇒ 真实缺口" % d
        result[d] = guards
    return "；".join("%s=%s" % (k.split("_")[0], ",".join(v))
                      for k, v in result.items())


@case("LAY-4b", "D1_FLAG_LEAK 是冗余不是纵深（≥2 层可独力拦住）")
def lay4b():
    """⚠ 方法要正确：「独力拦住」= 只留这一层时该维度 BLOCKED_BY_Lx，
    不是「只留这一层时 OPENED」。

    第一版写成了找 OPENED，结果 0 条，得出了「D1 没有独力守卫」的错误结论。
    实测（.local_scratch/diag_d1.py）：
        只留 L1 → BLOCKED_BY_L1      ← L1 独力拦住
        只留 L2 → BLOCKED_BY_L2      ← L2 独力拦住
        只留 L3 → ACCIDENT           ← 不是它拦的
        只留 L4 → ACCIDENT           ← 不是它拦的
    ⇒ D1 有 2 个独力守卫（L1、L2），互相冗余 ⇒ 这是冗余，不是纵深。
    """
    solo = []
    for keep in ALL_LAYERS:
        removals = [x for x in ALL_LAYERS if x != keep]
        obs = LE.observe(removals)
        if "error" in obs:
            continue
        cell = obs["results"]["D1_FLAG_LEAK"]
        c = LE.classify(cell, obs.get("base", {}))
        # 独力守卫 = 只留这一层时，它自己把它拦下
        if c["verdict"].startswith("BLOCKED_BY_") and c.get("blocker") == keep:
            solo.append(keep)
    assert len(solo) >= 2, (
        "D1 只有 %d 层可独力拦住（%s）⇒ 台账里「冗余」的说法要重写"
        % (len(solo), solo))
    return "D1 独力守卫 = %s（%d 层，互相冗余）" % (solo, len(solo))


# ---------------------------------------------------------------- LAY-5/6
def _make_accident_only():
    """构造一条「只被 ACCIDENT 挡住」的路径，用于 G1/G2/G3 的守卫测试。

    做法：拆掉所有能拦 D1_FLAG_LEAK 的【设计层】
    （显式拒收、白名单、来源护栏、入口硬编码），
    只留下 Record(**merged) 不接受多余键这个偶然因素。

    ⚠ 为什么不再用「四层全拆」：
      2026-11-25 重分类后，L2 的变异体只放行 "_via_correct" 一个键，
      于是「四层全拆」其实仍有白名单在拦 —— 那不是全拆。
      直接按【能拦 D1 的层清单】来拆，才不会因为层定义改了而前提失效。
    """
    d1_blockers = []
    for lid, desc, dims, anchor, repl in LE.LAYERS:
        if "D1_FLAG_LEAK" not in dims:
            continue
        obs = LE.observe([lid])
        if "error" in obs:
            continue
        c = LE.classify(obs["results"]["D1_FLAG_LEAK"], obs.get("base", {}))
        if c["verdict"].startswith("BLOCKED_BY_"):
            d1_blockers.append(lid)
    return d1_blockers


@case("LAY-5a", "ACCIDENT 必须与 BLOCKED_BY_Lx 区分开（G1/G2）")
def lay5a():
    blockers = _make_accident_only()
    assert blockers, "找不到任何 D1 的拦截层 ⇒ 前提变了，需重写本用例"
    obs = LE.observe(blockers)
    if "error" in obs:
        raise AssertionError("拆层失败：%s" % obs["error"])
    cell = obs["results"]["D1_FLAG_LEAK"]
    assert cell.get("exc") == "TypeError", (
        "前提变了：拆掉 %s 后 D1 不再撞 TypeError（实测 exc=%r, msg=%r）"
        % (blockers, cell.get("exc"), (cell.get("msg") or "")[:60]))
    c = LE.classify(cell, obs.get("base", {}))
    assert c["verdict"] == "ACCIDENT", (
        "TypeError 被归成 %s ⇒ 会被误当防御层" % c["verdict"])
    assert c["accident"] is True, "accident 标志未置位"
    assert c["blocker"] is None, "ACCIDENT 不得归到任何层（G1）"
    return "拆 %s ⇒ D1=ACCIDENT，blocker=None（不计入任何层）" % (
        ",".join(blockers),)


@case("LAY-5b", "ACCIDENT 不计入 CAUGHT：台账里不是 BLOCKED_BY_Lx")
def lay5b():
    blockers = _make_accident_only()
    obs = LE.observe(blockers)
    c = LE.classify(obs["results"]["D1_FLAG_LEAK"], obs.get("base", {}))
    assert not c["verdict"].startswith("BLOCKED_BY_"), (
        "拆掉所有设计层后 D1 仍被判为 %s ⇒ 还有层没拆掉" % c["verdict"])
    return "拆 %s 后 D1 判 %s（非 BLOCKED_BY_Lx）" % (
        ",".join(blockers), c["verdict"])


@case("LAY-6a", "只被 ACCIDENT 挡住的维度，最终状态判 OPENED（G3）")
def lay6a():
    blockers = _make_accident_only()
    obs = LE.observe(blockers)
    cell = obs["results"]["D1_FLAG_LEAK"]
    c = LE.classify(cell, obs.get("base", {}))
    assert c["verdict"] == "ACCIDENT"
    effective = "OPENED" if c["verdict"] == "ACCIDENT" else c["verdict"]
    assert effective == "OPENED", (
        "G3：只有 ACCIDENT 拦住时必须判 OPENED，实测 %s" % effective)
    # 并验证：D1 在四层全拆时状态其实【没有被改】——
    # 也就是说这不是「成功防御」，只是攻击没打进构造函数
    st = cell.get("state", {})
    assert st.get("participation_basis") == "first_person_report", (
        "D1 状态意外变了：%r" % st)
    return "D1=ACCIDENT ⇒ 按 G3 记 OPENED（状态未变，但不是因为护栏）"


# ---------------------------------------------------------------- LAY-7
@case("LAY-7a", "台账已落盘，含维度清单、层声明、ACCIDENT 单列")
def lay7a():
    """⚠ 不依赖「仓库里已有旧台账」——
    变异验证会在临时目录里跑本文件，那里没有历史台账。
    所以这里先主动生成一次（与 main() 同一路径），再校验它。
    """
    p = os.path.join(HERE, "reports", "layer_evidence.json")
    if not os.path.exists(p):
        LE.main()        # 现场生成，避免依赖外部残留
    assert os.path.exists(p), "台账缺失：%s" % p
    d = json.load(open(p, encoding="utf-8"))
    for key in ("dimensions", "layer_claims", "claims_verified",
                "dimension_reference", "accidents", "rows"):
        assert key in d, "台账缺关键字段：%s" % key
    assert len(d["dimensions"]) == len(ALL_DIMS), \
        "维度数不符：%d vs %d" % (len(d["dimensions"]), len(ALL_DIMS))
    for lc in d["layer_claims"]:
        assert lc.get("claims"), (
            "F1：层 %s 没有声明覆盖维度" % lc.get("id"))
    return "%d 维度 / %d 层声明 / %d 条 ACCIDENT 记录" % (
        len(d["dimensions"]), len(d["layer_claims"]), len(d["accidents"]))


# ---------------------------------------------------------------- 汇总
def main():
    print("=" * 86)
    print("分层证据台账自检（Mion 2026-11-25 裁定：F1/F2 + G1/G2/G3）")
    print("=" * 86)
    print()
    for fn in (lay1a, lay1b, lay2a, lay3a, lay4a, lay4b,
               lay5a, lay5b, lay6a, lay7a):
        fn()
    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print()
    print("=" * 86)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 86)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
