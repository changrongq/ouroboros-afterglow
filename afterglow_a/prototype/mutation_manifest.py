# -*- coding: utf-8 -*-
"""变异登记清单 —— 独立于执行计划，且带【内容身份】

凌翼 2026-11-27 裁定 §3.1：
    「固定经审查的 mutation manifest 身份，
      防止应跑清单与执行计划同步缩水而不报警。」

知微 2026-11-27 的判断（这一项停在哪）：
    「独立名册也不用再引出『谁来证明名册的名册』。
      等大家事前确认某一版本的名册，我们就把它当作这轮公开的起点，
      只验证后面的执行是否与它相符。
      有界保证的意义，也包括知道在哪里可以放心停笔。」

⇒ 本文件只做两件事：
    ① 名册内容有稳定摘要（manifest_sha256）
    ② 摘要被冻结在【经审查的值】里（REVIEWED_MANIFEST_SHA256）
  ⇒ 名册被改（增/删/改序）而未重新审查 ⇒ 摘要不符 ⇒ 报警。
  ⇒ 不再追问「谁证明这个摘要」—— 它由审查确认，是这轮的起点。

为什么这能防「同步缩水」
------------------------
    执行列表与名册同时删一项 ⇒ 名册摘要变了 ⇒ 与冻结值不符 ⇒ PARTIAL。
    ⇒ 除非有人【同时】改名册并更新 REVIEWED_MANIFEST_SHA256，
      而那一步是显式的、diff 里看得见的。

维护规则
--------
① 新增/删除/改序变异：
     a. 改 REGISTERED_MUTATION_IDS
     b. 运行 `python mutation_manifest.py --emit` 取得新摘要
     c. 把新摘要填进 REVIEWED_MANIFEST_SHA256，
        并在 REVIEW_LOG 追加一行（日期 + 摘要前 12 位 + 原因）
   ⇒ 只做 a 不做 c ⇒ 摘要不符 ⇒ PARTIAL（不会静默通过）
② 顺序也算内容：调整顺序即视为改动，需重新审查。
③ 本文件 ID 必须唯一。
"""
from __future__ import annotations

import hashlib
import json
import sys

#: 本轮应跑的变异 ID。与 test_mutations_importance.py 的 MUTATIONS 一一对应。
REGISTERED_MUTATION_IDS = (
    "I1",    # B1 排除条件被删掉
    "I2",    # B1 排除条件放宽（只排 first_person）
    "I3",    # exclude 参数被忽略
    "I4",    # 空分母判据失效
    "I5",    # 空分母仍返回全部候选
    "I6",    # 合成事件流不校验 record_id 存在性
    "I7",    # 合成事件流不拒绝完全重复事件
    "I8",    # 未知规则被静默忽略
    "I9",    # NOT_EVALUABLE 分支不标合成测量
    "I9b",   # EVALUATED 分支不标合成测量
    "I10",   # 空分母比例返回 0 而非 None
    "I11",   # B3 排除只看 basis_conflict 不看 observed_origin
    "I12",   # 显式范围允许重复 ID
    "I13",   # 显式范围静默丢弃未知 ID
    "I14",   # 不可核验率不计「从未观测」
)

#: 目标 case 映射，仅供人读；判定不依赖它。
REGISTERED_TARGETS = {
    "I1": ("A3-1a", "A3-1c", "A3-1d", "A3-1e"),
    "I2": ("A3-1d", "A3-1e"),
    "I3": ("A3-2a2", "A3-3a", "A3-3b"),
    "I4": ("A3-5a",),
    "I5": ("A3-5a",),
    "I6": ("A3-2b",),
    "I7": ("A3-2c",),
    "I8": ("A3-3c",),
    "I9": ("A3-6a2",),
    "I9b": ("A3-6a", "A3-6e"),
    "I10": ("A3-6d",),
    "I11": ("A3-1e",),
    "I12": ("A3-7a",),
    "I13": ("A3-7b",),
    "I14": ("A3-7d",),
}


def manifest_content():
    """参与摘要的内容 —— **顺序也算**（调整顺序即改动）。

    ⚠ 不含 REGISTERED_TARGETS：目标映射是注释性的，
      改它不该改变「今天该跑哪些变异」这件事。
    """
    return list(REGISTERED_MUTATION_IDS)


def manifest_sha256():
    """名册内容的稳定摘要。"""
    payload = json.dumps(manifest_content(), ensure_ascii=False,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


#: 经审查固定的名册摘要。
#:
#: ⚠ 只能由【显式审查】更新 —— 改名册而不改它 ⇒ 摘要不符 ⇒ PARTIAL。
#:   这不是「谁来证明名册的名册」，而是「这轮公开的起点」
#:   （知微 2026-11-27）。
REVIEWED_MANIFEST_SHA256 = (
    "e172ac40fa9cd73eb89019a7eadd5caeac59cacca08d72207319b53a83548dcd"
)

#: 审查日志 —— 每次更新 REVIEWED_MANIFEST_SHA256 必须追加一行。
#:
#: ⚠ 本日志只记录「摘要何时被谁固定」，不参与判定。
REVIEW_LOG = (
    ("2026-11-27", "e172ac40fa9c",
     "初始固定：15 项变异（I1-I14 + I9b），与本轮 MUTATIONS 逐项对应。"
     "凌翼 2026-11-27 裁定 §3.1。"),
)


def check_manifest_identity():
    """核对当前名册摘要与审查值是否一致。

    返回 dict：
      consistent / current / reviewed / reviewed_initialized /
      n_items / unique / duplicated / note
    """
    cur = manifest_sha256()
    ids = list(REGISTERED_MUTATION_IDS)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    initialized = (REVIEWED_MANIFEST_SHA256 != "PLACEHOLDER")
    consistent = initialized and (cur == REVIEWED_MANIFEST_SHA256)

    note = ""
    if not initialized:
        note = ("REVIEWED_MANIFEST_SHA256 未初始化 ⇒ 名册身份未固定 ⇒ "
                "至多 PARTIAL（凌翼 2026-11-27 §3.1）")
    elif not consistent:
        note = ("名册内容与审查值不符 ⇒ 名册被改过而未重新审查 ⇒ 至多 PARTIAL。"
                "若为有意变更，按维护规则 ①c 更新摘要并记 REVIEW_LOG。")
    elif dup:
        note = "名册 ID 有重复：%s" % dup

    return {
        "consistent": consistent,
        "current": cur,
        "reviewed": REVIEWED_MANIFEST_SHA256,
        "reviewed_initialized": initialized,
        "n_items": len(ids),
        "unique": not dup,
        "duplicated": dup,
        "note": note,
    }


if __name__ == "__main__":
    info = check_manifest_identity()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    if "--emit" in sys.argv:
        print()
        print("当前摘要（填进 REVIEWED_MANIFEST_SHA256）：")
        print("    " + info["current"])
        sys.exit(0)
    sys.exit(0 if info["consistent"] and info["unique"] else 1)
