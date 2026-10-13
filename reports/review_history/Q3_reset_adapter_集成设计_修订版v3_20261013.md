# Q3 reset adapter — 集成设计【修订版 v3：据凌翼 V2 REVIEW 修正伪代码】

**作者**: Coder
**日期**: 2026-10-13
**状态**: DESIGN REVISION（**未接线**）。**不**修改 RC11 / Q3 冻结源码。
**v3 依据**: 凌翼 `LINGYI Q3 RESET ADAPTER — V2 REVIEW`（2026-10-13）：
- `V2_DESIGN_DIRECTION = ACCEPTED`；`V2_PSEUDOCODE_AS_WRITTEN = NOT APPROVED FOR WIRING`。
- `ISOLATED_PROTOTYPE_IMPLEMENTATION = AUTHORIZED`；`REAL_EXECUTION_WIRING = NOT AUTHORIZED`；`SCIENTIFIC_EXECUTION = MAY NOT START`。
- 七项设计选择 = DECIDED（见 §2）；`REQUIRED_V2_CORRECTIONS` 5 条（其中 #4/#5 由 #1/#2/#3 的机制覆盖，见 §1）。

> **v3 = v2 + 三处关键修正**（凌翼 §一）。v2 正文保留为历史（`Q3_reset_adapter_集成设计_修订版v2_20261013.md`），**本文件为实施基准**。

---

## §1 三处修正（凌翼 §一；这是 v3 的核心）

### 修正 #1 —— `DONE` 必须是**整笔 reset 事务**的最终成功态，而非 Q3 阶段的成功态

**v2 的缺陷**（凌翼推导，非实测）：
```
_run_once(): Q3 成功 → self._tx.state = "DONE"; return r
restart_worker(): supervisor.ensure_business_worker(...)   # ← 若此处失败
                                                          #   事务仍停在 DONE
```
⇒ **成功状态产生得太早**。

**v3 规则**：
- 取消 `_run_once()` 里的 `DONE`。`_run_once()` 只把 Q3 阶段结果**收进事务**，状态置 `Q3_OK`（**中间态，非终态**）。
- **唯一**置 `DONE` 的地方是 `run_reset_transaction()`（§1 修正 #2 的入口），且**仅当全部终态门禁通过**。
- 任一阶段失败 ⇒ `state = FAILED` ⇒ **资源清理** ⇒ **禁止复用旧 PASS**（`DONE` 不可被重新读取为 PASS）。

**`DONE` 之前必须全部完成（合取，逐项字面成立）**：
1. **Q3 证明**：`r.valid is True`（11 门合取，第 191 句）；
2. **真实业务 worker**：`worker_supervisor` 从 OS 读取并绑定的身份/生命周期见证（SID + 创建时间 + 入口代码 hash），**非** `identity_bound=True` 布尔；
3. **持续隔离见证**：独立持久边界对**真实业务 worker** 实测 `ACCESS=DENIED`（**不得**重用 Q3 探针的 `READ=DENIED`）；
4. **RC11 `verify()`**：独立成立（`RESET_VALID`）；
5. **两套 preserve 验证**：RC11 侧（`literal`+`q_raw` 前后）+ Q3 侧（`protected` 前后）**各自**成立；
6. **事务证据绑定**：事务 ID + probe/业务 nonce + run-id 映射 + 证据 hash 完整。
> 消费者**只看终态** `DONE`，**不得**从中间态 `Q3_OK` 推出任何"成功"。

### 修正 #2 —— 增加**唯一**的最终裁决入口 `run_reset_transaction()`（**不改冻结 `reset.py`**）

**问题**（凌翼）：`reset.py.verify()` 只消费 `handoff`/`restored` + `clear_side_ok`/`access_side_ok`；它**不知道** `r.valid`、业务 worker OS 见证、事务 ID。
⇒ **若别的调用者人为传入两个 `True`，原始 `verify()` 仍可能返回 `RESET_VALID`**。因此 v2 §4 "`restart_worker()` 抛异常后 `verify()` 必须不 VALID" **不能**靠现有 hook 保证。

**裁决**：**不修改冻结 `reset.py`**。由**新集成层**建立**唯一权威入口**：

$$
\begin{aligned}
V_{\text{integration}} ={}& V_{\text{Q3}} \land V_{\text{real-reset}} \land V_{\text{business-worker}} \\
&\land V_{\text{persistent-isolation}} \land V_{\text{RC11}} \land V_{\text{binding}}
\end{aligned}
$$

