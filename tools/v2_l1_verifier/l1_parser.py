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
# 【2026-11-10 修正，知微 ZFP-04】：不新增未登记的 rule_id。
#   §2 步骤 9 的"三个值、两个约束"用【同一个 R-V2-09】表达，
#   并用 detail.cause 区分子情形：
#     cause = "declared_vs_read"  声明数 != 实读数
#     cause = "read_vs_spec"      实读数 != 规定字段数
#   理由：知微 明确建议"保留 R-V2-09，另加 cause/detail 表示"，
#         若正式新增 rule_id，须先批准并固定新规范。
R_MAGIC       = "R-V2-02a"   # MAGIC 不符
R_VER_MISMATCH= "R-V2-02b"   # 版本不匹配（专用入口只收自己的版本）
R_V1_N3       = "R-V2-02c"   # 高位类型在 v1 规则下出现（§2 N3）
R_V2_NOTYPE   = "R-V2-02d"   # 版本为 v2 但类型是未登记的 0x01-0x03
R_UNKNOWN_VER = "R-V2-03"    # 未知版本
R_RESERVED_T  = "R-V2-04"    # 0x00 或 0x80
R_NOT_LISTED  = "R-V2-05"    # 白名单外
R_RESERVED_B  = "R-V2-06"    # RESERVED != 0x00
R_TRUNC       = "R-V2-07"    # 长度/字段头不完整
R_TOTAL_LEN   = "R-V2-08"    # TOTAL_LEN 不符
R_FIELD_COUNT = "R-V2-09"    # 字段数不符（配 cause 区分子情形）
R_FIELD_SPEC  = "R-V2-10"    # TAG / 顺序 / 长度 / 取值不符


class Reject(Exception):
    def __init__(self, code, detail="", cause=None):
        self.code = code
        self.detail = detail
        self.cause = cause
        super().__init__(f"{code}: {detail}" + (f" [{cause}]" if cause else ""))


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
        # 【ZFP-04 后半】两个方向行为相同（都拒绝），但规则号归属不同：
        #   v2 -> v1 : R-V2-02b 已有规范依据（B_23 §3.2）
        #   v1 -> v2 : 规则号待定 REVERSE_VERSION_ENTRY_RULE_ID = PENDING_RULING
        # 用 detail 标注 direction，便于验收器区分，不擅自扩号。
        direction = "v2_to_v1" if (entry == "v1" and fv == FORMAT_V2) else \
                    "v1_to_v2" if (entry == "v2" and fv == FORMAT_V1) else \
                    "other"
        raise Reject(R_VER_MISMATCH,
                     f"entry={entry} got=0x{fv:04X} direction={direction}",
                     cause=direction)

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
        raise Reject(R_FIELD_COUNT, f"declared={fcnt} read={len(fields)}",
                     cause="declared_vs_read")

    spec = FIELD_COUNT.get(otype)
    if spec is None:
        raise Reject(R_NOT_LISTED, f"0x{otype:02X} no field spec")
    if len(fields) != spec:
        raise Reject(R_FIELD_COUNT, f"0x{otype:02X} needs {spec} got {len(fields)}",
                     cause="read_vs_spec")

    got_tags = [t for t, _ in fields]
    if got_tags != TAGS[otype]:
        raise Reject(R_FIELD_SPEC, f"tags {[hex(x) for x in got_tags]} != spec")

    _check_values(otype, fields, entry)

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


