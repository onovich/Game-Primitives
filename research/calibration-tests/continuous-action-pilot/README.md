# 连续行动先行组测试工作区

- 状态：`continuous-001` 因参与者预测接口不可构造而在正式输入执行前失败关闭；协议 0.1.1 的阶段契约、类型化模板、隔离门前检查与四席两阶段首答已由 `rehearsal-006` 全部验收，下一步建立 `continuous-002` 的增量契约与门前候选包
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
- [`task-packet-0.1.2.schema.json`](schema/task-packet-0.1.2.schema.json)：增加第二道 `projection_audit_task_packet`，强制直接绑定机械生成器、投影规范和两份生成视图，并审核唯一变量、中性不变量定义、结构引用闭包、第二阶段输入闭包、投影忠实度、等价闭包与派发对称性；预测任务中的匿名初态、正式输入、不变量、容差和停止点规格必须和中性信封逐项相同。保留旧版本供既有轮次复算。
- [`fixture-lock-0.1.0.schema.json`](schema/fixture-lock-0.1.0.schema.json)：把三案来源身份、构建门、正式输入与比较器锁定，并分别记录兼容、观察和规则变体是补丁、不适用还是仅配置实现，禁止以空白补丁填位。
- [`formal-build-readiness-0.1.0.schema.json`](schema/formal-build-readiness-0.1.0.schema.json)：要求三案的基线与变体配置最终构建全部通过，并绑定构建证据和仓库外输出散列；历史工具链探针不能代替它。
- [`formal-human-gate-authorization-0.1.0.schema.json`](schema/formal-human-gate-authorization-0.1.0.schema.json)：约束冻结后才允许建立的一次性人工放行凭据；正式分支必须绑定清单中的冻结提交、根摘要与真值承诺，以及最终构建记录、夹具锁、投影审核、授权 Schema、派发器、执行许可 Schema／物化器／校验器和只读准备门校验器。合成分支只有在系统临时目录中的无 Git、带专用标记副本里才可物化虚构回执；生产策略明确拒绝它。授权凭据本身不进入冻结清单，避免哈希循环。
- [`formal-execution-permit-0.1.0.schema.json`](schema/formal-execution-permit-0.1.0.schema.json)：约束四席预测冻结后机械派生的正式执行许可；它同时绑定正式人工授权、规范预测集合前像与摘要、R1—R3 案例范围、正式执行／比较范围，以及每案运行器、输入、测试体、比较器、支持制品和轨迹 Schema 的精确执行目标，并禁止在正式输入已执行或正式结果已产生后物化。
- [`stage1-seat-dispatch-envelope-0.1.0.schema.json`](schema/stage1-seat-dispatch-envelope-0.1.0.schema.json) 与 [`stage2-seat-dispatch-envelope-0.1.0.schema.json`](schema/stage2-seat-dispatch-envelope-0.1.0.schema.json)：区分永不放行的逐席惰性模板与门后、逐字节绑定授权和参与者输入的新建派发回执。
- [`stage1-cohort-lock-0.1.0.schema.json`](schema/stage1-cohort-lock-0.1.0.schema.json)：只有四席第一阶段回执、原始回答、机器信封和有效重构提交全部冻结后，才允许建立共同第二阶段输入锁。
- [`variant-envelope-0.1.0.schema.json`](schema/variant-envelope-0.1.0.schema.json)：只允许盲测者所需的中性变量、配置、观测、不变量、停止和容差信息，不提供来源路径或预期结果；用匿名字段自包含初态、时间基准、完整有序正式输入、中性不变量定义、结构化容差和停止点定义，裸 ID 不算闭合。
- [`response-template-0.1.0.schema.json`](schema/response-template-0.1.0.schema.json)：验证重构与预测的占位回答模板，不把占位符误当成真实回答。
- [`formal-input-trace-0.1.0.schema.json`](schema/formal-input-trace-0.1.0.schema.json)：以通用类型化字段和有序事件冻结三案正式输入，并把人工门前状态固定为未授权、未执行且未产生结果。
- [`formal-comparator-output-0.1.0.schema.json`](schema/formal-comparator-output-0.1.0.schema.json)：约束三案比较器的结构化观测、不变量与负对照结果，并要求结果直接绑定执行许可、正式输入和预测集合摘要；通过状态只允许完整观测、成立不变量和成立负对照。
- [`ca-r1-raw-trace-0.1.0.schema.json`](schema/ca-r1-raw-trace-0.1.0.schema.json)、[`ca-r2-raw-trace-0.1.0.schema.json`](schema/ca-r2-raw-trace-0.1.0.schema.json) 与 [`ca-r3-raw-trace-0.1.0.schema.json`](schema/ca-r3-raw-trace-0.1.0.schema.json)：分别封闭三案原始轨迹字段、配置、顺序与许可／正式输入／预测集合散列；R2 的 JSONL 在内存中归一化后再做 Schema 校验。
- [`execution-plan-preparation-0.1.0.schema.json`](schema/execution-plan-preparation-0.1.0.schema.json)：只表达尚被门前阻断的执行计划准备状态；它要求明确列出 `CA-R1` 合法许可阻断、三案候选 runner／比较器／轨迹 Schema、尚未创建的人工授权／预测集／执行许可和全部未执行标志，并指向将来原位替换它的最终计划 Schema。该制品不能满足人工门。
- [`role-submission-0.1.0.schema.json`](schema/role-submission-0.1.0.schema.json)：来源审核、重构、预测和揭示后制品审核的首次提交。
- [`role-submission-0.1.1.schema.json`](schema/role-submission-0.1.1.schema.json)：保留 0.1.0 并给预测期望增加必填 `configuration_id`，修复 `rehearsal-001` 发现的基线／变体寻址缺口。
- [`role-submission-0.1.2.schema.json`](schema/role-submission-0.1.2.schema.json)：把原始盲测 payload、机器信封与装配工具散列绑定到派生提交。
- [`blind-response-interface-0.1.0.schema.json`](schema/blind-response-interface-0.1.0.schema.json)：阶段专用的盲测语义 payload 与机器信封。
- [`blind-response-interface-0.1.1.schema.json`](schema/blind-response-interface-0.1.1.schema.json)：把参与者原始回答与保管者信封分离，并让确定／不确定预测的类型与单位分支都可达。
- [`response-template-0.1.1.schema.json`](schema/response-template-0.1.1.schema.json) 与 [`reconstruction-response-template-0.1.1.schema.json`](schema/reconstruction-response-template-0.1.1.schema.json)：把两阶段模板定义为带机器派生参与者契约的类型化选择模板，防止第一阶段泄漏第二阶段观察规则。
- [`prediction-participant-response-contract-0.1.1.schema.json`](schema/prediction-participant-response-contract-0.1.1.schema.json) 与 [`reconstruction-participant-response-contract-0.1.1.schema.json`](schema/reconstruction-participant-response-contract-0.1.1.schema.json)：分别约束两阶段参与者可见的字段、枚举、条件分支、ID、单位和可变数组规则。
- [`prediction-template-contract-check-0.1.0.schema.json`](schema/prediction-template-contract-check-0.1.0.schema.json)：记录任务、预测模板与响应 Schema 的参与者可达分支检查。
- [`prediction-template-contract-check-0.1.1.schema.json`](schema/prediction-template-contract-check-0.1.1.schema.json) 与 [`reconstruction-template-contract-check-0.1.1.schema.json`](schema/reconstruction-template-contract-check-0.1.1.schema.json)：记录 0.1.1 两阶段模板与机器派生契约的逐字段闭合检查。
- [`participant-interface-readiness-0.1.0.schema.json`](schema/participant-interface-readiness-0.1.0.schema.json)：要求协议 0.1.1 的正例、负控、无正式输入隔离重放和冻结依赖闭包同时成立；空白 actor 首答留给派发后验收。
- [`rehearsal-actor-dispatch-plan-0.1.0.schema.json`](schema/rehearsal-actor-dispatch-plan-0.1.0.schema.json)：固定 `rehearsal-006` 的四个 projectless 空白席位、模型配置、两阶段同会话规则与逐字节操作提示绑定。
- [`blind-protocol-incident-0.1.0.schema.json`](schema/blind-protocol-incident-0.1.0.schema.json)：记录人工门后、正式执行前发现的阻断性盲测协议事故及失败关闭状态。
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

