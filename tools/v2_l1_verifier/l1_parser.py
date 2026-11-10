# -*- coding: utf-8 -*-
"""L1 结构解析器（v1 / v2）—— 受限实验实现

授权依据：凌翼裁定 2026-11-10 D-C
  L1_STANDALONE_TEST_IMPLEMENTATION = CONDITIONALLY_AUTHORIZED

严格边界：
  只做 L1 结构解析。不做 L2 内容绑定，不做 L3 权威消费。
  不接入授权/身份/持久化/恢复路径。
  不修改冻结件。

规范固定点：commit 362e0e4
  §2 草案            blob e70a24d0d1b43c9656f21eb4e57f3b13709a0e3c
  B_23 v2 规范       blob 12b686172bce91b55344f7025cab9d3aa46beb45
  B_24 向量          blob d4c7ce05093963787c54a5317cb116d54d7abc57
  迁移账本            blob ffcc7b48846f8cb3c4c2dc97d94f7931e10f43e4
"""

MAGIC = b"AFGLREF\x00"

# ---- 版本与类型白名单（来自 B_23 §2，与 §2 2.2）----
V1_TYPES = {0x01, 0x02, 0x03}
V2_TYPES = {0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8B}
RESERVED_TYPES = {0x80}          # v2 下仍保留，不启用
FORMAT_V1 = 0x0001
FORMAT_V2 = 0x0002

# ---- 各类型规定字段数（B_22 §3 / B_23 §四）----
FIELD_COUNT = {
    0x01: 7, 0x02: 6, 0x03: 3,
    0x81: 7, 0x82: 7, 0x83: 6, 0x84: 7, 0x85: 7,
    0x86: 11, 0x87: 6, 0x88: 6, 0x89: 8, 0x8A: 11, 0x8B: 7,
}

# ---- 各类型允许的 TAG 白名单（B_22 §3.0a-3.0c / §3.1-3.11）----
TAGS = {
    0x01: [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07],
    0x02: [0x11, 0x12, 0x13, 0x14, 0x15, 0x16],
    0x03: [0x21, 0x22, 0x23],
    0x81: [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37],
    0x82: [0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47],
    0x83: [0x51, 0x52, 0x53, 0x54, 0x55, 0x56],
    0x84: [0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67],
    0x85: [0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77],
    # N5：0x8B 是保留值，不在白名单内
    0x86: [0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8C],
    0x87: [0x91, 0x92, 0x93, 0x94, 0x95, 0x96],
    0x88: [0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6],
    0x89: [0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8],
    0x8A: [0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xCB],
    0x8B: [0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7],
}

# ---- 拒绝原因代号（B_23 §3.2 / 3.3）----
R_MAGIC       = "R-V2-02a"   # MAGIC 不符
R_VER_MISMATCH= "R-V2-02b"   # 版本为 v2 的字节进入 v1 专用入口（或反之）
R_V1_N3       = "R-V2-02c"   # 高位类型在 v1 规则下出现（§2 N3）
R_V2_NOTYPE   = "R-V2-02d"   # 版本为 v2 但类型是未登记的 0x01-0x03
R_UNKNOWN_VER = "R-V2-03"    # 未知版本
R_RESERVED_T  = "R-V2-04"    # 0x00 或 0x80
R_NOT_LISTED  = "R-V2-05"    # 白名单外
R_RESERVED_B  = "R-V2-06"    # RESERVED != 0x00
R_TRUNC       = "R-V2-07"    # 长度/字段头不完整
R_TOTAL_LEN   = "R-V2-08"    # TOTAL_LEN 不符
R_FIELD_COUNT = "R-V2-09"    # FIELD_COUNT 与实读数不符
R_FIELD_SPEC  = "R-V2-10"    # TAG/顺序/长度/取值不符
R_FIELD_SPECN = "R-V2-10b"   # 实读数与该类型【规定字段数】不符
                             # （§2 步骤9：声明数 = 读取数 = 规定数，
                             #  这是三个约束，不是两个）


