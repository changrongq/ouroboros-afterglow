# -*- coding: utf-8 -*-
"""A16 L1 实际执行验证 runner

从 B_24 提取真实字节 → 用 l1_parser.py 解析 → 与 expected.py 比对 → 输出结果。

用法：
  python run_a16.py            # 跑全部
  python run_a16.py --json     # 输出 JSON

边界（凌翼 D-C）：
  本报告【只证明 L1 结构解析】。
  不代表 L2 可信摘要绑定、L3 权威消费、S1 隔离通过。
"""
import sys, re, os, json, hashlib
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import l1_parser as P
import expected as E

REPO = r"d:\qcr\ouroboros-afterglow"
B24 = os.path.join(REPO, "reports", "review_history",
                   "阶段B_24_v2规范向量与负向实例_Coder_20261110.md")

HEXRE = re.compile(r"([0-9A-F]{100,})")


def load_b24():
    """从 B_24 按【出现顺序】取 17 条去重字节。"""
    t = open(B24, "rb").read().decode("utf-8")
    hs = []
    for h in HEXRE.findall(t):
        if h not in hs:
            hs.append(h)
    return hs


def classify(h):
    raw = bytes.fromhex(h)
    fv = int.from_bytes(raw[8:10], "big")
    ot = raw[10]
    L = len(raw)
    tl = int.from_bytes(raw[-4:], "big")
    # 用结构特征定位每个编号，不依赖文档行号
    if raw[:7] == b"AFGLREX":
        return "NEG-09"
    if raw[11] != 0x00:
        return "NEG-10"
    if tl != L:
        return "NEG-08"
    if fv == 0x0003:
        return "NEG-05"
    # N5 保留 TAG
    if ot == 0x86:
        body = raw[14:-4]
        tags = []
        i = 0
        while i < len(body):
            tags.append(body[i])
            i += 3 + int.from_bytes(body[i+1:i+3], "big")
        return "NEG-07" if 0x8B in tags else "TV2-N5"
    if fv == 0x0001:
        return "NEG-01" if ot == 0x88 else "NEG-06"
    if ot == 0x80:
        return "NEG-02"
    if ot == 0x8C:
        return "NEG-03"
    if ot == 0x04:
        return "NEG-04"
    # v2 白名单：按长度与字段数区分
    m = {
        (0x88, 62): "TV2-01",
        (0x89, 168): "TV2-02",
        (0x8B, 157): None,      # 05 或 07，用 D5 计数区分
        (0x8A, 266): None,      # 06 或 OTHER，用 C7 kind 区分
        (0x86, 225): "TV2-N5",
    }
    if (ot, L) in m and m[(ot, L)]:
        return m[(ot, L)]
    if ot == 0x8B and L == 157:
        body = raw[14:-4]
        i = 0
        d5 = None
        while i < len(body):
            tg = body[i]
            ln = int.from_bytes(body[i+1:i+3], "big")
            if tg == 0xD5:
                d5 = int.from_bytes(body[i+3:i+3+ln], "big")
            i += 3 + ln
        return "TV2-05" if d5 == 0 else "TV2-07"
    if ot == 0x8A and L == 266:
        body = raw[14:-4]
        i = 0
        kind = None
        while i < len(body):
            tg = body[i]
            ln = int.from_bytes(body[i+1:i+3], "big")
            if tg == 0xC7:
                kind = body[i+3]
            i += 3 + ln
        return "TV2-06" if kind == 1 else "TV2-OTHER"
    return None