既有轮次仍由 [`build-role-submission.py`](tools/build-role-submission.py) 复算；协议 0.1.1 使用 [`build-role-submission-v0.1.1.py`](tools/build-role-submission-v0.1.1.py) 校验参与者原始回答、生成机器信封并确定性装配提交。修订理由与边界见[盲测回答接口修订](../../continuous-action-pilot-blind-response-interface.md)和[协议 0.1.1 修复计划](protocol-0.1.1-repair-plan.md)。

正式包使用 [`verify-run-package.py`](tools/verify-run-package.py) 统一检查 Schema、自声明版本、规范字节、清单与嵌套散列引用、任务输入／输出、冻结集合摘要及冻结锚点提交。`preparing` 包可以通过结构检查；人工门前还必须以 `--require-frozen` 通过。

[`verify-formal-readiness.py`](tools/verify-formal-readiness.py) 在包校验之上检查人工门所需的完整制品集合、夹具补丁分离、最终构建全通过、中性初态／正式输入／不变量／容差定义、受控变量与输入字段结构引用闭包、中性信封盲化、回答模板覆盖、第二道审核和正式输入未执行标志。它能识别并检查诚实的 `execution_plan_preparation`，但会以 `execution_plan_not_final` 明确拒绝人工门，直到该文件被绑定最终夹具锁的 `execution_plan` 原位替换。第二阶段任务只允许直接派发中性信封与回答模板，不得加入来源专用夹具 JSON。第二道任务必须直接绑定机械生成器、投影规范、两份生成视图、最终夹具锁、执行计划和最终构建准备记录，审核结果再绑定任务及全部任务输入；审核 actor 必须使用 `source_auditor` 角色，并以新的 `identifier` 和 `session_id` 与第一道来源审核隔离。校验器不会调用夹具、比较器或正式输入。rich 视图里的受控变量、正式输入 ID、时间基准及匿名初态／输入字段必须进入结构关系，atomic 视图才可以按规范删去这些职责边。冻结前可以用普通模式查看缺件，冻结后必须再加 `--require-frozen`。

