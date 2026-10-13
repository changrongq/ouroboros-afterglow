# Q3 reset adapter — 集成设计与接口草图（只读设计,不动冻结源码）

**作者**: Coder
**日期**: 2026-10-13
**依据**: 凌翼 Q3 DESIGN FREEZE RULING 之"后续"项 ——
> "Q3 的实际 reset adapter 集成和冻结后最终验收,仍须按照原定步骤独立处理。"
**状态**: 设计草案（DESIGN DRAFT）。**不**修改任何冻结源码。

---

## §1 关键约束（先钉死边界）

| 对象 | 能否改 |
|---|---|
| **RC11 20 角色**（含 `reset.py`、`harness_constants.py`） | ❌ 冻结,不得改 |
| **Q3 10 冻结角色**（digest `45034911…` @ `2c92074`） | ❌ 冻结,不得改 |
| **`reset.py` 的两个 hook**（`restart_worker` / `access_probe`） | ❌ 属 RC11,不改其文件 |
| **新适配器文件**（本设计产物） | ✅ 可新建（独立于以上两者） |

- 已核实:`reset.py` ∈ RC11 20 角色 ⇒ **只能"接",不能"改"**。
- 集成方式:**组合(subclass/compose)**——新适配器**继承 `ResetController` 并覆写两个 hook**,
  内部**调用**冻结的 `q3_reset_chain()`。**不触碰** `reset.py` 与 10 个 Q3 冻结文件。

## §2 现有接口（只读探查）

`reset.py`（RC11,冻结）暴露:
```python
class ResetController:
    def restart_worker(self) -> None:   # 默认 raise NotIsolatedError
    def access_probe(self)  -> bool:    # 默认 raise NotIsolatedError
    def capture_handoff(self) -> StateSnapshot
    def capture_restored(self) -> StateSnapshot
    def verify(self, handoff, restored, clear_side_ok, access_side_ok) -> ResetOutcome
```

Q3（冻结）暴露:
```python
def q3_reset_chain(account, password, work_dir, python_exe, protected,
                   run_nonce=None, clear_targets_by_category=None,
                   clear_na_declared=False, expected_sid=None,
                   old_worker_pid=None, terminate_old_worker=None,
                   clear_action=None) -> ResetChainResult
```
`ResetChainResult`（冻结）关键字段:
`clear_ok, preserve_ok, access_ok, handle_ok, identity_ok, lifecycle_ok,
matrix_ok, dacl_restore_ok, real_reset_required, real_reset_ok, valid`（全部须字面 True）

## §3 适配器设计（`q3_reset_adapter.py`,新文件）

### 3.1 目标
把冻结的 Q3 层**接到** `ResetController` 的语义上,使 `reset.py` 的
`restart_worker` / `access_probe` **有真实实现**,且**不损失 Q3 的证据强度**。

### 3.2 映射
| `ResetController` hook | 由 Q3 的什么提供 |
|---|---|
| `restart_worker()` | 冻结 `q3_reset_chain` 的 **生命周期 + 新 worker** 步骤（旧 worker 终止 → clear → 新 worker） |
| `access_probe()` | 冻结 `q3_reset_chain` 的 **F4 access gate**（严格 schema 的 `READ=DENIED`） |

### 3.3 草图（伪代码,fail-closed）

```python
# q3_reset_adapter.py  (NEW FILE; does NOT modify RC11 or the 10 frozen Q3 roles)
from reset import ResetController            # RC11 (read-only import)
from q3_reset_chain import q3_reset_chain     # Q3 frozen (read-only import)

class Q3ResetController(ResetController):
    """Adapter: ResetController hooks backed by the frozen Q3 reset chain."""

    def __init__(self, *, account, password, python_exe, work_dir, protected,
                 clear_targets_by_category, expected_sid,
                 old_worker_pid=None, terminate_old_worker=None, clear_action=None,
                 **kw):
        super().__init__(kw["literal_path"], kw["substrate_path"])
        self._q3 = dict(account=account, password=password, python_exe=python_exe,
                        work_dir=work_dir, protected=protected,
                        clear_targets_by_category=clear_targets_by_category,
                        expected_sid=expected_sid, old_worker_pid=old_worker_pid,
                        terminate_old_worker=terminate_old_worker,
                        clear_action=clear_action)
        self._last = None      # frozen ResetChainResult

    def _run_q3(self):
        if self._last is None:
            self._last = q3_reset_chain(**self._q3)
        return self._last

    def restart_worker(self) -> None:
        r = self._run_q3()
        # Q3's chain already performs: old-worker terminate -> clear -> new worker.
        # Fail closed if lifecycle/new-worker evidence is not literally True.
        if r.lifecycle_ok is not True or r.identity_ok is not True:
            from reset import NotIsolatedError
            raise NotIsolatedError(f"Q3 restart not isolated: {r.reason or 'lifecycle/identity'}")

    def access_probe(self) -> bool:
        r = self._run_q3()
        # access_ok True <=> strict-schema verdict RESULT == READ=DENIED (frozen F4 gate)
        return r.access_ok is True

    # Optional: surface the full frozen result for the caller's ledger.
    @property
    def last_result(self):
        return self._last
```

### 3.4 语义桥接（诚实标注）
- `NotIsolatedError` 在 Q3 未证明孤立时**照样抛出** —— 保持 `reset.py` 的 fail-closed 语义。
- `restart_worker()` 的"成功"断言**依赖** Q3 的 `lifecycle_ok + identity_ok`(字面 True),
  **不**自行判定。
- `access_probe()` 的"拒绝"断言**依赖** Q3 的 `access_ok`(严格 schema),**不**用"代码没尝试"冒充。

## §4 待凌翼/团队确认的开放问题（不擅自定）

1. **clear 侧来源**:`reset.py` 的 `clear_side_ok` 与 Q3 的 `clear_ok` 如何对齐?
   由适配器把 `r.clear_ok` 传给 `verify(clear_side_ok=...)`,还是另立映射?
2. **`preserve` 侧**:`reset.py.verify()` 自带 preserve 判定;Q3 也判 `preserve_ok`。
   两者**都保留**（不互相替代）还是择一为权威?
3. **run-nonce / run-id 绑定**:适配器是否需要把 `run_nonce` 与 `q3_qualify` 的 run-id 打通?
4. **profile 选择**:适配器是否固定 `API_NO_INHERIT_PROFILE`,仍由冻结合同决定?
5. **集成测试放哪**:新增 `q3_reset_adapter.py` 的 selftest + 一个"适配器→reset.py 语义"的桥接测试,
   **均不进 Q3 冻结集合**（冻结身份不变）。

## §5 不做的事（守线）
- ❌ 不改 `reset.py`（RC11）、不改 10 个 Q3 冻结文件。
- ❌ 不因设计冻结通过而放宽 `SCIENTIFIC_EXECUTION`（仍 = MAY NOT START）。
- ❌ 不在**未获凌翼对 §4 开放问题的裁决前**,把适配器接入任何真实执行路径。

> 本文件为**设计草案**,供凌翼审阅。落地代码将在其确认 §4 后,以**新文件**形式提交,
> 并附适配器 selftest + 桥接测试（独立于冻结身份）。
