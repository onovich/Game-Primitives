# continuous-001 盲测席位与派发计划

- 状态：正式门前；未创建真实 actor、会话、提交或派发回执
- 行为范围：`structural_only`
- 模型：`gpt-5.6-sol`
- 推理强度：`high`
- 当前授权：未获得“放行正式连续行动试验”

本文件描述保管设施如何把已经冻结的输入转化为可复算的派发回执。它不授权派发，也不把任何 `.template.json` 当作已经发生的事件。

## 固定席位

| 席位 | 条件 | 第一阶段 | 第二阶段 |
| --- | --- | --- | --- |
| `p01` | `condition-v01` | 独立重构 | 同一 actor、同一会话继续预测 |
| `p02` | `condition-v01` | 独立重构 | 同一 actor、同一会话继续预测 |
| `p03` | `condition-v02` | 独立重构 | 同一 actor、同一会话继续预测 |
| `p04` | `condition-v02` | 独立重构 | 同一 actor、同一会话继续预测 |

四个席位必须分别从空白上下文开始，并使用两两不同的 `actor_identifier`、`session_id` 和 actor 对象散列。门前不得用占位符冒充真实身份。席位—条件映射既由 Schema 约束，也由工具复算；不能在运行时改派。

## 模板与回执分离

八份 `stageN-dispatch-p0N.template.json` 永远是惰性计划：

- `artifact_type` 必须是 `stage1_seat_dispatch_template` 或 `stage2_seat_dispatch_template`；
- `dispatch_status` 固定为 `template_only`；
- `release_authorized` 固定为 `false`；
- actor、授权、前序提交、cohort lock 和所有文件散列保持显式 `null`；
- 模板不会被填充、改名或覆盖。

真正的门前事实只能写入新建回执：

```text
runs/continuous-001/submissions/dispatch/
├── human-gate-authorization.json
├── stage1-p01.json
├── stage1-p02.json
├── stage1-p03.json
├── stage1-p04.json
├── stage1-cohort-lock.json
├── stage2-p01.json
├── stage2-p02.json
├── stage2-p03.json
└── stage2-p04.json
```

物化工具拒绝覆盖任何已有文件，也拒绝把 `.template.json` 作为输出路径。输出目录必须由保管者事先建立；工具不会代为扩张授权范围。

## 参与者材料与设施材料

`participant_files` 只表示会进入参与者认知上下文的三份材料。

第一阶段每席：

1. 该条件的重构任务；
2. 该条件的投影视图；
3. 重构回答模板。

第二阶段每席：

1. 四席逐字节相同的预测任务；
2. 四席逐字节相同的中性变体信封；
3. 四席逐字节相同的预测回答模板。

`facility_files` 是保管设施用于机械验证的文件集：它等于三份参与者材料的递归 Schema 闭包，再加不进入参与者上下文的人工放行凭据 Schema。`schema_dependency_closure` 只记录参与者材料实际可达的递归依赖边，不伪造一条指向运维 Schema 的认知依赖。两者都不属于参与者材料。逐席 dispatch template、dispatch receipt、cohort lock、授权凭据及其 Schema 同样不派发给参与者。

任何参与者材料或其引用若触及另一条件、其他席位、来源包、fixture、comparator、真值、提交或结果，物化必须失败关闭。

## 人工放行凭据

冻结提交 B 完成且只读准备门以 `--require-frozen` 通过后，仍须取得作者一次明确的正式放行。保管设施随后才可在固定路径新建 `human-gate-authorization.json`。该文件必须：

- 使用 `formal-human-gate-authorization 0.1.0`，记录明确用户消息的来源定位与精确消息散列；
- 绑定 `manifest.json` 路径及其中不可改写的 `freeze_commit`、`frozen_artifact_set_digest` 与真值承诺；不绑定整个清单文件的散列，因为清单会在门后追加阶段索引；
- 绑定最终构建准备记录、夹具锁、通过的投影审核和当时使用的只读准备门校验器；
- 绑定授权 Schema、派发物化器，以及执行许可 Schema／物化器／校验器自身的精确散列，防止门后替换契约实现；
- 声明放行范围仅为盲测派发，以及“预测集合冻结后才可执行正式输入”的条件性后续范围；
- 明确记录授权前正式输入未执行、正式结果未生成；
- 保持规范 JSON 字节，且不覆盖既有文件。

