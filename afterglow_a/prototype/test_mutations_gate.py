# -*- coding: utf-8 -*-
"""
变异验证：门禁测试能不能被真的打破？

目的：证明 test_recovery_gate.py 的 10 条不是「怎么写都过」。
做法：把实现里每一处关键判断逐个破坏（mutate），
      确认【对应测试真的会失败】。

判据：
  CAUGHT      破坏后至少一条测试失败 —— 测试确实在守这件事
  MISSED      破坏后全部通过 —— 测试没守住（必须修测试）
  NOT_EXECUTED 破坏后测试根本没跑到 —— 假绿，最危险

运行：python afterglow_a/prototype/test_mutations_gate.py
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO_FILES = ("afcore.py", "afrecover.py")
# 变异验证必须跑【全部】守护测试。
# 之前只列了 test_recovery_gate / test_p1_p5，导致 Z61 新门禁的变异
# 全部 MISSED —— 不是门禁没守住，是守护它的测试没被跑。
#
# ⚠ test_layer_evidence.py 依赖同目录的 layer_evidence 模块，
#   该模块必须一并复制（见 MODULE_FILES），否则基线直接 ModuleNotFoundError。
TEST_FILES = ("test_recovery_gate.py", "test_p1_p5.py", "test_z61_gaps.py",
              "test_observed_channel.py", "test_origin_layer.py",
              "test_field_classification.py", "test_layer_evidence.py")
# 被测试 import 的同目录模块（不是测试文件本身，但必须存在）
MODULE_FILES = ("layer_evidence.py",)


def _harden_stdio():
    for name in ("stdout", "stderr"):
        st = getattr(sys, name, None)
        if st is None:
            continue
        try:
            st.reconfigure(encoding="utf-8")
        except Exception:
            try:
                st.reconfigure(errors="backslashreplace")
            except Exception:
                pass


_harden_stdio()


# ---------------------------------------------------------------- 变异定义
# 每条：(id, 说明, 目标文件, 原文, 替换为)
# 原文必须精确匹配一次，否则算 INVALID（变异没生效，不算数）

MUTATIONS = [
    # ---- 门禁核心：完整性失败是否阻断资格
    (
        "M1", "把 integrity_failed 的阻断删掉（失败也不影响资格）",
        "afrecover.py",
        '    if integ["status"] == "failed":\n'
        '        reasons.append("integrity_failed")\n'
        '    elif integ["status"] != "verified":\n'
        '        reasons.append("integrity_not_checked")',
        '    pass  # MUTANT: 完整性结果不参与资格判断',
    ),
    (
        "M2", "只删 failed 分支，未检查仍阻断",
        "afrecover.py",
        '    if integ["status"] == "failed":\n'
        '        reasons.append("integrity_failed")\n'
        '    elif integ["status"] != "verified":\n'
        '        reasons.append("integrity_not_checked")',
        '    if integ["status"] != "verified":\n'
        '        reasons.append("integrity_not_checked")',
    ),
    (
        "M3", "把 not_checked 当通过（默认为通过）",
        "afrecover.py",
        '    elif integ["status"] != "verified":\n'
        '        reasons.append("integrity_not_checked")',
        '    elif False:\n        reasons.append("integrity_not_checked")',
    ),
    # ---- 快照失效
    (
        "M4", "删掉 stale_check 阻断（旧检查结果可沿用）",
        "afrecover.py",
        '    if stale:\n        reasons.append("stale_check")',
        '    if False:\n        reasons.append("stale_check")',
    ),
    # ---- 登记身份
    (
        "M5", "删掉登记独立性阻断",
        "afrecover.py",
        '    if reg["present"] and not reg["independent"]:\n'
        '        reasons.append("registration_not_independent")',
        '    if False:\n        reasons.append("registration_not_independent")',
    ),
    (
        "M6", "让 check_registration 永远判独立",
        "afrecover.py",
        '    independent = (\n'
        '        reg.get("independent_of_write") == "yes"\n'
        '        and reg.get("before_exposure") == "yes"\n'
        '        and not problems\n    )',
        '    independent = True  # MUTANT',
    ),
    # ---- 空期望集
    (
        "M7", "删掉 no_expected_ids 阻断",
        "afrecover.py",
        '    elif not detail.get("expected"):\n'
        '        # 期望集为空列表时，集合关系无意义（任何 retrieved 都会 disjoint）\n'
        '        reasons.append("no_expected_ids")',
        '    elif False:\n        reasons.append("no_expected_ids")',
    ),
    # ---- 串轴：让完整性污染 match_kind
    (
        "M8", "让完整性失败改写 match_kind（两轴串了）",
        "afrecover.py",
        '        "match_kind": kind,',
        '        "match_kind": (None if integ["status"] == "failed" else kind),',
    ),
    # ---- not_run 重回枚举
    (
        "M9", "not_run 重新进入 MATCH_KINDS",
        "afcore.py",
        'MATCH_KINDS = {"exact", "superset", "subset", "disjoint"}',
        'MATCH_KINDS = {"exact", "superset", "subset", "disjoint", "not_run"}',
    ),
    (
        "M10", "未执行时返回字符串 not_run",
        "afrecover.py",
        '    if not ran or expected is None:\n'
        '        return None, {',
        '    if not ran or expected is None:\n'
        '        return "not_run", {',
    ),
    # ---- content_digest
    (
        "M11", "内容摘要缺字段时按缺省填充而不是报错",
        "afcore.py",
        '    missing = [k for k in CONTENT_DIGEST_FIELDS if k not in record]\n'
        '    if missing:\n'
        '        raise SchemaError(',
        '    missing = []\n'
        '    if missing:\n'
        '        raise SchemaError(',
    ),
    (
        "M12", "让 changed_at 混进内容摘要投影",
        "afcore.py",
        '    "relation",       # relation 是内容的一部分（指向谁、为何指向）\n)',
        '    "relation",       # relation 是内容的一部分（指向谁、为何指向）\n'
        '    "changed_at",\n)',
    ),
    # ---- 外部锚定
    (
        "M13", "声称外部锚定已建立",
        "afrecover.py",
        '        "trusted_chain_anchor": "not_established",',
        '        "trusted_chain_anchor": "established",',
    ),
    (
        "M14", "把工程结果标成科学结果",
        "afrecover.py",
        '        "is_scientific_result": False,',
        '        "is_scientific_result": True,',
    ),
    # ---- snapshot_token
    (
        "M15", "snapshot_token 忽略 live 侧",
        "afcore.py",
        '        for rid in sorted(self._live):\n'
        '            cur = self._live[rid]\n'
        '            parts.append([rid + "\\x00live",\n'
        '                          json.dumps(cur.to_dict(), sort_keys=True,\n'
        '                                     ensure_ascii=False,\n'
        '                                     separators=(",", ":"))])',
        '        pass  # MUTANT: 不纳入 live 侧',
    ),
    # Z61-02（知微 2026-11-24 §4）：快照必须覆盖历史实际内容
    (
        "M15b", "snapshot_token 只取历史条数不看内容（Z61-02 原缺陷形态）",
        "afcore.py",
        '            ver_parts = []\n'
        '            for d in hist:\n'
        '                ver_parts.append(json.dumps(\n'
        '                    d, sort_keys=True, ensure_ascii=False,\n'
        '                    separators=(",", ":")))\n'
        '            parts.append([rid, ver_parts])',
        '            parts.append([rid, len(hist)])  # MUTANT: 只看条数',
    ),
    # Z61-01（知微 2026-11-24 §3）：默认必须比较本次检查的快照
    (
        "M17", "G6 只在外部传 expected_snapshot 时生效（Z61-01 原缺陷形态）",
        "afrecover.py",
        '        if checked_tok is not None and now_tok != checked_tok:',
        '        if False and checked_tok is not None and now_tok != checked_tok:',
    ),
    # Z61-04（知微 2026-11-24 §6）：failed 不得被 stale 覆盖
    (
        "M18", "stale 时无条件改写状态（Z61-04 原缺陷形态）",
        "afrecover.py",
        '            if integ["status"] == "failed":',
        '            if False:',
    ),
    # Z61-03（知微 2026-11-24 §5）：登记身份空值必须判不合格
    (
        "M19", "不校验 registered_by/rev 的空白（Z61-03 原缺陷形态）",
        "afrecover.py",
        '        elif not v.strip():\n'
        '            problems.append("%s 为空或纯空白（须给出实际取值）" % k)',
        '        elif False:\n'
        '            problems.append("%s 为空或纯空白（须给出实际取值）" % k)',
    ),
    (
        "M20", "registered_by 非字符串类型被放行（Z61-03 变形）",
        "afrecover.py",
        '        elif not isinstance(v, str):\n'
        '            problems.append("%s 类型为 %s（须为字符串）" % (k, type(v).__name__))',
        '        elif False:\n'
        '            problems.append("%s 类型为 %s（须为字符串）" % (k, type(v).__name__))',
    ),
    # ---- 完整性检查：空范围当通过
    (
        "M16", "空检查范围当作 verified",
        "afrecover.py",
        '    ids = sorted(set(record_ids))\n'
        '    if not ids:\n'
        '        return {\n'
        '            "status": "not_checked",',
        '    ids = sorted(set(record_ids))\n'
        '    if not ids:\n'
        '        return {\n'
        '            "status": "verified",',
    ),
    # ---- Mion 2026-11-24 回复2 / 回复3 的四项改造
    (
        "M21", "conflict_summary 从返回结构删掉（Mion 第 0 项）",
        "afrecover.py",
        '        "conflict_summary": conflict,',
        '        # MUTANT: 不返回冲突摘要',
    ),
    (
        "M22", "「未观测」返回成 none 而非 observed_absent（Mion 第 0 项核心）",
        "afrecover.py",
        '        if val is None:\n'
        '            # 字段缺失 = 从未计算过 ⇒ 不得当作 none\n'
        '            buckets.setdefault("observed_absent", []).append(rid)',
        '        if val is None:\n'
        '            buckets.setdefault("none", []).append(rid)  # MUTANT',
    ),
    (
        "M23", "去掉 record_observed 的时序约束（Mion 第 2 项·批量补洞）",
        "afcore.py",
        '        if cur.revision != 1:',
        '        if False:  # MUTANT: 允许事后补观测',
    ),
    (
        "M26", "允许 Record 构造器填 observed_origin（Mion 第 1 项）",
        "afcore.py",
        '        if rec.observed_origin is not None or rec.basis_conflict is not None:',
        '        if False:  # MUTANT',
    ),
    # ---- Mion 回复4：观测在链外 + 判定表 + 派生标记
    (
        "M27", "观测不写进观测链（Mion 回复4 §二·链外问题）",
        "afcore.py",
        '        self._observed_chain.setdefault(record_id, []).append(entry)',
        '        pass  # MUTANT: 观测不进链',
    ),
    (
        "M28", "观测链不纳入 snapshot_token（Mion 回复4 §三）",
        "afcore.py",
        '        for rid in sorted(self._observed_chain):',
        '        for rid in []:  # MUTANT',
    ),
    (
        "M29", "record_only × model_generation 判成冲突（Mion 回复4 §4.2）",
        "afcore.py",
        '            conflict = "none"\n        else:\n'
        '            conflict = "observed_unresolved"',
        '            conflict = "asserted_contradicts_observed"\n        else:\n'
        '            conflict = "observed_unresolved"',
    ),
    (
        "M30", "伪亲历合并进 basis_conflict 当第五值（Mion 回复4 §五）",
        "afcore.py",
        '        pseudo = (asserted == "first_person_report"\n'
        '                  and observed == "model_generation")',
        '        pseudo = False  # MUTANT: 不派生伪亲历标记',
    ),
    # ---- 知微 2026-11-24：逐条绑定 + 观测携带所见版本
    (
        "M31", "不逐条绑定（只返回整批枚举，知微第一条）",
        "afrecover.py",
        '                "per_record": build_per_record(store, ids, buckets),',
        '                "per_record": [],  # MUTANT: 只有整批枚举',
    ),
    (
        "M32", "不校验观测所指版本是否存在（知微第二条）",
        "afcore.py",
        '            if observed_record_digest not in known_digests:',
        '            if False:  # MUTANT: 任何 digest 都接受',
    ),
    (
        "M33", "允许旧版 digest 贴到新内容上（知微指出的错位）",
        "afcore.py",
        '            if observed_rev != cur.revision:',
        '            if False:  # MUTANT: 不检查版本是否当前',
    ),
    # ---- Mion 2026-11-24 §二 第 4 项：原始来源层
    (
        "M34", "insert 不写 origin_*（Mion 第 4 项 ①）",
        "afcore.py",
        '        if rec.origin_source_kind is None:',
        '        if False:  # MUTANT: 不记录原始来源',
    ),
    (
        "M35", "revise 允许直接改来源（Mion 第 4 项 ②）",
        "afcore.py",
        '        if touching_source and not via_correct:',
        '        if False:  # MUTANT: 允许绕过 correct 改来源',
    ),
    (
        "M36", "was_corrected 用 revision>1 而非 origin≠current（Mion 第 4 项 ③）",
        "afcore.py",
        '        return any([\n'
        '            rec.origin_source_kind != rec.source_kind,',
        '        return rec.revision > 1 or any([\n'
        '            rec.origin_source_kind != rec.source_kind,',
    ),
    # ---- Mion 2026-11-25 回复6 §三：_via_correct 曾是调用方可自塞的键
    #
    # ⚠ 变异设计：v1 曾写「三层必须同时拆」，**那是错的**。
    #   Mion 回复7 E1 要求「无效变异必须由直接观测证成」，
    #   我照做后发现 v1 的探针只测了一种攻击（塞 "_via_correct" 字符串），
    #   于是把 `Record(**merged)` 撞出的 TypeError 误当成「拦住了」。
    #
    #   实测（layer_evidence.py v2，两种攻击分开测）：
    #     A 型（塞 _via_correct）     B 型（只改来源，不塞）
    #     （不拆）      BLOCKED_BY_L1  BLOCKED_BY_L3
    #     只拆 L3      BLOCKED_BY_L1  OPENED          ← 只拆一层就穿
    #     只拆 L1      BLOCKED_BY_L2  BLOCKED_BY_L3
    #     四层全拆      ACCIDENT       OPENED
    #
    #   ⇒ 真正守住「改来源必须走 correct()」的只有 L3_SOURCE_GUARD。
    #     L1/L2/L4 只对 `_via_correct` 这个【特定字符串】设防；
    #     攻击者不写这个字符串，三层全部不起作用。
    #   ⇒ 所以变异只需要拆 L3 一条。拆多层不是「更强的变异」，
    #     而是「把真正的那一层藏在一堆无关改动里」。
    (
        "M37", "拆掉来源字段护栏 ⇒ 可直接改来源且不留 correction_of"
               "（Mion 回复6 §三；回复7 E1 实测口径）",
        "afcore.py",
        '        if touching_source and not via_correct:',
        '        if False:  # MUTANT: 来源字段护栏失效（L3）',
    ),
    (
        "M38", "拆掉显式拒收保留键 ⇒ 只剩白名单拦（L1 单独证据）",
        "afcore.py",
        '        if "_via_correct" in changes:\n'
        '            raise SchemaError(\n'
        '                "changes 不得包含保留键 _via_correct。"\n'
        '                "「是否纠正流程」由调用哪个方法来决定，不由调用方传入。")',
        '        # MUTANT: L1 失效（B 型攻击不受影响，见 layer_evidence）',
    ),
    (
        "M39", "白名单放行 _via_correct ⇒ 只剩 L1 拦（L2 单独证据）",
        "afcore.py",
        '        allowed = self._correctable() if via_correct else set(self._REVISABLE)',
        '        allowed = (self._correctable() | {"_via_correct"} if via_correct\n'
        '                   else set(self._REVISABLE) | {"_via_correct"})'
        '  # MUTANT: L2 失效（两个分支都放行）',
    ),
    (
        "M40", "公开入口读 dict 里的标志 ⇒ 只剩 L1 拦（L4 单独证据）",
        "afcore.py",
        '        return self._revise_impl(record_id, changes, reason, authority,\n'
        '                                 via_correct=False)',
        '        return self._revise_impl(record_id, changes, reason, authority,\n'
        '                                 via_correct=bool(\n'
        '                                     changes.get("_via_correct")))'
        '  # MUTANT: L4 失效',
    ),
    # ---- Mion 2026-11-25 裁定2 H1/H2：字段三分类
    (
        "M41", "把某个来源字段偷偷放回可改白名单（H2b 必须红）",
        "afcore.py",
        '    _REVISABLE = {\n        "content", "commitment_state",',
        '    _REVISABLE = {\n        "content", "source_kind", "commitment_state",'
        '  # MUTANT: 来源字段混回白名单',
    ),
]


# ---------------------------------------------------------------- 执行

def run_tests(tmpdir):
    """在临时副本里跑两个测试文件，返回 (rc, 输出, 是否真的执行了)。"""
    outs = []
    any_executed = False
    rcs = []

    for tf in TEST_FILES:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.run(
            [sys.executable, os.path.join(tmpdir, tf)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=tmpdir, env=env, timeout=300)
        out = (p.stdout or "") + (p.stderr or "")
        outs.append("--- %s (rc=%d) ---\n%s" % (tf, p.returncode, out))
        rcs.append(p.returncode)

        # 「真的执行了」的判据：输出里出现 case 级结果行
        if re.search(r"\[(PASS|FAIL)\]", out):
            any_executed = True

    return rcs, "\n".join(outs), any_executed


def copy_proto(tmpdir):
    for f in PROTO_FILES + TEST_FILES + MODULE_FILES:
        src = os.path.join(HERE, f)
        shutil.copy2(src, os.path.join(tmpdir, f))
    # 测试依赖 reports 目录
    os.makedirs(os.path.join(tmpdir, "reports"), exist_ok=True)
    # test_p1_p5.py 依赖 synthetic/ 数据夹具；缺了会让基线不绿，
    # 那时变异结果没有意义。必须一并复制。
    syn_src = os.path.join(HERE, "synthetic")
    syn_dst = os.path.join(tmpdir, "synthetic")
    if os.path.isdir(syn_src):
        shutil.copytree(syn_src, syn_dst, dirs_exist_ok=True)
        return True
    return False


def apply_mutation(tmpdir, target, old, new):
    """应用一处或一组变异。

    组合变异写法（用于「多层防御必须同时拆掉才打得穿」的场景）：
        old = "锚A\n---\n锚B", new = "替换A\n---\n替换B"
    ⇒ 各锚必须在文件里恰好出现 1 次；任一不满足即 INVALID。
    ⚠ 注意（Mion 回复7 §四）：组合变异可以进 gate，
      但【每一层的单独证据必须另存在台账里】（layer_evidence.json）。
      组合 CAUGHT 只证明「整体有防御」，不证明「每层都必需」。
    """
    mult = (old.count("\n---\n") > 0) or (new.count("\n---\n") > 0)
    if mult:
        olds = old.split("\n---\n")
        news = new.split("\n---\n")
        if len(olds) != len(news):
            return False, "组合变异段数不齐：%d 锚 vs %d 替换" % (
                len(olds), len(news))
    else:
        olds, news = [old], [new]

    path = os.path.join(tmpdir, target)
    src = open(path, encoding="utf-8").read()

    # 先全部检查，任一不满足就不写（避免半应用）
    for i, o in enumerate(olds):
        n = src.count(o)
        if n != 1:
            return False, "第 %d 段锚点出现 %d 次（应为 1）" % (i + 1, n)

    for o, nw in zip(olds, news):
        src = src.replace(o, nw, 1)

    open(path, "w", encoding="utf-8", newline="\n").write(src)
    return True, "ok（%d 段）" % len(olds) if mult else "ok"


# ---------------------------------------------------------------- E1/E2/E3
#
# Mion 回复7：
#   E1 「无效变异」必须由【直接观测到行为未变】证成，不得由【目标测试未报】推断。
#   E2 无法独立观测 ⇒ UNRESOLVED，不得判无效。三态不许合并。
#   E3 「无效变异」结论必须附【被哪一层拦住】。

#: 探针：不跑目标测试，只调一次 revise() 并回报【外部状态】。
#: A 型 = 塞 _via_correct；B 型 = 只改来源不塞。
_PROBE_SRC = r'''# -*- coding: utf-8 -*-
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
                "msg": str(e)[:140],
                "basis_after": s.get("r1")["participation_basis"],
                "rev_after": s.get("r1")["revision"]}
    g = s.get("r1")
    return {"result": "SUCCEEDED", "exc": None, "msg": "",
            "basis_after": g["participation_basis"],
            "rev_after": g["revision"],
            "correction_of": any(r.get("relation_type") == "correction_of"
                                 for r in g["relation"])}

print("PROBE_JSON " + json.dumps({
    "A": run_case({"participation_basis": "third_person_report",
                   "_via_correct": True}),
    "B": run_case({"participation_basis": "third_person_report"}),
}, ensure_ascii=False))
'''


def _classify_block(msg, exc):
    """E3：把拦截归因到具体的层。归不到返回 None（→ 未查清）。"""
    if "不得包含保留键" in msg:
        return "L1_KEY_REJECT"
    if "不允许变更字段" in msg and "_via_correct" in msg:
        return "L2_WHITELIST"
    if "不允许直接改来源字段" in msg:
        return "L3_SOURCE_GUARD"
    if exc == "TypeError":
        return "ACCIDENT(TypeError)（非设计护栏）"
    return None


def probe_mutation_effect(target, old, new):
    """直接观测：应用该变异后，外部状态到底变不变？

    不参考任何目标测试的红绿（E1）。
    返回 None 表示无法独立观测（E2 ⇒ UNRESOLVED）。
    """
    if target != "afcore.py":
        return None      # 只对 afcore 的攻击面有探针
    td = tempfile.mkdtemp()
    try:
        shutil.copy2(os.path.join(HERE, "afcore.py"),
                     os.path.join(td, "afcore.py"))
        ok, _ = apply_mutation(td, target, old, new)
        if not ok:
            return None
        with open(os.path.join(td, "probe_mut.py"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(_PROBE_SRC)
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(
            [sys.executable, os.path.join(td, "probe_mut.py")],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=td, env=env, timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
        data = None
        for line in out.splitlines():
            if line.startswith("PROBE_JSON "):
                data = json.loads(line[len("PROBE_JSON "):])
                break
        if data is None:
            return None

        # 状态是否改变：任一攻击使 basis 从 first_person 变成别的
        changed = any(c.get("result") == "SUCCEEDED"
                      and c.get("basis_after") != "first_person_report"
                      for c in data.values())
        # 哪一层拦住（取第一个 BLOCKED 的归因）
        blocked_by = None
        for key in ("A", "B"):
            c = data[key]
            if c.get("result") == "BLOCKED":
                blocked_by = _classify_block(c.get("msg", ""), c.get("exc"))
                if blocked_by:
                    break
        return {"state_changed": changed, "blocked_by": blocked_by,
                "raw": data}
    except Exception:
        return None
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    print("=" * 78)
    print("变异验证 · 恢复资格门禁测试是否真的会亮红灯")
    print("=" * 78)
    print()

    # ---- 基线：未变异时必须全绿
    with tempfile.TemporaryDirectory() as td:
        copy_proto(td)
        rcs, out, executed = run_tests(td)
        baseline_ok = all(rc == 0 for rc in rcs)
        print("[基线] rc=%s  executed=%s  → %s"
              % (rcs, executed, "全绿" if baseline_ok else "非全绿"))
        if not baseline_ok:
            print(out[-3000:])
            print("!! 基线不绿，变异结果无意义。先修基线。")
            return 1
    print()

    rows = []
    for mid, desc, target, old, new in MUTATIONS:
        with tempfile.TemporaryDirectory() as td:
            copy_proto(td)
            ok, note = apply_mutation(td, target, old, new)
            if not ok:
                rows.append((mid, desc, "INVALID", note))
                print("  [INVALID] %-4s %s — %s" % (mid, desc, note))
                continue

            try:
                rcs, out, executed = run_tests(td)
            except subprocess.TimeoutExpired:
                rows.append((mid, desc, "TIMEOUT", "测试超时"))
                print("  [TIMEOUT] %-4s %s" % (mid, desc))
                continue

            if not executed:
                status = "NOT_EXECUTED"
                evid = "没有任何 case 级结果行（测试没跑到）"
            elif any(rc != 0 for rc in rcs):
                status = "CAUGHT"
                fails = re.findall(r"\[FAIL\]\s+(\S+)\s+([^\n]*)", out)
                if fails:
                    evid = "失败用例：%s" % (
                        "; ".join("%s %s" % (a, b.strip()[:32])
                                  for a, b in fails[:3]),)
                elif re.search(r"ERR ", out):
                    evid = "测试崩溃（也算被抓住）"
                else:
                    evid = "rc=%s 非零" % (rcs,)
            else:
                status = "MISSED"
                evid = "全部通过 —— 该变异没被任何测试拦住"

            # ---- Mion 回复7 E2/E3：MISSED 必须再判一次
            #
            # E2：若【无法独立观测】被变异点的实际结果，只能记 UNRESOLVED。
            # E3：若判为「无效变异」，必须说得出【被哪一层拦住】。
            #
            # 做法：MISSED 之后，用 layer_evidence 的【直接观测探针】
            # 独立打一次同一个改动，看外部状态是否真的变了。
            #   - 状态变了 + 测试没红  → 真 MISSED（测试漏洞，必须修测试）
            #   - 状态没变 + 说得出谁拦 → UNRESOLVED（E3 满足；不是测试失分）
            #   - 状态没变 + 说不出谁拦 → UNRESOLVED（未查清，仍不判无效）
            if status == "MISSED":
                probe = probe_mutation_effect(target, old, new)
                if probe is None:
                    evid += "；E2：无法独立观测 ⇒ UNRESOLVED（不得判为无效）"
                    status = "UNRESOLVED"
                elif probe.get("state_changed"):
                    evid += "；直接观测：外部状态【已变】⇒ 真 MISSED，测试有漏洞"
                else:
                    who = probe.get("blocked_by") or "未查清"
                    evid += ("；直接观测：外部状态【未变】，被 %s 拦住"
                             " ⇒ 该变异对此攻击无效（E3）" % who)
                    status = "UNRESOLVED"

            rows.append((mid, desc, status, evid))
            print("  [%-12s] %-4s %s" % (status, mid, desc))
            if status != "CAUGHT":
                print("              %s" % evid)

    print()
    print("=" * 78)
    counts = {}
    for _, _, st, _ in rows:
        counts[st] = counts.get(st, 0) + 1
    for st in ("CAUGHT", "UNRESOLVED", "MISSED", "INVALID",
               "NOT_EXECUTED", "TIMEOUT"):
        if st in counts:
            print("  %-13s %d" % (st, counts[st]))
    print("=" * 78)

    # Mion 回复7 E2：三态不许合并。
    #   CAUGHT      测试守住了
    #   UNRESOLVED  该变异改变了实现，但【直接观测到外部状态未变】——
    #               即这条变异并不真的打穿机制；或无法独立观测。
    #               ⇒ 不计为测试失分，但必须留在台账里（不许合并进 CAUGHT 报喜）
    #   MISSED      外部状态【已变】而测试没红 ⇒ 真漏洞，必须修测试
    bad = counts.get("MISSED", 0) + counts.get("INVALID", 0) + \
        counts.get("NOT_EXECUTED", 0) + counts.get("TIMEOUT", 0)
    verdict = "PASS" if bad == 0 else "FAIL"
    print("  判定：%s（共 %d 个变异）" % (verdict, len(rows)))
    if counts.get("UNRESOLVED", 0):
        print("  ⚠ UNRESOLVED %d 条：这些变异【没有真正打穿机制】，"
              "不是测试失分，" % counts["UNRESOLVED"])
        print("    但也不计入 CAUGHT —— 三态不合并（Mion 回复7 E2）。")
        print("    每一层的单独证据见 reports/layer_evidence.json。")

    out_dir = os.path.join(HERE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "mutations_gate_result.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump({"verdict": verdict, "counts": counts,
                   "rows": [{"id": a, "desc": b, "status": c, "evidence": d}
                            for a, b, c, d in rows]},
                  f, ensure_ascii=False, indent=2)
    print("  结果已写入 reports/mutations_gate_result.json")

    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
