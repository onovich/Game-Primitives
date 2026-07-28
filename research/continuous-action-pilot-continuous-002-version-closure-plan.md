# 连续行动先行组：continuous-002 旧绑定扫描与版本闭合计划

- 状态：工作计划；扫描、版本决策与批次 0 仓库实现已完成，独立调用方的带外 re-pin／验收待完成，批次 1 待开始
- 日期：2026-07-29
- 扫描基线：Git 提交 `68653ddf9609333c88e6a1f795da3faaa3719ada`
- 注册表：[`formal-required-component-registry-0.1.0.json`](calibration-tests/continuous-action-pilot/contracts/formal-required-component-registry-0.1.0.json)
- 扫描基线注册表 SHA-256：`8604f928c342f3cc256796c5c6267ac29176b44923f64f9f3331e534485f3669`
- 上位契约：[`continuous-002` 增量契约](continuous-action-pilot-continuous-002-delta-contract.md)

> [范围] 本文只审计非 `runs/**` 控制面文件及注册表元数据。扫描没有读取任何正式输入，没有打开 `runs/**` 中的既有轮次文件，没有运行正式 runner、comparator、派发器或真值揭示流程，也没有创建 `continuous-002` 任务、thread、session 或候选包。本文不是“放行正式连续行动试验”。

## 0. 批次 0 仓库实施记录（已完成；带外 re-pin 待验收）

批次 0 的仓库实现已在不接触 `runs/**` 的前提下完成：

- required-component Schema 增加 `hash_state=container_excluded`，并把它与 `component_kind=manifest_container` 双向约束；
- `candidate_run_manifest_instance` 从假散列阻断迁移到容器排除态；
- 依赖数组被明确定义为实际直接依赖，新增自环、一般环、门前→门后、runtime/execution→provenance、容器入边、`closed`→未闭合目标和门后联合状态检查；
- 原先被误标为 `closed` 的 `actor_dispatch_plan_development_incident` 重新打开为依赖阻断，因为它依赖的 actor-plan 组件尚未闭合；
- 隔离合成自测通过 15 项正控与 68 项具名负控，报告 `formal_input_access=false`、`runner_or_comparator_executed=false`、`temporary_repository_only=true`。

批次 0 后：

| 项目 | 值 |
|---|---|
| required-component Schema SHA-256 | `0f5f6ef1ba9f638a7adef1ea79f970b36f3191a9ff9481076de65ee9fb35ec03` |
| required-component registry SHA-256 | `9ecb305bf6b6ec00e9f71384764a6a1ca7264a9f2365539b5b07a1f75e2af855` |
| formal-run-delta self-test SHA-256 | `304f86878573cb9123603bafacfd921ea3ed07bed4103a72e711541c6493e3d7` |
| formal-run-delta core SHA-256 | `49afd42f82c6837e6db04489703601821b9e15efbf1f10652f8f641c61e73842` |
| 散列阻断 | 37 |
| 依赖阻断 | 111 |
| 不重复阻断组件 | 122 |

依赖阻断从扫描基线的 110 增为 111 不是回退，而是消除一个未经证明的“已闭合”声明；manifest 假散列阻断同时被移除，所以不重复阻断组件总数仍为 122。core SHA 只是供独立调用方复核并写入带外信任包的交接值，不是由 core 自证的信任锚。

## 1. 结论

### 1.1 扫描基线中的 38 个散列阻断并不等于 38 个待生成文件

扫描基线的注册表共有 158 个组件，当时报告：

- 38 个 `hash_state=unresolved_blocks_commit_a`；
- 110 个 `dependency_state=unresolved_blocks_commit_a`；
- 两类阻断的并集为 122 个组件。

对 38 个散列阻断逐项复核后，应拆成：

| 类别 | 数量 | 决策 |
|---|---:|---|
| 旧轮次绑定家族重发 | 26 | 发布 `continuous-002` 专用 `0.1.1` |
| 新控制面家族 | 11 | 按已登记接口完成首版 `0.1.0` |
| candidate manifest 容器 | 1 | 不补 SHA；修正为容器排除态，最后再物化 |

因此，真实缺失的是 37 份非 manifest 制品；第 38 项是扫描基线注册表当时不能正确表达“容器不自散列”造成的假阻断。批次 0 的仓库实现现已补上该状态及其完整验证路径。

