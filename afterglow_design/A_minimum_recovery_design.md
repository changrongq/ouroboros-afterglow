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
| 最小字段 | `recovery_id`、`query_ref`、`retrieved_ids`、`expected_ids`、`match_kind`、**`expected_ids_registration`（见下）** |
| `match_kind` 枚举 | `exact`、`superset`、`subset`、`disjoint`、`partial_overlap` |
| 关键约束 | **「未执行」不是一个 `match_kind` 值**，它是「没有 `match_kind`」——见下 |
| 反例 | 「恢复成功」当前无定义：没有 expected_ids，就无法说 retrievd 对不对 |

```text
⇒ 【2026-11-23 三处更正，据睫 r2/23 格三与第 ① 问】

  更正 1：枚举追平实现。
    原文只列五值（exact/superset/subset/disjoint/not_run），
    但实现里实际是六种集合关系（多一个 partial_overlap）。
    ⇒ 设计文本与实现差一个值，现补上 partial_overlap。

  更正 2：把 not_run 从枚举里移出。
    not_run 不是「第六种集合关系」，它是【没有 match_kind】：
    ran=False 或 expected_ids=None 时不产生关系值。
    ⇒ 它隐含了「谁跑没跑」这一维，但那一维不在这张表里。
    ⇒ 因此不写作枚举成员，写作独立状态。

  更正 3：新增 expected_ids 的登记身份（睫第 ① 问核心）。
    没有这一维，exact 分不开两件事：
      (a) 独立观察者按预登记期望集复算得到的 exact
      (b) 实现把自己的输出回填成期望集得到的 exact
    ⇒ 二者在同一个枚举值下无法区分，而后果完全不同。
```

```text
⇒ 【expected_ids_registration 最小字段】

  registered_by       谁登记的期望集
  registered_at       何时登记（须早于 outcome exposure）
  registered_rev      用哪一版代码登记
  independent_of_write 是否独立于写入路径（yes / no）
  before_exposure     是否在见到结果之前登记（yes / no）

⇒ 只要 independent_of_write = no 或 before_exposure = no，
  该次 exact 就【不得】被读作「独立复算成立」。
⇒ 这一条是本节的边界所在：它让 exact 有可辨识的来路，
  但仍【不】表达因果归属（见下）。
```

```text
⇒ 【本节的边界（重申，且更紧）】

  测到了（retrieved == expected）与 归属于（差异来自某次经历 E）
  【本来就不住在同一张表里】。
  ⇒ 本节只做前者。
  ⇒ 谁想把后者塞进来，就越过了本节自己划的界，
    等于把工程检查读成科学结果（凌翼 §三 明令禁止）。
  ⇒ 这不是「五值不够」，是「不该由这张表回答」。
```

```text
⇒ 【2026-11-24 据凌翼裁定回执补记：本节契约已实现，另立门禁】

  裁定要点：
    · 采用 B 方案：match_kind 保持纯集合语义，
      完整性另立 integrity_status 一轴，失败必须阻断资格
    · not_run 从集合关系枚举移出（本轮实现已追平）
    · expected_ids_registration 五字段已实现并接入门禁

  实现位置：afterglow_a/prototype/afrecover.py
  设计更正：afterglow_design/digest_semantics_and_recovery_gate.md

  验收（只报测得的结果，不报「已实现」）：
    test_p1_p5.py           17/17
    test_recovery_gate.py   10/10（覆盖裁定 §三 全部七条场景 + 3 项契约）
    test_mutations_gate.py  16 个变异全部 CAUGHT，MISSED 0

  ⚠ 状态登记：RECOVERY_GATE_IMPLEMENTED = NOT_VERIFIED
     我方不自行判定「实现完成」。判定权在知微（实现与设计一致性）
     与睫（声明边界）。本节只提供可复算的材料。

  ⚠ ZA01_VERIFIED_READ_BINDING 仍为 OPEN：
     门禁检查的是「检查时刻」的快照，覆盖「检查后消费前被替换」。
     不覆盖「读取与检查本身非原子」的情形。此项未解决。
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
P5  恢复后取回的结果能与期望集对比，并区分
    exact / superset / subset / disjoint / partial_overlap
    （未执行时 match_kind = None，不是枚举值 not_run —— 见 §1.8 更正二）
```

