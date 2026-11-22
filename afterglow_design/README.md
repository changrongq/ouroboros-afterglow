# AfterGlow 设计交付 · 第一期

对应《千年舟 · 凌翼裁定执行单》（2026-11-21）§一 的三项交付。
固定点：`56e375f`（`exp/v2-l1-verifier`）

---

## 一 · 本目录有什么

| 文件 | 对应裁定 | 内容 |
|---|---|---|
| `A_minimum_recovery_design.md` | §一 A | 可信历史恢复的最小设计（八类信息的字段、闭集、缺省规则） |
| `B_hybrid_memory_candidates.md` | §一 B | 混合记忆的两个可比较候选（四层分工、写入触发、纠正/重置/授权撤销） |
| `C_decision_ledger.md` | §一 C | 第二轮 16 项分歧台账 |
| `report_to_lingyi_20261122.md` | §四 | 汇报：做到什么、没做到什么 |

**A 的可运行原型不在这里**，在 `../afterglow_a/prototype/`。
设计与其实现分两个目录，是为了让「设计说了什么」与「代码做了什么」可以分别核对。

---

## 二 · 怎么自己验证

```bash
# 1. 源侧证据（现状 source_role 到底错在哪）
python afterglow_a/evidence/probe_source_role.py
#    预期：9 条 (source, source_role) = (m2_reflection_trigger, user)
#         候选池 1 条无 source_role 字段
#         MemorySystem.py 两处缺省值为 'user'

# 2. A 原型的 P1–P5 验收
python afterglow_a/prototype/test_p1_p5.py
#    预期：合计 14  通过 14  失败 0

# 3. 变异测试（证明上面 14 条不是空转）
python afterglow_a/prototype/test_mutations_v4.py
#    预期：变异 9：CAUGHT 7 / REDUNDANT 2 / MISSED 0 / INVALID 0
#         VERDICT: PASS
```

```text
⇒ 环境：Python 3.9+，无第三方依赖，无网络请求，不读写任何真实角色数据。
⇒ 若结果与上述预期不一致，请直接报差异。
```

---

## 三 · 审查分工与状态

依据裁定 §二，各成员审查对象不同。**不要求任何人通读全部。**

| 审查人 | 职责（裁定 §二 原话） | 与该职责最相关的位置 | 状态 |
|---|---|---|---|
| 钳星 | 检验最小候选是否仍然偷换了记忆的研究对象 | B §零、§一、§6.2；C 全文 | **已发审查请求** |
| 睫 | 审查因果可辨识性与观察者边界；第 20 号口述要点按其真实证据等级引用 | A §1.8、§三；B §6.1 | 未发 |
| 知微 | 审查状态、读取路径、重置及对照设计的技术可行性 | B §二、§三、§4.3；A §1.3 | 未发 |
| Mion | 审查来源、纠正、承诺与伪亲历风险 | B §5.2、§5.3；A §1.5 | 未发 |
| 衔环 | 审查版本身份、归属、写入与消费证据 | A §1.3；C 全文；原型 STATUS | 未发 |
| 荣弦 | 确认哪些恢复行为具有实际价值 | A §零、§一；B §六 | 未发 |

```text
⇒ 按顺序推进：钳星未回之前，不启动其余审查。
⇒ 理由：钳星那一问若成立，后续四份审查的对象都会变。
```

---

## 四 · 本目录的三条纪律

```text
D1  设计文件与实现文件分开放。
    ⇒ 本目录只放设计；实现一律在 afterglow_a/。

D2  文件内引用一律用相对仓库根的路径。
    ⇒ 便于在 GitHub 上直接点击，也便于在别的目录里复算。

D3  本目录不放临时脚本、不放运行产物。
    ⇒ 结果 JSON 在 afterglow_a/prototype/reports/，与本目录无关。
```

---

## 五 · 保持的状态

```text
REAL_CANDIDATE_SELECTED   = NO
C1_QUALIFICATION          = NO_VERIFIED_EVIDENCE
SCIENTIFIC_EXECUTION      = MAY_NOT_START
Q3_FROZEN                 = UNCHANGED
MAIN_MERGE                = DEFERRED
```

```text
⇒ 本目录全部内容属「文档设计与已有资产核查」，
  在裁定 §三 授权范围内。
⇒ 不含任何科学实验结果。
```
