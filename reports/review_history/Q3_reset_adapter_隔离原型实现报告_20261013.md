# Q3 reset adapter — 隔离原型实现报告（Q3_RESET_ADAPTER_INTEGRATION_V1）

**作者**: Coder
**日期**: 2026-10-13
**血统**: `Q3_RESET_ADAPTER_INTEGRATION_V1`（**独立**于 RC11 与 Q3 冻结十角色）
**授权**: 凌翼 `LINGYI Q3 RESET ADAPTER V3 REVIEW` — `DESIGN_V3 = ACCEPTED AS PROTOTYPE BASELINE`；
`ISOLATED_PROTOTYPE_IMPLEMENTATION = AUTHORIZED`。**未接线**：`REAL_EXECUTION_WIRING = NOT AUTHORIZED`。

---

## §0 新增文件（全部 NEW；**未**触碰 RC11 / Q3 冻结角色）

| 文件 | 作用 | bytes (LF) |
|---|---|---|
| `afterglow_harness/q3_reset_adapter.py` | 适配器 + `BusinessWorkerSupervisor` + 唯一裁决入口 `run_reset_transaction()` | 33303 |
| `afterglow_harness/q3_business_worker_entry.py` | **持续**业务 worker 入口（holding→release；自证访问） | 3699 |
| `afterglow_harness/test_q3_reset_adapter.py` | 三层回归（逻辑/受控负向/真实业务 worker） | 16549 |

**非吸收已证**：`q3_qualify.py:COMPONENT_MODULES` 是**显式元组**；`q3_provenance.py:Q3_EXECUTION_CRITICAL` 是**硬编码 10 元组**；全 `afterglow_harness` 无 `*.py` 目录扫描（仅 4 处 `.json` ledger glob）。⇒ 新文件**不会**被任何资格机制纳入。

---

## §1 五条实施约束的落地（凌翼 V3 REVIEW）

| # | 约束 | 落点 |
|---|---|---|
| **1** | `DURABLE_BOUNDARY_BEFORE_BUSINESS_EXECUTION` | `_stage_boundary()`（装持久 deny ACE）**先于** `_stage_business_worker()`；worker 以 `--holding` 启动、**信号 READY 后等待 release**；**仅**在 `_stage_persistent_isolation()` 证明隔离后才 `release_into_execution()` |
| **2** | `HOOK_RESULTS_ACTUALLY_CONSUMED` | `restart_worker()` 若在终态被调用 ⇒ 拒绝；`access_probe()` 反映**本事务**真实状态（不伪造 True）；RC11 `access_side_ok` **绑定本次真实业务 worker 的拒绝见证**，Q3 access 证明**另作**独立必要条件 |
| **3** | `TRUSTED_SNAPSHOT_AND_PID_BINDING` | `_stage_bind()` 把 `transaction_id / q3_run_nonce / old_worker_pid(=supervisor 权威) / protected 与 substrate 的 **OS 文件身份** / handoff,restored digest / worker pid+create_time+entry_sha` 绑成一份证据；`_assert_protected_is_substrate()` 用 **OS 文件身份**（`file_identity`），**非**字符串规范化 |
| **4** | `SINGLE_FAILURE_CONTRACT` | 唯一 `_fail()`：置 `FAILED`→清理→抛 `NotIsolatedError`；`run_reset_transaction()` 的 `except` **返回** `IntegrationOutcome(False)`（不再二次 `_fail()`），契约一致 |
| **5** | `IDEMPOTENT_CLEANUP` | `_cleanup()` 幂等（`_cleaned` 守卫）；`supervisor.terminate()` 幂等；跨账户句柄路径确认进程**真已退出**（`exit_time>0`）才返回 `TERMINATED` |

---

## §2 v3 核心（三条 ACCEPTED 修正）

