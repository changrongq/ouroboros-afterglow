# -*- coding: utf-8 -*-
"""凌翼 2026-11-27 裁定回执的定点回归

覆盖两条：
  裁定一 · 多次纠正的 cause 归因（含退出/恢复/再次退出）
  裁定二 · MUTATION_PREFLIGHT（含负向：锚点失效必须在跑变异前拒绝）

凌翼原话（裁定一）：
    「当前 synthetic_ratios() 在累计 relation 列表里取第一条 correction_of，
      可能在多次纠正时归因错误。
      请先构造：
        - 首次纠正后仍是 first_person_report；
        - 再次纠正后变成 record_only；
        - 验证 cause 对应实际造成这次分母流失的纠正依据。
      还应覆盖退出、恢复、再次退出分母的多次转换。
      如历史证据无法确定相应纠正依据，应显式报告归因未知，
      不得静默给出错误 ID。」

运行：python afterglow_a/prototype/test_attrition_preflight.py
"""
from __future__ import annotations

import json
import os
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


from afcore import Record, RecoveryStore  # noqa: E402
import afimportance as AI                   # noqa: E402
import mutation_preflight as PF             # noqa: E402
import test_mutations_importance as TM      # noqa: E402

PIN = "2026-11-27T00:00:00Z"


def _rec(rid, basis):
    return Record(
        record_id=rid, content="c-%s" % rid,
        source_kind="user_utterance", source_ref="utt/%s" % rid,
        participant_id=("A" if basis != "record_only" else None),
        participation_basis=basis, basis_ref="utt/%s" % rid,
        commitment_state="not_a_commitment", revision=1,
        prev_digest=None, changed_at=PIN, change_authority="synthetic")


def _store(*recs):
    s = RecoveryStore()
    for r in recs:
        s.insert(r)
    return s


# ================================================ 裁定一 · cause 归因

@case("AP-1", "凌翼反例：两次纠正，cause 必须是第二次的依据")
def ap1():
    """⚠ 凌翼静态推导出的反例，我复现成立，旧实现确实给错。

    旧实现：从累计 relation 取首条 ⇒ 给出 A（错）
    正确：  B（第二次纠正才把 R 搬出分母）
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))

    s.correct("R", "v2", "A", "first")
    assert s.get("R")["participation_basis"] == "first_person_report", (
        "前提：第一次纠正后 R 应仍是 first_person_report")
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 0

    s.correct("R", "v3", "B", "second")
    assert s.get("R")["participation_basis"] == "record_only"

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition"] == 1
    cause = r["denominator_attrition_cause"]["R"]
    assert cause == "B", (
        "cause 应为第二次纠正依据 'B'，实测 %r。"
        "若为 'A' 说明仍取累计 relation 首条。" % (cause,))
    return "cause='B'（不是 'A'）"


@case("AP-2", "三次纠正：取真正跃变那一版")
def ap2():
    """前两次都不改变 basis（都是 first_person），第三次才搬走。"""
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("A2", "first_person_report"),
               _rec("Z", "record_only"))
    s.correct("R", "v2", "A", "c1")
    s.correct("R", "v3", "A2", "c2")
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 0
    s.correct("R", "v4", "Z", "c3")

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition_cause"]["R"] == "Z", (
        "应追到第三次的 'Z'，实测 %r"
        % r["denominator_attrition_cause"]["R"])
    return "三条边中选第三条 'Z'"


@case("AP-3", "退出 → 恢复 → 再次退出，cause 跟着最后一次跃变")
def ap3():
    """凌翼要求覆盖「退出、恢复、再次退出」的多次转换。"""
    s = _store(_rec("R", "first_person_report"),
               _rec("out1", "record_only"),
               _rec("back1", "first_person_report"),
               _rec("out2", "record_only"))

    s.correct("R", "v2", "out1", "exit-1")
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 1
    assert AI.synthetic_ratios(s, [])["denominator_attrition_cause"]["R"] \
        == "out1"

    s.correct("R", "v3", "back1", "recover")
    r2 = AI.synthetic_ratios(s, [])
    assert r2["denominator_attrition"] == 0, (
        "恢复后应回到 0，实测 %d" % r2["denominator_attrition"])
    assert r2["denominator_attrition_cause"] == {}

    s.correct("R", "v4", "out2", "exit-2")
    r3 = AI.synthetic_ratios(s, [])
    assert r3["denominator_attrition"] == 1
    assert r3["denominator_attrition_cause"]["R"] == "out2", (
        "再次退出应追到 'out2'，实测 %r"
        % r3["denominator_attrition_cause"]["R"])
    return "exit(out1) → recover → exit(out2)，cause 跟最后跃变"


@case("AP-4", "回归：单次纠正仍然正确（不因修复而退化）")
def ap4():
    s = _store(_rec("R", "first_person_report"),
               _rec("only", "record_only"))
    s.correct("R", "v2", "only", "single")
    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition_cause"] == {"R": "only"}
    return "单次：cause='only'"


@case("AP-5", "归因未知必须显式报告，不得静默给错 ID")
def ap5():
    """凌翼：「如历史证据无法确定相应纠正依据，
            应显式报告归因未知，不得静默给出错误 ID。」

    构造：一条记录现在不是 first_person，历史里有过 first_person，
    但跃变那一版【没有】correction_of 边。
    直接篡改历史来模拟（normal 路径产生不了这种数据）。
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("donor", "record_only"))
    s.correct("R", "v2", "donor", "wash")

    # 模拟「跃变版缺边」：把 rev2 的 relation 清空
    for h in s._history["R"]:
        if h.get("revision") == 2:
            h["relation"] = []

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition"] == 1, (
        "前提：仍应算作流失，实测 %d" % r["denominator_attrition"])
    cause = r["denominator_attrition_cause"].get("R")
    assert cause == AI.UNKNOWN_CAUSE, (
        "无法归因时应为 %r，实测 %r（不得静默给一个 ID）"
        % (AI.UNKNOWN_CAUSE, cause))
    assert r["denominator_attrition_unknown"] == ["R"], (
        "应同时列出归因未知的记录，实测 %r"
        % r["denominator_attrition_unknown"])
    return "缺边 ⇒ cause=ATTRIBUTION_UNKNOWN 且列入 unknown"


