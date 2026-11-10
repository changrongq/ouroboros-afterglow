# -*- coding: utf-8 -*-
"""规范一致性检查：把 l1_parser.py 的硬编码与 B_22 规范表格程序化比对。

存在理由：
  B_26 报告承认了一个"已知上限"——
  解析器常量与预期表都是我【手抄】的，若抄错成同一个错，测试看不出。

  本脚本把这道手抄环节【替换成程序解析】：
  从 B_22 的 markdown 表格里解析出字段数与 TAG 序列，
  再与 l1_parser.py 的硬编码逐类比对。
  ⇒ 若不一致，说明硬编码偏离规范；若一致，手抄风险被消除。

用法：
  python check_spec.py
退出码：0 = 全部一致；1 = 存在不一致
"""
import sys, re, os
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import l1_parser as P

# 规范来源：B_22（字段表权威）+ §2（v1 三种引用类型）
SPEC_FILES = [
    ("阶段B_22_统一候选规范_编码卷_Coder_20261109.md", "B_22 §3"),
    ("原型实施授权申请_§2_P1引用完整性编码_草案_20261104.md", "§2 §3"),
]

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RH = os.path.join(REPO, "reports", "review_history")


def parse_b22(t):
    """从 B_22 的 ### 3.x 节解析 (类型 -> [TAG...])。"""
    out = {}
    for m in re.finditer(r"### 3\.\d+[a-c]? `(0x[0-9A-F]{2})`[^\n]*?\n(.*?)(?=\n### |\n---|\Z)",
                         t, re.S):
        ot = int(m.group(1), 16)
        tags = [int(x, 16) for x in
                re.findall(r"^\|\s*\d+\s*\|\s*`(0x[0-9A-F]{2})`", m.group(2), re.M)]
        if tags:
            out[ot] = tags
    return out


def parse_sec2(t):
    """从 §2 的 3.1/3.2/3.3 表解析 v1 三种类型的 TAG。
    表头是 | 顺序 | 字段 | TAG | 类型 | 约束 |，TAG 在第 3 列。"""
    out = {}
    for name, ot in [("ATTEMPT_REF", 0x01), ("RECEIPT_REF", 0x02), ("KEY_TRIPLE", 0x03)]:
        m = re.search(r"## 3\.\d " + name + r"[^\n]*\n(.*?)(?=\n## |\Z)", t, re.S)
        if not m:
            continue
        tags = [int(x, 16) for x in
                re.findall(r"^\|\s*\d+\s*\|\s*`[a-z_]+`\s*\|\s*`(0x[0-9A-F]{2})`",
                           m.group(1), re.M)]
        if tags:
            out[ot] = tags
    return out


def main():
    """分来源解析 → 每源独立断言 → 重叠源一致性 → 与实现比对。

    2026-11-10 修正（知微/睫 指出）：
      原实现 `spec.update(got)` 会静默覆盖，且不校验每份来源是否
      真的解析到预期数量。若 §2 文件无表格，它解析出 0 类，
      整体仍 PASS —— 那一步没有贡献任何校验。
      现改为：
        · 每个来源单独断言"必须解析出 N 类"（N 由来源登记）
        · 重叠类型必须【逐位相同】，不同即报冲突
        · 最后才与实现比对
    """
    # 各来源的期望覆盖数（登记在此，不符即失败）
    EXPECT = {
        "B_22": 14,   # §3.0a-3.11：11 类新类型 + 3 类引用类型
        "SEC2": 3,    # §2 §3.1-3.3：0x01 0x02 0x03
    }

    per_source = {}
    for fname, label in SPEC_FILES:
        fp = os.path.join(RH, fname)
        if not os.path.exists(fp):
            print(f"❌ 找不到规范文件: {fname}")
            return 1
        txt = open(fp, "rb").read().decode("utf-8")
        key = "B_22" if "B_22" in fname else "SEC2"
        got = parse_b22(txt) if key == "B_22" else parse_sec2(txt)
        print(f"  {label}: 解析到 {len(got)} 个类型"
              f"（登记期望 {EXPECT[key]}）")
        if len(got) != EXPECT[key]:
            print(f"  ❌ {label} 覆盖数不符：实得 {len(got)}，期望 {EXPECT[key]}")
            return 1
        per_source[key] = got

    # 重叠来源一致性
    print("\n=== 重叠来源一致性 ===")
    b22, sec2 = per_source.get("B_22", {}), per_source.get("SEC2", {})
    overlap = sorted(set(b22) & set(sec2))
    conflict = []
    for ot in overlap:
        if b22[ot] != sec2[ot]:
            conflict.append(ot)
            print(f"  0x{ot:02X}: B_22={[hex(x) for x in b22[ot]]} "
                  f"≠ §2={[hex(x) for x in sec2[ot]]}")
    print(f"  重叠类型 {len(overlap)} 个：{['0x%02X' % x for x in overlap]}")
    print(f"  冲突 {len(conflict)} 个：{'无' if not conflict else [hex(x) for x in conflict]}")
    if conflict:
        print("❌ 重叠来源不一致")
        return 1

    # 合并（此时重叠已确认一致）
    spec = {}
    for k, v in per_source.items():
        spec.update(v)

    print(f"\n{'类型':<8}{'规范 TAG 数':>12}{'实现 TAG 数':>12}"
          f"{'TAG 一致':>10}{'字段数一致':>12}")
    print("-" * 60)
    bad = []
    for ot in sorted(spec):
        st = spec[ot]
        it = P.TAGS.get(ot)
        ic = P.FIELD_COUNT.get(ot)
        ok_t = (it == st)
        ok_c = (ic == len(st))
        print(f"0x{ot:02X}    {len(st):>12}{len(it) if it else 0:>12}"
              f"{'✅' if ok_t else '❌':>10}{'✅' if ok_c else '❌':>12}")
        if not (ok_t and ok_c):
            bad.append((ot, st, it, len(st), ic))

    extra = sorted(set(P.TAGS) - set(spec))
    print(f"\n实现多出的类型: {[hex(x) for x in extra] or '无'}")
    print(f"规范解析出: {len(spec)} 个类型；实现: {len(P.TAGS)} 个")

    n5 = P.TAGS.get(0x86, [])
    print(f"\n保留 TAG 专项：N5(0x86) 白名单含 0x8B = {0x8B in n5}（须为 False）")

    if bad or extra or (0x8B in n5):
        print(f"\n❌ 存在 {len(bad)} 项不一致")
        for b in bad:
            print(f"   0x{b[0]:02X}: 规范 {[hex(x) for x in b[1]]} "
                  f"/ 实现 {[hex(x) for x in (b[2] or [])]}")
        return 1
    print("\n✅ 全部一致：实现硬编码未偏离规范表格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