class Reject(Exception):
    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def parse(raw, entry="dispatcher"):
    """L1 结构解析。

    entry: "dispatcher"（统一分派）或 "v1" / "v2"（直接调用专用入口）
    返回 dict：{"ver","type","fields","total_len"} —— 仅表示 STRUCTURALLY_VALID
    """
    L = len(raw)

    # ---- 统一分派器：只做前缀 + 版本分派，不判内容 ----
    if entry == "dispatcher":
        if L < 18:
            raise Reject(R_TRUNC, f"L={L} < 18")
        if raw[:8] != MAGIC:
            raise Reject(R_MAGIC, f"magic={raw[:8].hex()}")
        fv = int.from_bytes(raw[8:10], "big")
        if fv == FORMAT_V1:
            entry = "v1"
        elif fv == FORMAT_V2:
            entry = "v2"
        else:
            raise Reject(R_UNKNOWN_VER, f"FORMAT_VER=0x{fv:04X}")

    # ---- 专用入口：① 版本自检 → ② 该版本全部 L1 检查 ----
    if entry == "v1":
        expected, allowed, n3 = FORMAT_V1, V1_TYPES, True
    elif entry == "v2":
        expected, allowed, n3 = FORMAT_V2, V2_TYPES, False
    else:
        raise ValueError(f"unknown entry {entry}")

    if L < 18:
        raise Reject(R_TRUNC, f"L={L} < 18")
    if raw[:8] != MAGIC:
        raise Reject(R_MAGIC, f"magic={raw[:8].hex()}")

    # ① 版本自检（专用入口只收自己的版本）
    fv = int.from_bytes(raw[8:10], "big")
    if fv != expected:
        # v1 入口看到 v2 / v2 入口看到 v1 → 版本不匹配
        raise Reject(R_VER_MISMATCH, f"entry={entry} got=0x{fv:04X}")

    otype = raw[10]
    reserved = raw[11]
    fcnt = int.from_bytes(raw[12:14], "big")

    # ② 类型判定
    if otype == 0x00:
        raise Reject(R_RESERVED_T, "OBJECT_TYPE=0x00")
    if n3:
        # v1：≥0x80 一律拒绝（§2 N3）
        if otype >= 0x80:
            raise Reject(R_V1_N3, f"v1 + 0x{otype:02X} >= 0x80")
    else:
        # v2：0x80 保留；0x01-0x03 未登记；白名单外拒绝
        if otype in RESERVED_TYPES:
            raise Reject(R_RESERVED_T, f"OBJECT_TYPE=0x{otype:02X} reserved")
        if otype in (0x01, 0x02, 0x03):
            raise Reject(R_V2_NOTYPE, f"v2 + 0x{otype:02X} not registered")
        if otype not in allowed:
            raise Reject(R_NOT_LISTED, f"v2 + 0x{otype:02X} not in whitelist")

    if reserved != 0x00:
        raise Reject(R_RESERVED_B, f"RESERVED=0x{reserved:02X}")

    # ---- 字段区 ----
    body = raw[14:-4]
    total_len = int.from_bytes(raw[-4:], "big")
    fields = []
    i = 0
    while i < len(body):
        if i + 3 > len(body):
            raise Reject(R_TRUNC, f"field header at {i}")
        tag = body[i]
        ln = int.from_bytes(body[i+1:i+3], "big")
        if i + 3 + ln > len(body):
            raise Reject(R_TRUNC, f"field value at {i} needs {ln}")
        fields.append((tag, body[i+3:i+3+ln]))
        i += 3 + ln

    if total_len != L:
        raise Reject(R_TOTAL_LEN, f"TOTAL_LEN={total_len} L={L}")

    if fcnt != len(fields):
        raise Reject(R_FIELD_COUNT, f"declared={fcnt} read={len(fields)}")

    spec = FIELD_COUNT.get(otype)
    if spec is None:
        raise Reject(R_NOT_LISTED, f"0x{otype:02X} no field spec")
    if len(fields) != spec:
        raise Reject(R_FIELD_SPECN, f"0x{otype:02X} needs {spec} got {len(fields)}")

    got_tags = [t for t, _ in fields]
    if got_tags != TAGS[otype]:
        raise Reject(R_FIELD_SPEC, f"tags {[hex(x) for x in got_tags]} != spec")

    return {
        "FORMAT_VER": fv,
        "OBJECT_TYPE": otype,
        "FIELD_COUNT": len(fields),
        "TOTAL_LEN": total_len,
        "fields": fields,
        "entry": entry,
        "status": "STRUCTURALLY_VALID",
    }


def protocol_digest(raw):
    """§2 2.4 协议摘要。
    digest = SHA-256( OBJECT_TYPE ‖ FORMAT_VER ‖ OBJECT_TYPE ‖ RESERVED
                      ‖ FIELD_COUNT ‖ FIELDS )
    """
    import hashlib
    otype = raw[10:11]
    fmt   = raw[8:10]
    res   = raw[11:12]
    fcnt  = raw[12:14]
    fields= raw[14:-4]
    return hashlib.sha256(otype + fmt + otype + res + fcnt + fields).hexdigest()