@case("AP-6", "反证：AP-1 不是空的 —— 取累计首条会得到 'A'")
def ap6():
    """若把算法改回「取累计 relation 首条」，必须得到 'A'。
    证明 AP-1 的断言有分辨力。
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))
    s.correct("R", "v2", "A", "first")
    s.correct("R", "v3", "B", "second")

    # 旧算法的行为：取当前 relation 的第一条 correction_of
    old_cause = None
    for edge in (s.get("R").get("relation") or []):
        if edge.get("relation_type") == "correction_of":
            old_cause = edge.get("to_id")
            break
    assert old_cause == "A", (
        "旧算法应给出 'A'（证明它确实错），实测 %r" % old_cause)

    new_cause = AI.synthetic_ratios(s, [])["denominator_attrition_cause"]["R"]
    assert new_cause == "B" and new_cause != old_cause
    return "旧算法 'A' / 新算法 'B' —— 有分辨力"


@case("AP-13", "同一条依据被重复引用 ⇒ 不得误报 ATTRIBUTION_UNKNOWN")
def ap13():
    """⚠ 凌翼 2026-11-27 第二次静态核对指出的边界（我已复现成立）：

    「如果同一条纠正依据记录被重复引用，就可能发生误判。
      例如 R 第一次引用 A 时，A 是 first_person_report；
      后来 A 自身经过合法纠正，变成 record_only；
      R 第二次仍引用 A，结果退出第一人称分母。
      这时新的 correction_of 边已经追加，但 to_id 仍然是 A。
      当前算法会把它当成没有新增边，报告 ATTRIBUTION_UNKNOWN。」

    根因：原实现用【to_id 集合差】判断新增边 ——
      两次的 to_id 都是 'A'，集合差为空 ⇒ 误判为「无新增边」。
    修法：按【边数差】取尾部新增，不看 to_id 是否重复。
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("fixA", "record_only"))

    # 第 1 次：R 引用 A（A 此时 first_person）⇒ R 仍在分母
    s.correct("R", "v2", "A", "cite A #1")
    assert s.get("R")["participation_basis"] == "first_person_report"
    assert AI.synthetic_ratios(s, [])["denominator_attrition"] == 0

    # A 自身被合法纠正为 record_only
    s.correct("A", "A-v2", "fixA", "A 自身被改")
    assert s.get("A")["participation_basis"] == "record_only"

    # 第 2 次：R 再次引用 A ⇒ R 退出分母
    s.correct("R", "v3", "A", "cite A #2")
    assert s.get("R")["participation_basis"] == "record_only"

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition_ids"] == ["A", "R"], \
        r["denominator_attrition_ids"]
    cause = r["denominator_attrition_cause"]["R"]
    assert cause == "A", (
        "R 的纠正依据应为 'A'（第二次引用），实测 %r。"
        "若为 ATTRIBUTION_UNKNOWN，说明仍用 to_id 集合差判断新增边。"
        % (cause,))
    assert "R" not in r["denominator_attrition_unknown"], (
        "R 不应被列入归因未知")
    return "重复引用同一依据 ⇒ cause='A'，不误报 UNKNOWN"


