# 连续行动先行组测试工作区

- 状态：CA-07 已冻结；`continuous-001` 已完成来源编码与第一道独立审核，正在准备投影、夹具与第二道审核；正式包尚未冻结，正式轮次未运行
- 受测表示：[连续行动结构表示 v0.1](../../../theory/CONTINUOUS-ACTION-REPRESENTATION-0.1.md)
- 执行与结论规则：[CA-06](../../continuous-action-pilot-ca-06-execution-and-verdicts.md)
- 制品与放行规则：[CA-07](../../continuous-action-pilot-ca-07-artifacts-and-release.md)
- 正式包契约：[正式轮次包契约](../../continuous-action-pilot-formal-package-contract.md)

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
- [`run-manifest-0.1.1.schema.json`](schema/run-manifest-0.1.1.schema.json)：为正式包增加原始回答、机器信封、真实 actor 与原始执行制品种类；保留 0.1.0 供既有彩排复算。
- [`ca-sr-artifact-0.1.0.schema.json`](schema/ca-sr-artifact-0.1.0.schema.json)：来源包、CA-SR 规范编码、机械生成视图和投影规则。
- [`build-feasibility-0.1.0.schema.json`](schema/build-feasibility-0.1.0.schema.json)：记录人工门前的工具链可用性与案例级构建阻断，不允许把构建探针写成正式输入或正式结果。
- [`build-feasibility-0.1.1.schema.json`](schema/build-feasibility-0.1.1.schema.json)：增加逐文件证据绑定，并区分许可阻断、兼容探针通过和中性探针通过。
- [`task-packet-0.1.0.schema.json`](schema/task-packet-0.1.0.schema.json)：来源编码、来源审核、重构和预测的冻结派发信封。
- [`task-packet-0.1.1.schema.json`](schema/task-packet-0.1.1.schema.json)：为盲测任务增加允许配置与装配后输出 Schema；保留 0.1.0 供既有轮次复算。
- [`role-submission-0.1.0.schema.json`](schema/role-submission-0.1.0.schema.json)：来源审核、重构、预测和揭示后制品审核的首次提交。
- [`role-submission-0.1.1.schema.json`](schema/role-submission-0.1.1.schema.json)：保留 0.1.0 并给预测期望增加必填 `configuration_id`，修复 `rehearsal-001` 发现的基线／变体寻址缺口。
- [`role-submission-0.1.2.schema.json`](schema/role-submission-0.1.2.schema.json)：把原始盲测 payload、机器信封与装配工具散列绑定到派生提交。
- [`blind-response-interface-0.1.0.schema.json`](schema/blind-response-interface-0.1.0.schema.json)：阶段专用的盲测语义 payload 与机器信封。
- [`execution-artifact-0.1.0.schema.json`](schema/execution-artifact-0.1.0.schema.json)：执行计划、原始轨迹包和派生执行结果。
- [`execution-artifact-0.1.1.schema.json`](schema/execution-artifact-0.1.1.schema.json)：要求执行轨迹直接绑定原始调用／输出，执行结果直接绑定比较器输出。
- [`truth-reveal-0.1.0.schema.json`](schema/truth-reveal-0.1.0.schema.json)：密封真值与揭示后的承诺复算记录。
- [`run-report-0.1.0.schema.json`](schema/run-report-0.1.0.schema.json)：逐角色硬条件向量、两条结论轴、跨案例义务和组级结论。
- [`rehearsal-input-0.1.0.schema.json`](schema/rehearsal-input-0.1.0.schema.json)：仅供虚构彩排使用的条件视图、变体信封与真值承诺。
- [`rehearsal-input-0.1.1.schema.json`](schema/rehearsal-input-0.1.1.schema.json)：保留 0.1.0，并把写死的 `rehearsal-001` 放宽为带三位编号的排演 ID。
- [`markdown-document-0.1.0.schema.json`](schema/markdown-document-0.1.0.schema.json)：把说明性 Markdown 作为完整字符串进行最小格式校验。
- [`text-artifact-0.1.0.schema.json`](schema/text-artifact-0.1.0.schema.json)：把脚本、补丁、日志和其他 UTF-8 文本作为完整字符串进行最小校验。
- [`frozen-set-preimage-0.1.0.schema.json`](schema/frozen-set-preimage-0.1.0.schema.json)：约束冻结集合根摘要所使用的逐行 TSV 前像，便于独立复算。

根摘要应同时通过 [`verify-frozen-manifest.py`](tools/verify-frozen-manifest.py) 复算。校验器只读清单、制品与 Schema；不会修正已经冻结的值。

盲测回答使用 [`build-role-submission.py`](tools/build-role-submission.py) 渲染结构模板、捕获机器信封、确定性装配并复核。修订理由与边界见[盲测回答接口修订](../../continuous-action-pilot-blind-response-interface.md)。

正式包使用 [`verify-run-package.py`](tools/verify-run-package.py) 统一检查 Schema、自声明版本、规范字节、清单与嵌套散列引用、任务输入／输出、冻结集合摘要及冻结锚点提交。`preparing` 包可以通过结构检查；人工门前还必须以 `--require-frozen` 通过。

## 彩排记录

| 轮次 | 结果 | 发现 |
| --- | --- | --- |
| `rehearsal-001` | `procedure_fail` | 预测值缺少配置寻址 |
| `rehearsal-002` | `procedure_fail` | 冻结集合根摘要不可按文档算法复算 |
| `rehearsal-003` | `procedure_fail` | 任务包保留了旧输入散列 |
| `rehearsal-004` | `procedure_pass` | 六项阶段链闭合；完整提交接口仍过于脆弱 |
| `rehearsal-005` | `procedure_pass` | 两种条件的四份原始首答直接有效；机器装配逐字节可重复 |

失败轮次、无效首答和已冻结 README 均原样保留。两次通过都是程序结论，不是理论证据；ADR 0116 的接口限制已经由 `rehearsal-005` 聚焦复测解除。

## 计划中的轮次结构

下列目录只在产生真实制品时建立：

```text
continuous-action-pilot/
├── rehearsals/
│   └── rehearsal-001/
└── runs/
    └── continuous-001/
```

`rehearsals/` 只使用无游戏意义的虚构材料验证阶段顺序或聚焦方法接口，不产生理论证据。`runs/` 才保存正式证据轮次。失败彩排和失效轮次必须永久保留，修订使用新编号。

## 放行边界

增量彩排通过、正式包冻结并推送后，仍须向作者展示冻结提交、制品清单、全部公开哈希、真值承诺、准备性构建状态和已知限制，取得一次明确的“放行正式连续行动试验”。在此之前不得派发四名正式盲测执行者，也不得运行冻结的正式输入。
