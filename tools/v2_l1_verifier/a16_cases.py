# -*- coding: utf-8 -*-
"""A16 用例登记集合 —— 无执行副作用，供 mutate 与 a16_result_check 共用。

【为什么单独成文件（知微 ZB32-01 建议）】
  原来 REQUIRED_CASE_IDS / ALLOWED_VERDICTS 定义在 mutate.py 里，
  而 a16_result_check.py 从 mutate 导入它们；
  当 mutate 也要调用 a16_result_check 时，就形成循环导入。
  ⇒ 把【纯数据】抽到本模块：不 import 任何本项目模块、无副作用、不需执行。
  ⇒ mutate.py 与 a16_result_check.py 都从这里取，保持「单点定义」。

【谁是权威】
  ⇒ 本文件是唯一定义处。mutate.py 也从这里导入（不再自己定义）。
  ⇒ 改必需用例集合 = 只改这一个文件。
"""

# 必需用例 ID（顺序即报告顺序，集合语义）
REQUIRED_CASE_IDS = (
    # --- 向量类（来自 B_24 固定证据）---
    "TV2-01", "TV2-02", "TV2-05", "TV2-06", "TV2-07", "TV2-N5", "TV2-OTHER",
    "NEG-01", "NEG-02", "NEG-03", "NEG-04", "NEG-05", "NEG-06",
    "NEG-07", "NEG-08", "NEG-09", "NEG-10",
    "NEG-11", "X2", "X2b",
    # --- 构造类（结构/长度/字段数）---
    "C-TRUNC-SHORT", "C-TRUNC-FIELD", "C-TRAILING", "C-EMPTY-FIELDS",
    "C-DUP-RULE", "C-FCNT-MISMATCH", "C-MAGIC-ONLY", "C-V2-TYPE01",
    "C-WIDTH-EPOCH", "C-DOMAIN-GRANTKIND", "C-NESTED-TLEN",
    # --- 第三轮 6 项值/长度/最小值反例 ---
    "C-NESTED-TYPE", "C-LEN-EVENTID", "C-LEN-OBSERVED",
    "C-MIN-EPOCH", "C-MIN-SEQ", "C-MIN-RECEIPTSEQ",
    # --- 凌翼 2026-11-12 裁定 B-1 要求的三个明确负向测试 ---
    "B1-v1-into-v2", "B1-v2-into-v1", "B1-v2-badtype",
    # --- 知微 ZB31-01：未知版本 × 三个入口 ---
    "B31-unk-ver-disp", "B31-unk-ver-v1", "B31-unk-ver-v2",
    # --- 合法正例（防误伤）---
    "TV2-81", "TV2-82", "TV2-83", "TV2-84", "TV2-85", "TV2-87",
    "V1-ATTEMPT-REF-OK",
)

# 允许的判定取值
#   【凌翼 2026-11-12 裁定 B-1】：R-V2-02e 已正式登记，
#   OBSERVED_PENDING_RULING 这一「规则号待定」判定【不再允许出现】。
#   ⇒ 若仍出现，说明实现未落实，应判 INFRA_ERROR。
ALLOWED_VERDICTS = ("PASS", "FAIL", "SKIP")
PENDING_VERDICT = "OBSERVED_PENDING_RULING"   # 仅用于检出并报错，不列入允许值