@case("AP-14", "反证：AP-13 不是空的 —— to_id 集合差确实会误判")
def ap14():
    """证明 AP-13 有分辨力：用旧的集合差算法算一遍，必须得到「无新增边」。"""
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("fixA", "record_only"))
    s.correct("R", "v2", "A", "cite #1")
    s.correct("A", "A-v2", "fixA", "A changed")
    s.correct("R", "v3", "A", "cite #2")

    hist = s.history("R")
    prev_edges = [e for e in (hist[1].get("relation") or [])
                  if e.get("relation_type") == "correction_of"]
    this_edges = [e for e in (hist[2].get("relation") or [])
                  if e.get("relation_type") == "correction_of"]

    # 旧算法：to_id 集合差
    old_new = [e for e in this_edges
               if e.get("to_id") not in {pe.get("to_id") for pe in prev_edges}]
    assert old_new == [], (
        "旧算法应判「无新增边」（证明它确实会误报），实测 %r" % old_new)

    # 新算法：边数差
    n_new = len(this_edges) - len(prev_edges)
    assert n_new == 1, n_new
    assert this_edges[-n_new]["to_id"] == "A"

    # 而真实结果应是可归因
    assert AI.synthetic_ratios(s, [])["denominator_attrition_cause"]["R"] == "A"
    return "集合差→[] (误判) / 边数差→1 条 (正确)"


# ================================================ 裁定二 · preflight

@case("AP-7", "preflight 正常态：计划与登记一致、锚点各命中一次")
def ap7():
    pf = PF.preflight([m[0] for m in TM.MUTATIONS],
                      os.path.join(HERE, TM.TARGET),
                      TM.MUTATIONS)
    assert pf["ok"] is True, "正常计划被拒：%r" % pf["reasons"]
    assert pf["n_plan"] == pf["n_registered"], (
        "计划 %d / 登记 %d" % (pf["n_plan"], pf["n_registered"]))
    assert all(a["count"] == 1 for a in pf["anchors"])
    return "%d 条，全部 count==1" % pf["n_plan"]


@case("AP-8", "负向：人为使锚点失效 ⇒ preflight 必须拒绝")
def ap8():
    """凌翼裁定二：「增加一个负向回归：人为使锚点失效，
    preflight 应在完整变异运行前拒绝执行。」
    """
    bad = list(TM.MUTATIONS)
    # 把 I1 的旧锚点换成一个不存在的字符串
    m = bad[0]
    bad[0] = (m[0], m[1], "__ANCHOR_THAT_DOES_NOT_EXIST__", m[3], m[4])

    pf = PF.preflight([x[0] for x in bad],
                      os.path.join(HERE, TM.TARGET), bad)
    assert pf["ok"] is False, "锚点失效未被拒绝 ⇒ fail-open，违反裁定二第 3 条"
    assert any("锚点命中 0 次" in r for r in pf["reasons"]), pf["reasons"]
    return "拒绝执行，原因：%s" % pf["reasons"][0]