### 1.2 本轮不引入 `0.2.0`

本轮统一采用：

- **`0.1.1` 专用重发**：用于消除 `continuous-001` 的 run ID、路径、Schema、工具或验证假设绑定；
- **`0.1.0` 新家族**：用于 absence denylist、external dispatch attestation 与 truth continuity attestation；
- **`run-manifest 0.1.1` 同版本重新物化**：因为改变的是轮次实例，不是 manifest Schema 的语义。

`0.2.0` 只在组件被改造成显式接收轮次 profile、能够跨至少两个轮次复用，并有“不能串包”的跨轮次负控时使用。当前只有一次接口修复重跑；同时做通用化会扩大 API、依赖图与验证面，不能改善 `continuous-002` 的研究效度。

`verify-frozen-manifest` 与 `verify-run-package` 是未来最值得参数化的两个候选，但本轮仍做自包含的 `0.1.1` 专用入口。不得在 `0.1.1` 名义下悄悄引入未登记的 `0.2.0` 共享核心。

### 1.3 扫描基线的 110 个依赖阻断不能机械改成 `closed`

扫描基线的 110 项按绑定位置分为：

| 依赖层 | 数量 | 说明 |
|---|---:|---|
| `global_git_bound` | 50 | 27 Schema、12 verification tool、9 generator、1 research contract、1 submission assembler |
| `candidate_manifest_bound` | 60 | 37 个 CA-R1–R3 案例级执行目标；23 个参与者／控制面／候选总装制品 |

补充统计：

- 56 项属于 `runtime_binding`，54 项属于 `execution_binding`；
- 97 项当前没有声明任何依赖；
- 其余 13 项只声明了部分依赖：3 项各 1 条、8 项各 2 条、1 项 4 条、1 项 15 条。

扫描基线的验证器当时能检查排序、去重、目标 ID 存在、`closed` 非空和 runtime/execution 不依赖 provenance-only 组件，但尚不能证明无环、拓扑闭合或“声明边等于实际直接引用”。批次 0 已补上自环、一般环、时间逆向、作用域越界、容器边与伪闭合目标等可机械证明的图性质；“声明边等于实际直接引用”仍须由结构化依赖审计和针对性负控共同证明。因此，批量填入任意 ID 再把状态改成 `closed` 仍只会形成自我声明，不构成闭包证据。

本计划把 `allowed_dependency_component_ids` 操作性定义为**实际直接依赖集合**，而不是传递闭包或宽泛白名单。传递闭包由验证器计算；循环、越域边和遗漏的直接 Schema／加载器／共享语义核引用都必须失败关闭。

## 2. 扫描方法与解释边界

### 2.1 输入集合

扫描对象不是仓库中的所有历史说明文字，而是注册表中 26 个 `semantic_policy=round_bound_reissue` 组件各自的非 `runs/**` 前身。新家族没有前身，不计入旧字面量扫描。

目标模式为：

```text
continuous-001|runs/continuous-001
```

22 个前身文件共发现 160 个匹配；另外 4 个前身没有直接字面量，但通过旧 materializer 加载、旧验证假设或旧字段约束形成间接绑定。

### 2.2 匹配数不是缺陷数

匹配可能位于：

- 可执行常量、路径、Schema `const` 或正则；
- docstring、错误消息或自测夹具；
- 明确的来源说明。

所以匹配数只用于定位和防漏，不能替代语义审计。新版本允许在明确标记的 `provenance_reference_scope` 中提到 `continuous-001`，但不得让该值流入 `runtime_binding_scope` 或 `execution_binding_scope`。

### 2.3 可复现命令

下列 PowerShell 逻辑只应对第 3 节列出的 26 个前身路径执行；不得把 `runs/**` 加入输入：

```powershell
$matches = Select-String `
  -LiteralPath $predecessorPath `
  -Pattern 'continuous-001|runs/continuous-001' `
  -AllMatches