- 全部条件**严格成立**；任一不成立 ⇒ 入口**不输出集成 VALID**（fail-closed）。
- **防 FIRST_START 冒充**：当正在证明一次**真实替换**时，除 `r.valid is True` 外**还必须**：
  - `r.reset_mode == RESET_MODE_REAL_RESET`（`classify_reset_mode`：存在旧 worker ⇒ REAL_RESET）；
  - `r.real_reset_required is True`；
  - `r.real_reset_ok is True`。
  > 依据：`valid` 只在 `real_reset_required is True` 时才把 `real_reset_ok` 纳入合取（`q3_reset_chain.py` 573–586）；故**合法 `FIRST_START`（`real_reset_required=False`）可能 `valid=True`**，绝不能被当成"已完成 reset"。
- **§4 负向回归改测这个入口**：断言 `run_reset_transaction()` **不输出集成 VALID**；**不再**要求冻结的 `verify()` 去理解它从未接收过的证据。

### 修正 #3 —— §4 第 9 条负例**对象关系写反了**

- v2 §3 伪代码要求：`Path(protected).resolve() == Path(substrate_path).resolve()`。
- v2 §4 第 9 条却写：`literal_path ≠ protected ⇒ FAIL`。**两者不是同一条件**。
- 依据当前映射：**Q3 的 `protected` ↔ RC11 的 `substrate_path`**；`literal_path` 是**另一份必须保留的注册状态**。
- **正确负例**：`substrate_path` 与 `protected` **不对应同一受保护对象** ⇒ FAIL。
- 同时须明确 **`literal_path` 的保护要求、路径别名与文件替换问题**。
- **最终 Windows 验收**：用 **OS 文件身份核对**（VolumeSerialNumber + FileId，即 `GetFileInformationByHandle`），而**不是**仅凭字符串规范化路径推断"必然同一文件"。

---

## §2 七项裁决落实（凌翼 DECIDED）

| # | 裁决 | v3 落实 |
|---|---|---|
| **I-1 worker 类型** | **持续运行的真实业务 worker**（第一版目标）；限定生命周期与任务边界；**Q3 探针不算业务 worker**；一次性 worker 留作以后独立定义 | `worker_supervisor` 建立并**持有**长活业务 worker；`Result` 记录其真实身份与任务边界 |
| **I-2 隔离时点** | **独立、持续有效的隔离边界**（冻结 Q3 必在 `finally` 恢复 DACL ⇒ **不能**声称"直接采用退出后恢复"而不改 Q3） | 集成层在 Q3 临时 DACL 恢复后，**另建持久访问控制**隔离业务 worker；对**真实业务 worker** 实测持久 `DENIED`，**有自己的原始 OS 证据** |
| **I-3 对象绑定** | `protected` ↔ `substrate_path`；`literal_path` 单独保留并验证 | 修正 #3；`literal`/`protected` 各自建立真实对象与时序边界 |
| **valid 合取** | **接受**：`r.valid is True` 不可绕过；真实 reset 另需模式门禁；**本身不等于集成成功** | §1 修正 #2 的 $V_{integration}$ |
| **异常收敛** | **接受**：Q3 / supervisor / 证据绑定异常均 fail-closed，统一向外 **`NotIsolatedError` 或明确 INVALID**；原始类型/原因保留在**脱敏审计记录** | `run_reset_transaction()` 收敛所有异常；`except Exception → NotIsolatedError`；审计记录留存原始 |
| **worker supervisor** | **批准新增**；必须**真实持有并核验** OS 进程身份/生命周期/资源；**不接受** `identity_bound=True` 布尔就宣布合格 | supervisor 从 OS 读 SID/创建时间/入口 hash；布尔**仅作冗余**，**不是**证据 |
| **集成血统与目录** | 批准 **`Q3_RESET_ADAPTER_INTEGRATION_V1`**；可在 `afterglow_harness/` 新增，但须**验证未被 RC11/Q3 角色集合或任何资格扫描意外纳入** | §6 落地前**先证**非吸收（当前 RC11=显式 20 角色表、Q3=硬编码 10 元组，均非目录扫描） |

> **I-2 再强调**（凌翼）：持续隔离**必须针对真实业务 worker 实测**，**不得**把 Q3 探针的 `READ=DENIED` 重用一次。此安排**尚待实现与验证**，**不是**现有代码已具备。

---

## §3 修订后的伪代码（**未接线**；fail-closed；实施基准）

