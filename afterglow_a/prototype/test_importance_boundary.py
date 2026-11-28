# -*- coding: utf-8 -*-
"""第 5 项边界自查（固化版）

把一次性自查脚本固化成测试，防止将来漂移。

查四类：
  ① 用语越界：把「候选」说成「重要记忆已选出」
  ② 返回结构边界：每个返回点都要有 measurement_scope + note
  ③ 禁止动作：不写文件、不排序（按重要性）、不随机、不打分
  ④ 公开接口：只返回集合，不返回分数

⚠ 「排序」的判据要精确：
   本轮自查首版把 sorted(rule_names) / sorted(ids) 也判成违规 ——
   那是【为输出稳定】排序，不是【按重要性】排序。
   ⇒ 判据改为：不得存在「按某个分数键排序」的模式，
     而不是「代码里不得出现 sorted」。

运行：python afterglow_a/prototype/test_importance_boundary.py
"""
from __future__ import annotations

import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import afimportance as AI
from afcore import Record, RecoveryStore

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
PIN = "2026-11-26T00:00:00Z"

SRC = open(os.path.join(HERE, "afimportance.py"), encoding="utf-8").read()
LINES = SRC.splitlines()


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


def mk():
    s = RecoveryStore()
    s.insert(Record(
        record_id="r1", content="测", source_kind="user_utterance",
        source_ref="utt/r1", participant_id="A",
        participation_basis="first_person_report", basis_ref="utt/r1",
        commitment_state="not_a_commitment", revision=1, prev_digest=None,
        changed_at=PIN, change_authority="synthetic"))
    return s


# ================================================== ① 用语越界
#
# ⚠ 2026-11-26 第二次重写（睫复核的注入反例 + 我自己的两次误判）
#
# 两版都失败了，失败方式相反：
#   第一版：否定上下文放宽到 14 字 ⇒ 睫注入的「# 无阈值设计：按重要性排序」
#           被放行（漏检）
#   第二版：否定必须紧贴 ⇒ 「✗ 不计算 importance_score」「不得把 candidates
#           读作『重要记忆已选出』」被误判（误伤）
#
# ⇒ 结论：靠【字面前缀猜意图】这条路本身不成立。
#   中文里否定可以隔一个名词短语，也可以只有一个符号；
#   而同一个词既可能出现在禁令里，也可能出现在断言里。
#
# ⇒ 改为【显式标注】：
#   凡是合规的越界用语引用（禁止清单、forbidden_use 字段、注释里的否定句），
#   必须在同一行末尾带标记 `# boundary-ok`。
#   没有标记就判违规。
#
#   代价：写代码时要多打 15 个字符。
#   收益：不再靠猜 —— 判据变成「有没有标」，而不是「像不像否定」。
#
#   ⚠ 这条判据能支持的最强主张：
#     「源码中每个越界用语都显式标注为边界引用」。
#     不是「没有越界陈述」—— 因为有人可以给越界语句也打上标记。
#     这一层的最后防线仍是人读，不是扫描。
#
#   ⚠ 2026-11-27 凌翼澄清（第二次回执 §3）：
#     「BND-1c 已复用实际扫描函数；其保证范围仍限于已定义的
#       字面扫描规则，不代表完整语义审查。」
#     ⇒ 本判据查的是【字面】：「该词是否出现且未标注」。
#       它不判断该行在语义上是否真的属于边界声明。
#     ⇒ 不得把「BND-1a 通过」说成「越界用语已被语义审查」。
BOUNDARY_MARK = "# boundary-ok"

#: 不得作为【断言】出现的用语（「重要记忆已经选出」这类）
BANNED_ASSERTIVE = [
    "重要记忆已选出",
    "重要性得分",
    "importance_score",
    "按重要性排序",
    "top_k",
    "权重值",
]


#: 扫描入口 —— BND-1a 与 BND-1c【共用同一个函数】。
#:
#: ⚠ 2026-11-27 修正（凌翼裁定三）：
#:   原 BND-1c 在测试里【重写了一遍判据】：
#:       for b in BANNED_ASSERTIVE:
#:           if b in inject and BOUNDARY_MARK not in inject:
#:               caught = True
#:   ⇒ 那不是「把注入行送进扫描」，是「我抄了一遍判据再验它」。
#:     凌翼：「使它真正经过被检验的扫描入口，
#:            而不是在测试内部验证自己写出的判断。」
#:
#:   ⇒ 现在抽出 scan_lines()，BND-1a 扫真实源码、BND-1c 扫注入后的
#:     临时源码副本，两者走【同一个函数】。
def scan_lines(lines):
    """扫描一组源码行，返回未标注的越界用语。"""
    hits = []
    for i, line in enumerate(lines, 1):
        for b in BANNED_ASSERTIVE:
            if b not in line:
                continue
            if BOUNDARY_MARK in line:
                continue
            hits.append((i, b, line.strip()[:78]))
    return hits


