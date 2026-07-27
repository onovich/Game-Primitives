# 连续行动先行组：continuous-002 增量契约

- 状态：已接受；允许制作门前候选包，不授权正式派发或执行
- 日期：2026-07-28
- 决策记录：[ADR 0120](../docs/adr/0120-establish-continuous-002-on-protocol-0.1.1.md)
- 基准契约：[连续行动正式轮次包契约](continuous-action-pilot-formal-package-contract.md)
- 接口修复：[协议 0.1.1 修复计划](calibration-tests/continuous-action-pilot/protocol-0.1.1-repair-plan.md)
- 验收证据：[`rehearsal-006`](calibration-tests/continuous-action-pilot/rehearsals/rehearsal-006/reports/findings.md)

## 1. 作用与优先级

本文只规定 `continuous-001 → continuous-002` 的增量。CA-01–CA-07、ADR 0115–0119 与原正式包契约继续有效；发生冲突时，本文只在以下范围优先：

- 新轮次 ID、路径、冻结摘要与真值承诺；
- 协议 0.1.1 的参与者接口；
- 因旧轮次硬编码而必须新发的 Schema 和工具；
- 提交 B 前的缺席断言与新人工门。

本文不改变案例、来源版本、CA-SR 0.1、反事实、条件、硬条件、比较语义或结论规则。

## 2. 为什么不能复制旧包

旧正式包不仅在任务和模板中记录 `continuous-001`，授权、执行许可、逐席派发、共同锁、构建准备、原始轨迹、比较器输出及其物化／验证工具也绑定旧路径、旧接口或旧散列。

因此下列做法均不合格：

- 复制旧目录后只替换回答模板；
- 原位修改旧 Schema 或工具；
- 复用旧 actor、session、回答、授权或真值承诺；
- 只在 Markdown 中声明“已迁移”，却没有逐制品差分和机器检查；
- 在提交 B 后补入本应冻结的 002 专用 Schema 或工具。

## 3. 研究设计不变量

`continuous-002` 是接口修复重跑。候选包必须逐项证明以下内容与冻结上游决定相同：

| 层面 | 必须保持 |
|---|---|
| 核心问题 | CA-01“原子动作别名化”工作命题及反驳优先级 |
| 案例 | CA-R1、CA-R2、CA-R3 的职责、作品、版本、来源定位 |
| 表示 | CA-SR 0.1 |
| 操纵 | 每案唯一规则变量、基线／变体与装饰负对照 |
| 条件 | rich／atomic 两条件及派发对称性 |
| 强检验 | 四项硬条件、重构与设计变体预测 |
| 结论 | 熟悉度／污染处理、案例轴、表示轴与组级优先级 |
| 边界 | `structural_only`；不把技能、难度或体验主张混入 |

允许变化仅包括新轮次绑定、接口表达、参与者可构造性修复、确定性装配和消除旧硬编码所必需的版本化实现。

## 4. 版本矩阵

### 4.1 直接固定

| 职责 | `continuous-002` 版本 |
|---|---|
| 协议 | `0.1.1` |
| 清单 | `run-manifest 0.1.1` |
| 正式任务 | `task-packet 0.1.2` |
| 原始回答 | `blind-response-interface 0.1.1` |
| 预测模板 | `response-template 0.1.1` |
| 重构模板 | `reconstruction-response-template 0.1.1` |
| 预测参与者契约 | `prediction-participant-response-contract 0.1.1` |
| 重构参与者契约 | `reconstruction-participant-response-contract 0.1.1` |
| 预测契约检查 | `prediction-template-contract-check 0.1.1` |
| 重构契约检查 | `reconstruction-template-contract-check 0.1.1` |
| 保管装配 | `build-role-submission-v0.1.1.py` |
| 派生提交 | `role-submission 0.1.2` |

下列轮次无关家族可在散列复核后沿用：`ca-sr-artifact 0.1.0`、`fixture-lock 0.1.0`、`variant-envelope 0.1.0`、`formal-input-trace 0.1.0`、`execution-artifact 0.1.1`、`truth-reveal 0.1.0` 与 `run-report 0.1.0`。

### 4.2 至少必须审计并新发

以下清单不是穷举。凡旧硬编码扫描命中的家族及其物化／验证工具都必须进入版本矩阵；其中至少包括：

- `formal-build-readiness`；
- `formal-human-gate-authorization`；
- `formal-execution-permit`；
- `stage1-seat-dispatch-envelope`；
- `stage2-seat-dispatch-envelope`；
- `stage1-cohort-lock`；
- CA-R1／R2／R3 raw-trace；
- `formal-comparator-output`；
- 正式 readiness、dispatch、execution-permit、raw-trace、freeze manager；
- 实际引用旧 builder／旧 response schema 的夹具装配、最终计划与投影审核工具。

每一项必须选择：

1. 发布 `0.1.1` 的 002 专用版本；或
2. 发布 `0.2.0` 的显式参数化版本，并用负控证明不能跨轮次串包。