@case("AP-9", "负向：计划少于登记（清单缩水）⇒ 必须拒绝")
def ap9():
    plan = [m[0] for m in TM.MUTATIONS if m[0] != "I14"]
    pf = PF.preflight(plan, os.path.join(HERE, TM.TARGET), TM.MUTATIONS)
    assert pf["ok"] is False, "清单缩水未被拒绝 ⇒ 违反裁定二第 1 条"
    assert pf["missing_ids"] == ["I14"], pf["missing_ids"]
    return "missing_ids=['I14']"


@case("AP-10", "负向：计划含未登记项 ⇒ 必须拒绝")
def ap10():
    plan = [m[0] for m in TM.MUTATIONS] + ["I_GHOST"]
    pf = PF.preflight(plan, os.path.join(HERE, TM.TARGET), TM.MUTATIONS)
    assert pf["ok"] is False
    assert pf["unknown_ids"] == ["I_GHOST"], pf["unknown_ids"]
    return "unknown_ids=['I_GHOST']"


@case("AP-11", "要求 4：preflight 失败也留下带本次 run_id 的报告")
def ap11():
    """凌翼：「失败也必须留下具有本次 run_id 的可辨认结果，
    不得沿用旧报告。」

    ⇒ 跑真驱动，但先破坏目标文件的一个锚点（在临时目录里做），
      验证报告被覆写且 run_id 变化、verdict=EVIDENCE_FAIL、
      baseline 未运行。
    """
    import shutil
    import subprocess

    with tempfile.TemporaryDirectory() as td:
        work = os.path.join(td, "proto")
        shutil.copytree(HERE, work,
                        ignore=shutil.ignore_patterns("__pycache__",
                                                      "*.npy"))
        # 破坏 I1 的锚点
        m = TM.MUTATIONS[0]
        p = os.path.join(work, TM.TARGET)
        with open(p, encoding="utf-8") as f:
            src = f.read()
        assert src.count(m[2]) == 1
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(src.replace(m[2], "__BROKEN_ANCHOR__", 1))

        r = subprocess.run([sys.executable,
                            os.path.join(work, "test_mutations_importance.py")],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           cwd=work, timeout=600,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        assert r.returncode == 1, (
            "preflight 失败时退出码应为 1，实测 %d" % r.returncode)

        rep = os.path.join(work, "reports",
                           "mutations_importance_result.json")
        assert os.path.exists(rep), "preflight 失败未写报告"
        with open(rep, encoding="utf-8") as f:
            d = json.load(f)

    assert d["verdict"] == "EVIDENCE_FAIL", d["verdict"]
    assert d["manifest_check"] == "NOT_RUN_PREFLIGHT_FAILED", \
        d["manifest_check"]
    assert d["baseline_ok"] is None, (
        "preflight 失败时基线不应被运行，实测 baseline_ok=%r"
        % d["baseline_ok"])
    assert d.get("preflight", {}).get("ok") is False
    assert d.get("run_id"), "报告必须带 run_id"
    assert d.get("rows") == [], "preflight 失败时不应有变异行"
    return "verdict=FAIL / baseline 未跑 / 带 run_id"


@case("AP-12", "反证：正常计划下 preflight 通过，证明 AP-8/9/10 不是恒假")
def ap12():
    """若 preflight 永远返回 False，AP-8/9/10 也都会绿。
    这里必须有一条能通过的，证明上面三条有分辨力。
    """
    ok = PF.preflight([m[0] for m in TM.MUTATIONS],
                      os.path.join(HERE, TM.TARGET), TM.MUTATIONS)
    assert ok["ok"] is True, "正常计划应通过，实测 reasons=%r" % ok["reasons"]
    assert ok["reasons"] == []
    return "正常计划 ok=True / reasons=[]"


@case("AP-16", "歧义：跃变版新增两条边 ⇒ 归因未知，不得签发具体 ID")
def ap16():
    """⚠ 知微 2026-11-27 独立复核 §2 指出的第三种失效（我已复现）：

    「保留相同版本和退出事实，仅在只读历史替身里
      让退出版本同时新增指向 A、B 的两条纠正边。
      afimportance.py 按边数增长取新增段首条，
      返回流失 1、依据 A、未知清单为空。」

    ⇒ 两份候选都在新增段里，签发给 A 是【假的确定性】。
    ⇒ 修法（知微给定）：只有【新增段恰好一条】且可归属到本条记录、
      目标有效时才签发具体 ID；否则 ATTRIBUTION_UNKNOWN。

    ⚠ 本用例只改【只读历史替身】，不制造异常历史，不改真实存储。
    """
    import copy

    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))
    s.correct("R", "v2", "A", "cite A")
    s.correct("R", "v3", "B", "cite B")

    real = s.history("R")
    assert real[1]["participation_basis"] == "first_person_report"
    assert real[2]["participation_basis"] == "record_only"

    # 替身：退出版本同时新增 A、B 两条边
    sim = [copy.deepcopy(h) for h in real]
    prev = list(sim[1].get("relation") or [])
    sim[2]["relation"] = prev + [
        {"relation_type": "correction_of", "from_id": "R", "to_id": "A",
         "relation_basis": "cited again at same time"},
        {"relation_type": "correction_of", "from_id": "R", "to_id": "B",
         "relation_basis": "cited B"},
    ]

    class _Fake(RecoveryStore):
        def history(self, rid):
            if rid == "R":
                return copy.deepcopy(sim)
            return super().history(rid)

    fs = _Fake.__new__(_Fake)
    fs.__dict__.update(s.__dict__)

    r = AI.synthetic_ratios(fs, [])
    assert r["denominator_attrition"] == 1, (
        "流失计数应保留为 1，实测 %d" % r["denominator_attrition"])
    cause = r["denominator_attrition_cause"]["R"]
    assert cause == AI.UNKNOWN_CAUSE, (
        "新增两条边时不得签发具体 ID（实测 %r）—— "
        "那会给出假的确定性" % (cause,))
    assert "R" in r["denominator_attrition_unknown"], (
        "R 应进入 unknown 清单")
    return "两条新增边 ⇒ ATTRITION_UNKNOWN + unknown 含 R"


