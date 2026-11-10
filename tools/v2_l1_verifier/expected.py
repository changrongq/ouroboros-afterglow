# -*- coding: utf-8 -*-
"""独立预期表 —— 与 parser.py 【不共享任何常量或逻辑】

凌翼要求：「测试工具与受测解析器分别实现预期结果来源，
             避免两者复制同一错误。」

⇒ 本文件的做法：
   · 预期结果【手写】，逐条对着规范文字填
   · 不 import parser.py
   · 每条给出【依据条文】，便于第三方核对
   · 若本表与 parser.py 不一致 ⇒ 测试失败，暴露出至少一方有错

来源（固定 commit 362e0e4）：
  §2 草案   blob e70a24d0d1b43c9656f21eb4e57f3b13709a0e3c
  B_23      blob 12b686172bce91b55344f7025cab9d3aa46beb45
  B_24      blob d4c7ce05093963787c54a5317cb116d54d7abc57
"""

# 每条：(编号, 说明, 入口, 期望结果, 依据)
# 期望结果 = ("ACCEPT",) 或 ("REJECT", "规则号")
EXPECTED = [
    # ---------------- B_24 正例（v2）----------------
    ("TV2-01", "0x88 MAX_SCOPE_SET 空集合", "dispatcher",
     ("ACCEPT",), "B_24 §2.4 / B_23 §2.2 v2 白名单"),
    ("TV2-02", "0x89 TRUSTED_HWM", "dispatcher",
     ("ACCEPT",), "B_24 §2.5"),
    ("TV2-05", "0x8B 初始 EHWM", "dispatcher",
     ("ACCEPT",), "B_24 §2.1"),
    ("TV2-06", "0x8A 首条否定事件", "dispatcher",
     ("ACCEPT",), "B_24 §2.2"),
    ("TV2-07", "0x8B 推进后 EHWM", "dispatcher",
     ("ACCEPT",), "B_24 §2.3"),
    ("TV2-N5", "0x86 N5，跳过保留 TAG 0x8B", "dispatcher",
     ("ACCEPT",), "B_24 §2.6 / B_22 §3.1"),
    ("TV2-OTHER", "0x8A kind=4", "dispatcher",
     ("ACCEPT",), "B_24 §2.7"),

    # ---------------- B_24 负例 ----------------
    ("NEG-01", "v1 下 0x88（高位类型）", "dispatcher",
     ("REJECT", "R-V2-02c"), "B_23 §3.2c / §2 N3"),
    ("NEG-02", "v2 下 0x80（保留未启用）", "dispatcher",
     ("REJECT", "R-V2-04"), "B_23 §3.2 / §2 2.2"),
    ("NEG-03", "v2 下 0x8C（白名单外）", "dispatcher",
     ("REJECT", "R-V2-05"), "B_23 §2.2 v2 白名单"),
    ("NEG-04", "v2 下 0x04（未登记）", "dispatcher",
     ("REJECT", "R-V2-05"), "B_23 §2.2 v2 白名单"),
    ("NEG-05", "FORMAT_VER=0x0003（未知版本）", "dispatcher",
     ("REJECT", "R-V2-03"), "B_23 §2.3 X1"),
    ("NEG-06", "v1 头 + 0x8B，走分派器", "dispatcher",
     ("REJECT", "R-V2-02c"), "凌翼 D-A 残留2：版本匹配后撞 N3"),
    ("NEG-07", "N5 用保留 TAG 0x8B", "dispatcher",
     ("REJECT", "R-V2-10"), "B_22 §3.1 保留 TAG / §2 步骤9"),
    ("NEG-08", "声明 TOTAL_LEN=999（实际157）", "dispatcher",
     ("REJECT", "R-V2-08"), "B_23 §3.2 / §2 N9 N10"),
    ("NEG-09", "MAGIC 不符", "dispatcher",
     ("REJECT", "R-V2-02a"), "B_23 §3.2a / §2 N1"),
    ("NEG-10", "RESERVED=0x01", "dispatcher",
     ("REJECT", "R-V2-06"), "B_23 §3.2 / §2 N4"),

    # ---- NEG-11 / X2 / X2b 在 run_a16.py 中作为「复用字节+换入口」用例执行 ----
    # （它们不新增字节，故不列入此表，避免重复计数）
]

# ---- 直接调用版本的额外用例：v2 头进入 v1 入口（等价 NEG-11）----

# ---- 人工构造的边界负例（不依赖 B_24，符合凌翼「还需包含」清单）----
CONSTRUCTED = [
    ("C-TRUNC-SHORT", "总长 17（不足 18）", "dispatcher",
     ("REJECT", "R-V2-07"), "B_23 §3.1 步骤0 / §2 N16"),
    ("C-TRUNC-FIELD", "字段 VALUE 被截断", "dispatcher",
     ("REJECT", "R-V2-07"), "§2 N17"),
    ("C-TRAILING", "TOTAL_LEN 小于实际（有尾随）", "dispatcher",
     ("REJECT", "R-V2-08"), "§2 N9"),
    ("C-EMPTY-FIELDS", "FIELD_COUNT=0 的空帧", "dispatcher",
     ("REJECT", "R-V2-10b"), "§2 步骤9 空帧反例：声明数=读取数=0，但规定数 7"),
    ("C-DUP-RULE", "同时违反 FIELD_COUNT 与保留 TAG", "dispatcher",
     ("REJECT", "R-V2-10b"), "实读数 12 ≠ 规定 11，先于 TAG 检查（步骤9 顺序）"),
    # ---- 2026-11-10 补：由变异测试发现的盲区 ----
    ("C-FCNT-MISMATCH", "声明 FIELD_COUNT=5，实际 7 个字段",
     "dispatcher", ("REJECT", "R-V2-09"),
     "§2 步骤9：声明数 ≠ 读取数，须区别于「读取数 ≠ 规定数」(10b)"),
    ("C-MAGIC-ONLY", "MAGIC 第 1 字节错（分派与专用入口都须拦）",
     "dispatcher", ("REJECT", "R-V2-02a"), "§2 N1"),
    # ---- 2026-11-10 补：由变异测试发现的第二处盲区 ----
    ("C-V2-TYPE01", "v2 + 类型 0x01（v1 引用类型，v2 未登记）",
     "dispatcher", ("REJECT", "R-V2-02d"),
     "B_23 §2.2：v2 白名单不含 0x01-0x03；R-V2-02d 专用于此"),
]