```text
⇒ 2026-11-24 据凌翼裁定同步 P5 措辞：
   原写 "…/disjoint/not_run"，与 §1.8 更正二自相矛盾。
   实现已于本轮追平：MATCH_KINDS 不含 not_run，
   未执行返回 None。回归见 test_p1_p5.py P5 / P5b。
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

**截至 2026-11-24：P1–P5 五条命题的测试全部通过（当前 17/17）。**

```text
⚠ 但「测试全过」不等于「本文件描述的能力全部实现」。
  知微 2026-11-24（r2/26）指出两处设计已改、实现未同步：
    · §1.8 已把 not_run 移出 match_kind 并新增 expected_ids_registration，
      而 afrecover.py 仍是旧字节：ran=False 时报告里仍有 match_kind="not_run"，
      exact 报告里也没有 expected_ids_registration。
    · 因此应记「设计已接受、实现待同步」，
      不得再称「新设计所述能力已全部实现」。
  ⇒ 本条按指出处如实降级。
```

```text
P1  来源五值闭集，缺省 unknown .................... 已实现
P2  修改留上一版摘要，链可校验 ..................... 已实现（含篡改检测）
P3  纠正后旧版仍在且可指认 ........................ 已实现
P4  能报告「不知道」而不自动填值 ................... 已实现
P5  取回结果与期望集对比，区分五值 ................. 已实现
```

```text
⇒ 但「实现并测试通过」不等于「可用」。
⇒ 未做的部分如实列在 prototype/STATUS.md §四：
  无持久化、无并发保护、只跑合成资料、检索是子串匹配、
  权限是自由字符串、model_echo 与 system_generated 边界未定。
⇒ 进度与缺口以 STATUS.md 为准，本文件不重复。
```

---

## 九 · 怎么自己跑一遍（给审查者）

**不用信我写的数字。下面三条命令跑完，你自己看。**

```bash
# 1. 源侧证据：现状 source_role 到底错在哪
python afterglow_a/evidence/probe_source_role.py
#    预期：9 条 (source, source_role) = (m2_reflection_trigger, user)
#         候选池 1 条无 source_role 字段
#         MemorySystem.py 两处缺省值为 'user'

# 2. P1–P5 验收
python afterglow_a/prototype/test_p1_p5.py
#    预期：合计 17  通过 17  失败 0（含 ZA-01/02/03 三条回归）

# 3. 变异测试（证明上面 17 条不是空转）
python afterglow_a/prototype/test_mutations_v4.py
#    预期：变异 9：CAUGHT 7 / REDUNDANT 2 / MISSED 0 / INVALID 0
#         VERDICT: PASS
```

```text
⇒ 环境：Python 3.9+，无第三方依赖，无网络请求，不读写任何真实角色数据。
⇒ 结果会写入 afterglow_a/prototype/reports/*.json，与仓库内已有文件应一致。
⇒ 若你的结果与我写的不一致，那是我的错，不是你的环境问题。请直接报差异。
```

```text
⚠ 【输出编码：2026-11-22 修正】
  初版此处只写「Python 3.9+」，未说明终端编码要求。
  钳星在 cp936（Windows GBK）控制台下实跑，报 UnicodeEncodeError 并 exit 1。
  ⇒ 现三个脚本均已加 _harden_stdio()，并已把 print() 中的数学箭头改为 ASCII。
  ⇒ 已在 UTF-8 与 GBK 两种编码下各跑一遍，判定数字一致（6/6）。
  ⇒ 若你仍遇到编码相关崩溃，请报出你的 PYTHONIOENCODING 与终端码页。
```

```text
⇒ 【变异测试为什么必须跑】
  第 2 条全绿不能说明检查有效。
  我第一次跑变异测试时（2026-11-22，当时套件为 14 条），14/14 全绿，但 9 个变异里有 3 个没被捕获。
  ⇒ 全绿可能只是断言写得太松。
  ⇒ 变异测试是唯一能区分「真的守住了」和「看起来守住了」的手段。
  ⇒ 这一轮的详细经过写在 prototype/STATUS.md §三，包括我自己的三次误判。
```
