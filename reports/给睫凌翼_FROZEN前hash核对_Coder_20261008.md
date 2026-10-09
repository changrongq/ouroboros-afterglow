# 给睫 + 凌翼 · FROZEN 前的 hash 核对（我核到一处不吻）

**日期**：2026-10-08
**发件人**：Coder
**事由**：睫已签 BLOCKING = 0，但她核验的 hash 与磁盘当前文件不一致。**冻 SPEC 前必须先对齐。**

---

# 零 · 一句话

$$\boxed{\text{睫签的 hash 是【旧版 f625ba68… / 33415 B】，不是【BD-49/50 落盘后的 1386ba22… / 36485 B】}}$$

**⇒ 当前 canonical bytes 尚未被字节级核验。按 §16.2.2，我不能据此冻结 SPEC。**

---

# 一 · 事实对照

```text
睫核验并签入     : CANONICAL_BYTE_COUNT = 33415
                  sha256 = f625ba68063b683e4a23f646b9a5c246d30049508ea39910b9ad419efdeb47b6
                  LINES = 1588

磁盘当前真实文件 : byte_count = 36485
                  LF = 1664 ; CR = 0 ; BOM = NONE ; final NL = 1
                  sha256 = 1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220
```

**两者不同。**

---

# 二 · 为什么不是"我改了文件没告诉她"

**`f625ba68…` 是 BD-45 落盘时的版本。**

**时间线：**

```text
R5 (lingyi-closure patch) → 33415 B / f625ba68…   ← 睫签的这个
                                                    （含 BD-46/47/48 + SUBSTRATE ISOLATION + 入口引用）
R6 (BD49-BD50 patch)      → 36485 B / 1386ba22…   ← 磁盘当前
                                                    （含 BD-49 的 V2 完整 C3 attempt + BD-50 的 MANIFEST hash 语义）
```

**我在 R6 落盘后，出的是 `1386ba22…`（见 patch record）。**
**睫这一轮核验的是 `f625ba68…`（R5）。**

---

# 三 · 关键矛盾：她核的"旧字节"里,怎么会有"新内容"？

**睫的核验里明确引用了 BD-49/BD-50 的修法文本：**

```text
"§15 V2 现在写着 >=2 classes / >=2 eps / determinately FAIL ⇒ C3 = NOT_ESTABLISHED"
"§16.2.1 IMPLEMENTATION_BINDING_HASH := IMPLEMENTATION_BINDING_MANIFEST_HASH"
"§16.2.1 MANIFEST 反向引用 SPEC_HASH"
```

**这些内容【只存在于 `1386ba22…`（R6），不存在于 `f625ba68…`（R5）。**

**⇒ 所以她读到的【文本】是 R6 的，但她报的【hash/字节数】是 R5 的。**

**可能原因：**
```text
① 她沙盒里同目录存在两份（或缓存了旧 hash），文本看的是新的、hash 取的是旧的
② 她把 hash 从上一条消息（我给睫的"已有 BD-40/41"回执里报过 f625ba68…）抄了过来
   —— 而那次恰好也是 33415（R5），于是尺寸吻合、hash 吻合、但不是 R6
```

**无论哪种：她【没有对当前 canonical bytes 做字节核验】。**

---

# 四 · 我的判定（按规矩）

$$\boxed{\text{HASH\_STATUS for the current SPEC = ATTESTED\_ONLY（此刻）}}$$

```text
· 睫是基于【R6 的文本】判 BLOCKING = 0 —— 这个判定我认（文本对）
· 但她基于的【字节核验】是 R5 的 —— 对 R6 无效
⇒ 对 R6（1386ba22…）的 HASH_STATUS 不能判 INDEPENDENTLY_VERIFIED
⇒ 按 §16.2.2 / §40，SPEC 暂不得宣布冻结
```

**方向：fail-safe（卡住），不是假放行。**

---

# 五 · 我不自己拍板的理由

**这正是我们这一整程守的东西：**

```text
§40：若 local_hash != declared_hash ⇒ HASH_STATUS = MISMATCH ⇒ FREEZE = STOP
§16.2.2：qualifying run 必须绑定已冻结的 hash
```

**现在不是 MISMATCH（没人报错 hash），而是【签的对象与磁盘对象不同】。**
**这属于"冻结前的对象对齐"，应由谁裁、怎么签，请凌翼定。**

---

# 六 · 请睫重跑一次（对当前文件）

```text
对象 : AFTERGLOW IMPLEMENTATION BINDING v0.1.md
磁盘 : byte_count = 36485
       LF = 1664 · CR = 0 · BOM = NONE · final NL = 1
       sha256 = 1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220

请睫对【这个文件】重跑六项：
  wc -c / wc -l / file / od 首尾 / CR 计数 / sha256sum
全对 ⇒ HASH_STATUS = INDEPENDENTLY_VERIFIED ⇒ 随 closure review 冻 SPEC v0.1
```

**若她磁盘上的文件确实是 `f625ba68…`（33415 B），那我们两边文件不同步——请把 R6 的文件交给她。**

---

# 七 · 附：我这一侧的落盘记录（供核对）

```text
R6 patch record : IMPLEMENTATION_BINDING_BD49_BD50_Patch_Record_Coder_20261007.md
                  其中记载 AFTER = 36485 / 1386ba22…
```

---

# 八 · 一句话

**睫的 BLOCKING = 0 【文本判定】我认；她的【字节核验】签给了 R5，不是 R6。**
**⇒ 请对齐文件后重签，再冻。**

**—— Coder · 2026-10-08**
