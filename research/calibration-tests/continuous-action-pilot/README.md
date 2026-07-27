# 连续行动先行组测试工作区

- 状态：`continuous-001` 因参与者预测接口不可构造而在正式输入执行前失败关闭；协议 0.1.1 与 `rehearsal-006` 已通过，`continuous-002` 增量契约已接受，当前只制作门前候选包
- 受测表示：[连续行动结构表示 v0.1](../../../theory/CONTINUOUS-ACTION-REPRESENTATION-0.1.md)
- 执行与结论规则：[CA-06](../../continuous-action-pilot-ca-06-execution-and-verdicts.md)
- 制品与放行规则：[CA-07](../../continuous-action-pilot-ca-07-artifacts-and-release.md)
- 正式包契约：[正式轮次包契约](../../continuous-action-pilot-formal-package-contract.md)
- 新轮次增量：[`continuous-002` 增量契约](../../continuous-action-pilot-continuous-002-delta-contract.md)

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
- [`formal-run-delta-0.1.0.schema.json`](schema/formal-run-delta-0.1.0.schema.json)：约束 `continuous-001 → continuous-002` 在候选提交 A 之前的逐制品差异、固定版本矩阵、受保护研究设计、运行绑定／来源引用分流、禁止复用证据、门后制品缺席与 A/B 状态边界。
- [`formal-run-delta-semantic-review-0.1.0.schema.json`](schema/formal-run-delta-semantic-review-0.1.0.schema.json)：约束来源审核与投影审核的输入集合摘要、十一项受保护设计 claim 和实际审核结论。
- [`formal-post-gate-absence-denylist-0.1.0.schema.json`](schema/formal-post-gate-absence-denylist-0.1.0.schema.json)：固定候选提交 A 前必须缺席的路径族与 `artifact_type` 映射，禁止由增量实例自行改写为空 glob。
- [`base-post-run-completion-inventory-0.1.0.schema.json`](schema/base-post-run-completion-inventory-0.1.0.schema.json)：把基础轮次在“完成后”实际出现的正式制品按路径、角色、类型和精确散列建立只读清单，作为新轮次依赖审计的事实起点。
- [`formal-required-component-registry-0.1.0.schema.json`](schema/formal-required-component-registry-0.1.0.schema.json)：封闭 `continuous-002` 的门前、门后及容器组件全集，区分固定散列、候选 manifest 绑定、门后缺席和未解决阻断，并显式记录允许依赖。
- [`formal-actor-dispatch-plan-0.1.0.schema.json`](schema/formal-actor-dispatch-plan-0.1.0.schema.json)：约束四席、两阶段、同会话的静态派发计划；八份提示必须从三份固定正文来源逐字节确定性生成，且计划不得含真实 task、thread 或 session。

根摘要应同时通过 [`verify-frozen-manifest.py`](tools/verify-frozen-manifest.py) 复算。校验器只读清单、制品与 Schema；不会修正已经冻结的值。

既有轮次仍由 [`build-role-submission.py`](tools/build-role-submission.py) 复算；协议 0.1.1 使用 [`build-role-submission-v0.1.1.py`](tools/build-role-submission-v0.1.1.py) 校验参与者原始回答、生成机器信封并确定性装配提交。修订理由与边界见[盲测回答接口修订](../../continuous-action-pilot-blind-response-interface.md)和[协议 0.1.1 修复计划](protocol-0.1.1-repair-plan.md)。

正式包使用 [`verify-run-package.py`](tools/verify-run-package.py) 统一检查 Schema、自声明版本、规范字节、清单与嵌套散列引用、任务输入／输出、冻结集合摘要及冻结锚点提交。`preparing` 包可以通过结构检查；人工门前还必须以 `--require-frozen` 通过。

`continuous-002` 的增量记录由 [`materialize-formal-run-delta-v0.1.0.py`](tools/materialize-formal-run-delta-v0.1.0.py) 物化，并由 [`verify-formal-run-delta-v0.1.0.py`](tools/verify-formal-run-delta-v0.1.0.py) 只读复算。该工具只服务于候选提交 A 之前：候选 manifest 必须保持 `preparing`、`freeze_commit=null`，外部派发证明实例必须仍不存在；提交 B 的三字段冻结转换继续由冻结集工具验证。物化器只产生 `materialized_unbound`，待 manifest 登记增量记录 SHA、规范前像登记该行且根摘要闭合后，只读验证器才会报告 `verified`。共享语义核还会从 Git 对象验证基准 A/B、用固定哈希校验 Schema 与冻结管理器、执行 manifest 双向闭包、解析实际语义审核结论、扫描解码后的旧轮次引用，并依据版本化 denylist 复算仓库缺席。增量实例固定登记在 `inputs/formal-run-delta-v0.1.0.json`，以兼容 `run-manifest 0.1.1`。合成自测只在系统临时目录生成假的双轮次仓库，不读取本仓库的正式轮次目录：

