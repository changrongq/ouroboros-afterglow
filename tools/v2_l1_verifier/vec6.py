# -*- coding: utf-8 -*-
"""补齐凌翼 D-C 要求的剩余 6 类正例：0x81-0x85、0x87

生成最小合规字节（字段值取最简合法值），供 L1 解析验证。
不声称这些字节代表真实业务语义，只用于 L1 结构解析测试。
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")

MAGIC = b"AFGLREF\x00"

def ef(t, v):
    return bytes([t]) + len(v).to_bytes(2, "big") + v

def build(ot, fields, fv=0x0002):
    body = b"".join(ef(t, v) for t, v in fields)
    head = MAGIC + fv.to_bytes(2, "big") + bytes([ot]) + b"\x00" + len(fields).to_bytes(2, "big")
    total = len(head) + len(body) + 4
    return head + body + total.to_bytes(4, "big")

def build_v1(ot, fields):
    return build(ot, fields, fv=0x0001)

DOM = b"d0"
GEN = (1).to_bytes(4, "big")
ROOT = b"\x44" * 32
Z32 = b"\x00" * 32
REC16 = b"\x55" * 16          # recorder_id (bytes[16])

# ---- 0x81 IDENTITY_REGISTRATION · 7 字段 ----
# 0x31 recorder_id[16] 0x32 authority_domain 0x33 generation
# 0x34 root_ref[32] 0x35 registered_commitment[32]
# 0x36 predecessor_digest[32] 0x37 order_evidence_ref[32]
V2_81 = build(0x81, [
    (0x31, REC16), (0x32, DOM), (0x33, GEN),
    (0x34, ROOT), (0x35, b"\x11" * 32),
    (0x36, Z32), (0x37, b"\x22" * 32),
])

# ---- 0x82 EPOCH_ASSIGNMENT · 7 字段 ----
# 0x41 recorder_id[16] 0x42 domain 0x43 generation
# 0x44 epoch 0x45 assigned_from_max 0x46 max_scope_digest[32] 0x47 predecessor[32]
V2_82 = build(0x82, [
    (0x41, REC16), (0x42, DOM), (0x43, GEN),
    (0x44, (1).to_bytes(8, "big")), (0x45, (1).to_bytes(8, "big")),
    (0x46, b"\x33" * 32), (0x47, Z32),
])

# ---- 0x83 GRANT_RECORD · 6 字段 ----
# 0x51 recorder_id 0x52 domain 0x53 generation
# 0x54 grant_epoch 0x55 grant_kind 0x56 predecessor[32]
V2_83 = build(0x83, [
    (0x51, REC16), (0x52, DOM), (0x53, GEN),
    (0x54, (1).to_bytes(8, "big")), (0x55, b"\x01"), (0x56, Z32),
])

# ---- 0x84 PREPARE_RECORD · 7 字段 ----
# 0x61 recorder_id 0x62 domain 0x63 generation 0x64 intent_kind
# 0x65 intent_payload_digest[32] 0x66 attempt_nonce[16] 0x67 predecessor[32]
V2_84 = build(0x84, [
    (0x61, REC16), (0x62, DOM), (0x63, GEN), (0x64, b"\x01"),
    (0x65, b"\x44" * 32), (0x66, b"\x66" * 16), (0x67, Z32),
])

# ---- 0x85 CLOSURE_RECORD · 7 字段 ----
# 0x71 recorder_id 0x72 domain 0x73 generation 0x74 attempt_ref[32]
# 0x75 closure_result 0x76 result_payload_digest[32] 0x77 predecessor[32]
V2_85 = build(0x85, [
    (0x71, REC16), (0x72, DOM), (0x73, GEN),
    (0x74, b"\x77" * 32), (0x75, b"\x01"),
    (0x76, b"\x88" * 32), (0x77, Z32),
])

# ---- 0x87 REVOCATION_RECORD · 6 字段 ----
# 0x91 recorder_id 0x92 domain 0x93 generation
# 0x94 revoke_epoch 0x95 revoked_grant_digest[32] 0x96 predecessor[32]
V2_87 = build(0x87, [
    (0x91, REC16), (0x92, DOM), (0x93, GEN),
    (0x94, (2).to_bytes(8, "big")), (0x95, b"\x99" * 32), (0x96, Z32),
])

NEW = {
    "TV2-81": V2_81,
    "TV2-82": V2_82,
    "TV2-83": V2_83,
    "TV2-84": V2_84,
    "TV2-85": V2_85,
    "TV2-87": V2_87,
}

if __name__ == "__main__":
    import hashlib
    def proto(raw):
        o = raw[10:11]; f = raw[8:10]; r = raw[11:12]; c = raw[12:14]; fld = raw[14:-4]
        return hashlib.sha256(o + f + o + r + c + fld).hexdigest()

    print(f"{'编号':<9}{'类型':<7}{'字段':<5}{'字节':<6}{'协议摘要前16'}")
    print("-" * 60)
    for k, raw in NEW.items():
        ot = raw[10]
        fc = int.from_bytes(raw[12:14], "big")
        tl = int.from_bytes(raw[-4:], "big")
        assert tl == len(raw), f"{k} TOTAL_LEN 不闭合"
        print(f"{k:<9}0x{ot:02X}   {fc:<5}{len(raw):<6}{proto(raw)[:16]}")
        print(f"  {raw.hex().upper()}")
