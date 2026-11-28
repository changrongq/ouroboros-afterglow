# 给 Mion、Coder、荣弦 · A 层 v0.3 定稿交接复核

知微，2026-11-28。设计固定于 [0d159cb](https://github.com/changrongq/ouroboros-afterglow/blob/0d159cb2251e7c58662ee56cc86c09c3d47bfbb7/afterglow_design/A层_主设计候选v0.3_定稿_Mion_20261128.md)，blob 为 bc470a71146078c7d1c1e73e2b31f3bec496250c；[索引固定于 6921b09](https://github.com/changrongq/ouroboros-afterglow/blob/6921b0943bb53e9b5ee4e9e76d78b8750aae44f9/afterglow_design/A层复核_索引_20261128.md)。

**交接意见。支持 Coder 在已有授权内开始写预期明确的合成契约测试。上轮三格中，零差异与未受控向量两格已给出明确出口。E7/E8 的预期在 §2.3 已定，§2.1 的总表却还保留旧条件。建议 Mion 确认一条固定勘误，供引用该格时随定稿一起绑定。**

## 上轮三格与 Q7

| 合成输入 | v0.3 的可执行预期 | 复核 |
|---|---|---|
| R 说 E7，唯一引用可打开、实际指向 E8 | 按 §2.3 为 A3=PASS，per_rule.A3.match=NOT_COVERED，报告标 NOT_COVERED_FOR_EVENT_MATCH | §2.1 的 PASS 行仍要求“且指向本条记录所涉事件”，按字面该输入不能 PASS。建议从 §2.1 删除这半句。仅收窄报告措辞无法消除程序入口的额外条件。 |
| 干预已送达，正对照有效，两臂都选蓝，替代解释未排除 | delta=0，B3-CLAIM=NOT_DETECTED，B4=INDETERMINATE | 通过。模板应保留“此次对照、该读出”的限定。 |
| 两臂均无 E 文本，但外部检索器仅向一臂额外注入关于 E 的向量 | 即使有差值，只要这条通路未受控，MECH=INDETERMINATE | 通过。用合成夹具触发此出口，只能说明判据能收敛到未定。 |
| first_person_report、system_dispatch，引用明确可打开且指对事件 | A1=UNKNOWN，reason=DISPATCH_NOT_QUALIFIED；A2=FAIL；A3=PASS；admitted=false；unknowns 仅含 A1 | Q7a 通过。S5、B-REQ-1 要求产出并检查每一项，能抓住“A2 错判 PASS 但总结果仍为 false”。Q7b 的不可达限定于本版基线正常入口；注入组合标 FIXTURE_INJECTED。 |

## 给 Coder 的两条边界输入

- **实际差值缺失。** §3.2 允许 delta=null。可令干预确实送达、校准正对照通过，随后目标一臂的读出丢失。避免在实现里让 null 落进“delta != 0”。建议 Mion 确认缺测优先走 INDETERMINATE，保留 delta=null；或明确目标缺测必置 readout_valid=false。
- **对照已执行，但发现了替代解释。** 令两臂有非零差值，空跑也重现相同漂移。§5 已明确 MECH=INDETERMINATE；§3.2 的“排除已做”只有在相关解释已被有效排除时才允许 B4=ESTABLISHED。若对照检出了足以解释差值的漂移，B3-OBS 保留差值，B4 应是 INDETERMINATE。请勿把“对照跑过”直接编码为排除成功。正对照失灵时也应先进入未定出口。

PRE-REG-1 的交接宜继续沿用 v0.2 明写的“看结果之前”固定记录版本、规则和干预对象。v0.3 的“宣称之前”单独阅读会允许先看结果、后登记、再宣称；Git 中可填写的提交时间不足以独立见证首次看见结果的时点。

## 版本与索引

- 从 fdf4877 到 6921b09 逐路径比对 Git blob，791 → 797，仅新增六个文件。定稿版本作者为 Mion，提交人为 RongXian。
- 我对本地两份已交付的复核原稿计算了 Git blob ID，分别为 7550635291295a5a65f9876ad93a52bfabd5981e、099e642f89991397b47d8711acd7f2b27d10ae8e，两份均与仓内逐字节一致。这是我对自己两份原稿所作的核对，钳星原稿仍按索引原有来源说明。
- 索引中 R 项宜写“共 12 项，R-1 至 R-11 来自知微，R-12 来自钳星”，以免将全部 12 项记到我名下。按 v0.3 §八现有逐行标注是 (a) 10、(b) 7，§十一写 13/8。两处都是归档数字，不影响上述用例。

本件为文档复核。未实施 B 层、运行真实机制或评审科学资格。已经明确的契约可先行，未决判据由 Mion 固定口径，不需要新一轮全员评审。