真实候选上的 materializer／verifier 会为散列、Schema、冻结前像与仓库缺席检查遍历并读取 `.git` 之外的仓库文件，其中可能包括既有轮次文件和尚未执行的正式输入；它们不会再把“未执行”误报成“未读取”。发布信任包必须在带外同时固定 materializer、verifier 与共享语义核三份精确字节；两个入口只接受 `python -I` 隔离模式，阻止脚本目录中的同名模块抢先执行。公开 CLI 还必须取得调用方提供的共享语义核 SHA-256，并显式传入 `--allow-repository-wide-byte-reads`，否则在导入共享语义核、读取候选 draft 或扫描仓库前失败关闭。该标志只确认仓库级静态字节访问，不授权正式派发或执行。

```text
python research/calibration-tests/continuous-action-pilot/tools/self-test-formal-run-delta-v0.1.0.py
```

当前自测覆盖 14 项正控与 59 项具名负控，包括规范字节、可信 Schema／工具散列、真实 Git A/B、路径逃逸与大小写碰撞、固定版本矩阵、可闭合的全局组件 base endpoint、解码后的旧轮次引用、结构化且身份隔离的语义审核、禁止复用、required-component 注册表的类型／散列／依赖闭包、manifest 双向闭包、增量记录—冻结前像—根摘要绑定、事务短写回滚、Python 隔离模式、仓库级字节读取确认、wrapper 跨根拒绝、core 导入前散列校验，以及候选命名空间外与嵌套路径中的门后制品伪装；`P10` 式 B 后宽泛例外已被删除，pre-A 验证器对任何外部派发证明实例一律失败关闭。路径 glob 只接受版本化的仓库相对 `gitwildmatch` 子集（`*`、`**`、`?`），其余语法失败关闭。自测不会调用 runner 或 comparator。

基础清单由 [`base_post_run_inventory_contract.py`](tools/base_post_run_inventory_contract.py) 在只读基础轮次快照上复算；隔离自测把完成提交 `c42013d5cad89811e8838696c4072f6f71a859fb` 与树 `f8aae165fcf9620b8ba9cee64766e39f642d8d4c` 固定为 87 项制品，清单 SHA-256 为 `12f769ecbe378543a2f9ad153680266701a9d4d9d96f2eb3f56b42332aa5e673`，并通过 6 项正控与 10 项负控。required-component 注册表当前封闭 158 个组件，并诚实列出 materializer、verifier、共享语义核三项必须由调用方带外固定精确字节的外部信任根；两个入口再以必填 SHA-256 参数固定语义核。当前仍有 38 项散列阻断与 110 项依赖阻断，合计涉及 122 个不重复组件，所以注册表是“工作完整性地图”，不是提交 A 已就绪的证明。

actor 派发计划由 [`materialize-formal-actor-dispatch-plan-v0.1.0.py`](tools/materialize-formal-actor-dispatch-plan-v0.1.0.py) 从三份固定正文来源确定性物化，再由 [`verify-formal-actor-dispatch-plan-v0.1.0.py`](tools/verify-formal-actor-dispatch-plan-v0.1.0.py) 只读复算；隔离自测覆盖 10 项正控与 49 项负控，包括来源伪造、真实短写／部分异常回滚、跨仓库工具错绑、跨行／注释／尾随运行标识和嵌套转义。开发范围事件及修订证据见[actor 派发计划开发范围事件](development-scope-incident-2026-07-28-actor-dispatch-plan.md)。这些工具只建立门前静态计划，不创建真实 Codex task、thread、session 或 dispatch。

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
| `continuous-002` | `preparing` | 门前候选包 | 只允许重建协议 0.1.1 的版本、Schema、工具、来源、夹具、任务、提示、承诺与冻结闭包；尚未创建正式 actor 或授权实例 |

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