$occurrences = (
  $matches |
    ForEach-Object { $_.Matches.Count } |
    Measure-Object -Sum
).Sum
```

复核时还须人工检查零命中文件的导入、动态加载与验证语义，避免把“没有旧字符串”误判成“轮次无关”。

## 3. 26 个 `0.1.1` 专用重发

下表路径均相对于 `research/calibration-tests/continuous-action-pilot/`。`N @ L` 表示前身中有 N 个目标字面量，表中给出第一处定位；它不是对每一处匹配的语义定罪。

### 3.1 Schema 与研究契约

| component ID | 前身证据 | 候选文件 | 决策 |
|---|---|---|---|
| `ca_r1_raw_trace` | `schema/ca-r1-raw-trace-0.1.0.schema.json`，2 @ L169 | `schema/ca-r1-raw-trace-0.1.1.schema.json` | `0.1.1`；重绑 run、输入与执行许可 |
| `ca_r2_raw_trace` | `schema/ca-r2-raw-trace-0.1.0.schema.json`，2 @ L214 | `schema/ca-r2-raw-trace-0.1.1.schema.json` | `0.1.1`；重绑 run、输入与执行许可 |
| `ca_r3_raw_trace` | `schema/ca-r3-raw-trace-0.1.0.schema.json`，2 @ L372 | `schema/ca-r3-raw-trace-0.1.1.schema.json` | `0.1.1`；重绑 run、输入与执行许可 |
| `formal_build_readiness` | `schema/formal-build-readiness-0.1.0.schema.json`，1 @ L259 | `schema/formal-build-readiness-0.1.1.schema.json` | `0.1.1`；同步 task-packet 0.1.2 与 002 装配链 |
| `formal_comparator_output` | `schema/formal-comparator-output-0.1.0.schema.json`，1 @ L1557 | `schema/formal-comparator-output-0.1.1.schema.json` | `0.1.1`；保持三案例语义，重绑许可与轮次 |
| `formal_execution_permit` | `schema/formal-execution-permit-0.1.0.schema.json`，49 @ L279 | `schema/formal-execution-permit-0.1.1.schema.json` | `0.1.1`；与三份 trace Schema、计划、授权整族重发 |
| `formal_human_gate_authorization` | `schema/formal-human-gate-authorization-0.1.0.schema.json`，9 @ L357 | `schema/formal-human-gate-authorization-0.1.1.schema.json` | `0.1.1`；新授权必须绑定 002 冻结闭包 |
| `stage1_cohort_lock` | `schema/stage1-cohort-lock-0.1.0.schema.json`，2 @ L300 | `schema/stage1-cohort-lock-0.1.1.schema.json` | `0.1.1`；保留四席映射，替换轮次闭包 |
| `stage1_seat_dispatch_envelope` | `schema/stage1-seat-dispatch-envelope-0.1.0.schema.json`，12 @ L71 | `schema/stage1-seat-dispatch-envelope-0.1.1.schema.json` | `0.1.1`；重绑第一阶段输入、任务与回执 |
| `stage2_seat_dispatch_envelope` | `schema/stage2-seat-dispatch-envelope-0.1.0.schema.json`，8 @ L71 | `schema/stage2-seat-dispatch-envelope-0.1.1.schema.json` | `0.1.1`；重绑共同第二阶段输入与回执 |
| `formal_execution_target_contract` | `tools/formal_execution_target_contract.py`，2 @ L1 | `tools/formal-execution-target-contract-v0.1.1.py` | `0.1.1`；作为 002 专用执行目标契约，不在本轮泛化 |

### 3.2 物化器与冻结工具

| component ID | 前身证据 | 候选文件 | 决策 |
|---|---|---|---|
| `dispatch_materializer` | `tools/materialize-dispatch.py`，4 @ L2 | `tools/materialize-dispatch-v0.1.1.py` | `0.1.1`；重绑 run、许可、计划与回执 |
| `execution_permit_materializer` | `tools/materialize-execution-permit.py`，6 @ L2 | `tools/materialize-execution-permit-v0.1.1.py` | `0.1.1`；与 permit Schema 和 target contract 同批 |
| `final_execution_plan_materializer` | `tools/materialize-final-execution-plan.py`，7 @ L2 | `tools/materialize-final-execution-plan-v0.1.1.py` | `0.1.1`；重绑确定性输入／输出 |
| `fixture_assembly_materializer` | `tools/materialize-fixture-assembly.py`，4 @ L2 | `tools/materialize-fixture-assembly-v0.1.1.py` | `0.1.1`；改用新版 target contract |
| `freeze_manager` | `tools/manage-frozen-set.py`，5 @ L38 | `tools/manage-frozen-set-v0.1.1.py` | `0.1.1`；最后收口 002 manifest 与冻结集 |
| `preparing_manifest_updater` | `tools/update-preparing-manifest.py`，12 @ L2 | `tools/update-preparing-manifest-v0.1.1.py` | `0.1.1`；重建清单，不复制旧 allowlist |
| `projection_audit_task_materializer` | `tools/materialize-projection-audit-task.py`，14 @ L32 | `tools/materialize-projection-audit-task-v0.1.1.py` | `0.1.1`；重绑 task-packet 0.1.2 与投影闭包 |
| `python_runtime_evidence_materializer` | `tools/materialize-python-runtime-evidence.py`，2 @ L26 | `tools/materialize-python-runtime-evidence-v0.1.1.py` | `0.1.1`；重绑 002 工具链，不执行正式 runner |

### 3.3 验证器与自测

| component ID | 前身证据 | 候选文件 | 决策 |
|---|---|---|---|
| `blind_pipeline_self_test` | `tools/self-test-blind-pipeline.py`，9 @ L25 | `tools/self-test-blind-pipeline-v0.1.1.py` | `0.1.1`；只用合成夹具覆盖新版链 |
| `execution_permit_verifier` | 旧文件无 run 字面量；`tools/verify-formal-execution-permit.py:L14` 动态加载旧 materializer | `tools/verify-formal-execution-permit-v0.1.1.py` | `0.1.1`；精确固定新版 materializer |
| `fixture_assembly_self_test` | 旧文件无 run 字面量；`tools/self-test-fixture-assembly.py:L14` 加载旧 materializer | `tools/self-test-fixture-assembly-v0.1.1.py` | `0.1.1`；改测新版入口与失败关闭 |
| `formal_readiness_verifier` | `tools/verify-formal-readiness.py`，5 @ L282 | `tools/verify-formal-readiness-v0.1.1.py` | `0.1.1`；重建 002 路径表 |
| `frozen_manifest_verifier` | 无直接 run 字面量；`tools/verify-frozen-manifest.py:L66–107` 固定旧 task-packet 字段且缺少 002 增量／缺席约束 | `tools/verify-frozen-manifest-v0.1.1.py` | `0.1.1`；未来再评估 0.2.0 profile 化 |
| `raw_trace_verifier` | `tools/verify-formal-raw-trace.py`，2 @ L2 | `tools/verify-formal-raw-trace-v0.1.1.py` | `0.1.1`；绑定三份新版 trace Schema 与 permit verifier |
| `run_package_verifier` | 无直接 run 字面量；`tools/verify-run-package.py:L201–266` 固定旧 task 字段假设，且现有入口不知道 002 delta 闭包 | `tools/verify-run-package-v0.1.1.py` | `0.1.1`；未来再评估 0.2.0 profile 化 |

## 4. 11 个新增 `0.1.0` 控制面组件

这些家族没有可安全重命名的旧实现。可以复用已有规范 JSON、路径安全、Git 锚和 commitment 语义，但必须以新接口和新负控发布。

| component ID | 候选文件 | 最小职责 |
|---|---|---|
| `formal_post_gate_absence_denylist_instance` | `contracts/formal-post-gate-absence-denylist-0.1.0.json` | 固定 B 前必须缺席的路径族和 artifact type |
| `formal_post_gate_absence_verifier` | `tools/verify-formal-post-gate-absence-v0.1.0.py` | 只读复算 denylist 与仓库缺席 |
| `formal_post_gate_absence_self_test` | `tools/self-test-formal-post-gate-absence-v0.1.0.py` | 覆盖空 glob、嵌套伪装、越界路径和门后制品正负控 |
| `external_dispatch_attestation` | `schema/external-dispatch-attestation-0.1.0.schema.json` | 约束 B 后追加式外部派发状态证明 |
| `external_dispatch_attestation_template` | `contracts/external-dispatch-attestation.template-0.1.0.json` | 门前冻结空模板，不含真实 task/thread/session |
| `external_dispatch_attestation_verifier` | `tools/verify-external-dispatch-attestation-v0.1.0.py` | 校验 B、冻结根、observed head、时间、范围与能力限制 |
| `external_dispatch_attestation_self_test` | `tools/self-test-external-dispatch-attestation-v0.1.0.py` | 证明旧证明、宽泛能力声明和覆盖写入会失败 |
| `truth_continuity_attestation` | `schema/truth-continuity-attestation-0.1.0.schema.json` | 不含明文地绑定基准／候选承诺及可复核过程 |
| `truth_continuity_attestation_materializer` | `tools/materialize-truth-continuity-attestation-v0.1.0.py` | 从受控 commitment 与再生成／离线比较元数据确定性物化 |
| `truth_continuity_attestation_verifier` | `tools/verify-truth-continuity-attestation-v0.1.0.py` | 只读校验锚点、过程、审核者与非明文边界 |
| `truth_continuity_attestation_self_test` | `tools/self-test-truth-continuity-attestation-v0.1.0.py` | 覆盖换承诺、换生成器、泄露明文和审核身份缺失 |

`external_dispatch_attestation` 的真实实例不在上表。它的 registry 状态应继续是 `post_gate_not_materialized`，在提交 B 推送后才允许追加；门前不得为了“补齐 0.1.0 家族”而创建实例。

## 5. manifest 容器排除决策

扫描基线中的 `candidate_run_manifest_instance` 同时声明：

```text
binding_kind = container_excluded
hash_state   = unresolved_blocks_commit_a
```

这两个状态在扫描基线中相互冲突：

- `formal-run-delta` 的版本矩阵已经要求 manifest 的 base/candidate SHA 均为 `null`；
- manifest 是其他制品散列的容器，不能把自己的未来字节散列反向写进自己；
- 扫描基线的 required-component Schema 在 `hash_state` 枚举中尚无 `container_excluded`，所以注册表当时只能误用 unresolved；批次 0 的仓库实现现已补上该状态及双向约束。

决策：

1. 在 required-component registry `0.1.0` 首次进入 Commit A 前，给 `hash_state` 增加 `container_excluded`；
2. 只允许 `binding_kind=container_excluded` 的 manifest 容器使用该状态；
3. 强制 `expected_sha256=null`，并保留独立的 manifest Schema、双向制品闭包、冻结前像和根摘要验证；
4. `candidate_run_manifest_instance` 不再计入散列 blocker；
5. manifest 仍使用 `run-manifest 0.1.1`，并在所有非容器组件就绪后最后物化。

这是尚未被正式轮次冻结的新家族 `0.1.0` 的首次闭合修正，可以在首个 Commit A 前原位完成。若该 Schema 已经被正式冻结使用，新增状态才需要发布语义扩展版本；当前不满足该条件。

## 6. 依赖闭合语义

### 6.1 一条边表示什么

对组件 `A`，`allowed_dependency_component_ids` 必须等于 `A` 的**直接、实际、构建或验证所需**组件集合，包括：

- JSON Schema 的直接 `$ref` 或实例所声明的 Schema；
- Python／PowerShell 入口直接导入、加载或精确固定的共享语义核；
- materializer 直接读取并据以生成结果的契约、模板或输入制品；
- verifier 为给出通过结论而直接信任或复算的 Schema、契约、实现和记录。

它不包括：

- 仅在说明文字中提到的来源；
- 依赖的依赖；
- “以后可能读取”的宽泛白名单；
- 为了让列表非空而添加的无关组件。

### 6.2 `closed` 的最低证明

组件只有同时满足以下条件才能改为 `dependency_state=closed`：

1. 候选实现或候选制品的直接引用已经稳定；
2. 每条直接引用都映射到唯一 component ID；
3. 每个目标组件存在，且其生命周期允许当前引用；
4. 全图无自环、无环和未知节点；
5. runtime/execution 作用域不消费 provenance-only 数据；
6. 没有从门前组件指向门后实例的反向时间依赖；
7. 针对动态加载、Schema 替换和漏边分别有负控或人工审计定位。

验证器负责可机械证明的图性质；直接引用是否完整则由结构化依赖审计与针对性负控共同证明。不得把“验证器无法发现漏边”写成“已证明没有漏边”。

## 7. 实施批次

### 批次 0：先修注册表的表达能力（仓库实现已完成；带外 re-pin 待验收）

1. 为 manifest 加入 `hash_state=container_excluded`；
2. 明确依赖字段表示直接实际依赖；
3. 给验证器增加自环、一般环、门前→门后和容器错误散列负控；
4. **已完成（仓库内）**：重算 Schema 与 registry SHA-256，并更新 `formal_run_delta_contract.py` 中的精确散列常量；
5. **待独立验收（仓库外）**：由调用方复核本节交接的 core SHA-256，并刷新其带外固定的共享语义核／信任包；仓库内文件不能自证或代替该信任动作；
6. **已完成**：让 38 个扫描基线散列 blocker 正确归一为 37 个真实缺件。

批次 0 的仓库实施没有把扫描基线的 110 项依赖状态批量回填为 `closed`；唯一的依赖状态修正是把一项未经证明的 `closed` 重新打开，因此当前依赖阻断为 111 项。

### 批次 1：建立三个新增控制面家族

可分三条独立小链：

1. denylist instance → absence verifier → self-test；
2. external attestation Schema → 空 template → verifier → self-test；
3. truth continuity Schema → materializer → verifier → self-test。

外部派发证明的真实实例仍留到 B 后。

### 批次 2：重发 10 个 Schema 与 execution-target contract

先冻结字段、版本和路径约束，再让下游工具精确引用。三份 raw trace、execution permit、human gate、dispatch envelope 与 cohort lock 必须作为一个一致版本矩阵复核。

### 批次 3：重发 8 个 generator

顺序建议：

1. fixture assembly、runtime evidence、final execution plan；
2. projection audit task；
3. dispatch 与 execution permit；
4. preparing manifest updater；
5. freeze manager 最后收口。

### 批次 4：重发 7 个 verifier／self-test

先完成被其他入口加载的 verifier，再完成整包与盲管线自测。所有自测只使用系统临时目录中的合成材料，不读取或执行正式输入。

### 批次 5：闭合 50 个 global 依赖

按下列拓扑逐项登记直接边并复核：

```text
Schema
  → shared contract / semantic core
  → materializer / verifier
  → self-test / submission assembler