逐席派发由 [`materialize-dispatch.py`](tools/materialize-dispatch.py) 物化和复核。它不发送消息，也不执行正式输入；只有固定路径的、通过 [`formal-human-gate-authorization-0.1.0`](schema/formal-human-gate-authorization-0.1.0.schema.json) 校验且能复算全部冻结依据的授权凭据才可将模板变成回执。两层合成自检均只使用系统临时目录中的虚构冻结链：

```text
python research/calibration-tests/continuous-action-pilot/tools/materialize-dispatch.py self-test --repo-root .
python research/calibration-tests/continuous-action-pilot/tools/self-test-blind-pipeline.py --repo-root .
```

第二条命令覆盖四个独立 actor／会话、两种条件、两阶段提交、cohort lock，以及合成授权进入生产策略、缺回执、错席位、模板冒充回执和畸形授权的失败关闭；不会复制或运行正式输入、比较器或真实 fixture。

预测模板还须通过分支闭合检查；该检查不运行 fixture 或正式输入：

```text
python research/calibration-tests/continuous-action-pilot/tools/verify-prediction-template-contract-v0.1.0.py self-test
```

四席预测完成后，执行许可由 [`materialize-execution-permit.py`](tools/materialize-execution-permit.py) 机械生成，再由 [`verify-formal-execution-permit.py`](tools/verify-formal-execution-permit.py) 供三案运行器和比较器统一只读复核。人工授权本身不预填未来预测摘要；`prediction-set-preimage.tsv` 的精确字节散列才成为 `prediction_set_digest`。执行许可自检只在系统临时目录的可弃副本中运行，不读取正式输入，也不调用正式运行器、比较器或 test body：

```text
python research/calibration-tests/continuous-action-pilot/tools/materialize-execution-permit.py self-test --repo-root .
python research/calibration-tests/continuous-action-pilot/tools/verify-formal-raw-trace.py self-test --repo-root .
```

正式运行器与比较器用 [`verify-formal-raw-trace.py`](tools/verify-formal-raw-trace.py) 对每份轨迹做许可复验、执行目标选择、严格解析、案例 Schema 校验和三种散列闭合；案例比较器只有在这一步通过后才解释轨迹语义。

## 彩排记录

| 轮次 | 结果 | 发现 |
| --- | --- | --- |
| `rehearsal-001` | `procedure_fail` | 预测值缺少配置寻址 |
| `rehearsal-002` | `procedure_fail` | 冻结集合根摘要不可按文档算法复算 |
| `rehearsal-003` | `procedure_fail` | 任务包保留了旧输入散列 |
| `rehearsal-004` | `procedure_pass` | 六项阶段链闭合；完整提交接口仍过于脆弱 |
| `rehearsal-005` | `procedure_pass` | 两种条件的四份原始首答直接有效；机器装配逐字节可重复 |
| `rehearsal-006` | `procedure_pass` | 四个 projectless 空白 actor 的两阶段首答直接有效；V01 A/B 均唯一恢复并预测 7/4，V02 A/B 均保留不确定性；零纠错、零工具调用 |

失败轮次、无效首答和已冻结 README 均原样保留。三次通过都是程序结论，不是理论证据；ADR 0116 的信封分离由 `rehearsal-005` 验证，协议 0.1.1 的参与者可构造性由 `rehearsal-006` 验证。

## 正式轮次记录

| 轮次 | 结果 | 停止边界 | 发现 |
| --- | --- | --- | --- |
| [`continuous-001`](runs/continuous-001/) | `run_invalid` | 第二阶段提交装配 | 四席都命中预测模板固定单位与 `indeterminate` Schema 的系统性冲突；预测集合、执行许可、正式结果和真值揭示均未产生 |

`continuous-001` 的门后结果与保全证据见[轮次报告](runs/continuous-001/reports/README.md)。后续修订不得覆盖该轮冻结材料；[协议 0.1.1 修复计划](protocol-0.1.1-repair-plan.md)与 `rehearsal-006` 已完成，新的正式尝试必须使用 `continuous-002`、新的冻结摘要、真值承诺和一次性人工授权。

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
