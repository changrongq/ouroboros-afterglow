# Q3 reset adapter — 集成设计【修订版 v2】（据凌翼裁决 + 睫/知微/钳星定向评审）

**作者**: Coder
**日期**: 2026-10-13
**状态**: DESIGN REVISION（**未接线**）。**不**修改 RC11 / Q3 冻结源码。
**依据**:
- 凌翼 LINGYI Q3 RESET ADAPTER DESIGN REVIEW（2026-10-13）：`ADAPTER_DESIGN_DIRECTION = ACCEPTED`；
  `CURRENT_HOOK_PSEUDOCODE = NOT APPROVED FOR REAL WIRING`；`NEW INTEGRATION LINEAGE = REQUIRED`；
  `ADAPTER_IMPLEMENTATION_IN_ISOLATION = MAY PROCEED`；`REAL_EXECUTION_WIRING = PENDING DESIGN REVIEW`。
- 睫：11 个"须字面 True"只被读了 3 个、**`valid` 从未被读**（第 191 句）；集成血统独立但 `literal_path vs protected` 无等值检查（第 175 句第四处）；Profile B 范围叙述预支。
- 知微：4 项 P1（A 真实业务 worker / B 持续隔离与 DACL 时点 / C INVALID→VALID 桥接 / D 事务边界）；纯逻辑**实测** 5 个反例。
- 钳星：生命周期不对齐（短命 probe vs 长活业务 worker）、`_last` 失败重跑语义未定、异常未收敛、**需 worker supervisor**、资源回收。

---

## §0 三处"必须读的"（把三位评审的收敛点钉死）

1. **`valid` 是唯一合取** —— 新适配器的成功条件**必须**是 `r.valid is True`（第 191 句），
   **不得**拆成几个字段分开消费。
2. **生命周期语义差异**（凌翼 + 钳星）：`run_worker_attested()` 是**短命探针**、等其退出；
   而 `ResetController.restart_worker()` 语义期待**持续存在的业务 worker**。**不能**拿短命探针替代业务 worker。
3. **前三次"报告过 = 修过"的教训**（第 152 句四次形态）：apply_j 从未调用 / 守卫从未被推 / 返回值没人接 / **`valid` 从未被读**。
   ⇒ 新适配器**必须**有**负向回归实跑**（注入 Q3 失败，看 RC11 是否跟着失败），**不许**靠构造 `r.valid=False` 去"验比较器"（第 188 句）。

---

## §1 五项裁决的落点（凌翼）

| # | 裁决 | 落点 |
|---|---|---|
| **Q1** clear-side | `r.clear_ok` 可作 RC11 clear-side 证据，**但必须先 `r.valid is True`** | 只在 `r.valid is True` 之后，才把 `r.clear_ok` 传 `verify(clear_side_ok=...)`；**绝不**仅凭 `clear_ok` 宣布合格 |
| **Q2** preserve | **两套都保留、合取** | RC11 比较 `literal`+`q_raw` 前后快照；Q3 比较 `protected` 前后字节。**建立两者对应的真实对象与时间边界**，互不替代 |
| **Q3** run-id | **打通关联，不混为一个值** | 唯一**事务 ID** + 唯一 **probe/业务 nonce**，记录映射；`Q3_RUN_ID` 仍独立；**禁止消费旧结果** |
| **Q4** Profile | **冻结合同为唯一权威** | 只**读取并记录** `API_NO_INHERIT_PROFILE v1.0`；**不得**运行后动态挑 A/B，**不得**扩大 Profile B 声明 |
| **Q5** 测试 | **新文件、独立集成血统** | 适配器 + 测试**拥有独立可追溯的集成版本与证据身份**；**不并入** Q3 已冻结十角色 |

---

## §2 三个集成问题的处置（凌翼点名；归**新集成层**，不改冻结 Q3）

### I-1 新业务 worker 的生命周期（谁启动/持有/证明）
- **新增 `worker_supervisor`**（钳星判断"要"）：负责**启动、持有 PID/句柄、证明身份与权限、终止、回收**真实业务 worker。
- `restart_worker()` 成功返回的**精确含义** = **一个持续存在的真实业务进程已建立、且其身份（SID/创建时间/入口代码 hash）已由 observer 从 OS 读取绑定**。
- **不得**用短命 probe 冒充。
- **待凌翼选**（知微 P1-A 给了两型）：**常驻业务 worker** vs **一次性业务 worker**（须证明业务确实在该受限实例内完成并绑定其退出/输出）。

### I-2 隔离在返回后是否仍成立（DACL 恢复时点）
- 冻结 Q3 在 `finally` 恢复 `protected` 的原始 DACL —— 对 PoC 异常安全正确，但**业务持续隔离必须另行证明**。
- **写清**：**哪个对象的哪层 ACL，在哪个阶段恢复**（知微给了两类安排，须**明确选择**）。
- **不得**拿探针运行期的 `READ=DENIED` 证明之后一直 DENIED。
- 测试用**阶段握手/屏障**控制时序，**不靠 sleep 猜**。