# ---- 字段值约束表（ZFP-03 修正）----
# 依据 B_22 §3.0a–3.11 与 §2 2.3（整数定宽、字符串/bytes 带 LEN）
# 形式：{otype: {tag: ("int", 字节数) | ("bytes", 定长或None)
#                     | ("enum", {允许值}) | ("str", None) | ("nested", 类型)}}
VALUE_SPEC = {
    # 0x06/0x07 是【内容类】字段，依 §2 3.1 允许 LEN=0
    0x01: {0x01: ("str", None), 0x02: ("str", None), 0x03: ("nested", 0x03),
           0x04: ("str", None), 0x05: ("enum", {0x01}),
           0x06: ("str_opt", None), 0x07: ("str_opt", None)},
    0x02: {0x11: ("str", None), 0x12: ("str", None), 0x13: ("nested", 0x03),
           0x14: ("enum", {0x01}), 0x15: ("int", 8), 0x16: ("str", None)},
    0x03: {0x21: ("str", None), 0x22: ("int", 8), 0x23: ("int", 8)},
    0x81: {0x31: ("bytes", 16), 0x32: ("str", None), 0x33: ("int", 4),
           0x34: ("bytes", 32), 0x35: ("bytes", 32), 0x36: ("bytes", 32),
           0x37: ("bytes", 32)},
    0x82: {0x41: ("bytes", 16), 0x42: ("str", None), 0x43: ("int", 4),
           0x44: ("int", 8), 0x45: ("int", 8), 0x46: ("bytes", 32),
           0x47: ("bytes", 32)},
    0x83: {0x51: ("bytes", 16), 0x52: ("str", None), 0x53: ("int", 4),
           0x54: ("int", 8), 0x55: ("enum", {0x01}), 0x56: ("bytes", 32)},
    0x84: {0x61: ("bytes", 16), 0x62: ("str", None), 0x63: ("int", 4),
           0x64: ("enum", {0x01, 0x02, 0x03}), 0x65: ("bytes", 32),
           0x66: ("bytes", 16), 0x67: ("bytes", 32)},
    0x85: {0x71: ("bytes", 16), 0x72: ("str", None), 0x73: ("int", 4),
           0x74: ("bytes", 32), 0x75: ("enum", {0x01, 0x02, 0x03}),
           0x76: ("bytes", 32), 0x77: ("bytes", 32)},
    0x86: {0x81: ("str", None), 0x82: ("int", 4), 0x83: ("int", 8),
           0x84: ("int", 8), 0x85: ("bytes", 32), 0x86: ("int", 8),
           0x87: ("bytes", 32), 0x88: ("int", 8), 0x89: ("int", 8),
           0x8A: ("bytes", 32), 0x8C: ("bytes", 32)},
    0x87: {0x91: ("bytes", 16), 0x92: ("str", None), 0x93: ("int", 4),
           0x94: ("int", 8), 0x95: ("bytes", 32), 0x96: ("bytes", 32)},
    0x88: {0xA1: ("str", None), 0xA2: ("int", 4), 0xA3: ("int", 8),
           0xA4: ("int", 8), 0xA5: ("int", 4), 0xA6: ("bytes", None)},
    0x89: {0xB1: ("str", None), 0xB2: ("int", 4), 0xB3: ("int", 8),
           0xB4: ("bytes", 32), 0xB5: ("int", 8), 0xB6: ("bytes", 32),
           0xB7: ("int", 8), 0xB8: ("bytes", 32)},
    0x8A: {0xC1: ("str", None), 0xC2: ("int", 4), 0xC3: ("int", 8),
           0xC4: ("bytes", 32), 0xC5: ("int", 8), 0xC6: ("bytes", 32),
           0xC7: ("enum", {0x01, 0x02, 0x03, 0x04}), 0xC8: ("bytes", 32),
           0xC9: ("bytes", 32), 0xCA: ("bytes", 32), 0xCB: ("bytes", 32)},
    0x8B: {0xD1: ("str", None), 0xD2: ("int", 4), 0xD3: ("int", 8),
           0xD4: ("bytes", 32), 0xD5: ("int", 8), 0xD6: ("bytes", 32),
           0xD7: ("bytes", 32)},
}


def _check_values(otype, fields, entry):
    """校验字段 VALUE 的类型/宽度/取值域；nested 类型递归解析内层对象。"""
    spec = VALUE_SPEC.get(otype, {})
    for tag, val in fields:
        r = spec.get(tag)
        if r is None:
            continue
        kind = r[0]
        if kind == "int":
            if len(val) != r[1]:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X int width %d != %d" % (otype, tag, len(val), r[1]))
        elif kind == "bytes":
            if r[1] is not None and len(val) != r[1]:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X bytes len %d != %d" % (otype, tag, len(val), r[1]))
        elif kind == "enum":
            if len(val) != 1:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X enum width %d != 1" % (otype, tag, len(val)))
            if val[0] not in r[1]:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X enum %d not allowed" % (otype, tag, val[0]))
        elif kind == "str":
            # 标识类：必须非空（§2 2.3）
            if len(val) == 0 or b"\x00" in val:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X str empty or has NUL" % (otype, tag))
            try:
                val.decode("utf-8")
            except UnicodeDecodeError:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X str not UTF-8" % (otype, tag))
        elif kind == "str_opt":
            # 内容类：允许 LEN=0，仅禁 NUL 与非 UTF-8（§2 3.1）
            if b"\x00" in val:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X str_opt has NUL" % (otype, tag))
            try:
                val.decode("utf-8")
            except UnicodeDecodeError:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X str_opt not UTF-8" % (otype, tag))
        elif kind == "nested":
            try:
                parse(val, entry="v1")
            except Reject as e:
                raise Reject(R_FIELD_SPEC,
                             "0x%02X.0x%02X nested invalid: %s" % (otype, tag, e.code))
