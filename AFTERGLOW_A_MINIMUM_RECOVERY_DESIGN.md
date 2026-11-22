# AFTERGLOW_A_MINIMUM_RECOVERY_DESIGN

**可信历史恢复的最小设计**

依据：《千年舟 · 凌翼裁定执行单》§一 A，2026-11-21
固定点：`7e62cacfc0ed547e91b35698d439f5907c11be42`
撰写：Coder · 2026-11-22
状态：**设计文档 + 独立环境最小原型（合成资料）**
明确不做：不执行科学实验、不修改真实角色恢复状态、不改 Q3 冻结对象

---

## 零 · 一句话说明这个设计想解决什么

现状是：AfterGlow 会**写入**记忆，但说不清每条记忆**从哪来**。

最具体的证据（本仓库实测，可复算）：

```text
medium_term_memories.json   9 条，全部 (source, source_role) = (m2_reflection_trigger, user)
temp_candidate_fact_memories.json  1 条，无 source_role 字段
MemorySystem.py L1071  'source_role': candidate_fact.get('source_role', 'user')
MemorySystem.py L1310  ... fragment.get('source_role', existing.get('source_role','user'))
```

⇒ `source` 是系统自己生成的 (`m2_reflection_trigger`)，`source_role` 却写成 `user`。
⇒ 这不是「空字段被推定为用户」，是**「非用户来源被标成了用户」**。
⇒ 比凌翼指出的风险更靠前一步，也更难查：空字段至少能被 grep 到，
   填错的字段看起来是完整的。

**本设计的目标不是让系统记得更多，是让它能说明白自己记得的东西是谁说的。**

---

## 一 · 八类信息，各自的最小定义与字段

凌翼要求覆盖：来源、事件参与、历史版本、关系、承诺、纠正、未知、恢复后行为验证。

以下每条都给出：**最小字段 / 缺省如何表示 / 什么情况算未知 / 一条反例**。

### 1.1 来源（provenance）

| 项 | 内容 |
|---|---|
| 要回答的问题 | 这条记录里的这句话，**是谁**说的？ |
| 最小字段 | `source_kind`（枚举）、`source_ref`（指向具体事件/文件/轮次） |
| `source_kind` 枚举（**闭集，五个值**） | `user_utterance` 用户明确说过的原话<br>`system_generated` 系统自动生成（摘要、反思、模板）<br>`third_party` 第三方材料（文档、外部输入）<br>`model_echo` 模型自身输出被回读<br>`unknown` **显式未知** |
| 缺省 | **`unknown`，不是 `user`。** 字段缺失一律落 `unknown` |
| 什么情况算未知 | 字段缺失 / 值不在闭集内 / `source_ref` 为空或指向不存在的事件 / 值与 `source_ref` 指向的实体冲突 |
| 反例（现状） | 9 条记忆 `source=m2_reflection_trigger` 却 `source_role=user`。**系统生成的反思被记成用户原话。** |

```text
⇒ 【硬规则】`unknown` 是一个可以写进库的值，不是一个失败状态。
  允许「我不知道这句话是谁说的」长期存在，比允许「不知道就记成用户」安全。
```

### 1.2 事件参与（participation）

| 项 | 内容 |
|---|---|
| 要回答的问题 | 记录里那条陈述的**当事人**，是否参与了所述事件？ |
| 最小字段 | `participant_id`、`participation_basis`（枚举）、`basis_ref` |
| `participation_basis` 枚举 | `first_person_report` 当事人自述<br>`third_person_report` 他人转述<br>`record_only` 仅见于记录，无参与证据<br>`unknown` |
| 关键区分 | **「知道这件事」≠「参与了这件事」≠「读过关于它的记录」** 三者必须分列 |
| 缺省 | `unknown` |
| 反例 | 「钳星是千年舟的机械臂」——这是钳星自述？还是 Coder 转述？记录里分不出。 |

```text
⇒ 凌翼原话「事件参与」在此落为：**参与 ≠ 知情 ≠ 读过**，三个独立字段，不许合并。
```