### I-3 RC11 与 Q3 的状态对象绑定
- 必须明确：**哪些对象是受保护状态、哪些是待清除对象**，以及**两个控制器观察的是不是同一次 reset**。
- **`literal_path`/`substrate_path` 与 `protected` 的对应关系必须显式建立并检查**（睫第 175 句第四处）：**若 `protected` ≠ 受保护状态对象 ⇒ 直接 FAIL**，不得各自验一半。
- **`old_worker_pid`/`terminate_old_worker` 由谁传入**：若由**被验证的一方**（RC11 reset 流程）传入 ⇒ 命中第一百五十八句（被审问者不能替审问者写证词）。须由**独立 supervisor/事务层**持有，或**如实标 PARTIAL**。

---

## §3 修订后的适配器契约（**未接线**；伪代码，fail-closed）

```python
# q3_reset_adapter.py  (NEW FILE; does NOT modify RC11 or the 10 frozen Q3 roles)
from reset import ResetController, NotIsolatedError
from q3_reset_chain import q3_reset_chain

class ResetTransaction:
    """ONE reset = ONE transaction object. No reuse; failure is terminal."""
    STATES = ("NEW", "RUNNING", "DONE", "FAILED", "CLOSED")

class Q3ResetController(ResetController):
    """Adapter: ResetController hooks backed by the frozen Q3 chain, in ONE transaction."""

    def __init__(self, *, account, password, python_exe, work_dir, protected,
                 literal_path, substrate_path,               # RC11 objects
                 clear_targets_by_category, expected_sid,
                 transaction_id, worker_supervisor,           # NEW: independent supervisor
                 old_worker_pid=None, terminate_old_worker=None, clear_action=None):
        # I-3: the RC11 protected-state object and the Q3 protected path MUST be the SAME object.
        if Path(protected).resolve() != Path(substrate_path).resolve():
            raise NotIsolatedError("literal/substrate vs protected: OBJECT MISMATCH (I-3 / 第175句)")
        super().__init__(literal_path, substrate_path)
        self._tx = ResetTransaction(...)                  # NEW/RUNNING/DONE/FAILED/CLOSED
        self._supervisor = worker_supervisor              # owns the business-worker lifecycle
        self._result = None

    # ONE transaction; no second run; failure is terminal (钳星 Q2 + 知微 P1-D)
    def _run_once(self):
        if self._tx.state == "DONE":
            return self._result                          # idempotent SAME-request only
        if self._tx.state in ("RUNNING", "FAILED", "CLOSED"):
            raise NotIsolatedError(f"transaction not reusable: {self._tx.state}")
        self._tx.state = "RUNNING"
        try:
            r = q3_reset_chain(account=self._acct, password=self._pw, python_exe=self._py,
                               work_dir=self._work, protected=self._protected,
                               run_nonce=self._probe_nonce,               # Q3: bound nonce
                               clear_targets_by_category=self._clear,
                               expected_sid=self._sid,
                               old_worker_pid=self._old_pid,              # I-3: from supervisor, not caller
                               terminate_old_worker=self._term,
                               clear_action=self._clear_action)
        except Exception as e:                                        # 钳星 Q3: converge ALL to NotIsolatedError
            self._tx.state = "FAILED"
            raise NotIsolatedError(f"Q3 chain raised: {type(e).__name__}: {e}") from e
        self._result = r
        if r.valid is not True:                                       # 睫第191句: THE one conjunction
            self._tx.state = "FAILED"
            raise NotIsolatedError(f"Q3 not valid: {r.reason}")
        self._tx.state = "DONE"
        return r

    def restart_worker(self) -> None:
        r = self._run_once()
        # I-1: a REAL business worker must now exist (supervisor-established), NOT a short probe.
        self._supervisor.ensure_business_worker(identity_bound=(r.identity_ok is True))

    def access_probe(self) -> bool:
        r = self._run_once()
        return r.access_ok is True

    # NOTE: caller must also run RC11 verify(); this adapter does NOT replace it.
```

### 3.4 语义桥接（诚实标注，删掉未证成的声称）
- ❌ **删去**原 §3.1 "使有真实实现" ⇒ 改为 **"使两 hook 由一次 Q3 事务**支撑**；但真实业务 worker 由独立 supervisor 建立（I-1）"**。
- ❌ **删去**原 §3.1 "不损失 Q3 的证据强度" ⇒ 这是**声称不是论证**（睫第 171 句）；改为：
  **"成功条件 = 本次 `r.valid is True` ∧ RC11 `verify()` 成立 ∧ 独立业务 worker 见证成立 ∧ 证据绑定完整（合取，不可互相覆盖）"**。

