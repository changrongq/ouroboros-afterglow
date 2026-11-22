# AfterGlow-A 原型 · 实施状态

最后更新：2026-11-22
固定点基线：`7e62cacfc0ed547e91b35698d439f5907c11be42`

---

## 一 · 现在到底能做到什么

```text
P1  来源五值闭集，缺省 unknown .................... ✅ 已实现，13→14 项测试覆盖
P2  修改留上一版摘要，链可校验 ..................... ✅ 已实现，含篡改检测
P3  纠正后旧版仍在且可指认 ........................ ✅ 已实现
P4  能报告「不知道」而不自动填值 ................... ✅ 已实现
P5  取回结果与期望集对比，区分五值 ................. ✅ 已实现（+ partial_overlap 单列）
```

**验收结果（可复跑）**

```text
python afterglow_a/prototype/test_p1_p5.py
  ⇒ 合计 14  通过 14  失败 0

python afterglow_a/prototype/test_mutations_v4.py
  ⇒ 变异 9：CAUGHT 7 / REDUNDANT 2 / MISSED 0 / INVALID 0
  ⇒ VERDICT: PASS
```

结果文件：`prototype/reports/p1_p5_result.json`、`prototype/reports/mutation_result.json`

---

## 二 · 这些通过【不能】说明什么

```text
✗ 不能说明 AfterGlow 记得任何东西
✗ 不能说明任何记忆机制成立
✗ 不构成 C1 / C2 / C3 任何一级证据
✗ 不代表真实角色的历史被修复了
✗ 不代表 Q3 被触动
```

代码里已把这个边界写成字段：

```python
"engineering_only": True,
"is_scientific_result": False,
```

并有测试守着（`NC 工程结论不得冒充科学结果`）。
变异测试 M6 专门验证：如果有人把它改成 `True`，测试会红。

---

## 三 · 变异测试暴露的三次真实问题（按发生顺序）

这一节比第一节重要。**14/14 全绿的时候，有三个检查是哑的。**

### 3.1 第一次：切在了影子上

```text
做法：setattr(module, 'classify_match', ...)
结果：3 个变异"未被捕获"
真因：被测模块用 `from afcore import classify_match` 绑定了名字，
      改模块属性对已绑定引用无效。
⇒ 我的手术刀切在了影子上，不是检查不响。
```

### 3.2 第二次：假绿（最严重）

```text
v2 逻辑：missed = [r for r in applied if not r["caught"]]
问题：未生效的变异被排除在分母外
结果：7 个变异只生效 1 个，却输出"全部变异被捕获 ⇒ 断言不是空转"
⇒ 这是「检查没跑，报告说通过」。
⇒ 比「检查没响」更坏一档：没响还报了通过。
修复：INVALID 必须计入失败；只有 CAUGHT+VALID_REDUNDANT 全覆盖才 PASS。
```

### 3.3 第三次：把纵深防御误判成漏洞

```text
M3/M3b 未被捕获 → 我第一反应是"产品有缺口"。
查证后：prev_digest 为空有两道独立检查（validate 写入侧 / verify_chain 读取侧），
        去掉一道另一道仍会拦。
⇒ 是真·冗余，不是漏洞。

但这里有个陷阱：
  如果允许"没捕获就说是冗余"，以后每漏一个都能这么讲。
⇒ 判定规则收紧：
  凡未捕获的变异，必须在代码里注册 redundant_with，
  并由程序【实测】那道退路真的拦得住；
  拦不住，或没注册，一律判 MISSED。
```

```text
⇒ 记法：会失败的检查，最怕的不是失败，是没响。
  本次追加一条：更怕的是【没响，还报了响】。
  以及：解释一个好结果之前，先确认它是不是真的跑过。
```

### 3.4 第四次：钳星审出的跨平台 bug（2026-11-22，别人发现的）

```text
钳星在 cp936（Windows 默认 GBK）控制台下实跑，报：

  UnicodeEncodeError: 'gbk' codec can't encode character '\u21d2'
  File ".../test_mutations_v4.py", line 235
  ⇒ 脚本以 exit 1 退出

⇒ 判定数字其实已经算出来了（CAUGHT 7 / REDUNDANT 2 / MISSED 0），
  但最后打印那行 `⇒ 现有断言不是空转` 崩了，观感是"失败"。
```

