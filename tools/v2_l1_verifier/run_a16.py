# -*- coding: utf-8 -*-
"""A16 L1 实际执行验证 runner

用法：
  python run_a16.py                     # 用默认证据目录
  python run_a16.py --evidence <dir>    # 指定固定证据目录
  python run_a16.py --json

退出码（ZFP-01A 修正）：
  0 = 全部 PASS
  1 = 存在 FAIL
  2 = 存在 SKIP（必需输入缺失）——不得视为完成
  3 = 证据身份校验失败（ZFP-05）

边界（凌翼 D-C）：本工具只证明 L1 结构解析。
"""
import sys, re, os, json, hashlib, argparse
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import l1_parser as P
import expected as E

# ---- 固定证据身份（ZFP-05）----
B24_FILENAME = "阶段B_24_v2规范向量与负向实例_Coder_20261110.md"
B24_BLOB = "d4c7ce05093963787c54a5317cb116d54d7abc57"   # commit 362e0e4

SEARCH_DIRS = [
    os.path.join(HERE, "evidence"),
    os.path.join(HERE, "..", "..", "reports", "review_history"),
]
HEXRE = re.compile(r"([0-9A-F]{100,})")


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def find_evidence(cli_dir=None):
    cands = []
    if cli_dir:
        cands.append(os.path.join(cli_dir, B24_FILENAME))
    for d in SEARCH_DIRS:
        cands.append(os.path.abspath(os.path.join(d, B24_FILENAME)))
    for c in cands:
        if os.path.exists(c):
            return os.path.abspath(c), open(c, "rb").read()
    return None, None


def verify_evidence(raw):
    got = git_blob_sha1(raw)
    return (got == B24_BLOB), f"blob want={B24_BLOB[:12]} got={got[:12]}"


def load_b24(raw):
    hs = []
    for h in HEXRE.findall(raw.decode("utf-8")):
        if h not in hs:
            hs.append(h)
    return hs


def _walk(raw):
    body = raw[14:-4]; i = 0; out = []
    while i < len(body):
        tg = body[i]; ln = int.from_bytes(body[i+1:i+3], "big")
        out.append((tg, body[i+3:i+3+ln])); i += 3 + ln
    return out


def classify(h):
    raw = bytes.fromhex(h)
    fv = int.from_bytes(raw[8:10], "big"); ot = raw[10]
    L = len(raw); tl = int.from_bytes(raw[-4:], "big")
    if raw[:7] == b"AFGLREX":
        return "NEG-09"
    if raw[11] != 0x00:
        return "NEG-10"
    if tl != L:
        return "NEG-08"
    if fv == 0x0003:
        return "NEG-05"
    if ot == 0x86:
        return "NEG-07" if 0x8B in [t for t, _ in _walk(raw)] else "TV2-N5"
    if fv == 0x0001:
        return "NEG-01" if ot == 0x88 else "NEG-06"
    if ot == 0x80:
        return "NEG-02"
    if ot == 0x8C:
        return "NEG-03"
    if ot == 0x04:
        return "NEG-04"
    m = {(0x88, 62): "TV2-01", (0x89, 168): "TV2-02", (0x86, 225): "TV2-N5"}
    if (ot, L) in m:
        return m[(ot, L)]
    if ot == 0x8B and L == 157:
        d5 = next((int.from_bytes(v, "big") for t, v in _walk(raw) if t == 0xD5), None)
        return "TV2-05" if d5 == 0 else "TV2-07"
    if ot == 0x8A and L == 266:
        k = next((v[0] for t, v in _walk(raw) if t == 0xC7), None)
        return "TV2-06" if k == 1 else "TV2-OTHER"
    return None