### 1.3 历史版本（version）

| 项 | 内容 |
|---|---|
| 要回答的问题 | 这条记忆**改过几次**？每次改成什么？谁授权改的？ |
| 最小字段 | `record_id`（稳定）、`revision`（递增整数）、`prev_digest`、`this_digest`、`changed_at`、`change_authority` |
| 摘要 | `this_digest = sha256(canonical(该版全部字段, 除 digest 自身))` |
| 链式 | `prev_digest` 指向上版摘要，形成**可断点检测**的链 |
| 缺省 | 首版 `prev_digest = null`（**不是空串**，空串与 null 含义不同） |
| 什么情况算异常 | `prev_digest` 指的版本不存在 / 链断裂 / `revision` 重复 / 同一 `revision` 摘要不同 |
| 反例（现状） | `MemorySystem.py` 中 `json.dump=12`、`open(...,'w')=11`、`sha256=0`、`snapshot=0`。**没有任何版本机制，写就是覆盖。** |

```text
⇒ 「删除即永久」的现状，使「纠正」在物理上不可实现。
  本设计的最小要求不是「不许删」，是「删之前留下上一版的摘要」。
```

### 1.4 关系（relation）

| 项 | 内容 |
|---|---|
| 要回答的问题 | 两条记录之间是什么关系？（不是「哪条更重要」） |
| 最小字段 | `relation_type`（枚举）、`from_id`、`to_id`、`relation_basis` |
| `relation_type` 枚举 | `same_fact_different_time`、`correction_of`、`contradicts`、`elaborates`、`unknown` |
| 关键约束 | **不做强度排序**（据 Mion 2026-11-20 降级 4 与知微 18 §7：参与者/写入者/读过/没有可同时成立，不构成高低序列） |
| 缺省 | 不建边的记录就是无边，`relation = 空集`，不推定 `unknown` 边 |
| 反例 | 「钳星是机械臂」与「钳星是大副」两说并存，属 `contradicts` 还是 `elaborates`？**系统当前无法表达这个区别。** |

### 1.5 承诺（commitment）

| 项 | 内容 |
|---|---|
| 要回答的问题 | 某条记录是否构成一项**承诺**？承诺是否已被履行/撤回？ |
| 最小字段 | `commitment_state`（枚举）、`committed_by`、`committed_to`、`commitment_ref` |
| `commitment_state` 枚举 | `proposed`、`accepted`、`fulfilled`、`withdrawn`、`expired`、`unknown` |
| 关键区分 | **「记录了一句话」≠「作出了一项承诺」**。承诺需要 `committed_to`（对谁）与 `commitment_ref`（凭何为据） |
| 缺省 | `unknown`，**不是 `proposed`** |
| 反例 | 「我说明天交」——是承诺，还是举例，还是转述别人的话？当前 schema 无法区分。 |

### 1.6 纠正（correction）

| 项 | 内容 |
|---|---|
| 要回答的问题 | 一条错记录**能否被改对**，且改这件事本身可查？ |
| 最小字段 | 复用 1.3 版本链 + `correction_of` 关系边 + `correction_reason` |
| 最小操作 | **不原地改。** 新写一版，`prev_digest` 指向被纠正版 |
| 关键区分 | **纠正 ≠ 删除**。删除让旧版消失，纠正让旧版保留并标注 |
| 缺省 | 无纠正记录 = 从未纠正（不是「无需纠正」） |
| 反例（现状） | `MemorySystem.py` 无版本、无快照、无 sha256，**纠正只能表现为覆盖或删除**。 |

```text
⇒ 凌翼说「未知」也是一类信息。同理：**被纠正过的错误也是一类信息**，
  不是应当消失的痕迹。
```

### 1.7 未知（unknown）

这是本设计里最容易被当成「没做」的一节，也是最要紧的一节。

