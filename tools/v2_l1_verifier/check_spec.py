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
    spec = {}
    for fname, label in SPEC_FILES:
        p = os.path.join(RH, fname)
        if not os.path.exists(p):
            print(f"❌ 找不到规范文件: {fname}")
            return 1
        t = open(p, "rb").read().decode("utf-8")
        got = parse_b22(t) if "B_22" in fname else parse_sec2(t)
        print(f"  {label}: 解析到 {len(got)} 个类型")
        spec.update(got)

    print(f"\n{'类型':<8}{'规范 TAG 数':>12}{'实现 TAG 数':>12}{'TAG 一致':>10}{'字段数一致':>12}")
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

    # 反向：实现里有但规范解析不到
    extra = sorted(set(P.TAGS) - set(spec))
    print(f"\n实现多出的类型: {[hex(x) for x in extra] or '无'}")
    print(f"规范解析出: {len(spec)} 个类型；实现: {len(P.TAGS)} 个")

    # 保留 TAG 专项
    n5 = P.TAGS.get(0x86, [])
    print(f"\n保留 TAG 专项：N5(0x86) 白名单含 0x8B = {0x8B in n5}（须为 False）")

    if bad or extra or (0x8B in n5):
        print(f"\n❌ 存在 {len(bad)} 项不一致")
        for b in bad:
            print(f"   0x{b[0]:02X}: 规范 {[hex(x) for x in b[1]]} / 实现 {[hex(x) for x in (b[2] or [])]}")
        return 1
    print("\n✅ 全部一致：实现硬编码未偏离规范表格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
