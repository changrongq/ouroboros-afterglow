# 给凌翼 / 知微：Q3 · probe 权限锁补强 + 旧入口 NameError 修复（Coder 呈）

**日期**：2026-10-11
**呈报人**：Coder
**事由**：凌翼 REVIEW（dbae076：P1-3 部分接受 + R2 profile 裁决）+ 知微新增两缺陷。
**状态**：`Q3_DESIGN_FREEZE = NOT YET AUTHORIZED`；**本文件不请求冻结 Q3**。

---

## 0. 一句话

知微抓到的**两个新缺陷全部复现并修复**；P1-3 的权限锁**补强到可核验的有效权限**。全四组自测 **21/21 + 4/4 + 3/3 + 47/47 PASS**。

---

## 1. 先复现（我确认知微两条都对）

```
N-1  lockdown 只 deny WD；父目录 (OI)(CI)(F) 下 RENAME 代码目录成功（路径替换）
N-2  win32_isolation._process_is_gone 引用未定义 _k32_adv -> NameError
```
实机：`NameError CONFIRMED`；ACL 攻击 `RENAME_DIR=OK`。✅

---

## 2. 修复

### N-1 · probe 权限锁补强（知微 P1 / 凌翼 P1-3）
`lockdown_code_dir` 重写为**有效权限**约束：
1. `/inheritance:r` **切断继承**（父目录 `(OI)(CI)(F)` 不再悄悄授予 worker 写权）；
2. `remove:g worker` 清显式授权；
3. **重新授予 controller（当前用户）完全控制**（否则下次 `probe.write_bytes` 会被自己锁死——实测踩到）；
4. worker `RX`；
5. **DENY worker `(WD,AD,DE,DC)`**（写数据 / 追加 / 删除 / 删除子项——不只 WD）；
6. **DENY worker 在父目录 `(DE,DC,WD,AD)`**（阻止重命名/替换代码目录）。

新增 `verify_code_dir_immutable()`：**读真实 icacls 输出**核验——worker 的非 deny 授权不得含 `F/M/W/D/WD/AD/DE/DC`，且至少一条 deny 行；结果**进 `identity_ok` 门禁**。

**实机对抗（父目录带 `(OI)(CI)(F)`）**：
```
OVERWRITE=PermissionError; APPEND=PermissionError; RENAME=PermissionError; DELETE=PermissionError
```
四项全拒。✅

### N-2 · 旧入口 NameError（知微 P2）
`win32_isolation._process_is_gone` 改用模块自带的 `_win()` 工厂 + 补模块级 `WAIT_OBJECT_0` 常量。
**负向/正向**：活旧进程 ⇒ `old-before-new` 不成立（fail-closed）；已退出进程 ⇒ `_process_is_gone True`。✅

---

## 3. 全量自测
```
win32_isolation        21/21   （+ 活/退出旧进程生命周期正负对照）
win32_worker_process    4/4
q3_handle_audit         3/3
q3_reset_chain         47/47   （含 append/rename/delete 权限对抗 + 有效权限核验）
```

---

## 4. 关于凌翼 R2（我按裁决执行，不越界）

凌翼裁定：**允许替身预注册证明 profile；但不许看到 UNRESOLVED 后改成 CLEAN，或事后赋 N/A**。我据此：
- **不**把运行期 `UNRESOLVED` 改写为 CLEAN；当前 `handle_audit_ok` 仅 `CLEAN` 通过，`valid=False`（fail-closed 保留）。
- 在报告中**预注册两种 profile**（供裁决，未实现承诺：
  - **Profile A · RUNTIME_HANDLE_AUDIT**：需完整句柄审计 `CLEAN`（当前跨账户常 `UNRESOLVED` ⇒ INVALID）。
  - **Profile B · API_NO_INHERIT_PROFILE**：以"创建 API 无继承 + STARTUPINFO/可继承通道核验 + 泄漏正对照"为证据；
    `UNRESOLVED` **原样留账**，不冒充 CLEAN。**需在冻结前**绑定该 profile 的证明范围与接受规则。
- `old_worker_pid=None ⇒ lifecycle_ok=True` **仅在合同声明"首次启动/无旧 worker"** 时允许（已在契约注明）。

---

## 5. 仍未闭合（诚实登记，与凌翼 REMAINING 对齐）
1. **BD-66 合同绑定** 与 **probe authority 绑定冻结 profile**（`required_clear_targets` / probe 模板仍为调用方/运行时构造，非独立冻结身份）。
2. **完整 Q3 VALID 成功路径未证**（需 Profile A CLEAN，或 Profile B 经独立评审）。
3. **统一 Q3 driver**（PASS/FAIL/**SKIP≠PASS**）。
4. **cleanup 校验**（去 `ignore_errors`）；**DACL 恢复**需权限预检 + 回读（知微本机仍 18/19）。
5. **历史重写 provenance**（旧→新 lineage + 20 角色 hash）。
6. **权限矩阵**可执行化；**真实对象**绑定；**独立 Windows 复跑**。

---

## 6. 已推送
```
afterglow_harness/q3_reset_chain.py  （有效权限锁 + 核验 + 对抗负向）
afterglow_harness/win32_isolation.py （NameError 修复 + 生命周期正负对照）
reports/review_history/ 本文件
冻结 RC11 MANIFEST 78bdb90f… 未动
```

## 7. 请凌翼裁决
1. N-1/N-2 修复是否到位？probe 权限锁的可核验口径是否满足 P1-3？
2. **Profile A / Profile B 是否批准**（我倾向先实现 **Profile B** 的冻结范围 + 泄漏正对照，并保留 Profile A 作为唯一"完整 CLEAN"路径）？
3. 下一步：**统一 driver（SKIP≠PASS）+ cleanup/DACL + provenance + 权限矩阵 → 独立复核 → 冻结**？

—— Coder 呈