def build_constructed():
    MAGIC = b"AFGLREF\x00"
    def ef(t, v): return bytes([t]) + len(v).to_bytes(2, "big") + v
    def mk(ot, fv, fields, total=None, magic=MAGIC):
        body = b"".join(ef(t, v) for t, v in fields)
        head = magic + fv.to_bytes(2, "big") + bytes([ot]) + b"\x00" + len(fields).to_bytes(2, "big")
        tl = len(head) + len(body) + 4 if total is None else total
        return head + body + tl.to_bytes(4, "big")

    DOM = b"d0"; GEN = (1).to_bytes(4, "big"); ROOT = b"\x44"*32; Z = b"\x00"*32
    R16 = b"\x55"*16
    ehwm = [(0xD1, DOM), (0xD2, GEN), (0xD3, (0).to_bytes(8, "big")),
            (0xD4, Z), (0xD5, (0).to_bytes(8, "big")), (0xD6, ROOT), (0xD7, Z)]
    out = {}
    out["C-TRUNC-SHORT"] = (MAGIC + b"\x00\x02" + b"\x8B" + b"\x00" +
                            b"\x00\x07" + b"\x00\x00\x00\x12")[:-1]
    out["C-TRUNC-FIELD"] = mk(0x8B, 0x0002, ehwm)[:-8]
    t = mk(0x8B, 0x0002, ehwm)
    out["C-TRAILING"] = t[:-4] + (len(t) - 2).to_bytes(4, "big")
    out["C-EMPTY-FIELDS"] = MAGIC + b"\x00\x02" + b"\x8B" + b"\x00" + b"\x00\x00" + b"\x00\x00\x00\x12"
    p02 = bytes.fromhex("f6f23772abff685cbc66a963bc4649eec64e26c2942aa7e483326071208725c8")
    n5bad = [(0x81, DOM), (0x82, GEN), (0x83, (0).to_bytes(8, "big")),
             (0x84, (4).to_bytes(8, "big")), (0x85, b"\x11"*32),
             (0x86, (1).to_bytes(8, "big")), (0x87, p02),
             (0x88, (100).to_bytes(8, "big")), (0x89, (104).to_bytes(8, "big")),
             (0x8B, Z), (0x8A, ROOT), (0x8C, Z)]
    out["C-DUP-RULE"] = mk(0x86, 0x0002, n5bad)
    body7 = b"".join(ef(a, b) for a, b in ehwm)
    head = MAGIC + b"\x00\x02" + b"\x8B" + b"\x00" + (5).to_bytes(2, "big")
    out["C-FCNT-MISMATCH"] = head + body7 + (len(head)+len(body7)+4).to_bytes(4, "big")
    out["C-MAGIC-ONLY"] = mk(0x8B, 0x0002, ehwm, magic=b"XFGLREF\x00")
    t01 = [(0x01, b"e1"), (0x02, b"a1"), (0x03, b"\x00"*45),
           (0x04, b"s1"), (0x05, b"\x01"), (0x06, b""), (0x07, b"")]
    out["C-V2-TYPE01"] = mk(0x01, 0x0002, t01)

    # ---- ZFP-02 修正：真正的 v1 合法正例（§2 3.1 ATTEMPT_REF + 3.3 嵌套 KEY_TRIPLE）----
    inner = mk(0x03, 0x0001, [(0x21, b"R1"),
                              (0x22, (1).to_bytes(8, "big")),
                              (0x23, (1).to_bytes(8, "big"))])
    out["V1-ATTEMPT-REF-OK"] = mk(0x01, 0x0001, [
        (0x01, b"E1"), (0x02, b"A1"), (0x03, inner),
        (0x04, b"S1"), (0x05, b"\x01"), (0x06, b""), (0x07, b"")])

    # ---- ZFP-03 修正：值宽度 / 取值域 / 嵌套长度反例 ----
    out["C-WIDTH-EPOCH"] = mk(0x82, 0x0002, [
        (0x41, R16), (0x42, DOM), (0x43, GEN), (0x44, b"\x01"),
        (0x45, (1).to_bytes(8, "big")), (0x46, b"\x33"*32), (0x47, Z)])
    out["C-DOMAIN-GRANTKIND"] = mk(0x83, 0x0002, [
        (0x51, R16), (0x52, DOM), (0x53, GEN),
        (0x54, (1).to_bytes(8, "big")), (0x55, b"\x02"), (0x56, Z)])
    bad_inner = bytearray(inner)
    bad_inner[-4:] = (999).to_bytes(4, "big")
    out["C-NESTED-TLEN"] = mk(0x01, 0x0001, [
        (0x01, b"E1"), (0x02, b"A1"), (0x03, bytes(bad_inner)),
        (0x04, b"S1"), (0x05, b"\x01"), (0x06, b""), (0x07, b"")])
    # ==== 【ZRV-02】知微 第三轮指出的 6 个反例，常驻防回归 ====
    tri = mk(0x03, 0x0001, [(0x21, b"R1"),
                            (0x22, (1).to_bytes(8, "big")),
                            (0x23, (1).to_bytes(8, "big"))])
    inner_attempt = mk(0x01, 0x0001, [
        (0x01, b"E9"), (0x02, b"A9"), (0x03, tri),
        (0x04, b"S9"), (0x05, b"\x01"), (0x06, b""), (0x07, b"")])
    out["C-NESTED-TYPE"] = mk(0x01, 0x0001, [
        (0x01, b"E1"), (0x02, b"A1"), (0x03, inner_attempt),
        (0x04, b"S1"), (0x05, b"\x01"), (0x06, b""), (0x07, b"")])
    out["C-LEN-EVENTID"] = mk(0x01, 0x0001, [
        (0x01, b"x" * 256), (0x02, b"A1"), (0x03, tri),
        (0x04, b"S1"), (0x05, b"\x01"), (0x06, b""), (0x07, b"")])
    out["C-LEN-OBSERVED"] = mk(0x01, 0x0001, [
        (0x01, b"E1"), (0x02, b"A1"), (0x03, tri),
        (0x04, b"S1"), (0x05, b"\x01"), (0x06, b"y" * 1025), (0x07, b"")])
    out["C-MIN-EPOCH"] = mk(0x03, 0x0001, [
        (0x21, b"R1"), (0x22, (0).to_bytes(8, "big")),
        (0x23, (1).to_bytes(8, "big"))])
    out["C-MIN-SEQ"] = mk(0x03, 0x0001, [
        (0x21, b"R1"), (0x22, (1).to_bytes(8, "big")),
        (0x23, (0).to_bytes(8, "big"))])
    out["C-MIN-RECEIPTSEQ"] = mk(0x02, 0x0001, [
        (0x11, b"E1"), (0x12, b"A1"), (0x13, tri), (0x14, b"\x01"),
        (0x15, (0).to_bytes(8, "big")), (0x16, b"R")])

    return out


