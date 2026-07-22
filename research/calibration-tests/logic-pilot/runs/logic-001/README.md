# `logic-001`

- 状态：`reported`；正式结论为 `pass_in_scope`（**范围内通过**），四份证据均因原型识别或怀疑而降级保留
- 目的：逻辑解谜与状态空间组第一次强检验方法试验
- 当前内容：`rehearsal-001` 已通过；`source-encoding-v0.1.3` 已通过独立**来源忠实度审核**；4 个重构项目、8 个匿名夹具项目、任务说明、payload／response Schema 与**答案承诺**已冻结

清单中的 `protocol_version: 0.3.0` 包含 D2-5a–c 的隔离、制品、判定、污染与行为边界，以及 D2-6 的执行配置、GP-SR 0.1、彩排、冻结纪律和人工放行门。

## 冻结输入

| 输入 | 项目数 | SHA-256 |
| --- | ---: | --- |
| `inputs/reconstruction-input.json` | 4 | `59d5b07a5682fc38af20dcf5a4c9b8382d922922b53e135e7c385d03c8cc613b` |
| `inputs/annotation-input.json` | 8 | `4c74dec698c8e60e0db278ad5f9b708110fc5bde5352635d658d8894573d14ce` |

公开**答案承诺**为 `6241d17b5bd5fd748184d6ee84dff7a34796533f8512a91a31463521f43691d1`。四份**首次提交**冻结后，[精确真值](reveal/logic-truth.json)与 [`secret_nonce`、承诺复算记录](reveal/logic-reveal.json)才进入仓库；复算摘要与冻结承诺一致。公开包的制作与校验见 [`reports/formal-package-build-log.md`](reports/formal-package-build-log.md)。

来源编码、独立审核、正式包制作和双份独立收集均已完成。两名**重构者**收到完全相同的重构材料，两名**夹具标注者**收到完全相同的标注材料；同类首次提交在双方返回前彼此不可见。

[正式比较报告](reports/logic-001-comparison.md)记录了逐项证据、污染降级与主张边界；[机器可读报告](reports/logic-report.json)保存冻结结论。两名标注者各自得到 16／16 个预期判断，两名重构者都恢复了表达四项硬条件所需的来源规则结构，故四项硬条件综合判为 `recovered`。这只支持本轮 `structural_only` 范围，不证明 GP-SR 0.1 完整、最小或普适。

本轮首次 `frozen` 提交以后，任何测试者可见字节变化都不得回写；若必须修改，保留本轮并建立 `logic-002`。收集期间，同类两份**首次提交**在全部返回前保持彼此不可见，随后才写入共享工作区。
