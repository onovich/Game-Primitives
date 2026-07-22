# 逻辑解谜先行组测试工作区

- 状态：目录、JSON 约定、判定与污染字段已接受；`logic-001` 正在准备；尚未开始取证
- 决定：[ADR 0106](../../../docs/adr/0106-use-versioned-json-run-artifacts-for-logic-pilot.md)
- 方法：[第二轮案例校准协议](../../calibration-cycle-2-protocol.md)
- 隔离：[ADR 0105](../../../docs/adr/0105-use-procedural-blinding-and-answer-commitments-for-logic-pilot.md)

本目录保存逻辑解谜先行组每次测试的公开证据链。结构化制品以 JSON 为唯一数据来源；Markdown 只写任务说明、阅读导航和从 JSON 生成的视图。

## 固定约定

- JSON：UTF-8 无 BOM、LF、两个空格缩进、ASCII 小写 `snake_case` 字段、对象键排序、一个末尾换行。
- Schema：JSON Schema Draft 2020-12；每个制品显式记录协议或模式版本。
- 校验：轮次清单记录正式制品的相对路径、类型、版本与 SHA-256。
- 隔离：答案、映射与 `secret_nonce` 在揭示前保存在仓库外；本目录不得创建 `private/`、`hidden/` 或未跟踪答案副本。
- 追加：**首次提交**产生后，输入、承诺和该提交均不可覆盖；实质修订建立新轮次。

## 轮次结构

```text
runs/<run_id>/
├── README.md
├── manifest.json
├── instructions/
├── inputs/
├── commitments/
├── submissions/
├── reveal/
└── reports/
```

Git 只在目录出现真实制品时跟踪它。当前已经冻结协议信封、判定和污染字段；具体网格、图、状态与规则词块 payload Schema 将随 `logic-001` 实际输入一起建立，避免用空泛通用格式预判理论。

## 当前 Schema

- [`run-manifest.schema.json`](schema/run-manifest.schema.json)：轮次状态与制品索引；
- [`answer-commitment.schema.json`](schema/answer-commitment.schema.json)：公开**答案承诺**记录，不含答案或随机数；
- [`logic-input.schema.json`](schema/logic-input.schema.json)：随机化输入包信封，不规定具体 payload 结构；
- [`logic-submission.schema.json`](schema/logic-submission.schema.json)：回答、测试者范围与污染记录；
- [`logic-truth.schema.json`](schema/logic-truth.schema.json)：揭示后的内部映射、硬条件与预期判断；
- [`logic-report.schema.json`](schema/logic-report.schema.json)：逐项结果、污染影响和**强检验结论**。
