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


def find_evidence(cli_dir=None, strict=False):
    """查找证据文件。

    strict=True（--evidence-strict）：只查 cli_dir，【不回退】到 SEARCH_DIRS。
      理由（知微 第三轮 5.1）：--evidence 原本是【优先搜索】而非【排他路径】，
      指定目录缺文件时仍会回退到其他目录并成功，
      所以「改名一个目录」这类实验【不能证明缺失控制已触发】。
      要验证缺失控制，必须用 strict。
    """
    cands = []
    if cli_dir:
        cands.append(os.path.join(cli_dir, B24_FILENAME))
        if strict:
            c = cands[0]
            if os.path.exists(c):
                return os.path.abspath(c), open(c, "rb").read()
            return None, None
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

    # ------------------------------------------------------------------
    # 【B_32 §1.2 第 11/16/17 项：L1 可判定但原先无用例】
    #   知微/凌翼 都要求：不能把"实现会拒绝但没测"留在 L1 清单里。
    #   ⇒ 这三条把实现里【已存在但无用例】的判定固定下来：
    #       · TAG 重复
    #       · 非 UTF-8 字符串
    #       · 字符串含 NUL
    #   ⇒ 三者都归 R-V2-10（字段 SPEC 类），与实现当前行为一致。
    #   ⇒ 【注意】：若日后把某项独立编号，这三条期望要跟着改，
    #      那时应同步 B_23 规则表，而不是只改测试。
    # ------------------------------------------------------------------
    # 11) TAG 重复：0x03 规定 [0x21(str), 0x22(int>=1), 0x23(int>=1)]
    #     把第 3 个字段的 TAG 从 0x23 改成 0x22 ⇒ 序列变 [0x21, 0x22, 0x22]。
    #     【为什么这样构造（重要）】：
    #       · 若把第 2 个字段改成 0x21 并给 8 字节 int，
    #         则 _check_values 会因"0x21 位置要求 str"也拒绝 ——
    #         那样这条用例同时触发两个原因，【无法单独锁定 TAG 集合】。
    #       · 现构造让位置 2/3 都是 int8>=1，按位置类型全合法，
    #         只有 TAG 集合不同 ⇒ 才真正测到 TAG 比对本身。
    #     实测：整块跳过 TAG 比对后该输入变成 ACCEPT，隔离性成立。
    out["C-DUP-TAG"] = mk(0x03, 0x0001, [
        (0x21, b"R1"), (0x22, (1).to_bytes(8, "big")),
        (0x22, (1).to_bytes(8, "big"))])

    # 16) 非 UTF-8：0x21 字段含 0xFF 字节，长度合法
    out["C-UTF8-INVALID"] = mk(0x03, 0x0001, [
        (0x21, b"\xff" * 16), (0x22, (1).to_bytes(8, "big")),
        (0x23, (1).to_bytes(8, "big"))])

    # 17) 含 NUL：0x21 字段中嵌入 0x00
    out["C-NUL-IN-STR"] = mk(0x03, 0x0001, [
        (0x21, b"a" * 8 + b"\x00" * 8), (0x22, (1).to_bytes(8, "big")),
        (0x23, (1).to_bytes(8, "big"))])

    # 10) 【TAG 顺序置换】B_32 §1.2 第 10 项，2026-11-13 补
    #     0x03 规定 [0x21(str), 0x22(int8>=1), 0x23(int8>=1)]
    #     把 0x22 与 0x23 互换 ⇒ 序列变 [0x21, 0x23, 0x22]。
    #     【为什么这样构造】：位置 2/3 的值类型都是 int8>=1，
    #       ⇒ 按位置校验类型/值域【全都合法】，唯一不合法之处是 TAG 顺序。
    #     【隔离性已验证】：屏蔽 TAG 集合比对后，该输入变 ACCEPT。
    #     ⇒ 它确实只测顺序，不叠加其它拒绝原因；
    #       （注：解析器把顺序错也归 R-V2-10，与 TAG 集合共用同一判定，
    #         所以屏蔽该判定时它与 C-DUP-TAG 会同时变 ACCEPT —— 这是同源，不是缺陷。）
    out["C-TAG-ORDER"] = mk(0x03, 0x0001, [
        (0x21, b"R1"), (0x23, (1).to_bytes(8, "big")),
        (0x22, (1).to_bytes(8, "big"))])

    # ------------------------------------------------------------------
    # 【凌翼 2026-11-13 裁定 ②-c 要求：v1 嵌套的三类长度错误分别归类】
    #   裁定原文：「外层字段截断、外层总长度错误等情形，
    #   仍须按照各自的结构规则分类，不得声称所有嵌套长度错误一律属于 R-V2-10。」
    #
    #   ⇒ 下面四条把【实测到】的归属固定下来（不是按推测写）：
    #      · 内层 TOTAL_LEN 不符  → 外层抛 R-V2-10，
    #        但 detail 里保留内层真实规则号（嵌套递归把内层 Reject 包装了）
    #      · 外层字段 LEN 不符    → R-V2-07
    #      · 外层 TOTAL_LEN 不符  → R-V2-08
    #      · 外层对象被截断       → R-V2-07
    #   ⇒ 【注意】：这四条期望的是【外层观察到的规则号】，
    #     不是内层的。内层规则号只能从 detail 文本看出。
    # ------------------------------------------------------------------
    _inner_ok = mk(0x03, 0x0001, [
        (0x21, b"R1"), (0x22, (1).to_bytes(8, "big")),
        (0x23, (1).to_bytes(8, "big"))])

    def _outer(inner_bytes, total=None):
        return mk(0x01, 0x0001, [
            (0x01, b"E1"), (0x02, b"A1"), (0x03, inner_bytes),
            (0x04, b"C1"), (0x05, b"\x01"), (0x06, b""), (0x07, b"")],
            total=total)

    # 内层 TOTAL_LEN 声明比实际大 5
    _inner_bad_tl = _inner_ok[:-4] + (len(_inner_ok) + 5).to_bytes(4, "big")
    out["C-NEST-INNER-TLEN"] = _outer(_inner_bad_tl)

    # 外层 0x03 字段 LEN 声明 +3（并把外层 TOTAL_LEN 同步 +3）
    #   【头部长度必须算准】：MAGIC = "AFGLREF\x00" 是 8 字节（不是 9），
    #     所以头 = MAGIC(8) + FV(2) + OT(1) + RSV(1) + FC(2) = 14。
    #   ⇒ 我第一次写成 15，导致从第 15 字节开始遍历，第一个“字段”就是错的，
    #     于是构造失败。这里按实际 len(MAGIC) 计算，不写死数字。
    _o = bytearray(_outer(_inner_ok))
    _HEAD = len(MAGIC) + 2 + 1 + 1 + 2
    _i = _HEAD
    _f3 = None
    while _i < len(_o) - 4:
        _tag = _o[_i]
        _ln = int.from_bytes(_o[_i + 1:_i + 3], "big")
        if _tag == 0x03:
            _f3 = (_i + 1, _ln)
            break
        _i += 3 + _ln
    assert _f3 is not None, "构造失败：找不到 0x03 字段（HEAD=%d）" % _HEAD
    _o[_f3[0]:_f3[0] + 2] = (_f3[1] + 3).to_bytes(2, "big")
    _o[-4:] = (int.from_bytes(_o[-4:], "big") + 3).to_bytes(4, "big")
    out["C-NEST-OUTER-LEN"] = bytes(_o)

    # 外层对象 TOTAL_LEN 比实际大 5
    _o2 = _outer(_inner_ok)
    out["C-NEST-OUTER-TLEN"] = _o2[:-4] + (len(_o2) + 5).to_bytes(4, "big")

    # 外层对象被截断 8 字节（保留原 TOTAL_LEN）
    _o3 = _outer(_inner_ok)
    out["C-NEST-OUTER-TRUNC"] = _o3[:-8] + _o3[-4:]

    return out


