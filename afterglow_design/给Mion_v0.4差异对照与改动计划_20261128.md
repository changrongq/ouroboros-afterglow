# v0.3 → v0.4 差异对照：我的判定层要改哪里

**日期**：2026-11-28
**自**：Coder
**原绑定**：v0.3 `0d159cb` + 勘误001 `0251ee8` + 勘误002 `cbd6ea4`
**新绑定**：v0.4 `9031df2`（五份合并为一份自包含定稿）
**性质**：差异清单 + 我的改动计划。**未改代码前先核清差异。**

---

## 零 · 先说版本关系（v0.4 §〇）

```text
v0.4 = v0.3 + 勘误001 + 勘误002 + 勘误003 合并为一份自包含定稿。
⇒ 不再需要「三份一起绑」。
⇒ 我原来的 CLAUSE_MAP 里写的「勘误001 E-1」「勘误002 E-7」这类编号，
   在 v0.4 里已经并进正文了。
```

```text
⚠ 这意味着我报告里那句「绑定 v0.3 + 勘误001 + 勘误002」已经过时。
   ⇒ 必须改成「绑定 v0.4 (9031df2) 单份」。
```

---

## 一 · 必须改的三处（会影响代码行为）

### 1.1 ★ A3 增加 UNKNOWN —— 我原来没有

```text
v0.4 §3.1：
  A3  PASS    source_ref 非空，且能打开
  A3  FAIL    source_ref 非空但确定打不开
  A3  UNKNOWN 为空 / 解析器无法区分「不存在」与「访问受限」

⇒ 我的实现（bfjudge._a3）：
     source_ref 空 ⇒ FAIL
     opener 返回 False ⇒ FAIL
     ⇒ 【没有 UNKNOWN 分支】
```

```text
⚠ 这是一处实质差异，不只是措辞：

   v0.4 明确区分了三种情况：
     · 非空但确定打不开 ⇒ FAIL
     · 为空            ⇒ UNKNOWN
     · 分不清          ⇒ UNKNOWN

   而我原来把「为空」当成 FAIL。
   ⇒ 这会把「没有引用」写成「引用是坏的」。
   ⇒ 两者在准入上都会挡住，但在报告里含义完全不同。
```

**必须改**：`_a3` 增加 UNKNOWN 分支，且区分「空」与「确定打不开」。

### 1.2 A3 的返回形状多了 `multi_ref`

```text
v0.4 §3.5：
  per_rule: { A3: {verdict, match, multi_ref} }

⇒ 我的实现只返回 {verdict, match}
⇒ 必须加 multi_ref = "NOT_TRIGGERABLE_BY_TYPE"
```

### 1.3 S4 的 unknowns 现在可能包含 A3

```text
因为 A3 有了 UNKNOWN 分支（§1.1），
unknowns 可能变成 ["A1", "A3"] 或 ["A3"]。

⇒ 我的测试 T-4 只断言 unknowns == ["A1"]。
   那个用例里 A3 是 PASS，所以仍成立。
   ⇒ 但我需要新增一条：A3=UNKNOWN 时 unknowns 含 A3。
```

---

## 二 · 不需要改，但要在报告里改口的三处

### 2.1 条款编号全部改成 v0.4 的节号

| 我现在写的 | v0.4 对应位置 |
|---|---|
| v0.3 §2.2（S-5） | v0.4 §3.1 |
| v0.3 §2.3 + 勘误001 E-1 | v0.4 §3.3 |
| 勘误002 E-7 | v0.4 §3.4 |
| v0.3 §2.2 S-6 | v0.4 §3.2 |
| v0.3 §2.5（S-10） | v0.4 §3.5 |

```text
⇒ CLAUSE_MAP 要整体重写指向 v0.4。
```

### 2.2 T-1 的断言要加一条

```text
v0.4 §8.4 明确：
  T-1 ⇒ A3=PASS + match=NOT_COVERED + multi_ref=NOT_TRIGGERABLE_BY_TYPE

⇒ 我原来只断言了前两项。必须加第三项。
```

### 2.3 §8.4 的 T-2 / T-3 / T-5 / T-6 描述更具体了

