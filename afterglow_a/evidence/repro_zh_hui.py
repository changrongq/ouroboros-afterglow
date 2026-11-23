# -*- coding: utf-8 -*-
"""
固化知微 2026-11-23 独立审查（r2/24）的复核结果。

本脚本有两个作用：
  1) 记录【修前】四项指控均已复现（历史事实，写入 before_fix）
  2) 检测【修后】每一项是否已被拒绝或隔离（FIXED / STILL_OPEN）

⇒ 若某天有人把修复改回去了，重跑本脚本，FIXED 会变回 STILL_OPEN。
"""
import sys, os, json, tempfile, shutil, importlib
sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"d:\qcr\ouroboros-afterglow"
PROTO = os.path.join(ROOT, "afterglow_a", "prototype")
SRC = r"d:\qcr\EntropyDrivenAI\selective_forgetting"
OUT = os.path.join(ROOT, "afterglow_a", "evidence", "zh_hui_counterexamples.json")

sys.path.insert(0, PROTO)
from afcore import Record, RecoveryStore, SchemaError

SEED = os.path.join(PROTO, "synthetic", "records_seed.json")
results = []


def rec(ident, desc, observed, status, before, after):
    results.append({"id": ident, "desc": desc, "observed": observed,
                    "status": status, "before_fix": before, "after_fix": after})
    print("  %-8s %-38s %s" % (ident, desc[:38], status))


print("=" * 74)
print("A. 原型四项缺口：修后状态")
print("=" * 74)

# ---------------- ZA-01 ----------------
st = RecoveryStore(); st.load_seed(SEED)
r = Record(record_id="alias-1", content="原始内容",
           source_kind="user_utterance", source_ref="synth/turn/1",
           participant_id="p1", participation_basis="first_person_report",
           basis_ref="synth/turn/1", commitment_state="not_a_commitment",
           revision=1, prev_digest=None,
           changed_at="2026-11-23T00:00:00Z", change_authority="t")
st.insert(r)
r.content = "MUTATED OUTSIDE REVISE"
after = st.get("alias-1")["content"]
hist = st.history("alias-1")[0]["content"]
okc, _ = st.verify_chain("alias-1")
fixed1 = (after == "原始内容" and hist == "原始内容" and okc)
rec("ZA-01", "调用者改对象是否影响库内状态",
    {"get": after, "history": hist, "chain_ok": okc},
    "FIXED" if fixed1 else "STILL_OPEN",
    "get() 返回被改内容，history 仍是原值，链仍通过",
    "insert/revise 深拷贝入库，调用者的改动被隔断")

# ---------------- ZA-02 ----------------
st2 = RecoveryStore(); st2.load_seed(SEED)
try:
    st2.revise("syn-0001", {"record_id": "renamed-id"})
    rejected2, detail2 = False, "仍未拒绝"
except SchemaError as e:
    rejected2, detail2 = ("record_id" in str(e)), str(e)[:56]
rec("ZA-02", "revise 是否允许变更 record_id",
    {"rejected": rejected2, "detail": detail2},
    "FIXED" if rejected2 else "STILL_OPEN",
    "身份被改 → get('syn-0001')['record_id']='renamed-id'，链仍通过",
    "revise 加字段白名单，record_id 不在其中")

# ---------------- ZA-03 ----------------
t2 = Record(record_id="x", content="c", source_kind="user_utterance",
            source_ref=None, participant_id="p",
            participation_basis="first_person_report", basis_ref=None,
            commitment_state="not_a_commitment", revision=1, prev_digest=None,
            changed_at="2026-11-23T00:00:00Z", change_authority="t")
empty_ref_rejected = any("source_ref" in p for p in t2.validate())

st3 = RecoveryStore(); st3.load_seed(SEED)
try:
    st3.correct("syn-0004", "新内容", correcting_record_id="DOES-NOT-EXIST", reason="t")
    dangling_rejected = False
except SchemaError:
    dangling_rejected = True

st4 = RecoveryStore(); st4.load_seed(SEED)
try:
    st4.correct("syn-0004", "新内容", correcting_record_id="syn-0005", reason="t")
    nosrc_rejected = False
except SchemaError:
    nosrc_rejected = True