@case("AP-17", "对照：新增段恰好一条且可归属 ⇒ 仍签发具体 ID")
def ap17():
    """AP-16 不能把正常可归因的情况也判成未知。
    这是 AP-16 的必需对照，否则修法会退化成「全都不签」。
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))
    s.correct("R", "v2", "A", "cite A")
    s.correct("R", "v3", "B", "cite B")

    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition_cause"]["R"] == "B", \
        r["denominator_attrition_cause"]
    assert "R" not in r["denominator_attrition_unknown"]
    return "单条可归属 ⇒ cause='B'"


@case("AP-18", "解码失败 ⇒ preflight 必须走失败出口并落本轮报告")
def ap18():
    """⚠ 知微 2026-11-27 独立复核 §3：

    「另一个真入口对照先保留上轮 COMPLETE 报告，
      再在临时副本中让目标文件无法按 UTF-8 解码。
      实得退出码 1、UnicodeDecodeError，磁盘报告逐字节未变，
      仍显示上轮 EVIDENCE_COMPLETE。
      本轮停止执行了，却没有给读取报告的人留下本轮的失败记录。」

    根因：UnicodeDecodeError 是 ValueError 子类，【不是】OSError，
          原 preflight 只接住 OSError ⇒ 异常逃出 ⇒ 跳过失败报告。
    """
    import json
    import shutil
    import subprocess

    with tempfile.TemporaryDirectory() as td:
        work = os.path.join(td, "proto")
        shutil.copytree(HERE, work,
                        ignore=shutil.ignore_patterns("__pycache__",
                                                      "*.npy"))
        rep = os.path.join(work, "reports",
                           "mutations_importance_result.json")

        # 先放一份「上轮成功报告」
        os.makedirs(os.path.dirname(rep), exist_ok=True)
        with open(rep, "w", encoding="utf-8") as f:
            json.dump({"verdict": "EVIDENCE_COMPLETE",
                       "run_id": "OLD-RUN-FROM-LAST-ROUND",
                       "exit_code": 0}, f)
        old_bytes = open(rep, "rb").read()

        # 让目标文件无法按 UTF-8 解码
        p = os.path.join(work, TM.TARGET)
        with open(p, "wb") as f:
            f.write(b"\xff\xfe\x00\x00invalid utf8 \xc3\x28\n")

        r = subprocess.run(
            [sys.executable,
             os.path.join(work, "test_mutations_importance.py")],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=work, timeout=600,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        assert r.returncode == 1, (
            "解码失败时退出码应为 1，实测 %d" % r.returncode)

        new_bytes = open(rep, "rb").read()
        assert new_bytes != old_bytes, (
            "报告未被本轮覆盖 ⇒ 读报告的人看到的是上轮的 COMPLETE")

        d = json.loads(new_bytes.decode("utf-8"))

    assert d["verdict"] == "EVIDENCE_FAIL", d["verdict"]
    assert d["run_id"] != "OLD-RUN-FROM-LAST-ROUND", (
        "run_id 应为本轮新值，实测 %r" % d.get("run_id"))
    assert d["baseline_ok"] is None, (
        "解码失败时基线不应运行，实测 baseline_ok=%r" % d["baseline_ok"])
    assert d["rows"] == [], d["rows"]
    reasons = " ".join(d.get("preflight", {}).get("reasons") or [])
    assert "UTF-8" in reasons or "UTF" in reasons, (
        "报告应含可辨认的解码原因，实测 reasons=%r" % reasons)
    return "解码失败 ⇒ 新 run_id / FAIL / baseline 未跑 / 原因可辨认"


@case("AP-15", "边界：preflight【不】校验经审查的名册摘要身份")
def ap15():
    """⚠ 凌翼 2026-11-27 第二次核对：

    「preflight 目前核对清单 ID 与锚点；
      经过审查的清单摘要身份仍在变异执行后核对。
      因此它不能被描述为完整的前置可信身份验证。
      现有最终判定仍保留这层防护，不必为此另开一轮工程。」

    ⇒ 本用例把这个【范围限制】写成断言，
      防止以后有人把 preflight 说成「完整前置可信身份验证」。

    做法：
      (a) 断言 preflight 模块不 import 名册摘要校验
      (b) 篡改名册的 REGISTERED_MUTATION_IDS 但保持计划不变 ⇒
          preflight 仍判 ok（因为它不比摘要）
          —— 这正是「它管不到摘要」的证据
      (c) 而 check_manifest_identity 能发现篡改
          —— 说明防护在另一处，不是没有
    """
    import inspect
    import io
    import tokenize
    src = inspect.getsource(PF)
    # ⚠ 只检查【代码】，不检查注释与文档字符串 ——
    #   我在模块 docstring 里【提到】了 check_manifest_identity 来说明
    #   「本模块不做这件事」。若按整份源码查，会把这句说明当成违规。
    #   （AP-15 第一次跑就撞上了这个：断言抓到我自己的注释。）
    code_only = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            code_only.append(tok.string)
    except (tokenize.TokenError, IndentationError):
        code_only = [src]
    code_text = " ".join(code_only)
    for banned in ("check_manifest_identity", "REVIEWED_MANIFEST_SHA256",
                   "manifest_sha256"):
        assert banned not in code_text, (
            "preflight 的【代码】里出现了 %r ⇒ 它可能在比摘要，"
            "与「摘要身份在后续阶段核对」的说法不符" % banned)

    # (b) 差分对照（知微 2026-11-27 第二次复验修正）：
    #
    # ⚠ 我上一版的做法有漏洞（知微实测指出）：
    #     我重新绑定 MM.REGISTERED_MUTATION_IDS，
    #     但 mutation_preflight 在模块加载时【按名字导入】了原元组
    #     （from mutation_manifest import REGISTERED_MUTATION_IDS），
    #     重绑定 manifest 模块的属性【不会】影响 preflight 里的那个名字。
    #   ⇒ 两个模块读到的顺序实测不同 ⇒ 我那条「一对相反结果」是假的：
    #     preflight 那边根本没经历同一项变化。
    #
    #   ⇒ 现在把反转后的序列【显式传给】PF.preflight 的 registered_ids，
    #     并用同一序列做名册身份核验，使两侧真正经历同一项变化。
    import mutation_manifest as MM
    plan = [m[0] for m in TM.MUTATIONS]
    orig = list(MM.REGISTERED_MUTATION_IDS)
    rev = list(reversed(orig))
    assert set(rev) == set(orig), "顺序颠倒不应改变集合"

    # 对照一：原顺序 ⇒ preflight 通过、身份一致
    pf_same = PF.preflight(plan, os.path.join(HERE, TM.TARGET),
                           TM.MUTATIONS, registered_ids=orig)
    ident_same = MM.check_manifest_identity()
    assert pf_same["ok"] is True, pf_same["reasons"]
    assert ident_same["consistent"] is True

    # 对照二：仅顺序反转，【显式喂给 preflight 同一序列】
    pf_rev = PF.preflight(plan, os.path.join(HERE, TM.TARGET),
                          TM.MUTATIONS, registered_ids=rev)
    assert pf_rev["ok"] is True, (
        "preflight 只看集合与锚点，顺序反转后应仍通过；实测 reasons=%r"
        % pf_rev["reasons"])

    # 倒序分支的身份核验必须调用【真实核验器】，不能手算摘要
    #
    # ⚠ 2026-11-27 第三次修正（知微第三次复验指出）：
    #   原写法在测试里【手算】倒序摘要再与冻结值比，
    #   ⇒ 知微实测：把真实核验器改成「始终使用登记摘要」，AP-15 仍绿。
    #     因为根本没经过那个核验器。
    #   ⇒ 现在：在测试作用域里让名册模块读到同一倒序元组，
    #     断言真实 check_manifest_identity()["consistent"] is False，
    #     再在 finally 中恢复。
    orig_tuple = MM.REGISTERED_MUTATION_IDS
    try:
        MM.REGISTERED_MUTATION_IDS = tuple(rev)
        ident_rev = MM.check_manifest_identity()
        assert ident_rev["consistent"] is False, (
            "倒序名册下真实核验器应判不一致，实测 %r"
            % ident_rev["consistent"])
        assert ident_rev["current"] != ident_rev["reviewed"]
    finally:
        MM.REGISTERED_MUTATION_IDS = orig_tuple

    # 恢复后应回到一致
    assert MM.check_manifest_identity()["consistent"] is True
    return ("仅反转登记顺序：preflight 通过 / 真实 check_manifest_identity "
            "判不一致 ⇒ 两阶段责任不同")


@case("AP-19", "前缀不匹配：退出版本边序为 [B,A] 而前版 [A] ⇒ 归因未知")
def ap19():
    """⚠ 知微 2026-11-27 第二次复验指出（我已复现）：

    「在相同 R 历史中，只让退出版本返回的纠正边顺序从 [A,B] 变成 [B,A]，
      前版仍为 [A]。实测流失数 1，cause=A，unknown 为空。
      长度差仍是 1，但末尾的 A 在上一版就已经存在。
      以末尾位置签发 A 的依据不足。
      建议在取新增段前检验历史前缀。」

    ⇒ 修法：先验证 prev_edges 是 this_edges 的【前缀】；
      不匹配 ⇒ 无法判断哪条新增 ⇒ ATTRIBUTION_UNKNOWN。
    """
    import copy
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))
    s.correct("R", "v2", "A", "cite A")
    s.correct("R", "v3", "B", "cite B")
    real = s.history("R")

    sim = [copy.deepcopy(h) for h in real]
    # 顺序反转：前版 [A]，本版 [B, A] —— 前版不是本版前缀
    sim[2]["relation"] = [
        {"relation_type": "correction_of", "from_id": "R", "to_id": "B",
         "relation_basis": "b"},
        {"relation_type": "correction_of", "from_id": "R", "to_id": "A",
         "relation_basis": "a"},
    ]

    class _F(RecoveryStore):
        def history(self, rid):
            if rid == "R":
                return copy.deepcopy(sim)
            return super().history(rid)

    f = _F.__new__(_F)
    f.__dict__.update(s.__dict__)
    r = AI.synthetic_ratios(f, [])

    assert r["denominator_attrition"] == 1, r["denominator_attrition"]
    assert r["denominator_attrition_cause"]["R"] == AI.UNKNOWN_CAUSE, (
        "前缀不匹配时不得签发任何 ID，实测 %r"
        % r["denominator_attrition_cause"]["R"])
    assert "R" in r["denominator_attrition_unknown"]
    return "边序 [B,A] 非前版 [A] 的前缀 ⇒ ATTRIBUTION_UNKNOWN"


@case("AP-20", "边缺 from_id ⇒ 不得签发（须由边本身证明归属）")
def ap20():
    """⚠ 知微 2026-11-27 第二次复验：

    「另一个可以直接裁定的约定是缺失 from_id：
      删去该字段，当前会签发 B。
      若历史容器本身提供可采信的归属，可注明该前提；
      若需要边本身证明归属，应要求 from_id 等于 R。」

    ⇒ 我选后者：要求 from_id 显式等于 rid。
      理由：历史容器不提供可采信的归属证据，
            只有边自己的 from_id 能证明它属于本条记录。

    ⚠ 2026-11-27 第三次修正（知微第三次复验指出，我已复现）：
      原用例「删除退出版本【所有】边的 from_id」——
      连旧边（前版已有那条）也改了，
      于是【前缀检查先拒绝】这份历史，根本走不到「新增边归属」那一关。
      知微实测：在临时副本恢复「允许空 from_id」的旧判断，仓内 AP-20 仍绿。
      ⇒ 单因素：只删【新增边】的 from_id，前版边逐项原样。
    """
    import copy
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))
    s.correct("R", "v2", "A", "cite A")
    s.correct("R", "v3", "B", "cite B")
    real = s.history("R")

    sim = [copy.deepcopy(h) for h in real]
    prev_edges = list(sim[1].get("relation") or [])
    # 只删【新增那一条】的 from_id；前版边保持原样（前缀仍成立）
    new_edge = copy.deepcopy(sim[2]["relation"][len(prev_edges)])
    new_edge.pop("from_id", None)
    sim[2]["relation"] = copy.deepcopy(prev_edges) + [new_edge]

    # 自检：前缀仍成立，确认这条用例真的走到了「新增边归属」那一关
    assert sim[2]["relation"][:len(prev_edges)] == prev_edges, (
        "用例构造错误：前缀被打断 ⇒ 测不到新增边归属")
    assert "from_id" not in sim[2]["relation"][-1], "新增边应已无 from_id"
    assert all("from_id" in e for e in prev_edges), "旧边不应被改动"

    class _F(RecoveryStore):
        def history(self, rid):
            if rid == "R":
                return copy.deepcopy(sim)
            return super().history(rid)

    f = _F.__new__(_F)
    f.__dict__.update(s.__dict__)
    r = AI.synthetic_ratios(f, [])

    assert r["denominator_attrition"] == 1, r["denominator_attrition"]
    assert r["denominator_attrition_cause"]["R"] == AI.UNKNOWN_CAUSE, (
        "新增边缺 from_id 时不得签发，实测 %r"
        % r["denominator_attrition_cause"]["R"])
    assert "R" in r["denominator_attrition_unknown"]
    return "仅新增边缺 from_id（前缀完好）⇒ ATTRIBUTION_UNKNOWN"


@case("AP-21", "反证：AP-19/20 不是空的 —— 正常边仍签发 'B'")
def ap21():
    """若修法退化成「全都不签」，AP-19/20 会绿而 AP-17 也会红。
    这里再确认一次正常路径，防止三处一起退化。
    """
    s = _store(_rec("R", "first_person_report"),
               _rec("A", "first_person_report"),
               _rec("B", "record_only"))
    s.correct("R", "v2", "A", "cite A")
    s.correct("R", "v3", "B", "cite B")
    r = AI.synthetic_ratios(s, [])
    assert r["denominator_attrition_cause"]["R"] == "B", \
        r["denominator_attrition_cause"]
    assert r["denominator_attrition_unknown"] == []
    return "正常路径仍签发 'B'，unknown=[]"


# ================================================ 汇总
def main():
    print("=" * 80)
    print("凌翼 2026-11-27 裁定 · 定点回归（cause 归因 + preflight）")
    print("=" * 80)
    print()
    for f in (ap1, ap2, ap3, ap4, ap5, ap6, ap13, ap14, ap16, ap17,
              ap19, ap20, ap21,
              ap7, ap8, ap9, ap10, ap11, ap12, ap18, ap15):
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
