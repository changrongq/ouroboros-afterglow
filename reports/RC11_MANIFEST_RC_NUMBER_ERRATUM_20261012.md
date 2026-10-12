# RC11 MANIFEST — RC-NUMBER ERRATUM (external)

**Issued by**: Coder
**Date**: 2026-10-12
**Authority**: 凌翼 LINGYI RC11 MANIFEST REVIEW (2026-10-12, REVIEWED_HEAD `644ec5f`)
> "DISPOSITION = B — Create external RC11 erratum. Preserve the exact frozen bytes."
> "建议命名：`reports/RC11_MANIFEST_RC_NUMBER_ERRATUM_20261012.md`"
**Basis (原始核对报告)**: `review_history/RC11_MANIFEST_头尾RC编号核对_20261012.md`
**Scope**: EXTERNAL erratum only. This file does **NOT** modify any RC11 byte.

---

## 1. The defect (CONFIRMED / RECORD CONSISTENCY)

In `reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md` (frozen bytes):

| 位置 | 行 | 内容 | RC 号 |
|---|---|---|---|
| 头部·性质 | 6 | "MANIFEST 实例化版（RC11）" | RC11 |
| 头部·STATUS | 9 | `STATUS = INSTANTIATED MANIFEST (RC11) / PENDING FREEZE` | RC11 |
| 头部·修正说明 | 14 | "RC11 修正说明（…知微 RC10 独立复核…）" | RC11 |
| changelog 末条 | 528 | `v0.1-RC9 （本次）…` | RC9 |
| **底部·STATUS** | 544 | `STATUS = INSTANTIATED MANIFEST (RC9) / PENDING FREEZE` | **RC9** |

- **HEADER_RC = RC11**, **FOOTER_RC = RC9**, **CHANGELOG_LAST_ENTRY = RC9**,
  **RC10_RC11_CHANGELOG = MISSING**.
- **TWO_NUMBER_SYSTEMS_CLAIM = NOT SUPPORTED BY DOCUMENT.** 不存在"RC11=周期号、RC9=内部迭代号"
  两套编号；changelog 是单序列 `v0.1-RC2 … RC9`，RC 是**同一迭代号**。底部与 changelog **滞后**。
- **SECURITY_FAIL_OPEN_FROM_THIS_DEFECT = NOT DEMONSTRATED.** `qualification_binding` 的消费路径
  **不读**底部 STATUS 文本（只读 §十三 角色表 + detached hash），故不 fail-open。

## 2. Frozen bytes (UNCHANGED — verified at erratum time)

| Object | bytes | sha256 |
|---|---|---|
| `AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md` | 28142 | `78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059` |

`verify_manifest_binding.py` at erratum time: **BINDING_INTEGRITY = PASS**.

## 3. Disposition (凌翼 ruling)

- **RC11_FROZEN_BYTES = DO NOT MODIFY.** 本勘误为外部记录，不改底部 RC9、不改 changelog。
- **RC12_FUTURE_MANIFEST**（凌翼 指示）：
  - 使用**内部一致的 RC12 身份**；
  - **保留 RC9 历史条目**；
  - **补入有出处的 RC10、RC11 条目**；
  - 新 MANIFEST 需**新 hash + 新 qualification**。
- **Q3 / RC12 / RC11 Phase A 状态不变**；本勘误不重开任何已闭合验收，不重跑 RC11，
  不改 `qualification_binding`。

## 4. 历史意义

这不改变任何执行事实：RC11 在 `78bdb90f…` 上的独立核验（睫字节+执行、知微复核）依然成立。
缺陷**只是记录面**：头尾 RC 自称不同号、changelog 少两行。**原字节原封保留**，勘误在外部说明。