```

每次只关闭已有真实实现证据的一组，不做全表机械替换。

### 批次 6：闭合 23 个候选控制面／参与者制品

这 23 项包括 20 个参与者表面或控制面制品，以及 candidate build-readiness、fixture-lock、execution-plan 三个候选总装制品。它们只在 global 依赖稳定后登记直接边。

### 批次 7：闭合 37 个案例级 execution target

按 CA-R1、CA-R2、CA-R3 分组，分别闭合 runner、comparator、formal input、test body、support artifact 与 build evidence；完成后执行全图拓扑、越域和反向引用检查。

### 批次 8：最后创建候选包

只有版本矩阵和 required-component 依赖图全部闭合后，才允许：

1. 创建 `runs/continuous-002/` 的 `preparing` 候选包；
2. 确定性生成候选制品；
3. 最后物化 manifest；
4. 物化 delta、冻结前像与根摘要；
5. 完成语义审核并准备 Commit A／B。

创建候选包不等于正式派发授权。正式 actor、真实 task/thread/session、runner、comparator 和真值揭示仍受一次性人工门约束。

## 8. 验收条件

### 8.1 本扫描计划

- 基线提交、注册表路径和 SHA 可复算；
- 26 个前身、22 个直接命中文件、4 个间接绑定和 160 个字面量匹配可复现；
- 26／11／1 的分类与注册表逐项对应；
- 文档没有把来源引用误报为运行绑定；
- `runs/**` 保持在扫描范围之外。

### 8.2 后续实现

- 26 个重发组件均使用已决定的 `0.1.1`，11 个新组件均使用 `0.1.0`；
- 新版 runtime/execution 绑定中没有旧轮次 ID 或路径；
- 允许保留的旧轮次引用被显式限制在 provenance 作用域；
- manifest 使用容器排除态且不存在自散列；
- 每项 `closed` 都有直接依赖证据，全图无环、无越域边；
- 提交 A 前没有未解决的 required-component 散列或依赖 blocker；
- 门后实例、正式 actor、正式派发、正式执行和真值揭示仍然缺席。

## 9. 紧接着做什么

下一项实现工作是**批次 1 的 denylist 小链：`formal-post-gate-absence-denylist 0.1.0` 实例 → 只读 verifier → 合成 self-test**。它依赖的 Schema 与共享扫描语义已经存在，适合作为三个新增控制面家族中的第一个纵向切片。仍不应先复制 26 个旧文件，也不应先创建 `runs/continuous-002/`。