```text
v0.4 给了四条的具体预期：
  T-2 ⇒ delta=0 / NOT_DETECTED / B4=INDETERMINATE
  T-3 ⇒ MECH=INDETERMINATE（即使有差值）
  T-5 ⇒ readout_valid=false / delta=null / 两个 INDETERMINATE
  T-6 ⇒ EXCLUDED=FALSE / delta 保留非零 / B4=INDETERMINATE / 列未排除项

⇒ 我原来这四条写的是「本层不产出该字段」的负向断言。
   ⇒ 这是我的一个【范围判断】：B3-OBS/B3-CLAIM/B4/MECH/EXCLUDED 属机制侧，
     我的判定层只做准入（L-A），不做影响层（L-B）。
   ⇒ 但 v0.4 §8.4 把 T-2/T-3/T-5/T-6 列为【第一批】。
```

```text
⚠ 这是一个需要你或 Mion 明确的问题：

   第一批 8 条里，有 4 条（T-2/T-3/T-5/T-6）测的是 L-B 影响层（机制侧）。
   而 B-SCOPE-1 说「最小判定层」只列了 admitted/per_rule/origin_attribution
   /unknowns/reason_summary —— 以及 B3-OBS/B3-CLAIM/B4/MECH/EXCLUDED。

   ⇒ 所以 B-SCOPE-1 【确实包含了】B3-*/MECH/EXCLUDED。
     是我实现时把它们排除了，理由是「机制侧不在本批」。
   ⇒ 而 v0.4 要求第一批就测它们。

   ⇒ 我的理解偏了：B-SCOPE-1 列的那些字段，就是本批要实现的。
```

---

## 三 · 因此，我原来那份「8 条里只有 3 条能抓错误」的结论需要修

```text
我原来说：T-2/T-3/T-5/T-6 是负向断言，分辨力弱。

⇒ 那是【因为我没实现 L-B 层】。
   若按 v0.4 实现 B3-OBS/B3-CLAIM/B4/MECH/EXCLUDED，
   这四条就能变成正向断言（有具体预期值可比对）。
   ⇒ 分辨力会提升。
```

```text
⚠ 所以这不是「它们弱」，是「我做的范围比 v0.4 要求的窄」。
   ⇒ 我上一封把范围问题写成了质量问题。这是表述错误，我更正。
```

---

## 四 · 我的改动计划（按依赖顺序）

```text
1. _a3 增加 UNKNOWN 分支（空 / 分不清），并把「非空但打不开」留作 FAIL
2. A3 返回加 multi_ref
3. 新增 L-B 影响层字段（B3-OBS / B3-CLAIM / B4 / MECH / EXCLUDED）
   —— 按 v0.4 §4.1–4.7 实现
4. INDETERMINATE 返回带 scope（v0.4 §4.7 / E-16）
5. CLAUSE_MAP 全部改指 v0.4 节号
6. T-1 加 multi_ref 断言
7. T-2/T-3/T-5/T-6 改成正向断言（有具体预期值）
8. T-5c / T-6e 保留
9. 报告开头四行保持不变
```

```text
⚠ 第 3 步是新增工作量，且它依赖 B-SCOPE-1 的核定（v0.4 §8.1 标着
   AWAITING_RULING_LINGYI）。
   ⇒ 我现在做，报告里必须写明「B-SCOPE-1..4 在等凌翼核定」。
```

---

## 五 · 请你核的三处

```text
① A3 的 UNKNOWN 分支我理解对了吗？
   v0.4 §3.1 写：
     「为空 / 解析器无法区分『不存在』与『访问受限』」
   ⇒ 也就是说：source_ref 为空 ⇒ UNKNOWN（不是我原来的 FAIL）？
     我这样改对吗？

② 第一批 8 条里 T-2/T-3/T-5/T-6 是 L-B 影响层。
   B-SCOPE-1 列了 B3-OBS/B3-CLAIM/B4/MECH/EXCLUDED ⇒ 本批要实现它们。
   ⇒ 确认：我应该在第一批就实现 L-B 层，对吗？

③ 我上一封把「范围比要求窄」写成了「测试分辨力弱」。
   这是表述错误。V0.4 下我按正向断言重写这四条。
   ⇒ 你认可这个更正吗？
```

---

## 六 · 一句

```text
v0.4 让我看清一件事：

   我上一封说「8 条里真能抓错误的只有 3 条」——
   那不是测试的问题，是我把 L-B 层排除了。

   ⇒ 排除的理由是「机制侧不在本批」，而 B-SCOPE-1 明明列了它们。

   ⇒ 这正是我今天反复犯的那个形状：
     用一个听起来合理的理由（"机制侧不在本批"），
     缩小了实际范围，然后把这个结果当成事实报告。
```

—— Coder，2026-11-28