def build_constructed():
    """人工构造的边界负例。"""
    MAGIC = b"AFGLREF\x00"
    def ef(t, v): return bytes([t]) + len(v).to_bytes(2, "big") + v
    def mk(ot, fv, fields, total=None, magic=MAGIC):
        body = b"".join(ef(t, v) for t, v in fields)
        head = magic + fv.to_bytes(2, "big") + bytes([ot]) + b"\x00" + len(fields).to_bytes(2, "big")
        tl = len(head) + len(body) + 4 if total is None else total
        return head + body + tl.to_bytes(4, "big")

    DOM = b"d0"; GEN = (1).to_bytes(4, "big"); ROOT = b"\x44"*32; Z = b"\x00"*32
    ehwm = [(0xD1, DOM), (0xD2, GEN), (0xD3, (0).to_bytes(8, "big")),
            (0xD4, Z), (0xD5, (0).to_bytes(8, "big")), (0xD6, ROOT), (0xD7, Z)]

    out = {}
    # 总长 17（真正 17 字节：MAGIC8+VER2+TYPE1+RES1+FC2+TL4 = 18，故砍 1 字节）
    full17 = MAGIC + b"\x00\x02" + b"\x8B" + b"\x00" + b"\x00\x07" + b"\x00\x00\x00\x12"
    out["C-TRUNC-SHORT"] = full17[:-1]        # 17 字节
    # 字段 VALUE 截断：声明 LEN 大于实际
    good = mk(0x8B, 0x0002, ehwm)
    out["C-TRUNC-FIELD"] = good[:-8]          # 砍掉末尾，TOTAL_LEN 与字段都残
    # 尾随字节：TOTAL_LEN 声明值小于实际长度（字节数不变，只改声明）
    t = mk(0x8B, 0x0002, ehwm)
    out["C-TRAILING"] = t[:-4] + (len(t) - 2).to_bytes(4, "big")
    # 空帧：FIELD_COUNT=0
    out["C-EMPTY-FIELDS"] = MAGIC + b"\x00\x02" + b"\x8B" + b"\x00" + b"\x00\x00" + b"\x00\x00\x00\x12"
    # 同时违反字段数 + 保留 TAG：N5 用 0x8B 且共 12 字段
    p02 = bytes.fromhex("f6f23772abff685cbc66a963bc4649eec64e26c2942aa7e483326071208725c8")
    n5bad = [(0x81, DOM), (0x82, GEN), (0x83, (0).to_bytes(8, "big")),
             (0x84, (4).to_bytes(8, "big")), (0x85, b"\x11"*32),
             (0x86, (1).to_bytes(8, "big")), (0x87, p02),
             (0x88, (100).to_bytes(8, "big")), (0x89, (104).to_bytes(8, "big")),
             (0x8B, Z), (0x8A, ROOT), (0x8C, Z)]
    out["C-DUP-RULE"] = mk(0x86, 0x0002, n5bad)

    # ---- 2026-11-10 补：变异测试发现的盲区 ----
    # 声明 FIELD_COUNT=5，实际写 7 个字段（声明数 ≠ 实读数）
    body7 = b"".join(ef(t, v) for t, v in ehwm)
    head = MAGIC + b"\x00\x02" + b"\x8B" + b"\x00" + (5).to_bytes(2, "big")
    tl = len(head) + len(body7) + 4
    out["C-FCNT-MISMATCH"] = head + body7 + tl.to_bytes(4, "big")

    # MAGIC 第 1 字节错
    out["C-MAGIC-ONLY"] = mk(0x8B, 0x0002, ehwm, magic=b"XFGLREF\x00")

    # v2 + 类型 0x01（v1 引用类型，v2 未登记）
    # 用 7 个字段以避开字段数干扰，专门测类型白名单
    t01 = [(0x01, b"e1"), (0x02, b"a1"), (0x03, b"\x00"*45),
           (0x04, b"s1"), (0x05, b"\x01"), (0x06, b""), (0x07, b"")]
    out["C-V2-TYPE01"] = mk(0x01, 0x0002, t01)

    return out


