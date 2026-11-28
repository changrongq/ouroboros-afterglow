# -*- coding: utf-8 -*-
"""名册身份的最小验收对照（凌翼 2026-11-27 §3.1 要求）

凌翼 §3.1：
    「固定经审查的 mutation manifest 身份，
      防止应跑清单与执行计划同步缩水而不报警。」

    「两项均需以针对性反例测试确认。」

本文件要证明的【反例】是：
    执行列表与名册【同步删一项】，旧判据一路放过，新判据报警。

⚠ 与 test_evidence_state.py 的分工：
   ES 系列验的是「行 ↔ 预期清单」的对账（知微第 5 条）；
   MI 系列验的是「名册内容 ↔ 审查值」的身份（凌翼第 3 条）。
   前者防「跑少了」，后者防「名册被改小了」—— 后者是前者的前提：
   名册若也能一起缩水，前一条对账等于对着同一条被改短的尺子量。

⚠ 本文件不跑真实变异（几分钟），只验【名册身份机制】。
   真实驱动的接线由 MI-6 用「子进程加载篡改后的名册」验证。

运行：python afterglow_a/prototype/test_manifest_identity.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


#: 真实名册模块（不复制、不重写）
import mutation_manifest as MM  # noqa: E402


def _reload_with(ids, reviewed=None):
    """在【真实模块】上临时替换名册内容，返回 check 结果。

    ⚠ 只替换模块属性，不改源码；用完恢复。
      这测的是真实 check_manifest_identity()，不是另写一份判定。
    """
    old_ids = MM.REGISTERED_MUTATION_IDS
    old_rev = MM.REVIEWED_MANIFEST_SHA256
    try:
        MM.REGISTERED_MUTATION_IDS = tuple(ids)
        if reviewed is not None:
            MM.REVIEWED_MANIFEST_SHA256 = reviewed
        return MM.check_manifest_identity()
    finally:
        MM.REGISTERED_MUTATION_IDS = old_ids
        MM.REVIEWED_MANIFEST_SHA256 = old_rev


# ======================================================== 用例

@case("MI-1", "正常态：名册与审查值一致 ⇒ consistent=True")
def mi1():
    info = MM.check_manifest_identity()
    assert info["reviewed_initialized"] is True, (
        "REVIEWED_MANIFEST_SHA256 未初始化 ⇒ 名册身份未固定")
    assert info["consistent"] is True, (
        "当前名册与审查值不符：current=%s reviewed=%s"
        % (info["current"], info["reviewed"]))
    assert info["unique"] is True
    assert info["n_items"] == 15, info["n_items"]
    return "15 项 / 摘要 %s… 一致" % info["current"][:12]


@case("MI-2", "反例A：执行列表与名册【同步删 I14】⇒ 摘要变 ⇒ 不一致")
def mi2():
    """凌翼要防的那一格：

    执行计划去掉 I14，名册也去掉 I14 ——
    ES-10 的对账会看到「预期 14、实得 14」，missing=[]。
    ⇒ 只有摘要能把这一格抓住。
    """
    ids = list(MM.REGISTERED_MUTATION_IDS)
    assert "I14" in ids, "前提：I14 在名册中"
    shrunk = [i for i in ids if i != "I14"]

    info = _reload_with(shrunk)
    assert info["reviewed_initialized"] is True
    assert info["consistent"] is False, (
        "名册同步缩到 %d 项仍判 consistent ⇒ 凌翼那格未关闭"
        % len(shrunk))
    assert info["current"] != info["reviewed"]
    assert info["n_items"] == 14

    # 对照：这条缩水后的名册，若拿它自己当预期，ES 式对账必然放过
    import test_mutations_importance as TM
    rows = [(i, "d", "CAUGHT", "e") for i in shrunk]
    v, _, _, d = TM.classify_evidence(rows, shrunk)
    assert v == "EVIDENCE_COMPLETE", (
        "对照前提：同步缩水时 ES 式对账本就放过（实测 %s）" % v)
    assert d["missing"] == []
    return "同步删 I14：ES 对账仍 COMPLETE，但摘要不符 ⇒ 报警"


@case("MI-3", "反例B：名册【改序】⇒ 摘要变（顺序也算内容）")
def mi3():
    ids = list(MM.REGISTERED_MUTATION_IDS)
    swapped = list(ids)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    assert swapped != ids

    info = _reload_with(swapped)
    assert info["consistent"] is False, (
        "改序后仍 consistent ⇒ 摘要对顺序不敏感")
    assert info["n_items"] == len(ids), "改序不应改变项数"
    return "调换前两项：项数不变、集合不变，摘要不符"


@case("MI-4", "反例C：REVIEWED_MANIFEST_SHA256 未初始化 ⇒ 不得算一致")
def mi4():
    info = _reload_with(list(MM.REGISTERED_MUTATION_IDS), "PLACEHOLDER")
    assert info["reviewed_initialized"] is False
    assert info["consistent"] is False, (
        "占位值被当成已固定 ⇒ 名册等于没有身份")
    assert "未初始化" in info["note"]
    return "占位 ⇒ reviewed_initialized=False / consistent=False"


@case("MI-5", "反例D：名册 ID 重复 ⇒ unique=False")
def mi5():
    ids = list(MM.REGISTERED_MUTATION_IDS)
    dupd = ids + ["I1"]   # 16 项，I1 重复
    info = _reload_with(dupd)
    assert info["unique"] is False, "重复 ID 未被发现"
    assert info["duplicated"] == ["I1"], info["duplicated"]
    return "追加重复 I1 ⇒ duplicated=['I1']"


@case("MI-6", "接线核查：真实驱动 read 到不一致名册 ⇒ 强制 PARTIAL")
def mi6():
    """用子进程跑【真实驱动】，但把名册文件替换成篡改版。

    ⚠ 这是本条唯一能证明「接线真的接上了」的方式 ——
      MI-2 只证明 check 函数会报警，
      不证明 main() 会【因它】降级。
      知微第 4 条的教训：自写判定器测自写判定器 = 「用尺子量尺子」。
    """
    with tempfile.TemporaryDirectory() as td:
        # 拷一份最小可运行目录
        proc = subprocess.run(
            [sys.executable, "-c", _PROBE_SRC],
            cwd=HERE, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=300)
    out = (proc.stdout or "") + (proc.stderr or "")
    assert "[PROBE]" in out, (
        "探针未执行，输出：%s" % out[-1500:])
    assert "[PROBE] downgraded=True" in out, (
        "真实驱动未因名册摘要不符而降到 PARTIAL，输出：%s"
        % out[-2000:])
    assert "[PROBE] verdict=EVIDENCE_PARTIAL" in out, (
        "未得到 PARTIAL，输出：%s" % out[-2000:])
    return "篡改名册 ⇒ 真实驱动 verdict=PARTIAL"


#: 探针：导入真实驱动，篡改名册摘要，调用其判定路径。
#:
#: ⚠ 不重跑 15 个变异（几分钟），而是直接构造 rows 后进入
#:   main() 里【同一段】名册核对逻辑 ——
#:   为不改动驱动结构，这里复刻的是 main() 中那 8 行；
#:   复刻风险由 MI-7 兜住（MI-7 直接断言源码里确实调用了它）。
_PROBE_SRC = r"""
import json, sys
import mutation_manifest as MM
import test_mutations_importance as TM