REUSE_CASES = [
    ("NEG-11", "v2 头，直调 v1 专用入口", "v1", ("REJECT", "R-V2-02b"),
     "版本不匹配（v2 字节进 v1 入口）"),
    # 【凌翼 2026-11-12 裁定 B-1：X2 转正式规则验收】
    #   原为 REJECT_PENDING_RULING / OBSERVED_PENDING_RULING（不计入 PASS）。
    #   裁定后 R-V2-02e 已正式登记 ⇒ 必须按正常 REJECT 规则号验收，
    #   【不得】再以 pending 状态返回绿色。
    ("X2", "v1 头，直调 v2 专用入口", "v2", ("REJECT", "R-V2-02e"),
     "B_23 R-V2-02e：VERSION_V1_ENTERED_V2_PARSER（入口版本错，非类型错）"),
]

EXTRA_CASES = [
    ("X2b", "v2 头 + 白名单类型，直调 v2 入口（应接受）", "v2", ("ACCEPT",),
     "版本对+类型对 => 接受；反证 X2 的拒绝来自版本而非类型"),
    # ------------------------------------------------------------------
    # 【凌翼 2026-11-12 裁定 B-1 · 第 4 条：三个明确的负向测试】
    #   裁定要求「增加或核实三个明确的负向测试：
    #             v1→v2、v2→v1、v2 头部配未登记引用类型」。
    #   下面三条把它们【并列】列出，且各自断言不同的规则号，
    #   从而证明 02b / 02e / 02d 三者【不混用】。
    #   （原有 X2 / NEG-11 / C-V2-TYPE01 已覆盖行为，
    #     这三条是把"互斥关系"本身变成可执行断言。）
    # ------------------------------------------------------------------
    ("B1-v1-into-v2", "【裁定B-1】v1 记录 → v2 专用入口 ⇒ 必须 R-V2-02e",
     "v2", ("REJECT", "R-V2-02e"),
     "R-V2-02e = VERSION_V1_ENTERED_V2_PARSER；入口版本错，不是类型错"),
    ("B1-v2-into-v1", "【裁定B-1】v2 记录 → v1 专用入口 ⇒ 必须 R-V2-02b",
     "v1", ("REJECT", "R-V2-02b"),
     "R-V2-02b 仅覆盖此方向；若返回 02e 即为方向混淆"),
    ("B1-v2-badtype", "【裁定B-1】v2 头 + 未登记引用类型 ⇒ 必须 R-V2-02d",
     "dispatcher", ("REJECT", "R-V2-02d"),
     "R-V2-02d = 版本对、类型未登记；若返回 02e 即为版本/类型混淆"),
    # ------------------------------------------------------------------
    # 【知微 ZB31-01 修正 · 未知版本 × 三个入口】
    #   原实现把"不是对方版本"一律报 R-V2-02b，
    #   于是 0x0000/0x0003/0xFFFF 直调专用入口被错归为"版本不匹配"。
    #   ⇒ B_23 §2.3 五情形表 / §3.2 规则表：未知版本一律 R-V2-03。
    #   ⇒ 增加三个入口条，避免只测 dispatcher 就宣称覆盖。
    # ------------------------------------------------------------------
    ("B31-unk-ver-disp", "【ZB31-01】未知版本 0x0003 走 dispatcher ⇒ R-V2-03",
     "dispatcher", ("REJECT", "R-V2-03"),
     "B_23 §2.3：未知版本独立归 R-V2-03"),
    ("B31-unk-ver-v1", "【ZB31-01】未知版本 0x0003 走 v1 专用入口 ⇒ R-V2-03",
     "v1", ("REJECT", "R-V2-03"),
     "未知版本不属于 02b（02b 仅 v2→v1）；须先判未知版本"),
    ("B31-unk-ver-v2", "【ZB31-01】未知版本 0x0003 走 v2 专用入口 ⇒ R-V2-03",
     "v2", ("REJECT", "R-V2-03"),
     "未知版本不属于 02e（02e 仅 v1→v2）；须先判未知版本"),
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
    # ---- B_32 §1.2 第 11/16/17 项：L1 可判定但原先无用例 ----
    #   三者均为【隔离构造】：只触发被测的那一项，不叠加其它拒绝原因。
    ("C-DUP-TAG", "0x03 TAG 序列变 [0x21,0x22,0x22]（0x22 重复；按位置类型全合法）",
     "v1", ("REJECT", "R-V2-10"),
     "§2 N7：TAG 集合须与规定一致；重复即不符（屏蔽其它原因后仍须拒绝）"),
    ("C-UTF8-INVALID", "0x21 字段含非 UTF-8 字节（0xFF）",
     "v1", ("REJECT", "R-V2-10"),
     "§2 3.3：字符串须为合法 UTF-8"),
    ("C-NUL-IN-STR", "0x21 字段中含 NUL（0x00）",
     "v1", ("REJECT", "R-V2-10"),
     "§2 3.3：字符串不得含 NUL"),
    # 10) 【TAG 顺序置换】B_32 §1.2 第 10 项，2026-11-13 补
    ("C-TAG-ORDER", "0x03 TAG 序列 [0x21,0x23,0x22]（0x22/0x23 顺序互换）",
     "v1", ("REJECT", "R-V2-10"),
     "§2 N7：TAG 顺序须与规定一致（按位置类型全合法，仅顺序错）"),
    # ---- 凌翼 2026-11-13 裁定 ②-c：v1 嵌套三类长度错误分别归类 ----
    #   期望值是【实测】出来的外层规则号，不是按推测填的。
    ("C-NEST-INNER-TLEN", "嵌套 KEY_TRIPLE 的内层 TOTAL_LEN 声明过大（+5）",
     "v1", ("REJECT", "R-V2-10"),
     "内层递归失败被包装为 R-V2-10；detail 保留内层真实规则号 R-V2-08"),
    ("C-NEST-OUTER-LEN", "外层 0x03 字段 LEN 声明比实际多 3 字节",
     "v1", ("REJECT", "R-V2-07"),
     "外层字段长度与实际不符 ⇒ R-V2-07（不归 R-V2-10）"),
    ("C-NEST-OUTER-TLEN", "外层对象 TOTAL_LEN 声明比实际多 5 字节",
     "v1", ("REJECT", "R-V2-08"),
     "外层对象总长度不符 ⇒ R-V2-08（不归 R-V2-10）"),
    ("C-NEST-OUTER-TRUNC", "外层对象被截断 8 字节（TOTAL_LEN 保持原值）",
     "v1", ("REJECT", "R-V2-07"),
     "外层字段头不完整 ⇒ R-V2-07（不归 R-V2-10）"),
]


