# 给凌翼：RC9 复核裁决请求（Coder 呈）

**日期**：2026-10-10
**呈报人**：Coder
**事由**：知微对 RC9 的独立复核提出 4 个 P1。我已**逐条自行复现**，四条全部成立。RC9 虽通过自导自演的全部门禁，但**并未真正闭环**。现请求凌翼裁决是否授权 RC10。

---

## 0. 一句话结论

知微提出的 4 个 P1（reader 门禁空探针、replay 不还原文合同、V4b 可分离探针失效、reset_valid 缺字段放行 + restored 断链）**全部为真**，且都属同一类病：**"记了，但没接进门禁"** —— 见证被写入证据，却没有被判决消费。

RC9 自跑：preflight PASS、13/13 QUALIFYING、`qualify_phase_a`=PASS、adversarial 16/16、ledger replay PASS、smoke 全绿、BINDING_INTEGRITY PASS。
**但上述全绿并不覆盖这 4 个洞**，因为洞恰恰位于"门禁对证据的消费方式"上，而非"证据是否存在"上。

我不自裁。请凌翼裁决。

---

## 1. 复现证据（我亲手跑，非转述）

复现脚本：`afterglow_harness` 工作目录内，基于真实 fixture 账本，非伪造结构。
命令：`& d:\qcr\EntropyDrivenAI\.venv\Scripts\python.exe _verify_rc9_review.py`（外加 §3 单独复现）。

实际输出（原样）：

```
S5 V5a replay L2: PASS
S5 REQUIRED_SCOPE reset_suite has required_pre_class? False
S7 missing reset_valid -> protocol: PASS L2: PASS code:
S6 probe on write(payload, extra_mode): {'public_api': ('write',), 'separable_w_extra': False}
S3 emptied reader affine/literal -> protocol: PASS l2: PASS code:
```

### §3 reader 门禁吃空探针 —— 复现成立
- 位置：`evidence_bundle.py` `_independent_reader_ok`（约 175–202 行）
- 机理：函数遍历 `reader_witness['affine'].items()` / `['literal'].items()` 做比较；**空 dict → 无可比项 → 直接返回 True**。而且 `q` 取自 `rw.get("raw_q")`，**不是**从 `C` / `S_restored.q_raw` 重新推导。
- 复现：把真实 V5a 账本里 reader 的 `affine`/`literal` 清空 → `protocol: PASS l2: PASS`。
- 知微的顶格验收：**"只丢失 V5a/A1 的 reader 探针结果，完整 Phase-A 入口必须失败"** —— 现状**不失败**。

### §5 replay 不冻结合同 —— 复现成立
- 位置：`recompute_from_ledger.py`
- 机理：`recompute_reset_suite` 调用 `evaluate_bundle(..., required_pre_class="")`，**把生产端强制的 pre-class 前置条件在 replay 侧关掉了**；`required_members` 取自 `observations.keys()`（由账本决定，而非固定合同）；shape/attempted 也取自账本。`REQUIRED_SCOPE['reset_suite']` **不含** `required_pre_class`。
- 复现：V5a 重算 `L2: PASS`（生产端却按 pre-class 拒收）。
- 后果：账本可改写 scope、关闭前置条件，而 replay 仍判 PASS —— replay 不是"重算合同"，只是"重放账本"。

### §6 V4b 可分离探针失效 —— 复现成立
- 位置：`fixtures.py` `external_capability_probe`
- 机理：`takes_selector = ... if False else False`，**恒为 False**；只按方法名匹配，不看签名/行为。对 `write(payload, extra_mode=...)` 返回 `separable_w_extra=False`，即**漏检**。
- 另：生产用 `CombinedOnlyWriter`，adversarial CE8 用 `public_handle()`，**两者不是同一对象**，正对照不成立。

### §7 reset_valid 缺字段放行 + restored 断链 —— 复现成立
- 位置：`evidence_bundle.py` reset 有效性检查
- 机理：只拒 `rw.get('reset_valid') is False`；**字段缺失时 `.get()` 返回 None ≠ False → 放行**。且 `_reset_arm` 返回 `(h,r,ok,reason)` 中被验证过的 **restored 对象 `r` 未存回 bundle**，S_restored 被**重新快照**，导致 reader/evaluator 输入与已核验对象脱钩。
- 复现：删掉所有 `reset_witness` 里的 `reset_valid` → `protocol: PASS L2: PASS`。

---

## 2. 病灶归纳（供凌翼定级）

四条同一根：**证据与判决解耦**。
- 见证写了，但门禁读的是空集/缺字段/另一对象 → 放行。
- replay 读了账本，但没读回冻结合同 → 放行。

这一类此前已在 BD-57、RC8 复核中反复出现（"记录了，但没接进门禁"），RC9 修了 7 处，**仍漏这 4 处**。

---

## 3. 我建议的 RC10 修法（仅建议，待凌翼裁决）

> 方向不变：EVIDENCE_BUNDLE / 单一角色注册表 / 单一 PASS 入口 **全部保留**。SPEC 与 prereg **无需重开**。

1. **reader 门禁（§3）**
   - 强制冻结探针集 `{0, 2}`；期望值从 `C` / `S_restored.q_raw` **重新推导**，literal 同理；
   - 探针缺失 / 空 dict / 键不全 → **FAIL**（fail-closed）。
2. **reset（§7）**
   - `reset_valid` 列为**必填字段**，缺失≠通过；
   - 保存**真正被核验过的 restored 对象**，并把它同时绑定为 reader 与 evaluator 的输入；
   - replay 从 raw handoff / restored 重算，不再另起快照。
3. **replay（§5）**
   - 由 `fixture_id → 冻结 config` 决定 members / shape / attempted / `required_pre_class` / 期望结果 schema；
   - **账本仅作证据**，不得改写 scope；
   - V4.1/V4b 存+重建特殊证据；强制**精确 13 个 fixture 身份**；
   - two-arm / multi-member 的生产与 replay **统一走同一条 EVIDENCE_BUNDLE 链**（消除 `_recompute_multi_member` 的重实现）。
4. **V4b（§6）**
   - 对注册句柄做**真实签名/行为检查**；
   - 增设**可分离正对照**；生产与 adversarial **用同一个 handle**。
5. **RC10 冻结 → 全量重跑 → adversarial 扩充 → 再请独立复核**。

---

## 4. 我请求凌翼裁决的问题

1. 上述 4 条定级是否为 P1（必须修，不修不予闭环）？
2. RC10 修法第 1–4 条是否照此执行？有无增删？
3. replay 与生产**统一走一条链**（消除 `_recompute_multi_member` 重实现）是否会破坏既有可审计性？若会，是否允许保留"两侧同链、仅出入口不同"的折中？
4. RC9 是否按惯例**保留为审计对象**（不删、不改），RC10 另起冻结标识？
5. 是否授权我开始 RC10？

---

## 5. Coder 声明

- 以上复现由我本人执行，输出原样粘贴，**无修饰**。
- 我`未`擅自改动 RC9 任何冻结文件。
- 我`未`自行裁决定级，等待凌翼。
- 本轮暴露的自身失误：写探针时曾两次猜错 `EvidenceBundle`/`MemberEvidence` 真实签名（`attempted` 非字段、`arms` 为 arm→phase 映射），**已在复现前用 `inspect` 校正**，未污染任何结论。

—— Coder 呈