```python
# q3_reset_adapter.py  (NEW FILE; does NOT modify RC11 or the 10 frozen Q3 roles)
from reset import ResetController, NotIsolatedError
from q3_reset_chain import q3_reset_chain
from q3_contract import RESET_MODE_REAL_RESET

class ResetTransaction:
    """ONE reset = ONE transaction. No reuse. Failure is terminal."""
    # NEW -> Q3_OK -> WORKER_OK -> ISOLATION_OK -> RC11_OK -> DONE
    #   any step failing -> FAILED (terminal) -> cleanup; DONE is never re-read as PASS.
    STATES = ("NEW", "Q3_OK", "WORKER_OK", "ISOLATION_OK", "RC11_OK", "DONE", "FAILED", "CLOSED")

class Q3ResetController(ResetController):
    def __init__(self, *, account, password, python_exe, work_dir,
                 protected, literal_path, substrate_path,
                 clear_targets_by_category, expected_sid,
                 transaction_id, worker_supervisor,
                 old_worker_pid=None, terminate_old_worker=None, clear_action=None):
        # 修正 #3 (I-3): Q3 protected MUST correspond to the SAME protected object as RC11 substrate.
        self._assert_same_object(protected, substrate_path)   # OS file-identity, not just string
        super().__init__(literal_path, substrate_path)        # literal_path preserved separately
        self._tx = ResetTransaction(...)                      # state=NEW
        self._supervisor = worker_supervisor
        self._r = None; self._rc11 = None

    # ---- stage runners: each updates tx state, NEVER sets DONE ----
    def _run_q3(self):
        if self._tx.state != "NEW":
            raise NotIsolatedError(f"transaction not reusable: {self._tx.state}")
        try:
            r = q3_reset_chain(account=self._acct, password=self._pw, python_exe=self._py,
                               work_dir=self._work, protected=self._protected,
                               run_nonce=self._probe_nonce,          # Q3 bound nonce
                               clear_targets_by_category=self._clear,
                               expected_sid=self._sid,
                               old_worker_pid=self._old_pid,         # I-3: from supervisor, not caller
                               terminate_old_worker=self._term,
                               clear_action=self._clear_action)
        except Exception as e:
            self._fail("Q3 chain raised", e)
        if r.valid is not True:                                    # 睫第191句: THE conjunction
            self._fail(f"Q3 not valid: {r.reason}")
        # 修正 #2: REAL_RESET mode gate (only when proving a real replacement)
        if self._proving_real_replacement:
            if r.reset_mode != RESET_MODE_REAL_RESET: self._fail(f"mode={r.reset_mode} != REAL_RESET")
            if r.real_reset_required is not True:     self._fail("real_reset_required not True")
            if r.real_reset_ok is not True:           self._fail("real_reset_ok not True")
        self._r = r; self._tx.state = "Q3_OK"                      # intermediate, NOT success

    def _run_business_worker(self):
        # I-1: establish + OS-identity-bind a PERSISTENT business worker (not the probe)
        w = self._supervisor.ensure_business_worker()             # returns OS witness
        if not self._supervisor.witness_ok(w):                    # SID+start-time+entry-hash from OS
            self._fail("business worker OS witness not established")
        self._w = w; self._tx.state = "WORKER_OK"

    def _run_persistent_isolation(self):
        # I-2: REAL business worker must be DENIED on the durable boundary (own OS evidence)
        isol = self._supervisor.prove_persistent_isolation(self._w)   # fresh ACCESS attempt on the worker
        if isol is not True:
            self._fail("persistent isolation not proven on the real business worker")
        self._tx.state = "ISOLATION_OK"

    def _run_rc11_verify(self, handoff, restored):
        self._rc11 = super().verify(handoff, restored,
                                    clear_side_ok=(self._r.clear_ok is True),
                                    access_side_ok=(self._r.access_ok is True))
        if self._rc11.reset_valid is not True:
            self._fail(f"RC11 verify not VALID: {self._rc11.reason}")
        self._tx.state = "RC11_OK"

    # ---- hooks: NOT the adjudicator; delegate into the single transaction ----
    def restart_worker(self) -> None:
        self._stage_business_worker_via_tx()      # does NOT set DONE

    def access_probe(self) -> bool:
        return self._r.access_ok is True if self._r else False   # read from Q3, never fabricate

    # ---- THE single authoritative entry ----
    def run_reset_transaction(self, handoff, restored) -> "IntegrationOutcome":
        """Only place that may set DONE — after ALL final gates."""
        try:
            self._run_q3()
            self._run_business_worker()
            self._run_persistent_isolation()
            self._run_rc11_verify(handoff, restored)
            self._bind_evidence()                 # 修正 #1 item 6: tx id + nonce + run-id map + hashes
            self._tx.state = "DONE"               # FINAL success only here
            return IntegrationOutcome(integration_valid=True, ...)
        except NotIsolatedError as e:
            self._fail(str(e), e)                 # already FAILED inside; converges
        except Exception as e:
            self._fail("integration raised", e)   # fail-closed convergence
        # if here: not VALID
        return IntegrationOutcome(integration_valid=False, reason=self._tx.fail_reason, ...)

    def _fail(self, msg, exc=None):
        self._tx.state = "FAILED"
        self._tx.fail_reason = msg
        self._cleanup()                           # release worker/probe/handles
        raise NotIsolatedError(msg) from exc
```