REUSE_CASES = [
    ("NEG-11", "v2 头，直调 v1 专用入口", "v1", ("REJECT", "R-V2-02b"),
     "版本不匹配（v2 字节进 v1 入口）"),
    # 【ZRV-03】反向入口：拒绝行为已观察，但规范规则号待定。
    # 预期写成占位码，使其【不计入】"规范规则号符合"的 PASS。
    ("X2", "v1 头，直调 v2 专用入口（规则号待定）", "v2",
     ("REJECT_PENDING_RULING", "PENDING_RULING_VERSION_ENTRY"),
     "B_23：R-V2-02b 仅限 v2→v1；反向规则号 PENDING_RULING"),
]

EXTRA_CASES = [
    ("X2b", "v2 头 + 白名单类型，直调 v2 入口（应接受）", "v2", ("ACCEPT",),
     "版本对+类型对 => 接受；反证 X2 的拒绝来自版本而非类型"),
    ("TV2-81", "0x81 IDENTITY_REGISTRATION", "dispatcher", ("ACCEPT",), "B_22 §3.6"),
    ("TV2-82", "0x82 EPOCH_ASSIGNMENT", "dispatcher", ("ACCEPT",), "B_22 §3.7"),
    ("TV2-83", "0x83 GRANT_RECORD", "dispatcher", ("ACCEPT",), "B_22 §3.8"),
    ("TV2-84", "0x84 PREPARE_RECORD", "dispatcher", ("ACCEPT",), "B_22 §3.9"),
    ("TV2-85", "0x85 CLOSURE_RECORD", "dispatcher", ("ACCEPT",), "B_22 §3.10"),
    ("TV2-87", "0x87 REVOCATION_RECORD", "dispatcher", ("ACCEPT",), "B_22 §3.11"),
    ("V1-ATTEMPT-REF-OK", "v1 ATTEMPT_REF 合法正例（含嵌套 KEY_TRIPLE）",
     "dispatcher", ("ACCEPT",), "§2 3.1 + 3.3"),
    ("C-WIDTH-EPOCH", "0x82 epoch 仅 1 字节（应 8 字节 u64）",
     "dispatcher", ("REJECT", "R-V2-10"), "§2 2.3 整数定宽"),
    ("C-DOMAIN-GRANTKIND", "0x83 grant_kind=2（值域只 1）",
     "dispatcher", ("REJECT", "R-V2-10"), "B_22 §3.8 取值域"),
    ("C-NESTED-TLEN", "v1 嵌套 KEY_TRIPLE 的 TOTAL_LEN=999",
     "dispatcher", ("REJECT", "R-V2-10"), "§2 N11 内外长度一致"),

    # ---- 【ZRV-02】常驻防回归（知微 第三轮反例）----
    ("C-NESTED-TYPE", "嵌套类型冒充：内层 ATTEMPT_REF 充当 KEY_TRIPLE",
     "dispatcher", ("REJECT", "R-V2-10"), "§2 3.3：该位置须为 0x03"),
    ("C-LEN-EVENTID", "event_id 256 字节（上限 255）",
     "dispatcher", ("REJECT", "R-V2-10"), "§2 3.1：字符串 1..255"),
    ("C-LEN-OBSERVED", "observed_state 1025 字节（上限 1024）",
     "dispatcher", ("REJECT", "R-V2-10"), "§2 3.1：内容类 0..1024"),
    ("C-MIN-EPOCH", "KEY_TRIPLE.epoch = 0（应 >=1）",
     "dispatcher", ("REJECT", "R-V2-10"), "§2 3.3：epoch >= 1"),
    ("C-MIN-SEQ", "KEY_TRIPLE.seq = 0（应 >=1）",
     "dispatcher", ("REJECT", "R-V2-10"), "§2 3.3：seq >= 1"),
    ("C-MIN-RECEIPTSEQ", "receipt_seq = 0（应 >=1）",
     "dispatcher", ("REJECT", "R-V2-10"), "§2 3.2：receipt_seq >= 1"),
]