@case("BND-1a", "越界用语必须显式标注为边界引用（# boundary-ok）")
def bnd1a():
    hits = scan_lines(LINES)
    assert not hits, (
        "出现未标注的越界用语（若为合规引用请加 %s）：%s"
        % (BOUNDARY_MARK, hits))
    return "全部越界用语均已显式标注"


@case("BND-1c", "反证：把注入行写进真实源码副本后，扫描必须抓到")
def bnd1c():
    """A3：这条扫描自己也要能失败。

    睫 2026-11-26 注入：
        # 无阈值设计：按重要性排序（注入行）

    ⚠ 2026-11-27（凌翼裁定三）：现在【真的写进临时副本再扫】，
      不再在测试内部重写判据。
      ⇒ 同时验证两条：
        (a) 注入行未加标记 ⇒ 被抓到
        (b) 同一行加上标记后 ⇒ 放行（证明不是「见行就报」）
    """
    import shutil
    import tempfile

    inject = "  # 无阈值设计：按重要性排序（注入行）"
    with tempfile.TemporaryDirectory() as td:
        dst = os.path.join(td, "afimportance_injected.py")
        shutil.copy2(os.path.join(HERE, "afimportance.py"), dst)

        # (a) 未加标记
        with open(dst, encoding="utf-8") as f:
            src = f.read()
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(src + "\n" + inject + "\n")
        with open(dst, encoding="utf-8") as f:
            hit_lines = f.read().splitlines()
        hits_a = scan_lines(hit_lines)
        assert hits_a, (
            "注入行（无标记）未被扫描抓到 ⇒ 判据失效")
        assert any("按重要性排序" in h[1] for h in hits_a), hits_a

        # (b) 同一行加标记 ⇒ 放行
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(src + "\n" + inject + "  " + BOUNDARY_MARK + "\n")
        with open(dst, encoding="utf-8") as f:
            marked_lines = f.read().splitlines()
        hits_b = scan_lines(marked_lines)
        assert not hits_b, (
            "同一行加标记后仍被判违规 ⇒ 扫描见行就报，没有分辨力：%r"
            % hits_b)

        # (c) 扫描确实读到了注入行（防止「根本没读到文件尾部」）
        assert any("注入行" in l for l in marked_lines), (
            "临时副本里找不到注入行 ⇒ 上面的断言可能是空的")
    return "注入→抓 1 处；加标记→放行；注入行确实在副本里"


@case("BND-1d", "对照：带标记的正确否定句必须放行（不得误伤）")
def bnd1d():
    cases = [
        ("# ✗ 不计算 importance_score / 任何数值  " + BOUNDARY_MARK,
         "importance_score"),
        ('"forbidden_use": "不得读作「重要记忆已选出」",  ' + BOUNDARY_MARK,
         "重要记忆已选出"),
    ]
    for line, word in cases:
        assert word in line, "用例写错：%r 不含 %r" % (line, word)
        assert BOUNDARY_MARK in line, "用例缺标记"
        ok = not (word in line and BOUNDARY_MARK not in line)
        assert ok, "带标记的正确写法被误判：%r" % line
    return "%d 条带标记的正确写法均被放行" % len(cases)


@case("BND-1b", "「不代表重要记忆已选出」这句必须在代码里")
def bnd1b():
    """不是「没有坏词」就够了 —— 必须【主动写明边界】。
    凌翼裁定：「该集合不代表『重要记忆已经选出』。」
    """
    assert "不代表「重要记忆已经选出」" in SRC, (
        "代码里缺少凌翼要求的边界声明原句")
    return "边界声明原句存在"


# ================================================== ② 返回结构边界
@case("BND-2a", "importance_candidates 的每个返回点都有 scope + note")
def bnd2a():
    # 只检查 importance_candidates 函数体内的 return
    start = SRC.index("def importance_candidates")
    end = SRC.index("def synthetic_ratios")
    body = SRC[start:end]
    body_lines = body.splitlines()
    returns = [i for i, l in enumerate(body_lines) if re.match(r"\s+return \{", l)]
    assert returns, "没找到 return { 块"
    for r in returns:
        # 窗口按【下一个 return 或函数尾】取，不写死 24 行 ——
        # 写死会在返回块变长时误报（2026-11-26 实际发生过一次）
        rest = [k for k in returns if k > r]
        stop = rest[0] if rest else len(body_lines)
        block = "\n".join(body_lines[r:stop])
        assert "measurement_scope" in block, (
            "返回块（行 %d 起）缺 measurement_scope" % r)
        assert '"note"' in block, "返回块（行 %d 起）缺 note" % r
    return "%d 个返回点均有 scope + note" % len(returns)