def run(evidence_dir=None, strict=False):
    path, raw = find_evidence(evidence_dir, strict)
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

    # ---- 裁定 B-1 三个明确负向测试的字节绑定 ----
    #   B1-v1-into-v2 : 与 X2 同一字节（v1 记录），换入口断言 02e
    #   B1-v2-into-v1 : 与 NEG-11 同一字节（v2 记录），换入口断言 02b
    #   B1-v2-badtype : 与 C-V2-TYPE01 同一字节（v2 头 + 0x01 类型），断言 02d
    #   ⇒ 【不新造字节】：复用已验证的同一批输入，只改断言，
    #     这样三条断言之间才是"同一输入、不同入口/不同类型"的严格对照。
    if "X2" in c:
        c["B1-v1-into-v2"] = c["X2"]
    if "NEG-11" in c:
        c["B1-v2-into-v1"] = c["NEG-11"]
    if "C-V2-TYPE01" in c:
        c["B1-v2-badtype"] = c["C-V2-TYPE01"]

    # ---- 知微 ZB31-01：未知版本 × 三个入口 ----
    #   同一 18 字节前缀，FORMAT_VER=0x0003（既非 0x0001 也非 0x0002）。
    #   ⇒ 三个入口必须【都】报 R-V2-03，而不是 dispatcher 对、专用入口错。
    _unk = bytes.fromhex("4146474c5245460000030100000000000012")
    c["B31-unk-ver-disp"] = _unk
    c["B31-unk-ver-v1"] = _unk
    c["B31-unk-ver-v2"] = _unk

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
    # 【凌翼 2026-11-12 裁定 B-1】
    #   原第四类 OBSERVED_PENDING_RULING（规则号待定，不计入 PASS）【已删除】。
    #   理由：R-V2-02e 已正式登记，反向入口不再是"待定项"，
    #         必须以正常 REJECT 规则号比对。
    #   ⇒ 若仍保留该分支，CI 就可能以 pending>0 返回绿色，
    #     而裁定明确要求 PENDING = 0。
    if exp[0] == "REJECT_PENDING_RULING":
        # 防御：不允许再有用例以旧形式声明"待定"。
        raise AssertionError(
            "用例 %s 仍使用已废止的 REJECT_PENDING_RULING；"
            "凌翼裁定 B-1 后必须写正式规则号（如 R-V2-02e）" % vid)
    return dict(id=vid, desc=desc, entry=entry, expected=exp, actual=act,
                basis=basis, verdict="PASS" if act == exp else "FAIL", **extra)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--evidence-strict", action="store_true",
                    help="--evidence 指定目录必须含证据文件，不回退到其他搜索路径")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    res, meta = run(a.evidence, a.evidence_strict)
    n = len(res)
    p = sum(1 for r in res if r["verdict"] == "PASS")
    f = sum(1 for r in res if r["verdict"] == "FAIL")
    s = sum(1 for r in res if r["verdict"] == "SKIP")
    pend = sum(1 for r in res if r["verdict"] == "OBSERVED_PENDING_RULING")

    if a.json:
        # 【知微 ZBR-02 配套修正 2026-11-11】
        #   原 summary 只有 total/pass/fail/skip，
        #   ⇒ total(44) != pass(43)+fail(0)+skip(0)，第四类 pending 在机器结果里消失。
        #   现补 pending 与守恒校验字段。
        # 【凌翼 2026-11-12 裁定】pending 必须恒为 0：
        #   R-V2-02e 登记后，不应再有“规则号待定”的用例。
        summary = {"total": n, "pass": p, "fail": f, "skip": s, "pending": pend}
        summary["conserved"] = (p + f + s + pend == n)
        print(json.dumps({"meta": meta, "results": res, "summary": summary},
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
        print(f"合计 {n}  通过 {p}  失败 {f}  跳过 {s}  待定 {pend}")

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
        # 【凌翼 2026-11-12】：正式规范符合性检查【不得】以 pending>0 返回绿色。
        #   裁定后 R-V2-02e 已登记，不应再出现待定项；出现即说明实现未落实。
        print(f"\n[exit 1] {pend} 项仍为 PENDING_RULING；"
              f"凌翼裁定 B-1 后 R-V2-02e 已登记，不允许待定项", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
