# -*- coding: utf-8 -*-
"""注释判定表 ↔ 实现 一致性检查。

Mion 2026-11-24：
  「这张表是下一个人读代码的第一入口。表错了，他就不会去读实现。」

⇒ 所以表必须被机器守着，不能靠人记得同步。
"""
import sys, os, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

#: ⚠ 2026-11-27 修正（凌翼裁定三 · 可移植性）：
#:   原实现硬编码 ROOT = r"d:\qcr\ouroboros-afterglow"
#:   ⇒ 在作者本机 rc=0，在干净克隆上 FileNotFoundError（睫与知微均已实测）。
#:   ⇒ 现按【本文件位置】反推仓库根：本文件在 <root>/afterglow_a/prototype/ 下，
#:     上溯两级即 root。不依赖任何绝对路径，也不依赖 cwd。
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
CORE = os.path.join(_THIS_DIR, "afcore.py")

if not os.path.exists(CORE):
    print("[FAIL] afcore.py 不在 %s —— 本文件位置假设被破坏" % _THIS_DIR)
    sys.exit(1)
src = open(CORE, encoding="utf-8").read()
lines = src.splitlines()

# ---- 1. 从注释表里解析出期望值
#   asserted \ observed | system_dispatch | model_generation | human_input
#   first_person_report |  【冲突】        |    【冲突】      |  none
EXPECT = {}
COL_OBS = ["system_dispatch", "model_generation", "human_input"]

for i, l in enumerate(lines):
    m = re.match(r"\s*#\s*(first_person_report|third_person_report|record_only)"
                 r"\s*\|(.+)$", l)
    if not m:
        continue
    asserted = m.group(1)
    cells = [c.strip() for c in m.group(2).split("|")]
    if len(cells) < 3:
        continue
    vals = []
    for c in cells[:3]:
        vals.append("asserted_contradicts_observed" if "冲突" in c else "none")
    EXPECT[asserted] = dict(zip(COL_OBS, vals))

print("=" * 78)
print("一 · 从注释表解析出的期望矩阵")
print("=" * 78)
if not EXPECT:
    print("  !! 解析不到表，可能格式改了")
    sys.exit(1)
for a, row in EXPECT.items():
    print("  %-20s %s" % (a, row))

# ---- 2. 实测：逐格跑一遍
print()
print("=" * 78)
print("二 · 实测矩阵")
print("=" * 78)
sys.path.insert(0, _THIS_DIR)
import afcore

PIN = "2026-11-24T00:00:00Z"
actual = {}
for asserted in ("first_person_report", "third_person_report", "record_only"):
    actual[asserted] = {}
    for obs in COL_OBS:
        s = afcore.RecoveryStore()
        # source_kind 必须与 asserted 相容才能构造
        kind = {"first_person_report": "user_utterance",
                "third_person_report": "third_party",
                "record_only": "third_party"}[asserted]
        s.insert(afcore.Record(
            record_id="r", content="c", source_kind=kind,
            source_ref="u/r", participant_id=None,
            participation_basis=asserted, basis_ref="u/r",
            commitment_state="not_a_commitment", revision=1, prev_digest=None,
            changed_at=PIN, change_authority="f"))
        s.record_observed("r", obs)
        actual[asserted][obs] = s.get("r")["basis_conflict"]

for a, row in actual.items():
    print("  %-20s %s" % (a, row))

# ---- 3. 比对
print()
print("=" * 78)
print("三 · 比对")
print("=" * 78)
bad = []
for a in EXPECT:
    if a not in actual:
        bad.append((a, "实测缺失"))
        continue
    for obs in COL_OBS:
        e = EXPECT[a].get(obs)
        g = actual[a].get(obs)
        if e != g:
            bad.append((a, obs, "表=%s 实测=%s" % (e, g)))
            print("  ✗ %-20s × %-18s 表=%s  实测=%s" % (a, obs, e, g))
if not bad:
    print("  ✓ 全部 9 格一致")

# ---- 4. 额外：旧理由句必须已删
print()
print("=" * 78)
print("四 · 旧理由句是否已删除")
print("=" * 78)
stale_hits = []
for idx, l in enumerate(lines):
    if "没有第三方来源可言" not in l:
        continue
    # 看【上下文三行】：续行情形下否定词可能在上一行
    ctx = "\n".join(lines[max(0, idx - 2):idx + 2])
    if any(k in ctx for k in ("不要写成", "原文只指定", "旧理由", "原写",
                              "Mion 要求换成", "⚠", "后者要求先定义")):
        continue
    stale_hits.append(l)
print("  仍作为【理由】存在的行数：%d" % len(stale_hits))
for l in stale_hits[:3]:
    print("    %s" % l.strip()[:90])

ok = (not bad) and (not stale_hits)
print()
print("=" * 78)
print("判定：%s" % ("PASS" if ok else "FAIL"))
print("=" * 78)
sys.exit(0 if ok else 1)