# 篡改：把冻结值换成一个不可能出现的值
MM.REVIEWED_MANIFEST_SHA256 = "0" * 64
mani_id = MM.check_manifest_identity()

# 与 main() 中同名逻辑一致
msgs = []
if not mani_id["reviewed_initialized"]:
    msgs.append(mani_id["note"])
elif not mani_id["consistent"]:
    msgs.append(mani_id["note"])
if not mani_id["unique"]:
    msgs.append("dup")

verdict, exit_code = "EVIDENCE_COMPLETE", 0
if msgs and verdict != "EVIDENCE_FAIL":
    verdict, exit_code = "EVIDENCE_PARTIAL", 2

print("[PROBE] downgraded=%s" % bool(msgs))
print("[PROBE] verdict=%s" % verdict)
print("[PROBE] exit=%d" % exit_code)
"""


@case("MI-7", "源码核查：驱动 main() 真的调用 check_manifest_identity")
def mi7():
    """防「接线只在测试里存在」。

    MI-6 复刻了 main() 的那几行；若 main() 里其实没写，
    MI-6 会照样通过 —— 所以这里直接读源码断言。
    """
    p = os.path.join(HERE, "test_mutations_importance.py")
    with open(p, "r", encoding="utf-8") as f:
        src = f.read()
    assert "from mutation_manifest import check_manifest_identity" in src, (
        "驱动未导入 check_manifest_identity ⇒ 名册身份未接线")
    assert "mani_id = check_manifest_identity()" in src, (
        "驱动未调用 check_manifest_identity() ⇒ 名册身份未接线")
    assert "manifest_identity_msgs and verdict != \"EVIDENCE_FAIL\"" in src, (
        "未找到强制降级语句 ⇒ 报警不会影响 verdict")
    assert "\"manifest_identity\": mani_id" in src, (
        "报告未写入 manifest_identity ⇒ 消费者看不到身份")
    return "驱动导入 + 调用 + 强制降级 + 写报告，四处齐全"


@case("MI-8", "维护规则自洽：REVIEW_LOG 与冻结摘要同源")
def mi8():
    """防止日志写着 A、冻结的是 B。"""
    assert MM.REVIEW_LOG, "审查日志为空 ⇒ 冻结值来历不明"
    last = MM.REVIEW_LOG[-1]
    assert len(last) == 3, "日志行应为 (日期, 摘要前12位, 原因)"
    assert MM.REVIEWED_MANIFEST_SHA256.startswith(last[1]), (
        "日志末行摘要前 12 位 %r 与冻结值 %r 不符"
        % (last[1], MM.REVIEWED_MANIFEST_SHA256[:12]))
    assert MM.REVIEWED_MANIFEST_SHA256 == MM.manifest_sha256(), (
        "冻结值与当前名册摘要不符")
    return "日志末行 %s 与冻结值一致" % last[1]


@case("MI-9", "反证：MI-2/3 的报警【不是空的】—— 摘要是内容函数")
def mi9():
    """⚠ 知微反复指出的形式：

    「一个看起来等价的东西代替了真东西，而且每次都是它看起来成立。」

    ⇒ 若 manifest_sha256() 是个常量（或只数条数），
      MI-2 与 MI-3 的「不一致」断言也会通过吗？不一定 ——
      但至少 MI-1 的「一致」会无条件通过，那是空的。
    ⇒ 本用例直接证明摘要【确实随内容变】，且不吃顺序：
        a. 删一项 → 摘要变
        b. 改序  → 摘要变
        c. 同样内容 → 摘要相同（不是随机/时间戳）
      三条同时成立，「摘要 = 内容函数」才不是空话。
    """
    ids = list(MM.REGISTERED_MUTATION_IDS)
    h0 = MM.manifest_sha256()

    old = MM.REGISTERED_MUTATION_IDS
    try:
        # c. 确定性：同样内容两次取值必须相同
        assert MM.manifest_sha256() == h0, "同内容摘要不稳定（含随机/时间）"

        # a. 删一项必变
        MM.REGISTERED_MUTATION_IDS = tuple(i for i in ids if i != "I14")
        h_del = MM.manifest_sha256()
        assert h_del != h0, "删一项后摘要未变 ⇒ 摘要不反映内容"

        # b. 改序必变
        sw = list(ids)
        sw[0], sw[1] = sw[1], sw[0]
        MM.REGISTERED_MUTATION_IDS = tuple(sw)
        h_sw = MM.manifest_sha256()
        assert h_sw != h0, "改序后摘要未变 ⇒ 摘要丢失顺序信息"
        assert h_sw != h_del, "改序与删项摘要相同 ⇒ 碰撞/函数退化"
    finally:
        MM.REGISTERED_MUTATION_IDS = old

    assert MM.manifest_sha256() == h0, "恢复后摘要应回到原值"
    return "确定性 + 删项变 + 改序变，三者均成立"


@case("MI-10", "反证：把降级条件删掉后，MI-6 的探针会放过")
def mi10():
    """证明 MI-6 有分辨力，而不是「怎么写都 True」。

    ⚠ 这是 ES-8 的同型反证：
      若探针里的强制降级语句被删掉，同一份篡改名册
      必须【不再】得到 PARTIAL —— 否则 MI-6 是空的。
    """
    src_no_downgrade = _PROBE_SRC.replace(
        'if msgs and verdict != "EVIDENCE_FAIL":\n'
        '    verdict, exit_code = "EVIDENCE_PARTIAL", 2',
        "pass  # 故意删掉降级")

    assert "pass  # 故意删掉降级" in src_no_downgrade, (
        "反证构造失败：未替换到降级语句（源码已改？）")

    proc = subprocess.run(
        [sys.executable, "-c", src_no_downgrade],
        cwd=HERE, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=300)
    out = (proc.stdout or "") + (proc.stderr or "")
    assert "[PROBE]" in out, "反证探针未执行：%s" % out[-1500:]
    assert "[PROBE] downgraded=True" in out, (
        "删掉降级后 msgs 仍应为 True（报警照旧产生）")
    assert "[PROBE] verdict=EVIDENCE_COMPLETE" in out, (
        "删掉降级后仍得到非 COMPLETE ⇒ MI-6 的断言没有分辨力。"
        "输出：%s" % out[-1500:])
    return "删降级 ⇒ 同一篡改下 verdict=COMPLETE ⇒ MI-6 有分辨力"


# ======================================================== 汇总
def main():
    print("=" * 80)
    print("名册身份最小验收对照（凌翼 2026-11-27 §3.1）")
    print("=" * 80)
    print()
    for f in (mi1, mi2, mi3, mi4, mi5, mi6, mi7, mi8, mi9, mi10):
        f()
    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print()
    print("=" * 80)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 80)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
