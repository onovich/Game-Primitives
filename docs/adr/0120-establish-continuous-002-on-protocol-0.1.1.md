# 0120 以协议 0.1.1 建立 continuous-002 的不可回写增量契约

- 状态：已接受
- 日期：2026-07-28
- 来源证据：`continuous-001` 协议事故、协议 0.1.1 修复计划与 `rehearsal-006`
- 修订对象：[ADR 0117](0117-freeze-the-formal-run-package-contract.md)、[ADR 0118](0118-separate-formal-pre-gate-artifacts.md)、[ADR 0119](0119-separate-human-authorization-from-execution-permit.md)

## 背景

`continuous-001` 在正式输入执行前失败关闭。失败来自参与者接口：旧模板虽然对应合法 Schema，却没有让参与者仅凭派发材料构造所有合法分支。它没有产生预测集合、执行许可、正式轨迹、比较结果或真值揭示。

协议 0.1.1 将重构与预测契约分离，引入类型化选择模板、参与者可见契约和确定性保管装配。`rehearsal-006` 随后用四个独立 projectless 空白会话完成两条件 A/B、两阶段首答；八份原始回答首次即有效，且确定与不确定分支都可实际构造。

但 ADR 0117 冻结的是 `continuous-001` 与旧回答接口。现有授权、派发、执行许可、轨迹、比较器和准备门家族也有大量轮次 ID、路径或旧 Schema 散列绑定。原位修改这些文件会破坏历史复算；只复制旧包并替换模板又会留下跨轮次硬编码。

## 决策

### 1. 轮次性质

建立 `continuous-002` 作为同一研究设计的**接口修复重跑**，不是新的理论操纵。

以下研究设计保持不变：

- CA-01 的核心失真与可反驳命题；
- CA-02–CA-03 的案例职责、作品、版本与来源范围；
- CA-SR 0.1；
- CA-05 的单变量反事实与装饰负对照；
- CA-06 的双条件、四项硬条件、熟悉度／污染与结论优先级；
- CA-07 的追加式证据链、两提交冻结和一次性人工门。

若候选包需要改变上述任何语义内容，必须另立决定；不得把它伪装成接口迁移。

### 2. 不可回写与禁止复用

`continuous-001` 的冻结制品、Schema、工具、事故记录、actor、session、原始回答、信封和派生提交保持原样。不得为它补造预测集合、执行许可、轨迹、结果或揭示。

`continuous-002` 不得复用 `continuous-001` 的：

- 盲测回答、actor 或 session；
- 派发回执、共同阶段锁或人工授权；
- 预测集合前像、执行许可或真值承诺；
- 运行绑定的任务、模板、信封、清单或路径散列。

相同研究语义应从冻结的上游来源、设计决定和生成工具重新物化到新轮次命名空间，而不是从旧 `runs/continuous-001/` 复制门后状态。

`rehearsal-006` 只作为接口验收证据引用，不进入正式理论证据。

### 3. 参与者接口版本

`continuous-002` 固定采用：

- 协议 `0.1.1`；
- `blind-response-interface 0.1.1`；
- `response-template 0.1.1`；
- `reconstruction-response-template 0.1.1`；
- prediction／reconstruction participant response contract `0.1.1`；
- prediction／reconstruction template contract check `0.1.1`；
- `build-role-submission-v0.1.1.py`；
- `task-packet 0.1.2`；
- `role-submission 0.1.2`；
- `run-manifest 0.1.1`。

未改变语义且不绑定旧轮次的家族可继续使用既有版本。任何包含 `continuous-001`、旧回答接口、旧模板、旧装配器或旧散列信任锚的 Schema／工具，都必须以新文件发布：

- 仅修订为 `continuous-002` 专用绑定时，至少升为 `0.1.1`；
- 改造成显式参数化、可跨轮次复用的契约时，升为 `0.2.0`；
- 不得原位编辑旧 `0.1.0` 文件。

至少要审计并新发：最终构建准备、人工授权、执行许可、两阶段逐席派发、第一阶段共同锁、三案原始轨迹、正式比较器输出，以及它们的物化、验证、冻结和准备门工具。

提交 A 前还必须闭合五个新家族：`formal-run-delta 0.1.0`、`formal-actor-dispatch-plan 0.1.0`、`formal-post-gate-absence-denylist 0.1.0`、`external-dispatch-attestation 0.1.0` 与 `truth-continuity-attestation 0.1.0`。外部派发证明在门前只冻结 Schema、空模板和校验器，实际实例在提交 B 推送后生成；真值连续性证明是不含明文、绑定基准／候选承诺与生成或比较过程的门前冻结制品。

### 4. 增量契约制品

门前包必须包含一份通过 `formal-run-delta 0.1.0` 校验的增量契约，至少记录：