> **注意**：上为**设计**伪代码，**未落盘为可运行代码**（`ISOLATED_PROTOTYPE_IMPLEMENTATION = AUTHORIZED`，须在隔离中实现）。

---

## §4 负向回归（**改测 `run_reset_transaction()` 入口**；凌翼修正 #2）

**两条断言**：① `run_reset_transaction()` **不输出集成 VALID**（`integration_valid is not True`）；② 内部 `restart_worker()` 路径抛 `NotIsolatedError`。
**注入方式**（第 188 句）：**在冻结 Q3 实际计算之前**改变**输入**，让 Q3 **真的跑出一次失败**；**不许**构造 `valid=False` 塞进去"验比较器"。

| # | 注入 | 期望 |
|---|---|---|
| 1 | `real_reset_ok=False`（REAL_RESET） | 入口不 VALID（正是凌翼 B2 那格） |
| 2 | `clear_ok=False`（Q1） | 入口不 VALID |
| 3 | `access_ok=False` | 入口不 VALID；另验 **RC11 侧是否有人接 `access_probe` 返回值**（第 152 句姐妹格：返回值必须被消费） |
| 4 | `handle_ok=False` | 入口不 VALID（知微反例） |
| 5 | `matrix_ok=False` | 入口不 VALID（知微反例） |
| 6 | `dacl_restore_ok=False` | 入口不 VALID（知微反例） |
| 7 | `preserve_ok=False` | 入口不 VALID（知微反例） |
| 8 | `access_ok=False` 时 RC11 侧**无人接** `access_probe` 返回值 ⇒ 断言失败 | 暴露"返回值没人接" |
| 9 | **`substrate_path` 与 `protected` 不对应同一受保护对象** ⇒ FAIL | **修正 #3**：对象关系负例（**非** `literal≠protected`） |
| 10 | **合法 `FIRST_START`**（`real_reset_required=False`，`valid=True`）被当"已完成 reset" ⇒ FAIL | 修正 #2：模式门禁防止 FIRST_START 冒充 |
| 11 | 业务 worker 已启动、随后隔离验证失败 ⇒ 须**及时终止 + 句柄关闭 + 失败产物不可再被消费** | 修正 #1 + 凌翼 §三 |

---

## §5 测试三层（凌翼 §三：保留 v2 方向，修正验收目标）

| 层次 | 能证明什么 | **不能**替代什么 |
|---|---|---|
| **逻辑单元测试** | 事务状态机、返回值消费、异常处理、重复调用与缓存拒绝 | 真实进程隔离 |
| **受控 Windows 负向测试** | 在冻结 Q3 实际计算**之前**改测试输入，验证失败**传播至集成裁决入口** | 全部业务生命周期 |
| **真实业务 worker 集成测试** | 真实替换、SID、代码身份、长期隔离、ACL 时序、失败回收、RC11 结果绑定 | **最终科学实验授权** |

**明令禁止**：用 mock 让 supervisor 返回 `True`，再宣布真实 worker 身份与隔离已验证。
知微 **W00–W15** 矩阵作为**集成测试需求**保留（原则接受），归入三层之一，**不**用合成通过替代 OS 级证明。

---

## §6 `Q3_RESET_ADAPTER_INTEGRATION_V1`（独立血统；**须先证非吸收**）

- **新文件**（`afterglow_harness/`）：`q3_reset_adapter.py` + 业务入口 + 独立测试 + 集成角色清单。
- **父身份保持原值**：RC11 MANIFEST `78bdb90f…`、Q3 digest `45034911…`（**不变**）。
- **先证非吸收**：确认 RC11 角色集合 / Q3 硬编码 10 元组 / 任何资格扫描**均不会**把适配器目录吸进 ⇒ hash/MANIFEST 不变。
- **绑定**：RC11 冻结 hash + Q3 十角色 hash + 适配器源码/测试 hash + 原始证据。

---

## §7 状态（据凌翼 V2 REVIEW）

```
Q3 reset adapter · v3 (伪代码修正)
架构方向           = ACCEPTED
七项设计选择       = DECIDED
§3 伪代码          = 修正后实现（本文件）
隔离原型实现       = AUTHORIZED（在隔离中；新文件）
真实执行接线       = NOT AUTHORIZED
三位审查者         = 代码落地后定向复核
Q3_DESIGN_FREEZE   = UNCHANGED
RC11_FROZEN_BYTES  = UNCHANGED
RC12               = SEPARATE
SCIENTIFIC_EXECUTION = MAY NOT START
```

**下一步**（Coder）：以**新文件**在隔离中实现 v3 原型（§3），附 §4 负向回归 + §5 三层测试；随后交**睫（证明语义/冻结边界）· 知微（独立 Windows 见证）· 钳星（生命周期/失败安全）** 定向复核。
**不需重跑已冻结 Q3**；新证据只针对**新增适配器 + 真实业务 worker**。
