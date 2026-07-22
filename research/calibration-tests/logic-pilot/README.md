# 逻辑解谜先行组测试工作区

- 状态：目录、JSON 约定、判定与执行方法已接受；`rehearsal-001` 已以 `procedure_pass` 完成，`logic-001` 的四份盲测首次提交已冻结，答案承诺已经揭示并复算一致，正在形成正式报告
- 决定：[ADR 0106](../../../docs/adr/0106-use-versioned-json-run-artifacts-for-logic-pilot.md)
- 方法：[第二轮案例校准协议](../../calibration-cycle-2-protocol.md)
- 隔离：[ADR 0105](../../../docs/adr/0105-use-procedural-blinding-and-answer-commitments-for-logic-pilot.md)
- 执行：[ADR 0108](../../../docs/adr/0108-freeze-logic-pilot-execution-representation-and-rehearsal.md)

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

rehearsals/<rehearsal_id>/
├── README.md
├── manifest.json
├── instructions/
├── inputs/
├── commitments/
├── submissions/
├── reveal/
└── reports/
```

`runs/` 只保存正式证据轮次；`rehearsals/` 使用虚构材料验证流程，不能产生**强检验结论**。彩排失败也必须保留，并以新编号重试。

Git 只在目录出现真实制品时跟踪它。当前已经冻结协议信封、判定和污染字段；`logic-001` 已随实际输入建立重构、网格、图、状态与规则词块 payload／response Schema，没有用空泛通用格式预判理论。

`logic-001` 的受测表示固定为[游戏原语结构表示 v0.1](../../../theory/STRUCTURAL-REPRESENTATION-0.1.md)。首个 `frozen` 提交之后，任何测试者可见字节变化都建立新轮次，不在原轮次回写。

## 当前 Schema

- [`run-manifest.schema.json`](schema/run-manifest.schema.json)：轮次状态与制品索引；
- [`answer-commitment.schema.json`](schema/answer-commitment.schema.json)：公开**答案承诺**记录，不含答案或随机数；
- [`logic-input.schema.json`](schema/logic-input.schema.json)：随机化输入包信封，不规定具体 payload 结构；
- [`logic-submission.schema.json`](schema/logic-submission.schema.json)：回答、测试者范围与污染记录；
- [`logic-truth.schema.json`](schema/logic-truth.schema.json)：揭示后的内部映射、硬条件、逐项精确预期、输入哈希与随机化记录；
- [`logic-reveal.schema.json`](schema/logic-reveal.schema.json)：正式轮次的随机数揭示、真值哈希与承诺复算记录；
- [`logic-report.schema.json`](schema/logic-report.schema.json)：逐项结果、污染影响和**强检验结论**。
- [`source-packet.schema.json`](schema/source-packet.schema.json)：来源编码者可见的一手事实、内容机械转写与范围边界；
- [`source-encoding.schema.json`](schema/source-encoding.schema.json)：GP-SR 0.1 的来源视图与中性盲测视图；
- [`source-fidelity-audit.schema.json`](schema/source-fidelity-audit.schema.json)：绑定来源定位的忠实度异议与冻结裁决；
- [`rehearsal-arithmetic.schema.json`](schema/rehearsal-arithmetic.schema.json)：流程彩排使用的虚构算术 payload 与回答结构；
- [`rehearsal-truth.schema.json`](schema/rehearsal-truth.schema.json)：流程彩排揭示后的精确真值包；
- [`rehearsal-reveal.schema.json`](schema/rehearsal-reveal.schema.json)：流程彩排的随机数揭示与承诺复算记录；
- [`rehearsal-report.schema.json`](schema/rehearsal-report.schema.json)：九项全有或全无的流程彩排裁决。
