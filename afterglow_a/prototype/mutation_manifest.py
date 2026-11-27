# -*- coding: utf-8 -*-
"""变异登记清单 —— 独立于执行计划（知微 2026-11-27）

为什么单独一份
--------------
知微 2026-11-27 指出：

    「main 遍历 MUTATIONS，随后从同一个 MUTATIONS 生成 expected_ids。
      预期没有从 rows 反推，但【预期与执行计划仍同源】。」

    实测：给真实 main 的可执行列表仅去掉 I14（不补副本），
          14 项照常真跑 ⇒ COMPLETE / 0，manifest_ok=True，missing=[]

    ⇒ 这是未关闭的一格。

所以本文件是【独立登记】：它不是从 MUTATIONS 生成的，
执行列表改动了本文件没跟上 ⇒ 对账时报 missing / unexpected ⇒ PARTIAL。

维护规则
--------
① 新增变异：先改本文件，再改 test_mutations_importance.py 的 MUTATIONS。
   两处不一致时判 PARTIAL（不是 FAIL —— 它说明的是登记没跟上）。
② 删除变异：两处同时删。只删执行列表时，本文件仍列它 ⇒ missing ⇒ PARTIAL。
③ 本文件 ID 必须唯一。重复会让判定函数报 expected_duplicated。
"""

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
