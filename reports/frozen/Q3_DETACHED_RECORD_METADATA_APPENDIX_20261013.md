# Q3 DETACHED RECORD — EXTERNAL METADATA APPENDIX (VERSION)

**Issued by**: Coder
**Date**: 2026-10-13
**Authority**: 凌翼 LINGYI DETACHED RECORD VERSION RULING (2026-10-13)
> "XIANHUAN_SUGGESTION = ACCEPTED IN PRINCIPLE; CODER_EXTERNAL_METADATA_APPROACH = APPROVED.
>  ACTION = ADD EXTERNAL VERSION METADATA; BIND TO EXISTING RECORD + FREEZE IDENTITY.
>  MODIFY_Q3_PROVENANCE_PY = NO; MODIFY_EXISTING_DETACHED_RECORD = NO;
>  MODIFY_FROZEN_REFERENCE = NO; NEW_Q3_LINEAGE_REQUIRED = NO."

**Scope**: EXTERNAL metadata only. This file **does not** modify `q3_provenance.py`,
the existing detached record, or the frozen reference. It **references** them by hash.

**澄清（凌翼）**: 既有 detached record **没有独立的 `VERSION` 字段**,但**并非没有版本信息**
—— `Q3_LINEAGE_ID` 已含 `V1`。缺的是**显式的 detached-record 格式版本**,与 Q3 血统版本**不是同一个概念**。
本附录的 `RECORD_METADATA_VERSION = 1` 是**本附录自身**的格式版本,**不**声称旧记录原本有此字段。

---

## 元数据（机器可读块）

```text
RECORD_METADATA_VERSION = 1
RECORD_FORMAT_STATUS    = LEGACY_V1

Q3_LINEAGE_ID           = Q3_OS_ISOLATION_LINEAGE_V1

FROZEN_CODE_COMMIT      = 2c92074a9808b1c9acd5ad5a36cba7a34e472892

Q3_LINEAGE_DIGEST       = 450349115b71bc9013c7a79f91d9bdf5f1728f2cbae65b025eb35a66af56da36

DETACHED_RECORD_PATH    = reports/Q3_PROVENANCE_DETACHED_20261011.txt
DETACHED_RECORD_BYTES   = 2723
DETACHED_RECORD_SHA256  = 39d368e67465d5c7b2c40d53e4fcb7ab6aef948534452c9b75797ab04c563252

FROZEN_REFERENCE_PATH   = reports/frozen/Q3_FROZEN_REFERENCE_2c92074.txt
FROZEN_REFERENCE_SHA256 = 97c3065f0a970ba8a8cd3208a9cacf378d1ca39565b739669becf42d1ba32a98

FROZEN_REGISTRATION_PATH        = reports/frozen/Q3_DESIGN_FREEZE_REGISTRATION_20261012.md
FROZEN_ROLES_JSON_PATH          = reports/frozen/Q3_FROZEN_ROLES_2c92074.json
```

## 重要区分（不可混用）

| 哈希 | 对象 | 值 |
|---|---|---|
| **`DETACHED_RECORD_SHA256`** | **该 `.txt` 文件自身的字节** | `39d368e67465d5c7b2c40d53e4fcb7ab6aef948534452c9b75797ab04c563252` |
| **`Q3_LINEAGE_DIGEST`** | **十个 Q3 角色的 lineage digest**（**不是**文件的哈希） | `450349115b71bc9013c7a79f91d9bdf5f1728f2cbae65b025eb35a66af56da36` |

> 凌翼明令:`DETACHED_RECORD_SHA256` **必须**是对**实际文件字节**计算的结果,
> **不得**把 Q3 lineage digest 当成该文件自身的哈希。（此处二者确实不同,已分别列明。）

## 一致性检查声明

- 本附录**未**修改 `q3_provenance.py`、既有 detached record、或冻结引用。
- `DETACHED_RECORD_SHA256` 与 `FROZEN_REFERENCE_SHA256` 均由 Coder 对**实际字节**计算。
- `Q3_LINEAGE_DIGEST` 与冻结身份一致（`Q3_FROZEN_IDENTITY = OK`）。
- **将来**若要让资格校验器**强制消费** record schema version,那属**新的接口合同**,
  须放入**新版本**的记录生成与验证流程,**单独审查**,**不得**追溯修改冻结的 V1。