候选包在版本矩阵尚有“待定”时不得进入提交 A。

### 4.3 新增的 002 契约家族

以下家族必须在提交 A 前以 Schema、模板／实例、校验器和负控闭合：

- `formal-run-delta 0.1.0`；
- `formal-actor-dispatch-plan 0.1.0`；
- `formal-post-gate-absence-denylist 0.1.0`；
- `external-dispatch-attestation 0.1.0`：门前只冻结 Schema、空模板和校验器，实际证明实例在提交 B 推送后生成；
- `truth-continuity-attestation 0.1.0`：不含明文真值，门前冻结并绑定基准／候选承诺、确定性生成器或离线比较过程及审核者。

## 5. formal-run-delta

提交 A 前新增 `formal-run-delta 0.1.0` Schema、物化器和只读校验器，并在 `continuous-002` 中生成唯一增量记录。它至少包含：

- 基准与候选 run ID；
- `continuous-001` 的冻结提交和根摘要；
- 协议、任务、回答 Schema、模板和装配器的前后版本；
- `research_design_change=false`；
- 每项候选制品的 `change_kind`；
- 基准／候选路径与 SHA-256；
- `participant_visible` 与 `semantic_change`；
- 明确分开的 `runtime_binding_scope` 与 `provenance_reference_scope`；
- 禁止复用集合；
- 可由仓库证明的 `repository_absence_assertions`；
- `external_dispatch_attestation_required_after_b=true`，以及所冻结证明契约的路径和 SHA-256；
- `candidate_status_at_audit=preparing` 与 `expected_post_b_status=frozen`；
- 审核结论与审核时间。

`delta_scope` 不包含增量记录实例自身、run manifest、冻结前像或根摘要，因而增量记录不得登记自己的 SHA-256。`formal-run-delta` Schema、物化器和校验器可以作为普通候选制品进入差分。冻结前像必须登记增量记录实例的 SHA-256，但不得登记冻结前像自身的 SHA-256；manifest 再单向绑定冻结前像及根摘要。任何容器都不反向进入增量记录的逐项散列清单。

校验器必须拒绝：

- 把旧路径改名后声称“未变”；
- 候选任务、提示、信封、授权、许可、轨迹或其他运行绑定字段仍引用 `continuous-001`；
- 旧回答接口或装配器进入参与者链；
- 声称设计不变却改变案例、变量、条件、观察、容差或结论规则；
- B 前仓库中已经出现任何门后制品实例。

`continuous-001` 可以出现在增量记录、ADR、来源说明和审核记录的来源引用中；这种 `provenance_reference_scope` 不得流入 `runtime_binding_scope`。校验器必须分别检查两种作用域，而不是禁止所有旧轮次字符串。

`research_design_change=false` 不是由一个布尔值自证。机器校验负责证明受保护字段、登记散列和差分闭包没有未声明变化；独立来源／投影审核负责判断这些受保护内容仍忠实表达同一研究设计。两类证据缺一不可。

新真值承诺在揭示前只能证明来源和生成过程受控，不能证明隐藏明文与基准语义相同。门前须冻结通过 `truth-continuity-attestation 0.1.0` 校验的非明文证明，绑定基准／候选承诺、确定性再生成器或离线比较过程及审核者；揭示后再对明文完成最终机械复核。

## 6. 门前 actor 与派发

候选包必须新增并冻结 `formal-actor-dispatch-plan 0.1.0` Schema、物化器、只读校验器、一份正式 actor 派发计划和八份惰性提示模板：

- 四个席位与条件分配；
- `requested_model_alias`、`requested_reasoning_effort`，以及固定为 `null`／`unknown` 的 `observed_model_build`；实际 build 只在门后 actor 描述或派发回执中追加；
- 第一阶段与第二阶段使用同一新会话；
- projectless 空白上下文；
- 禁止工具、网络、共享工作区、其他条件与其他提交；
- 每个派发回合的首个且唯一 assistant 事件必须直接是 final JSON；
- 无追加格式纠错；
- 无效第一阶段不得进入第二阶段；
- 每回合 assistant 事件的捕获与 transcript 审核规则：stage 1 用户消息之后、stage 2 用户消息之前必须恰有一个 assistant 事件，且只能是 final JSON；stage 2 用户消息之后也必须恰有一个 assistant 事件，且只能是 final JSON。任一回合出现更早的 commentary、可见 analysis、工具调用、附件或同回合第二个 final 都使该回合首次回答失效；合法的 stage 2 final 不追溯使 stage 1 失效；
- 提示文件的精确路径、UTF-8 字节长度与 SHA-256；
- 同条件第一阶段提示散列相同，四席第二阶段提示散列相同。

“精确提示字节”在本协议中不声称平台 wire-byte identity。可验证的传输链定义为：冻结 UTF-8 文件严格解码为 Unicode，解码所得字符串作为派发参数；门后读取任务中的用户消息，再按 UTF-8 编码并与源 SHA-256 比较。派发回执必须记录源散列、回读散列和 thread ID。若平台不能提供可信回读，只能声明“向派发 API 提交的 Unicode 字符串与冻结文本一致”，不得声明精确内容已经送达或 wire bytes 相同。