def run(evidence_dir=None):
    path, raw = find_evidence(evidence_dir)
    if raw is None:
        return [], {"evidence_path": None, "evidence_ok": False,
                    "evidence_detail": "未找到证据文件", "unknown_vectors": []}
    ok, detail = verify_evidence(raw)

    vectors, unknown = {}, []
    for h in load_b24(raw):
        n = classify(h)
        (vectors.__setitem__(n, h) if n else unknown.append(h[:16]))

    c = build_constructed()
    if "TV2-05" in vectors:
        c["NEG-11"] = bytes.fromhex(vectors["TV2-05"])
        c["X2b"] = bytes.fromhex(vectors["TV2-05"])
    if "NEG-01" in vectors:
        c["X2"] = bytes.fromhex(vectors["NEG-01"])

    # ---- 接入 vec6.py 的 6 类正例（0x81-0x85、0x87）----
    try:
        import vec6
        c.update(vec6.NEW)
    except Exception:
        pass

    results = []
    for (vid, desc, entry, exp, basis) in (list(E.EXPECTED) + list(E.CONSTRUCTED)
                                           + REUSE_CASES + EXTRA_CASES):
        src = vectors.get(vid) or c.get(vid)
        if isinstance(src, str):
            src = bytes.fromhex(src)
        if src is None:
            results.append(dict(id=vid, desc=desc, entry=entry, expected=exp,
                                actual=("SKIP", "input missing"),
                                basis=basis, verdict="SKIP"))
        else:
            results.append(_judge(vid, desc, entry, exp, src, basis))
    meta = {"evidence_path": path, "evidence_ok": ok,
            "evidence_detail": detail, "unknown_vectors": unknown}
    return results, meta