---

## §4 必做的负向回归（睫要求；**注入 Q3 失败，验推导器**，非篡改结论）

每例一条用例；**两条断言都要**：① `restart_worker()` **抛 `NotIsolatedError`**；② `reset.py.verify(...)` **不返回 VALID**。

| # | 注入 | 备注 |
|---|---|---|
| 1 | `real_reset_ok=False`（REAL_RESET） | 正是凌翼 B2 要的那格 |
| 2 | `clear_ok=False` | Q1 |
| 3 | `access_ok=False` | 另验 **RC11 侧是否有人接 `access_probe` 返回值** |
| 4 | `handle_ok=False` | 知微反例 |
| 5 | `matrix_ok=False` | 知微反例 |
| 6 | `dacl_restore_ok=False` | 知微反例 |
| 7 | `preserve_ok=False` | 知微反例 |
| 8 | `access_ok=False` 时 RC11 侧**是否有人接** access_probe 返回值 ⇒ 无人接 ⇒ 断言失败 | 第 152 句姐妹格 |
| 9 | `literal_path ≠ protected` ⇒ **必须 FAIL** | 第 175 句第四处 |

> **注意（第 188 句）**：这些用例**不能**靠"造一个 `valid=False` 塞进去"来验（那只验比较器）。
> 必须**让 Q3 真的跑出一次失败**（改**它算之前**的那份输入），再观察 RC11 是否跟着失败。

---

## §5 测试矩阵（接知微 W00–W15，作为**待实现/待实机**要求）

采用知微 §4 的 W00–W15 全矩阵（身份与前提 / 真实业务正常路径 / 两次真实替换 / 持续隔离与 DACL 恢复 / 读写正反对照 / 业务对象覆盖 / 句柄与输出渠道 / 单门禁失败 / 顺序缓存重复 / 并发重入 / 绑定变异 / 启动前失败 / 启动后失败 / preserve 时间窗 / 失败回收重试 / 无凭据与环境分层）。
- mock/合成**仅**用于消费者与状态机反例；**身份/权限/持续运行/进程清理必须另有 Windows 原始事件**。
- 产物名区分 **`Q3` 组件资格** 与 **`ADAPTER_INTEGRATION` 集成结果**；**不**把旧 `FULL_VALID_SUCCESS_PATH` 自动升级为"业务集成通过"。

---

## §6 新集成血统（`Q3_RESET_ADAPTER_INTEGRATION_V1`）——**须独立**

- **新文件**：`q3_reset_adapter.py` + 业务入口 + 独立测试 + 集成角色清单。
- **父身份保持原值**：RC11 MANIFEST `78bdb90f…`、Q3 digest `45034911…`（**不变**）。
- **新增代码必须有身份**（字节 hash），且**不被吸进** RC11 或 Q3 冻结集合。
  - ⚠️ 待确认（睫）：**适配器落在哪个目录**？若某资格集合是**目录扫描式** ⇒ 会被吸进 ⇒ MANIFEST/hash 可能变。**须先确认**（RC11 是显式 20 角色表、Q3 是硬编码 10 元组 ⇒ 当前均**非**目录扫描，但落地前须再证）。
- **绑定**：RC11 冻结 hash + Q3 十角色 hash + 适配器源码/测试 hash + 原始证据。

---

## §7 请凌翼裁决（**接线前**）

1. **I-1 生命周期**：选 **常驻业务 worker** 还是 **一次性业务 worker**（知微 P1-A 两型）？
2. **I-2 DACL 时点**：选哪一类安排（独立持续边界 / 退出后才恢复）？
3. **I-3 受保护对象**：`literal/substrate` 与 `protected` 的**显式对应**如何定？`old_worker_pid` 由谁传入（不得由被验证方）？
4. **`valid` 合取**：确认 `restart_worker()` 以 **`r.valid is True`** 为唯一成功门（第 191 句）？
5. **异常收敛**：确认适配器把 Q3 抛出的异常**统一收敛成 `NotIsolatedError`**（钳星 Q3）？
6. **supervisor**：确认**新增** `worker_supervisor`（钳星 Q4）？
7. **集成血统目录**：确认适配器目录**不**被任何资格集合扫描吸收（睫）？

> Coder 不自行接线、不自行冻结。**待凌翼对 §7 裁定后**，再以**新文件**在隔离中实现（`ADAPTER_IMPLEMENTATION_IN_ISOLATION = MAY PROCEED`），
> 并附 §4 负向回归 + §5 矩阵；随后交**睫（证明语义/冻结边界）· 知微（独立 Windows 见证）· 钳星（生命周期/失败安全）** 定向收口。
> `REAL_EXECUTION_WIRING = PENDING DESIGN REVIEW`；`SCIENTIFIC_EXECUTION = MAY NOT START`。