计划和惰性模板不含真实 thread／session。提交 B 前不得创建实际 Codex 正式任务、thread 或 session；冻结的 `task-packet` 与惰性提示仍须在提交 A 前存在。提交 B 后也必须先取得一次性人工放行。

## 7. 候选包与两提交

在旧正式包契约的门前清单基础上，`continuous-002` 还必须冻结：

- 本增量契约与 `formal-run-delta` 制品链；
- 协议 0.1.1 的两阶段模板、参与者契约和契约检查通过记录；
- `rehearsal-006` procedure-pass 报告的路径与 SHA-256；
- 002 专用或参数化的 Schema／工具闭包；
- 正式 actor 派发计划与八份精确惰性提示；
- 新真值承诺；
- 通过 `truth-continuity-attestation 0.1.0` 校验的非明文真值连续性证明；
- `formal-post-gate-absence-denylist 0.1.0` 与 `external-dispatch-attestation 0.1.0` 的门前契约链；
- 新冻结前像与根摘要。

顺序固定为：

```text
增量契约
→ 002 专用 Schema／工具与自检
→ 来源、编码、审核、投影、夹具与构建
→ 两阶段任务、模板、actor 计划与真值承诺
→ formal-run-delta 审核
→ 全包只读准备门
→ 提交 A
→ 只改 manifest
→ 提交 B
→ 展示证据并等待一次性人工门
```

提交 B 只能改变 manifest 的：

- `freeze_commit`；
- `status`；
- `updated_at`。

## 8. B 时的缺席断言

B 完成时必须用版本化的路径／artifact-type denylist 证明以下仓库制品实例不存在：

- 人工授权实例；
- 正式 actor 描述；
- 实际派发回执；
- 原始回答、机器信封、派生提交与无效首答；
- 第一阶段共同锁；
- 预测集合前像与摘要；
- 正式执行许可；
- 正式原始轨迹、比较器输出与执行结果；
- 明文真值、揭示、制品审核与最终报告。

惰性派发模板、授权／许可 Schema 和工具属于门前冻结依据，不属于上述实例。

仓库校验必须覆盖大小写归一、符号链接解析、manifest 未登记文件与 denylist 外溢，不能只扫描约定目录名。实际 Codex 正式任务、thread 或 session 属于平台外部状态。提交 A 前只冻结 `external-dispatch-attestation 0.1.0` 的 Schema、空模板与校验器；提交 B 推送后、展示人工门材料前，保管者再对项目管理范围内的查询结果生成新鲜证明实例，绑定提交 B、冻结根、`observed_head`、查询时间、查询范围与能力限制。初次 `observed_head` 为提交 B；后续 `observed_head` 必须是 B 的后代，且 B 之后只能有既有外部证明的追加提交。生成时工作区必须干净且仓库缺席检查刚刚通过。

实例追加保存到 `runs/continuous-002/gate/external-dispatch-attestations/<attestation_id>.json`，不进入冻结集。保存提交的父提交必须等于该实例的 `observed_head`，且该提交只能新增该证明。若工作区、外部状态或连续门展示窗口发生变化，必须在新提交追加新证明，不得覆盖旧证明；人工门必须明确引用最新证明及其保存提交。版本化 denylist 只在提交 B 后对该追加式路径族和 artifact type 开例外，其余正式 actor、派发或回答制品仍须缺席。该证明不得被用来宣称平台全局绝对不存在相关对象。

## 9. 失效与放行

以下任一情况使候选包停在 `preparing`，不得建立提交 A：

- 版本矩阵未闭合；
- 仍有旧轮次硬编码；
- 受保护字段、登记散列或差分闭包无法机械核对，或独立来源／投影审核未通过；
- 任一正式配置构建失败；
- 投影、任务、模板、参与者契约或 actor 提示不闭合；
- 真值承诺、冻结前像或根摘要不可复算；
- 门后缺席断言不成立。

提交 B 后改变冻结制品，`continuous-002` 立即失效并转入新编号。

提交 B 与推送只意味着“冻结完成、等待授权”。正式派发仍须用户明确说出针对本轮的“放行正式连续行动试验”；普通的“继续”“完成项目”或此前对 `continuous-001` 的授权都不适用于 `continuous-002`。

## 10. 立即下一步

1. 建立 `formal-run-delta 0.1.0` 与 `formal-actor-dispatch-plan 0.1.0` 的 Schema、工具和自检。
2. 生成旧硬编码扫描报告，逐项决定 0.1.1 专用版或 0.2.0 参数化版。
3. 冻结版本化的门后制品 denylist、外部派发证明契约与非明文真值连续性证明。
4. 只在版本矩阵闭合后创建 `runs/continuous-002/` 的 `preparing` 候选包。
5. 不创建正式会话，不运行正式输入、runner 或 comparator。