def _judge(vid, desc, entry, exp, raw, basis):
    try:
        r = P.parse(raw, entry=entry)
        act = ("ACCEPT",)
        extra = {"digest": P.protocol_digest(raw), "type": r["OBJECT_TYPE"],
                 "ver": r["FORMAT_VER"], "len": len(raw),
                 "input_sha256": hashlib.sha256(raw).hexdigest()[:16]}
    except P.Reject as e:
        act = ("REJECT", e.code)
        extra = {"detail": e.detail, "len": len(raw),
                 "input_sha256": hashlib.sha256(raw).hexdigest()[:16]}
    # 【ZRV-03】预期为 PENDING_RULING 时，行为正确也只记 OBSERVED_PENDING_RULING，
    # 不计入 PASS（规范规则号符合）。
    if exp[0] == "REJECT_PENDING_RULING":
        behavior_ok = (act[0] == "REJECT" and act[1] == exp[1])
        return dict(id=vid, desc=desc, entry=entry, expected=exp, actual=act,
                    basis=basis,
                    verdict=("OBSERVED_PENDING_RULING" if behavior_ok else "FAIL"),
                    pending_rule_id=exp[1], **extra)
    return dict(id=vid, desc=desc, entry=entry, expected=exp, actual=act,
                basis=basis, verdict="PASS" if act == exp else "FAIL", **extra)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    res, meta = run(a.evidence)
    n = len(res)
    p = sum(1 for r in res if r["verdict"] == "PASS")
    f = sum(1 for r in res if r["verdict"] == "FAIL")
    s = sum(1 for r in res if r["verdict"] == "SKIP")
    pend = sum(1 for r in res if r["verdict"] == "OBSERVED_PENDING_RULING")

    if a.json:
        print(json.dumps({"meta": meta, "results": res,
                          "summary": {"total": n, "pass": p, "fail": f, "skip": s}},
                         ensure_ascii=False, indent=2))
    else:
        print(f"证据: {meta['evidence_path']}")
        print(f"      {meta['evidence_detail']}")
        if meta["unknown_vectors"]:
            print(f"      未识别向量 {len(meta['unknown_vectors'])} 条: {meta['unknown_vectors']}")
        print()
        print(f"{'编号':<20}{'入口':<11}{'期望':<22}{'实际':<22}{'判定'}")
        print("-" * 92)
        for r in res:
            e = r["expected"][0] if r["expected"][0] == "ACCEPT" else f"REJECT {r['expected'][1]}"
            x = r["actual"][0] if r["actual"][0] == "ACCEPT" else f"REJECT {r['actual'][1]}"
            print(f"{r['id']:<20}{r['entry']:<11}{e:<22}{x:<22}{r['verdict']}")
        print("-" * 92)
        print(f"合计 {n}  通过 {p}  失败 {f}  跳过 {s}")

    if not meta["evidence_ok"]:
        print("\n[exit 3] 证据身份校验失败", file=sys.stderr)
        return 3
    if f > 0:
        print("\n[exit 1] 存在 FAIL", file=sys.stderr)
        return 1
    if s > 0:
        print(f"\n[exit 2] {s} 项 SKIP（必需输入缺失），不得视为完成", file=sys.stderr)
        return 2
    if pend > 0:
        print(f"\n[note] {pend} 项行为已观察，但规范规则号 PENDING_RULING；"
              f"不计入 PASS（规范符合）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
