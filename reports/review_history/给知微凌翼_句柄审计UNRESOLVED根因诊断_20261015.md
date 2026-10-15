# 给知微 / 凌翼 —— `HANDLE_AUDIT_UNRESOLVED` 根因诊断（接 D4 管理员重放）

**作者**: Coder（经船长转交）
**日期**: 2026-10-15
**依据**: 知微 `D4 修复独立复核` + `D4 管理员重放结果复核`（`REVIEWED_COMMIT=11eeb65`）；你的要求："定位未解析的具体 API … 在**独立诊断驱动/未冻结观察层**记录逐句柄数据 … 不要先改权限或 ACL"。
**新文件**: `afterglow_harness/q3_handle_audit_diagnostic.py`（**未冻结**观察层；**未**改 `q3_handle_audit.py`）

---

## 0. 结论一句话

**未解析的 API 是 `GetFileInformationByHandle`（`q3_handle_audit.py:168`）** —— **不是** `OpenProcess`，**不是** `DuplicateHandle`（后两者逐句柄全成功）。
**但真正的根因更深**：目标进程里被审计的 11 个"FILE 句柄"里，**没有一个指向被保护对象** —— 它们其实是 **1 个目录句柄 + 8 个 `\Device\ConDrv`（控制台驱动）句柄**。冻结实现把它们**误判为 FILE 类型**，再用 `GetFileInformationByHandle` 去读（对目录/非文件句柄必然失败），于是产出了 `unresolved=11` ⇒ `UNRESOLVED`。
⇒ **正确结论本应是 `CLEAN`**（worker 并不持有目标句柄），却因**类型判定 + 身份读取**两处缺陷被伪报为 UNRESOLVED。

---

## 1. 逐句柄实测（我的独立诊断，真跨账户 worker PID 29180）

```
controller_token_privileges: SeDebugPrivilege=absent, SeBackup=absent, SeRestore=absent
file_type_index (冻结 _file_type_index 判定): 37
summary: file_type_total=9  openprocess_fail=0  duplicate_fail=0  getfileinfo_fail=9  resolved=0  non_file_skipped=41
```
每个被判为"FILE 类型(37)"的句柄：

| handle | granted_access | OpenProcess | DuplicateHandle | GetFileInformationByHandle | NtQueryObject 名称 |
|---|---|---|---|---|---|
| 64 | 1048608 | ok | ok | **fail err=5 (ACCESS_DENIED)** | `\Device\HarddiskVolume3\…\diag_mailbox`（**目录**） |
| 68 | 1180063 | ok | ok | **fail err=1 (INVALID_FUNCTION)** | `\Device\ConDrv`（**控制台驱动**） |
| 72 | 1180063 | ok | ok | **fail err=1** | `\Device\ConDrv` |
| 80 | 1180063 | ok | ok | **fail err=1** | `\Device\ConDrv` |
| 84/88/160/164 | 1180063 | ok | ok | **fail err=1** | `\Device\ConDrv` |

**→ 失败集中在第 3 个 API（`GetFileInformationByHandle`）；前两个 API 全通过。**

---

## 2. 两处冻结实现缺陷（**未改，交你与凌翼裁**）

### 缺陷 A（主因）：`_file_type_index` 把**非文件**句柄判成 FILE 类型
- 目标进程真实持有的 file-type(37) 句柄里，名称解析出来是 **`\Device\ConDrv`**（控制台驱动）与**目录**。
- `GetFileInformationByHandle` 对这两类必然失败（err 1 / err 5）。
- ⇒ `_file_type_index`（冻结，`q3_handle_audit.py:251`）得到的 "file 类型索引 37" **不能**区分"真文件"与"控制台/目录"，于是把非文件句柄纳入审计并计入 `unresolved`。

### 缺陷 B（次因/放大器）：用 `GetFileInformationByHandle` 读 `DUPLICATE_SAME_ACCESS` 句柄
- `DuplicateHandle` 用 `DUPLICATE_SAME_ACCESS` 复制的是**原句柄的访问权**。
- 目录句柄以 `FILE_LIST_DIRECTORY` 打开、**未含 `FILE_READ_ATTRIBUTES`** ⇒ `GetFileInformationByHandle` 返回 err 5。
- ⇒ 即使类型判定正确，**按身份读**对这类句柄也不可靠。

**对照**：同一批句柄用 **`NtQueryObject(ObjectNameInformation)`**（冻结模块里**已有** `_name_of_remote_handle`）**能拿到名字** —— 说明**名称路径可用，身份路径不可用**。这是给凌翼的**具体修复方向**。

---

## 3. 为什么这**不是**"管理员重跑就会好"

- 管理员重放的 `file_handles_scanned=0 / names_unresolved=11` 与我普通权限**完全一致**。
- 我的诊断显示 **controller token 甚至没有 `SeDebugPrivilege`**（admin ≠ SeDebugEnabled）；但**即便有**，也改变不了缺陷 A（`ConDrv`/目录**本就不是文件**）。
- ⇒ **提升权限不能**把 `ConDrv` 变成文件。根因在**类型判定**，与权限无关。

---

## 4. 我给凌翼的修复建议（**不自行改冻结对象**）

按你的要求，**未改** `q3_handle_audit.py` canonical bytes。建议方向（择一，走**变更+重验流程**）：
1. **按名称判定**：对每个候选句柄用 `_name_of_remote_handle`（`NtQueryObject`）取路径；**只把"看起来是文件路径"的句柄**纳入审计；`\Device\ConDrv`、目录、无名称者**计入 `skipped_non_file`**（而非 unresolved）。
2. **按名字重开比对身份**：拿到名称后，**controller 侧重开该路径**得 OS 身份，再与被保护对象比 —— 这正是冻结合同一贯的"名称→重开→身份"套路。
3. 若仍用身份路径：对 err 5 的**目录/无属性句柄**要**单独归类**（不是 unresolved），并**保留 GetLastError**（当前被合并成 None）。

**验收**：应新增一条"worker 只持有目录/ConDrv 句柄、不持有目标文件 ⇒ 判 **CLEAN**（不是 UNRESOLVED）"的用例。

---

## 5. 交付物

- `afterglow_harness/q3_handle_audit_diagnostic.py`（**新、未冻结**）：逐句柄记录 `OpenProcess`/`DuplicateHandle`/`GetFileInformationByHandle` 的返回 + `GetLastError`，并额外尝试 `NtQueryObject` 名称、记录 controller token 的 `SeDebug/Backup/Restore` 状态。**不做裁决、不改 ACL**。
- 本次实测 JSON（真跨账户 worker）。

## 6. 状态
- `D4_01_MAILBOX_SEPARATION = VERIFIED_FIXED`（你已确认，普通+管理员均有效）。
- `BUSINESS_WORKER_HANDLE_AUDIT = UNRESOLVED`；**`ROOT_CAUSE = q3_handle_audit.py 的 file-type 判定 + 身份读取**（**已定位**，`GetFileInformationByHandle` 为失败 API；非 OpenProcess/DuplicateHandle）。
- `q3_handle_audit.py` **未改**（冻结）；如需改，走变更+重验流程。
- `FULL_REAL_RESET_ADAPTER_ACCEPTANCE = NOT_ESTABLISHED`；`REAL_EXECUTION_WIRING = NOT_AUTHORIZED`；`SCIENTIFIC_EXECUTION = MAY_NOT_START`。

> 注：这条根因**落在冻结对象** `q3_handle_audit.py` 上（不在适配器层），**需凌翼裁决**是否走冻结变更流程。我**没有**擅自修改。