- `base_run_id=continuous-001` 与 `candidate_run_id=continuous-002`；
- 基准冻结提交与根摘要；
- 协议、回答接口和模板的前后版本；
- `research_design_change=false`；
- 每项制品的变化种类、路径、散列、参与者可见性与语义变化标记；
- 分开的运行绑定作用域与来源引用作用域；
- 禁止复用集合；
- 仓库门后制品缺席断言、`external_dispatch_attestation_required_after_b=true` 及所冻结证明契约；
- `candidate_status_at_audit=preparing`、`expected_post_b_status=frozen` 与审核结论。

该 Schema 和物化／验证工具必须在提交 A 前进入冻结集合。增量记录的逐项散列作用域排除记录自身、manifest、冻结前像与根摘要，避免散列自引用；冻结前像必须登记增量记录实例的 SHA-256，但不得登记自身，manifest 再单向绑定冻结前像与根摘要。旧轮次只禁止进入任务、提示、信封、授权、许可和轨迹等运行绑定字段，允许作为增量记录、ADR 和审核材料的来源引用。

`research_design_change=false` 由机器差分闭包与独立来源／投影审核共同支持：工具只能证明受保护字段、路径和散列没有未声明变化，不能用一个布尔字段替代语义审核。

新真值承诺在揭示前只能证明来源和生成过程受控；门前另需冻结通过 `truth-continuity-attestation 0.1.0` 校验的非明文证明，绑定基准／候选承诺、确定性再生成器或离线比较过程及审核者，隐藏明文与基准语义相同的最终机械复核留到揭示后完成。

### 5. 正式 actor 计划

门前新增并冻结 `formal-actor-dispatch-plan 0.1.0` Schema、工具和实例，约束四个正式席位的条件分配、模型别名与推理强度、两阶段提示、projectless 空白上下文、同会话续接、工具／网络／共享工作区禁令、无效第一阶段不得续跑及零纠错规则。每个派发回合的首个且唯一 assistant 事件必须直接是 final JSON：stage 1 与 stage 2 用户消息之间恰有一个，stage 2 用户消息之后也恰有一个；同回合更早的 commentary、可见 analysis、工具调用、附件或第二个 final 都使该回合首次回答失效，合法的 stage 2 final 不追溯使 stage 1 失效。计划中的实际 build 固定为 `null`／`unknown`，平台返回值只在门后 actor 描述或回执中追加。

“精确提示字节”只指可审核传输链：冻结 UTF-8 文件严格解码为派发字符串，门后回读用户消息再按 UTF-8 编码并复核散列；回执记录源散列、回读散列和 thread ID。无法可信回读时只能声明“向派发 API 提交的 Unicode 字符串与冻结文本一致”，不声明精确内容已经送达或平台 wire-byte identity。

提交 B 前不得创建实际 Codex 正式任务、thread 或 session；冻结的 `task-packet` 与惰性提示仍须在提交 A 前存在。真实 actor 描述、派发回执和首次回答只能在一次性人工门之后追加。

### 6. 两提交与一次性人工门

继续使用两提交冻结：

1. 提交 A 首次包含全部门前冻结制品的精确字节，manifest 仍为 `preparing`；
2. 提交 B 只修改 manifest 的 `freeze_commit`、`status` 与 `updated_at`，其中 `freeze_commit=A`。

提交 B 后改变任何冻结制品都会使 `continuous-002` 失效。

B 完成时，版本化路径／artifact-type denylist 必须证明仓库中仍不存在：

- 人工授权实例；
- 正式 actor 描述或派发回执；
- 原始回答、机器信封、派生提交或共同阶段锁；
- 预测集合前像或执行许可；
- 正式轨迹、结果、明文真值、揭示或最终报告。

实际 Codex 正式任务、thread 与 session 属于平台外部状态。提交 A 前只冻结外部证明的 Schema、空模板和校验器；提交 B 推送后、展示人工门材料前，保管者再在项目管理范围内生成新鲜证明实例，绑定提交 B、冻结根、`observed_head`、查询时间、范围与能力限制。初次 `observed_head` 为 B；之后只能是 B 的后代，且 B 后只能追加既有证明提交。实例保存到 `runs/continuous-002/gate/external-dispatch-attestations/<attestation_id>.json`，不进入冻结集；保存提交的父提交等于 `observed_head`，且只能新增该证明。状态变化或门展示中断／延后时追加新证明，不覆盖旧证明；人工门引用最新证明及其保存提交。denylist 只在 B 后为该路径族和 artifact type 开例外。仓库校验不得声称证明平台全局不存在相关对象。

完成 B 并推送后，必须向作者展示 A/B、冻结摘要、增量差分、真值承诺、构建状态、彩排证据与已知限制，再取得明确针对 `continuous-002` 的“放行正式连续行动试验”。一般性的“继续”不替代该门。

## 影响

本决定允许制作 `continuous-002` 的增量契约、Schema／工具闭包和门前候选包，止于提交 B。它不授权正式派发、运行正式输入、比较、揭示或理论判断。

本决定不增加**共享术语**，不修改 CA-SR 0.1，也不把程序性彩排结果升级为游戏设计证据。
