# `logic-001`

- 状态：`frozen`；尚未进入 `collecting`
- 目的：逻辑解谜与状态空间组第一次强检验方法试验
- 当前内容：`rehearsal-001` 已通过；`source-encoding-v0.1.3` 已通过独立**来源忠实度审核**；4 个重构项目、8 个匿名夹具项目、任务说明、payload／response Schema 与**答案承诺**已冻结

清单中的 `protocol_version: 0.3.0` 包含 D2-5a–c 的隔离、制品、判定、污染与行为边界，以及 D2-6 的执行配置、GP-SR 0.1、彩排、冻结纪律和人工放行门。

## 冻结输入

| 输入 | 项目数 | SHA-256 |
| --- | ---: | --- |
| `inputs/reconstruction-input.json` | 4 | `59d5b07a5682fc38af20dcf5a4c9b8382d922922b53e135e7c385d03c8cc613b` |
| `inputs/annotation-input.json` | 8 | `4c74dec698c8e60e0db278ad5f9b708110fc5bde5352635d658d8894573d14ce` |

公开**答案承诺**为 `6241d17b5bd5fd748184d6ee84dff7a34796533f8512a91a31463521f43691d1`；精确真值、随机种子、逻辑映射、配对与 `secret_nonce` 已在仓库外密封。公开包的制作与校验见 [`reports/formal-package-build-log.md`](reports/formal-package-build-log.md)。

来源编码、独立审核与正式包制作均已完成。当前只等待作者检查冻结提交、制品清单、公开哈希与承诺并明确放行；放行后才把状态改为 `collecting`，向两名**重构者**和两名**夹具标注者**派发完全相同的对应输入。

本轮首次 `frozen` 提交以后，任何测试者可见字节变化都不得回写；若必须修改，保留本轮并建立 `logic-002`。本轮尚未派发盲测任务，也没有产生重构或标注提交。
