# 连续行动先行组测试工作区

- 状态：CA-07 已冻结；工作区与 Schema 已建立，尚未建立彩排或正式轮次
- 受测表示：[连续行动结构表示 v0.1](../../../theory/CONTINUOUS-ACTION-REPRESENTATION-0.1.md)
- 执行与结论规则：[CA-06](../../continuous-action-pilot-ca-06-execution-and-verdicts.md)
- 制品与放行规则：[CA-07](../../continuous-action-pilot-ca-07-artifacts-and-release.md)

本工作区保存连续行动方法试验的结构化制品。当前授权仅覆盖 Schema、来源编码、来源审核、夹具准备、比较器准备和虚构材料的增量彩排，不授权正式盲测、三案冻结输入的精确执行或真值揭示。

## 固定约定

- JSON Schema 使用 Draft 2020-12；每个 Schema 文件名和制品都显式记录版本。
- JSON 使用 UTF-8 无 BOM、LF、两空格缩进、稳定键序和单一末尾换行。
- SHA-256 对精确文件字节计算；不对重新序列化后的“语义等价内容”计算。
- 每个 Schema 家族以 `artifact_type` 和封闭 `oneOf` 区分制品种类。
- 对象默认 `additionalProperties: false`；禁止 `custom`、任意 `parameters` 和未声明属性。
- 需要动态数量的内容使用带稳定 ID 的数组，不使用任意属性名映射。
- Schema 文件一经正式轮次引用便保持不变；语义变化发布带新版本的文件。
- 明文真值、条件映射和 `secret_nonce` 在揭示前不得进入本工作区。
- 首次 `frozen` 提交后，测试者可见内容、投影、变体、比较器、容差和真值不得回写。
- Markdown 只负责说明与导航；JSON 是结构化事实源。

## Schema

- [`run-manifest-0.1.0.schema.json`](schema/run-manifest-0.1.0.schema.json)：正式轮次或彩排的状态、阶段、制品索引、冻结集合摘要和真值承诺。
- [`ca-sr-artifact-0.1.0.schema.json`](schema/ca-sr-artifact-0.1.0.schema.json)：来源包、CA-SR 规范编码、机械生成视图和投影规则。
- [`task-packet-0.1.0.schema.json`](schema/task-packet-0.1.0.schema.json)：来源编码、来源审核、重构和预测的冻结派发信封。
- [`role-submission-0.1.0.schema.json`](schema/role-submission-0.1.0.schema.json)：来源审核、重构、预测和揭示后制品审核的首次提交。
- [`execution-artifact-0.1.0.schema.json`](schema/execution-artifact-0.1.0.schema.json)：执行计划、原始轨迹包和派生执行结果。
- [`truth-reveal-0.1.0.schema.json`](schema/truth-reveal-0.1.0.schema.json)：密封真值与揭示后的承诺复算记录。
- [`run-report-0.1.0.schema.json`](schema/run-report-0.1.0.schema.json)：逐角色硬条件向量、两条结论轴、跨案例义务和组级结论。

## 计划中的轮次结构

下列目录只在产生真实制品时建立：

```text
continuous-action-pilot/
├── rehearsals/
│   └── rehearsal-001/
└── runs/
    └── continuous-001/
```

`rehearsals/` 只使用无游戏意义的虚构材料验证“重构冻结 → 预测 → 执行 → 揭示”的新增顺序，不产生理论证据。`runs/` 才保存正式证据轮次。失败彩排和失效轮次必须永久保留，修订使用新编号。

## 放行边界

增量彩排通过、正式包冻结并推送后，仍须向作者展示冻结提交、制品清单、全部公开哈希、真值承诺、准备性构建状态和已知限制，取得一次明确的“放行正式连续行动试验”。在此之前不得派发四名正式盲测执行者，也不得运行冻结的正式输入。