**我复现了，并且查到比钳星报的更准的一层：**

```text
three scripts 的表现不同：

  probe_source_role.py      已有 reconfigure   OK
  test_p1_p5.py             第 171 行的 ⇒ 在【注释】里，不输出  OK
  test_mutations_v4.py      第 235 行的 ⇒ 在【print】里，崩      崩溃

⇒ 关键不是"哪个文件有 ⇒"，是"哪个 ⇒ 会被打印出来"。
⇒ 我第一眼看到 test_p1_p5.py 也有 ⇒ 会以为钳星报错了 —— 差点判错。
```

**根因不是编码，是验证范围：**

```text
我在 A 文件 §九 写了「Python 3.9+，无第三方依赖」，
还写了「若你的结果与我写的不一致，那是我的错」。

⇒ 但我只在 UTF-8 终端里跑过。
⇒ 「跨平台可复算」是一句承诺，我验证的是"我这台机器可复算"。
⇒ 钳星是第一个在非 UTF-8 终端跑它的人。
```

**修法（两件一起做，缺一件都不够）：**

```text
1. 加 _harden_stdio()：stdout/stderr 优先 reconfigure(utf-8)，
   失败则 reconfigure(errors="backslashreplace")，绝不因输出崩溃。
2. 把 print() 里的 ⇒ / → 全部换成 ASCII（=> / ->）。
   ⇒ 只做 1，在真正的 GBK 控制台（不是模拟的）仍可能出问题；
   ⇒ 只做 2，别的非 ASCII 字符（中文）仍可能崩。
   ⇒ 两个都做才稳。
```

**验证（双编码，且证明检查不是空转）：**

```text
python .local_scratch/verify_both_enc.py
  ⇒ 三个脚本 × UTF-8/GBK = 6/6，且判定数字确实被打印出来
     （不只看 rc=0，还 grep CAUGHT 7 / REDUNDANT 2 / MISSED 0 / VERDICT: PASS）

python .local_scratch/mut_gbk.py
  ⇒ 把 _harden_stdio 改成 no-op，GBK 下重新崩溃（rc=1）
  ⇒ 证明上面的 6/6 不是空转
```

```text
⇒ 记法：把「可复算」写成承诺之前，先问：我在几种环境下跑过？
⇒ 只在一种终端验证过的东西，不能叫「跨平台」。
⇒ 钳星这一条虽不属「偷换研究对象」，但它比很多实质意见更有用：
  它说明我的「已通过」是有环境前提的。
```

---

## 四 · 原型覆盖不到的地方（诚实清单）

| 缺口 | 说明 | 为什么不补 |
|---|---|---|
| **并发写** | 只有单写者假设，两个进程同时 revise 会丢版本 | 最小原型刻意不做；知微 §1.3 问题待答 |
| **持久化** | 全内存，无磁盘落盘 | 不做持久化就测不出「断电后链是否还完整」 |
| **真实数据迁移** | 只跑合成资料 | 凌翼 §三 明令不得改真实角色历史 |
| **检索质量** | selector 是简单子串匹配 | P5 只验「取回的是不是写进去的」，不验相关性 |
| **权限** | `change_authority` 是自由字符串，无人校验 | 授信体系不在本次范围 |
| **`model_echo` vs `system_generated`** | 两者边界我怀疑自己划错了 | 已列为给衔环的问题，未解决 |

---

## 五 · 下一步（若凌翼允许）

```text
1. 持久化：加落盘 + 断电重启后链校验（能把 P2 从"内存内可校验"升到"落盘后可校验"）
2. 并发：加单写者锁，或改成追加日志
3. 把 §四 第一行「source_role 误标」在合成数据上做一次【迁移演练】，
   证明 pending_verification 规则（设计 §四 M2）可执行
   —— 仍然不碰真实数据
```

```text
⇒ 以上都不是科学实验，都是工程检查。
⇒ 都需要凌翼点头才做，因为涉及"新增运行时实现"。
```