| 项 | 内容 |
|---|---|
| 要回答的问题 | 系统能否**说出自己不知道什么**？ |
| 最小字段 | 每个枚举字段都有 `unknown` 成员；`unknown_reason`（可选，枚举） |
| `unknown_reason` 枚举 | `field_absent`、`value_conflict`、`ref_dangling`、`never_observed`、`not_applicable` |
| 关键约束 | **`unknown` 不得被静默替换为任何「像答案」的值** |
| 可验证方式 | 断言检查：任何枚举字段取值 ∉ 闭集 ⇒ 必须报错，不得自动落缺省 |
| 反例（现状） | `get('source_role', 'user')` 是**缺省值伪装成答案**的标准形式。 |

```text
⇒ 【与本项目既有的记法对齐】
  UNKNOWN != NON_TARGET
  测不到 ≠ 不存在
  NOT_ASSESSED ≠ NOT_DETECTED
  ⇒ 本设计把这三条从「文档里的口号」变成「字段上的闭集 + 断言」。
```

### 1.8 恢复后的行为验证（post-recovery behaviour verification）

| 项 | 内容 |
|---|---|
| 要回答的问题 | 恢复出来的历史，**能不能拿出来用**？ |
| 最小字段 | `recovery_id`、`query_ref`、`retrieved_ids`、`expected_ids`、`match_kind` |
| `match_kind` 枚举 | `exact`、`superset`、`subset`、`disjoint`、`not_run` |
| 关键约束 | **`not_run` 必须能被报告**，不能因为没有测试就当作通过 |
| 反例 | 「恢复成功」当前无定义：没有 expected_ids，就无法说 retrievd 对不对 |

```text
⚠ 本节只做**工程一致性检查**（取回的是不是写进去的那些）。
  ⚠ 这【不是】C1/C2/C3 的科学结果。
  ⇒ 凌翼 §三 明令：不得将工程原型测试冒充 C1/C2/C3 正式结果。
```

---

## 二 · 与现状的差异表（逐项可核对）

| 能力 | 现状（实测） | 本设计最小值 | 差距性质 |
|---|---|---|---|
| 来源可判定 | 9/9 条误标 `user` | 五值闭集 + `unknown` 缺省 | **语义错误**，非缺失 |
| 参与可分 | 无字段 | 三分列（参与/知情/读过） | 缺失 |
| 版本可追 | `sha256=0`、无快照 | 摘要链 + `prev_digest` | 缺失 |
| 关系可表达 | 无 | 五类枚举，不排序 | 缺失 |
| 承诺可判定 | 无 | 六态枚举 | 缺失 |
| 纠正可执行 | 只能覆盖/删除 | 新写一版 + `correction_of` | **机制性缺陷** |
| 未知可表达 | 缺省值冒充答案 | 闭集含 `unknown` + 断言 | **机制性缺陷** |
| 恢复可验证 | 无 expected/retrieved 对 | `match_kind` 五值，含 `not_run` | 缺失 |

**注：第一行与第四、六、七行不是「功能没做」，是「做了但语义错了」。**
后者比前者难改，因为错的字段看起来是完整的、能用的。

---

## 三 · 最小原型（合成资料，独立非冻结环境）

### 3.1 环境边界

```text
目录：afterglow_a/prototype/
数据：synthetic/ 下自造，不含任何真实角色内容
隔离：不读取、不写入、不覆盖
      d:\qcr\EntropyDrivenAI\medium_term_memories.json
      d:\qcr\EntropyDrivenAI\temp_candidate_fact_memories.json
      及任何 xiaomi_*.json / dialogue_history*.json
冻结：不触碰 Q3 冻结对象
```

### 3.2 原型要证明的最小命题

```text
P1  一条记录的来源可以被判定为五个值之一，缺省为 unknown
P2  修改一条记录会留下上一版摘要，链可校验
P3  一条被纠正的记录，旧版仍在，且能被指认
P4  系统能报告「我不知道」而不自动填值
P5  恢复后取回的结果能与期望集对比，并区分 exact/superset/subset/disjoint/not_run
```