授权凭据不进入它所引用的冻结清单，否则会形成清单与授权互相包含的哈希循环。任何任意文本文件、早期“同意”、模板中的 `null`，或未绑定冻结依据的 JSON 都不能替代它。Schema 另有封闭的 `synthetic_self_test` 分支，但生产策略拒绝该分支；只有系统临时目录中的无 Git、带专用标记副本及内部环境令牌同时成立时，合成流水线才可使用它。

## 预测冻结与执行许可

人工放行凭据产生于参与者预测之前，因此不记录未来的预测摘要。第二阶段只有在 `p01`—`p04` 四席的首次有效提交都通过连续性、席位、条件映射和规范字节校验后，才按固定顺序写出：

```text
submissions/prediction-set-preimage.tsv
```

前像恰有四行，每行为 `<repo-relative stage2 submission path>\t<sha256>\n`，路径依次为 `p01-stage2.json`、`p02-stage2.json`、`p03-stage2.json`、`p04-stage2.json`。该文件精确字节的 SHA-256 同时是 `prediction_set_digest`。

随后保管设施从正式人工授权与预测前像机械派生：

```text
execution/formal-execution-permit.json
```

执行许可不进入其引用的冻结集合，也不需要第二次人工批准。它必须绑定正式而非合成授权、四席预测前像、三案范围和正式执行／比较范围，并证明物化时正式输入尚未执行、正式结果尚未产生。R1、R2、R3 的运行器与比较器在接触正式输入、原始轨迹或输出之前，都必须调用同一个只读校验器；每份原始轨迹和比较器输出还须写入同一个 `execution_permit_sha256` 与 `prediction_set_digest`。

## 第一阶段回执

获得一次明确的作者放行并保存授权回执后，保管设施才可为每席建立第一阶段回执。回执只记录派发前能够从现有字节复算的事实：

- 模板、授权回执和 actor 来源文件的路径与 SHA-256；
- 固定的席位—条件—任务—视图映射；
- actor 标识、会话与规范化 actor 对象散列；
- 精确的参与者文件集、设施 Schema 集、递归依赖边及各文件散列；
- `dispatch_status: ready_for_dispatch` 与 `release_authorized: true`。

actor 对象的唯一散列算法为：

```text
UTF-8(
  json.dumps(actor, ensure_ascii=false, sort_keys=true, indent=2)
  + "\n"
)
```

即键名排序、两空格缩进、非 ASCII 不转义、仅 LF，并以一个 LF 结尾；再对这些精确字节计算 SHA-256。

第一阶段回执不能声明任何尚未收到的回答性质，例如答案键唯一、笛卡尔积覆盖、歧义见证或响应 Schema 已通过。那些都属于回答到达后的验证。

## 第一阶段冻结与 cohort lock

第二阶段不能按单席提前放行。只有四席各自的以下四类制品全部存在、通过相应 Schema 与连续性校验，并以精确散列冻结后，才可新建唯一的 `stage1-cohort-lock.json`：

1. 第一阶段派发回执；
2. 原始回答载荷；
3. 机器装配信封；
4. 首次有效重构提交。

cohort lock 必须复算并证明：

- 恰有 `p01`—`p04` 四席，每席一次；
- `p01`、`p02` 为 `condition-v01`，`p03`、`p04` 为 `condition-v02`；
- 四个 actor 标识、会话和 actor 对象散列分别两两不同；
- 每份提交与对应第一阶段回执使用同一 actor、会话、条件、任务和输入散列；
- 原始载荷、机器信封、装配提交和第一阶段回执均能由锁中引用重新取得相同字节；
- 四份第二阶段模板声明完全相同的 `participant_files`、`facility_files` 与递归 Schema 闭包。