fixed3 = empty_ref_rejected and dangling_rejected and nosrc_rejected
rec("ZA-03", "空引用 / 悬空依据 / 无来源依据",
    {"empty_ref_rejected": empty_ref_rejected,
     "dangling_basis_rejected": dangling_rejected,
     "basis_without_source_rejected": nosrc_rejected},
    "FIXED" if fixed3 else "STILL_OPEN",
    "三者均通过：空 ref 合法；纠正可指向不存在记录；可沿用旧来源",
    "三者均被拒：validate 拦空 ref；correct 要求依据存在且有 source_ref")

# ---------------- ZA-04 ----------------
tmp = tempfile.mkdtemp(prefix="za04_")
try:
    for f in os.listdir(PROTO):
        p = os.path.join(PROTO, f)
        if os.path.isfile(p) and f.endswith(".py"):
            shutil.copy2(p, tmp)
    shutil.copytree(os.path.join(PROTO, "synthetic"), os.path.join(tmp, "synthetic"))
    tgt = os.path.join(tmp, "afcore.py")
    s = open(tgt, encoding="utf-8", newline="").read()
    s = s.replace("class SchemaError(Exception):", "class SchemaError(Exception)", 1)
    open(tgt, "w", encoding="utf-8", newline="").write(s)

    sys.path.insert(0, tmp)
    import test_mutations_v4 as drv
    importlib.reload(drv)
    rc2, pa2, to2, out2, execd, saw, crash = drv.run_in(tmp)
    new_says = "NOT_EXECUTED" if not execd else "CAUGHT"
    old_logic = "CAUGHT" if ((rc2 != 0) or (pa2 != to2)) else "-"
    rec("ZA-04", "语法错误变异是否被算 CAUGHT",
        {"exit": rc2, "saw_summary": saw, "hard_crash": crash,
         "executed": execd, "old_logic": old_logic, "new_logic": new_says},
        "FIXED" if new_says == "NOT_EXECUTED" else "STILL_OPEN",
        "caught=(rc!=0 or p!=t)：rc=1 即算 CAUGHT，但 0 条测试执行",
        "run_in 增加 executed 判定；NOT_EXECUTED 计入失败，整体 FAIL")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("=" * 74)
print("B. B §4.3 原结论（已被知微推翻，我的读法错误）")
print("=" * 74)

amend = open(os.path.join(SRC, "_dhe_12f_v1_1_amend.py"), encoding="utf-8").read()
derive = open(os.path.join(SRC, "_dhe_12f_s2_s6_derive_replay.py"), encoding="utf-8").read()

check = {
    "amend_声明不加载模型且不算endpoint":
        ("不加载模型" in amend and "不算任何 endpoint" in amend),
    "amend_有_patch_定义":
        "H[0, t_dec, :] += sign * LAMBDA * d" in amend,
    "derive_delta_由激活差分算出":
        "(zA / 24.0) - (zB / 24.0)" in derive,
    "derive_归一化为方向":
        "d64 = mean64 / n64" in derive,
    "derive_保存方向_npy":
        "_dhe_12f_raw_dm.npy" in derive,
}
for k, v in check.items():
    print("  %-44s %s" % (k, "OK" if v else "XX"))

allok = all(check.values())
rec("ZW-3.1", "d 的来源：激活差分方向，非 endpoint 之差",
    check,
    "MY_READING_WAS_WRONG" if allok else "CHECK_INCOMPLETE",
    "Coder 原读：d = U(p_A) − U(p_B)，固定规则 ⇒ 与经历无关",
    "实际：d 由 (zA/24 − zB/24) 归一化得到（4096 维方向向量）；"
    "U 之差是注入后的标量测量指标，在 d 的下游。结论已撤回。")

print()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"generated_by": "afterglow_a/evidence/repro_zh_hui.py",
               "purpose": "固化知微 2026-11-23 审查：修前复现 + 修后状态",
               "results": results}, f, ensure_ascii=False, indent=2)
n_fixed = sum(1 for r in results if r["status"] == "FIXED")
print("结果已写:", OUT)
print("共 %d 项；FIXED %d 项" % (len(results), n_fixed))
sys.exit(0 if (n_fixed == 4 and allok) else 1)