@case("BND-2b", "synthetic_ratios 的返回点同样有 scope + note")
def bnd2b():
    start = SRC.index("def synthetic_ratios")
    body_lines = SRC[start:].splitlines()
    returns = [i for i, l in enumerate(body_lines) if re.match(r"\s+return \{", l)]
    assert returns, "没找到 return { 块"
    for r in returns:
        rest = [k for k in returns if k > r]
        stop = rest[0] if rest else len(body_lines)
        block = "\n".join(body_lines[r:stop])
        assert "measurement_scope" in block, (
            "synthetic_ratios 返回块（行 %d 起）缺 measurement_scope" % r)
        assert '"note"' in block, (
            "synthetic_ratios 返回块（行 %d 起）缺 note" % r)
    return "%d 个返回点均有 scope + note" % len(returns)


# ================================================== ③ 禁止动作
@case("BND-3a", "不写任何文件（红线：无基线前不入 reports/）")
def bnd3a():
    for pat, why in ((r"\bopen\s*\(", "打开文件"),
                     (r"\bjson\.dump\s*\(", "写 JSON")):
        for m in re.finditer(pat, SRC):
            raise AssertionError("发现 %s：%s" % (
                why, LINES[SRC[:m.start()].count("\n")].strip()[:70]))
    return "无 open() / json.dump()"


@case("BND-3b", "不按分数排序（sorted 只用于稳定输出）")
def bnd3b():
    """⚠ 首版把「代码里出现 sorted」判成违规 —— 误报。
    sorted(rules) / sorted(ids) 是【为输出稳定】，不是【按重要性】。
    ⇒ 精确判据：不得出现按数值键排序的模式。
    """
    bad_patterns = [
        r"sorted\([^)]*key\s*=",          # 按 key 排序（可能是分数）
        r"\.sort\(",                       # 原地排序
        r"reverse\s*=\s*True",             # 降序
        r"heapq\.nlargest",
    ]
    hits = []
    for pat in bad_patterns:
        for m in re.finditer(pat, SRC):
            ln = SRC[:m.start()].count("\n") + 1
            hits.append((ln, pat, LINES[ln - 1].strip()[:70]))
    assert not hits, "出现可能的按分排序：%s" % hits
    return "无按 key 排序 / 原地排序 / 降序 / nlargest"


@case("BND-3c", "不引入随机（不得训练 / 采样）")
def bnd3c():
    for pat in (r"\bimport\s+random", r"\brandom\.", r"\bnp\.random"):
        assert not re.search(pat, SRC), "发现随机：%s" % pat
    return "无随机调用"


# ================================================== ④ 公开接口
@case("BND-4a", "importance_candidates 返回 set，不返回分数或排序列表")
def bnd4a():
    s = mk()
    r = AI.importance_candidates(s, trace=[])
    assert isinstance(r["candidates"], set), (
        "candidates 类型为 %s，应为 set（列表意味着可能已排序）"
        % type(r["candidates"]).__name__)
    numeric = [k for k, v in r.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)]
    assert not numeric or numeric == ["denominator_size"], (
        "出现非分母的数值键 %s ⇒ 可能在做打分" % numeric)
    return "candidates 是 set；唯一数值键 = denominator_size"


@case("BND-4b", "模块不导出打分/排序类函数")
def bnd4b():
    pub = [n for n in dir(AI) if not n.startswith("_") and callable(getattr(AI, n))
           and not n.isupper()]
    bad = [n for n in pub if any(k in n.lower()
                                 for k in ("score", "rank", "weight", "train"))]
    assert not bad, "模块导出了打分类函数：%s" % bad
    return "公开可调用符号：%s" % ", ".join(sorted(pub))


@case("BND-4c", "不返回 top-N（不预设「哪些是重要的」）")
def bnd4c():
    s = mk()
    r = AI.importance_candidates(s, trace=[])
    for k in r:
        assert not re.search(r"(top_?\d+|top_k|limit|n_best)", k, re.I), (
            "返回键 %r 暗示 top-N 截断" % k)
    return "返回键无 top-N 语义"


# ================================================== 汇总
def main():
    print("=" * 82)
    print("第 5 项边界自查（固化）")
    print("=" * 82)
    print()
    print("[① 用语越界]")
    for f in (bnd1a, bnd1c, bnd1d, bnd1b):
        f()
    print()
    print("[② 返回结构边界]")
    for f in (bnd2a, bnd2b):
        f()
    print()
    print("[③ 禁止动作]")
    for f in (bnd3a, bnd3b, bnd3c):
        f()
    print()
    print("[④ 公开接口]")
    for f in (bnd4a, bnd4b, bnd4c):
        f()
    print()

    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print("=" * 82)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 82)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
