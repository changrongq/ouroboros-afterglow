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
#: 不得作为【断言】出现的用语（「重要记忆已经选出」这类）
BANNED_ASSERTIVE = [
    "重要记忆已选出",
    "重要性得分",
    "importance_score",
    "按重要性排序",
    "top_k",
    "权重值",
]


@case("BND-1a", "代码中不出现断言性的越界用语")
def bnd1a():
    """⚠ 首版直接扫字面，把 docstring 里「✗ 不计算 importance_score」
    判成违规 —— 误报：那是否定句，正是我们要写的边界声明。

    ⇒ 判据必须区分【断言】与【否定/禁止】：
      同行内该词前面出现 不 / 不得 / ✗ / 禁 / 禁止 / 无  ⇒ 视为否定，放行。
    """
    NEG_MARKERS = ("不", "✗", "禁", "无", "非", "避免")

    def negated(line, idx):
        head = line[max(0, idx - 14):idx]
        return any(m in head for m in NEG_MARKERS)

    hits = []
    for i, line in enumerate(LINES, 1):
        for b in BANNED_ASSERTIVE:
            idx = line.find(b)
            if idx < 0:
                continue
            if negated(line, idx):
                continue
            hits.append((i, b, line.strip()[:80]))
    assert not hits, "出现断言性越界用语：%s" % hits
    return "无命中（扫描 %d 个用语，已排除否定上下文）" % len(BANNED_ASSERTIVE)


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
        block = "\n".join(body_lines[r:r + 24])
        assert "measurement_scope" in block, (
            "行 %d 附近的返回块缺 measurement_scope" % (
                start and SRC[:start].count("\n") + r + 1))
        assert '"note"' in block, "返回块缺 note"
    return "%d 个返回点均有 scope + note" % len(returns)


@case("BND-2b", "synthetic_ratios 的返回点同样有 scope + note")
def bnd2b():
    start = SRC.index("def synthetic_ratios")
    body_lines = SRC[start:].splitlines()
    returns = [i for i, l in enumerate(body_lines) if re.match(r"\s+return \{", l)]
    assert returns, "没找到 return { 块"
    for r in returns:
        block = "\n".join(body_lines[r:r + 24])
        assert "measurement_scope" in block, "synthetic_ratios 返回块缺 measurement_scope"
        assert '"note"' in block, "synthetic_ratios 返回块缺 note"
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
    for f in (bnd1a, bnd1b):
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