def run():
    vectors = {}
    for h in load_b24():
        name = classify(h)
        if name:
            vectors[name] = h

    constructed = build_constructed()

    # ---- 凌翼 D-C 要求：补齐 0x81-0x85、0x87 六类 v2 正例 ----
    import vec6
    for name, raw in vec6.NEW.items():
        constructed[name] = raw

    # ---- 复用型用例：不改字节，只改调用入口 ----
    # NEG-11 / X2 / X2b 按凌翼 D-A 残留2 的要求，
    # 用【已存在的字节】验证「版本不匹配」先于「类型白名单」。
    if "TV2-05" in vectors:
        constructed["NEG-11"] = bytes.fromhex(vectors["TV2-05"])   # v2 头，直调 v1
        constructed["X2b"] = bytes.fromhex(vectors["TV2-05"])      # v2 头 + 高位类型，直调 v2
    if "NEG-01" in vectors:
        constructed["X2"] = bytes.fromhex(vectors["NEG-01"])       # v1 头，直调 v2

    results = []
    for (vid, desc, entry, exp, basis) in E.EXPECTED:
        h = vectors.get(vid)
        if not h:
            results.append(dict(id=vid, desc=desc, entry=entry,
                                expected=exp, actual=("SKIP", "no bytes"),
                                basis=basis, verdict="SKIP"))
            continue
        raw = bytes.fromhex(h)
        results.append(_judge(vid, desc, entry, exp, raw, basis))

    for (vid, desc, entry, exp, basis) in E.CONSTRUCTED + [
        ("NEG-11", "v2 头，直调 v1 专用入口", "v1",
         ("REJECT", "R-V2-02b"), "凌翼 D-A 残留2：版本不匹配"),
        ("X2", "v1 头，直调 v2 专用入口", "v2",
         ("REJECT", "R-V2-02b"), "凌翼：应先以版本不匹配拒绝，不是 02d"),
        ("X2b", "v2 头 + 白名单类型，直调 v2 入口（应接受）", "v2",
         ("ACCEPT",), "版本对+类型对 => v2 入口正确地接受；反证 X2 的拒绝来自版本而非类型"),
        # ---- 六类补全（凌翼 D-C 要求）----
        ("TV2-81", "0x81 IDENTITY_REGISTRATION", "dispatcher",
         ("ACCEPT",), "B_22 §3.6 七字段"),
        ("TV2-82", "0x82 EPOCH_ASSIGNMENT", "dispatcher",
         ("ACCEPT",), "B_22 §3.7 七字段"),
        ("TV2-83", "0x83 GRANT_RECORD", "dispatcher",
         ("ACCEPT",), "B_22 §3.8 六字段"),
        ("TV2-84", "0x84 PREPARE_RECORD", "dispatcher",
         ("ACCEPT",), "B_22 §3.9 七字段"),
        ("TV2-85", "0x85 CLOSURE_RECORD", "dispatcher",
         ("ACCEPT",), "B_22 §3.10 七字段"),
        ("TV2-87", "0x87 REVOCATION_RECORD", "dispatcher",
         ("ACCEPT",), "B_22 §3.11 六字段"),
    ]:
        raw = constructed.get(vid)
        if raw is None:
            results.append(dict(id=vid, desc=desc, entry=entry,
                                expected=exp, actual=("SKIP", "not built"),
                                basis=basis, verdict="SKIP"))
            continue
        results.append(_judge(vid, desc, entry, exp, raw, basis))

    return results


def _judge(vid, desc, entry, exp, raw, basis):
    try:
        r = P.parse(raw, entry=entry)
        act = ("ACCEPT",)
        extra = {"digest": P.protocol_digest(raw),
                 "type": r["OBJECT_TYPE"], "ver": r["FORMAT_VER"]}
    except P.Reject as e:
        act = ("REJECT", e.code)
        extra = {"detail": e.detail}
    ok = (act == exp)
    return dict(id=vid, desc=desc, entry=entry, expected=exp, actual=act,
                basis=basis, verdict="PASS" if ok else "FAIL", **extra)


def main():
    res = run()
    if "--json" in sys.argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        w = 14
        print(f"{'编号':<16}{'入口':<11}{'期望':<22}{'实际':<22}{'判定'}")
        print("-" * 88)
        for r in res:
            e = r["expected"][0] if r["expected"][0] == "ACCEPT" else f"REJECT {r['expected'][1]}"
            a = r["actual"][0] if r["actual"][0] == "ACCEPT" else f"REJECT {r['actual'][1]}"
            print(f"{r['id']:<16}{r['entry']:<11}{e:<22}{a:<22}{r['verdict']}")
        n = len(res)
        p = sum(1 for r in res if r["verdict"] == "PASS")
        f = sum(1 for r in res if r["verdict"] == "FAIL")
        s = sum(1 for r in res if r["verdict"] == "SKIP")
        print("-" * 88)
        print(f"合计 {n}  通过 {p}  失败 {f}  跳过 {s}")
    return 0 if all(r["verdict"] != "FAIL" for r in res) else 1


if __name__ == "__main__":
    sys.exit(main())