任何一席缺失、重复、污染或不一致时，不得生成 cohort lock，也不得物化任何第二阶段回执。

## 第二阶段回执

第二阶段回执必须同时绑定：

- 唯一且可复验的 `stage1-cohort-lock.json`；
- cohort lock 中该席位唯一的第一阶段派发回执；
- cohort lock 中该席位唯一的冻结重构提交；
- 从第一阶段继承且不可改写的 actor、会话、条件视图及其散列；
- cohort lock 冻结的共同第二阶段参与者文件、设施 Schema 与依赖闭包；
- 与第一阶段相同的作者授权回执。

因此第二阶段不是“重新选择输入”，而是对已经完成四席冻结的共同输入做逐席实例化。工具拒绝另一席提交、另一条件、另一 actor、不同 cohort、被修改的共同文件或错误的预定输出路径。

## 回答到达后的验证

派发回执只证明“放行前输入与身份绑定成立”，不证明参与者将来提交的内容正确。回答到达后，保管设施另行永久保存原始字节，再由 submission builder 和回答 Schema 完成：

- 回答接口与 artifact type 校验；
- `CA-R1`、`CA-R2`、`CA-R3` 的案例覆盖；
- 标识键唯一；
- 配置—观察量笛卡尔积覆盖；
- `indeterminate` 时的完整兼容替代与分歧见证；
- 机器信封、原始载荷、装配提交和 prior 的连续性绑定。

任何失败回答都保留为原始证据，但不进入有效 cohort。替补必须换用新的空白 actor 与会话，从第一阶段重新开始。

## 盲化边界

盲测 actor 在两阶段都不得：

- 调用工具、搜索或访问网络；
- 读取共享工作区或派发包之外的文件；
- 创建子任务；
- 查看另一条件、其他席位、来源身份、fixture、真值或结果；
- 由保管者通过追问补入结构线索或答案暗示。

这是程序性盲化约束，不是权限沙箱。任何意外暴露都必须进入完整性污染记录。

## 唯一物化与验证工具

`tools/materialize-dispatch.py` 只生成或验证保管设施制品，不发送参与者消息，也不运行正式输入：

```text
python tools/materialize-dispatch.py self-test --repo-root <repo>
python tools/materialize-dispatch.py materialize-stage1 ...
python tools/materialize-dispatch.py materialize-cohort ...
python tools/materialize-dispatch.py materialize-stage2 ...
python tools/materialize-dispatch.py verify ...
python tools/self-test-blind-pipeline.py --repo-root <repo>
python tools/materialize-execution-permit.py self-test --repo-root <repo>
python tools/materialize-execution-permit.py materialize --repo-root <repo>
python tools/verify-formal-execution-permit.py verify --repo-root <repo> --permit-path <path> --case-id <CA-R1|CA-R2|CA-R3>
```

第一个 `self-test` 检查 Schema、八份惰性模板、规范化 actor 散列、授权链和 cohort 独立性负例。第二个自检在系统临时目录完成四席、两阶段的完整合成流水线，并验证合成授权进入生产策略、畸形授权、缺回执、错 actor／席位和模板冒充回执均失败关闭；它不复制正式输入、比较器或真实 fixture。执行许可自检同样只能在系统临时目录的可弃副本中运行，并覆盖缺席、重席、错条件、非规范前像、摘要不一致、合成授权与既有正式输出等负例。正式物化命令只在人工门已放行且前序制品真实存在时使用。

`build-role-submission.py` 的 `capture-envelope`、`assemble` 与 `verify` 均必须显式接收本席 `--dispatch-receipt`；第二阶段还必须接收对应的 `--prior-stage-dispatch-receipt`。因此回答不能脱离派发回执单独装配，也不能把另一席或另一阶段的先前提交接入当前链。

## 当前硬停止点

当前没有真实 actor、会话、第一阶段回答、冻结提交、cohort lock 或派发回执，也没有作者的正式放行口令。本轮只完成门前契约及合成自测；不得创建正式会话、派发参与者材料、执行 formal input 或生成正式结果。