⇒ 这五条都是**工程一致性**命题，不涉及「是否记住了」的科学判断。

### 3.3 不会做的事

```text
✗ 不声称原型证明了记忆机制
✗ 不把 P1–P5 通过写成 C1 资格
✗ 不用真实角色数据
✗ 不因为原型跑通就改 Q3 或声称可执行科学实验
```

---

## 四 · 迁移策略：既有记录怎么办

凌翼明令：「既有记录不得未经核查批量改写为确定来源。」

```text
规则 M1  不批量改写。任何改写须逐条、有依据、留记录。
规则 M2  存量 9 条 (m2_reflection_trigger, user) 的处置：
         · 不得直接改成 system_generated  —— 那同样是"批量推定"
         · 也不得保留 user  —— 那是已知错误的继续
         · 正确做法：标为 【待核查】(pending_verification)，
           并记录「原值 user，存疑原因：source=m2_reflection_trigger」
规则 M3  pending_verification 是一等状态，不是过渡态垃圾。
         它可以长期存在。
规则 M4  核查一条改成确定值的条件：
         能指出该条内容与哪一次具体用户发言逐字对应。
         做不到，就停在 pending_verification。
```

```text
⇒ 【我的判断，非凌翼指示】9 条里可能没有一条能在当前资料下核成 user_utterance。
  因为 source 全是 m2_reflection_trigger，而反思生成的文本通常不是逐字原话。
  ⇒ 这意味着「已核查的来源」可能长期为 0 条。
  ⇒ 这不是失败。这是诚实。
```

---

## 五 · 明确不做的（防止本设计被读大）

```text
✗ 本设计不回答「AfterGlow 是否记得」
✗ 不提供 C1/C2/C3 任何一级的证据
✗ 不修改真实角色恢复状态
✗ 不改 Q3 冻结对象
✗ 不合并 main
✗ 不实现 L2/L3 运行时
```

```text
保持：
  REAL_CANDIDATE_SELECTED   = NO
  C1_QUALIFICATION          = NO_VERIFIED_EVIDENCE
  SCIENTIFIC_EXECUTION      = MAY_NOT_START
  Q3_FROZEN                 = UNCHANGED
  MAIN_MERGE                = DEFERRED
```

---

## 六 · 留给审查者的问题（各自按分工）

| 审查人 | 我要问的具体问题 |
|---|---|
| 钳星 | 本设计是否仍偷换了研究对象？把「可追溯」当成「记忆」了没有？ |
| 睫 | §1.8 的 `match_kind` 是否足以表达「测到了」与「归属于」的区别？我怀疑不够。 |
| 知微 | §1.3 摘要链在「同一 revision 并发写」时如何防冲突？我目前只能靠单写者假设。 |
| Mion | §1.5 承诺六态是否漏了「被遗忘」这一态？`expired` 不等价于 `forgotten`。 |
| 衔环 | §1.1 的 `model_echo` 与 `system_generated` 边界是否清楚？我担心我把同一现象拆成了两格。 |

```text
⇒ 以上五问不是「停工条件」，是**我这一版已知的薄弱处**。
  按凌翼 §四：不把未解决的哲学问题变成工程停工条件。
  所以：设计照常推进，问题照常挂着。
```

---

## 七 · 本文件的证据等级

```text
MEASURED    : 零·全部数字（9条/1条/L1071/L1310/sha256=0 等）
              复算脚本：afterglow_a/evidence/probe_source_role.py
INFERENCE   : §二 差距性质分类（「语义错误」vs「缺失」是我的判断）
DESIGN      : §一 字段设计、§三 原型命题、§四 迁移规则
NOT_DONE    : 原型本身（见 §八）
```

---

## 八 · 原型实施状态

**截至本文件成稿：原型未开始实现。**

写这句话是因为：凌翼要的是「设计 + 原型」，而我先交了设计。
把「未开始」写在文档里，比在汇报时说「基本完成」要好。

进度以 `afterglow_a/prototype/STATUS.md` 为准，不以此为据。
