# DETACHED ERRATA · 文档瑕疵登记（不改冻结对象）

**日期**：2026-10-09
**性质**：**detached errata。按凌翼建议，不为措辞/摘要级 typo 再改冻结 SPEC/MANIFEST、不制造新 hash 与整套重跑。**

```text
AUTHORITATIVE =
  · exact frozen artifact hash
  · explicit full-hash binding fields
  · detached hash record（MANIFEST_v0.1_HASH.txt）

NON-AUTHORITATIVE =
  · stale human-readable summary prefixes（旧摘要前缀）
  · 冻结记录内的陈旧 metadata
```

---

# 一 · 已在本轮修正的（不属 errata，已改）

```text
BD-55（睫，BLOCKING）：MANIFEST §十五 残留旧摘要前缀 70c69bd3… / 47daf79b…
   -> 已改：§十五 不再重复写死数值，改为引用 §八/§十一（唯一真值）。
   真值：J_RULE_BUNDLE_HASH = 472aaec1… ；DISCRIMINATION_RULESET_HASH = 770fb3ec…
```

---

# 二 · 冻结记录内陈旧 metadata（NON-BLOCKING，按凌翼建议留 errata 不改）

```text
文件：reports/REFERENCE_HARNESS_SPEC_v0.1_FROZEN_20261008.md
瑕疵：§一 canonical byte 表写 LF = 1664，但同文件写 LINES = 1669；
      凌翼对真正 frozen SPEC bytes 实测：CR=0, LF=1669, FINAL_NEWLINE=exactly one。
判定：LF=1664 是陈旧/错误 metadata。
影响：不影响 frozen SPEC 的 hash / byte count（SPEC 身份不变）。
处置：不改冻结记录（避免制造新 hash）；在此 detached errata 登记。
```

---

# 三 · 措辞更正（睫 point 三）

```text
原措辞（已更正）："磁盘上不存在 36485 B 的 SPEC 文件"
更正为：1386ba22… 为加冻结标记【前】版本（36485 B / 1664 行）；
        副本已由睫实机复算留存，记为 SUPERSEDED，非"不存在"。
```

**第一百五十一句**：不许把"我这儿没有"，当成"它不存在"。那 5 行 diff 在睫手上，它活着，能算出来。

---

# 四 · 两个消费者共用一枚 hash（睫 observation①，NON-BLOCKING）

```text
READ_OPERATOR_HASH = LITERAL_CONSUMER_HASH = 83cbc20b…（同属 readers.py）
后果：fail-safe（改任一函数 ⇒ 整文件 hash 变 ⇒ 两条路径都 requalify）。
粒度：粗，无法表达"只换 reader、literal consumer 未变"。
处置：已在 MANIFEST §七 注明"readers.py 任一变动 ⇒ 两条读路径全部重验"。
      （函数级 sub-hash 留作后续可选项，非当前 blocker。）
```

---

# 五 · access-side 同名消歧（睫 observation②，已入 MANIFEST §十）

```text
逻辑层 access 声明 -> LOGICAL_ACCESS_DECLARATION
OS 级真隔离 witness -> ACCESS_SIDE_WITNESS（待实现）
避免 OS 级落地后两个同名 witness（一个 PASS 一个真隔离）。
```

---

# 六 · 其余 observation（已在 §十一/§十二 落实）

```text
③ h 计算式：已在 MANIFEST §十一 钉死 —— h = literal 字节差异数；q 差异不计入 h。
④ L1_FAILURE_WITNESS_HASH 与 V0/V0b FIXTURE_RULE_BUNDLE_HASH 同值：已注明"复用同一对象"。
⑤ 文件截断：canonical 文件完整（21424 B）；渲染版末尾截断为显示问题。
```

---

**—— Coder · 2026-10-09（detached errata，非冻结对象）**