- **DONE 终态**：状态机 `NEW→Q3_OK→BOUNDARY_OK→WORKER_OK→ISOLATION_OK→RC11_OK→DONE`；`DONE` **只在** `run_reset_transaction()` 全部门禁通过时设置；`Q3_OK` 等为**中间态**，**永不**作为成功消费。
- **唯一裁决入口**：`V_integration = Q3 ∧ real-reset ∧ business-worker ∧ persistent-isolation ∧ RC11 ∧ binding`。
- **REAL_RESET 门禁**：证明真实替换时，除 `r.valid is True` 外**还须** `reset_mode==REAL_RESET` ∧ `real_reset_required is True` ∧ `real_reset_ok is True`（挡 `FIRST_START` 冒充）。
- **对象绑定**：Q3 `protected` ↔ RC11 `substrate_path`（OS 同一文件）；`literal_path` **单独**保留。

---

## §3 回归结果（三层；`test_q3_reset_adapter.py`）

**总计 23 项全 PASS**（`ADAPTER_REGRESSION = PASS`；exit 0；clone 复现同结果）。

### Layer A — 逻辑单元（9 PASS）
DONE 终态 · Q3_OK 非成功 · **invalid Q3 ⇒ 集成 INVALID** · 状态 FAILED · **FIRST_START 冒充 ⇒ INVALID** · 二次调用拒绝（无陈旧复用） · Q3 异常 ⇒ INVALID · 异常后 FAILED · 清理幂等。

### Layer B — 受控负向（10 PASS；**在冻结 Q3 计算前改输入**）
- **B1** `protected≠substrate`（不同文件）⇒ 拒绝。
- **B2** **硬链接别名**（不同路径、**同一 OS 文件**）⇒ **接受**（证明用的是 OS 身份，不是字符串）。
- **B3×7** 七个门禁各自失败 ⇒ **集成 INVALID**（`real_reset_ok / clear_ok / access_ok / handle_ok / matrix_ok / dacl_restore_ok / preserve_ok`）——覆盖**全部**门禁，不止草案读的 3 个。
- **B10** 隔离未证 ⇒ 集成 INVALID（**即使 Q3 valid**）。

### Layer C — 真实业务 worker 集成（4 PASS；**真实跨账户**）
- **C2** 无口令 ⇒ **同账户 worker 被拒**（fail-closed，不假装跨账户隔离）。
- **C1** worker OS 见证 OK（**真实账户 SID `S-1-5-21-262…` ≠ 控制器**；pid+create_time 实读）。
- **C1** **持久隔离在真实业务 worker 上证明**（**worker 自己**发起读，返回 `DENIED`）。
- **C1** 终止幂等、无残留活进程。

> **诚实标注**：Layer C 在**本机 `administrator`** 下运行、以 `CreateProcessWithLogonW` 创建 **`afterglow_worker`** 子进程。
> 这是**真实跨账户**的一版原型验证。它**尚不**等于最终 Windows 验收（须由**知微独立重放** + **睫证明语义复核** + **钳星生命周期复核**）。

---

## §4 未触碰验证

- `reports/frozen/` 无改动；RC11 MANIFEST = `78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059`（28142 B，**不变**）。
- `verify_q3_freeze.py` = `Q3_FROZEN_IDENTITY = OK`（10 roles，digest `45034911…`）+ 交叉核对 OK。
- 10 个 Q3 冻结角色 + `reset.py` **零改动**。

---

## §5 待定向复核（实现后，凌翼要求）

- **睫**：证明语义 / 冻结边界（尤其 Layer B 的"改输入而失败"是否真实、`valid` 合取是否不可绕）。
- **知微**：独立 Windows 重放（Layer C 跨账户证据、DACL 时序、失败回收）。
- **钳星**：生命周期 / 失败安全（holding→release 握手、worker supervisor、句柄回收）。

`REAL_EXECUTION_WIRING = NOT AUTHORIZED`；`SCIENTIFIC_EXECUTION = MAY NOT START`。
