# 连续行动先行组：正式轮次包契约

- 状态：已冻结；允许制作 `continuous-001` 门前制品，不授权正式派发或执行
- 日期：2026-07-27
- 决策记录：[ADR 0117](../docs/adr/0117-freeze-the-formal-run-package-contract.md)
- 门前制品修订：[ADR 0118](../docs/adr/0118-separate-formal-pre-gate-artifacts.md)
- 执行许可修订：[ADR 0119](../docs/adr/0119-separate-human-authorization-from-execution-permit.md)
- 上游规则：[CA-07](continuous-action-pilot-ca-07-artifacts-and-release.md)
- 回答接口：[盲测回答接口修订](continuous-action-pilot-blind-response-interface.md)

## 1. 契约目的

本文只回答一个问题：在请求一次性人工放行前，`continuous-001` 必须长成什么样，哪些内容已经冻结，哪些内容只能在放行后追加。

它不替代 CA-01–CA-07 的理论、选案、变体和判定规则。

## 2. 正式目录

```text
research/calibration-tests/continuous-action-pilot/runs/continuous-001/
├── README.md
├── manifest.json
├── source/
│   ├── source-packet.json
│   ├── canonical-encoding-v0.1.0.json
│   ├── encoding-audit-v0.1.0.json
│   └── projection-audit-v0.1.0.json
├── inputs/
│   ├── source-encoding-packet.json
│   ├── source-audit-packet.json
│   ├── projection-spec.json
│   ├── generate-continuous-views-v0.1.0.py
│   ├── stage1-view-v01.json
│   ├── stage1-view-v02.json
│   ├── stage1-condition-v01.task.json
│   ├── stage1-condition-v02.task.json
│   ├── projection-audit.task.json
│   ├── stage2-variant-envelope.json
│   ├── stage2-prediction.task.json
│   ├── actor-plan.md
│   ├── frozen-set-preimage.tsv
│   ├── reconstruction-response.template.json
│   └── prediction-response.template.json
├── fixtures/
│   ├── fixture-lock.json
│   ├── formal-build-readiness-v0.1.0.json
│   ├── r1/
│   ├── r2/
│   └── r3/
├── execution/
│   ├── formal-execution-permit.json
│   ├── execution-plan.json
│   ├── raw/
│   ├── trace-bundle.json
│   └── execution-result.json
├── submissions/
│   ├── actors/
│   ├── dispatch/
│   │   ├── human-gate-authorization.json
│   │   ├── stage1-p01.json
│   │   ├── ...
│   │   ├── stage1-cohort-lock.json
│   │   └── stage2-p04.json
│   ├── raw/
│   ├── envelopes/
│   ├── invalid/
│   ├── p01-stage1.json
│   ├── p02-stage1.json
│   ├── p03-stage1.json
│   ├── p04-stage1.json
│   ├── p01-stage2.json
│   ├── p02-stage2.json
│   ├── p03-stage2.json
│   └── p04-stage2.json
├── reveal/
│   ├── truth.json
│   └── reveal.json
└── reports/
    ├── artifact-audit.json
    └── report.json
```

目录只在有真实制品时创建。`submissions/raw/` 与 `submissions/envelopes/` 采用和派生提交相同的提交 ID；无效首答进入 `submissions/invalid/`，不得覆盖或修补。

## 3. 版本矩阵

| 职责 | 正式版本 |
| --- | --- |
| 清单与阶段索引 | `run-manifest 0.1.1` |
| 来源、编码、投影与视图 | `ca-sr-artifact 0.1.0` |
| 正式任务包 | `task-packet 0.1.2` |
| 夹具锁 | `fixture-lock 0.1.0` |
| 最终构建准备记录 | `formal-build-readiness 0.1.0` |
| 人工放行凭据 | `formal-human-gate-authorization 0.1.0` |
| 预测冻结后的执行许可 | `formal-execution-permit 0.1.0` |
| 逐席派发模板与回执 | `stage1-seat-dispatch-envelope 0.1.0`、`stage2-seat-dispatch-envelope 0.1.0` |
| 第一阶段共同冻结锁 | `stage1-cohort-lock 0.1.0` |
| 中性变体信封 | `variant-envelope 0.1.0` |
| 回答模板 | `response-template 0.1.0` |
| 冻结正式输入轨迹 | `formal-input-trace 0.1.0` |
| 原始回答与机器信封 | `blind-response-interface 0.1.0` |
| 派生角色提交 | `role-submission 0.1.2` |
| 执行计划、轨迹与结果 | `execution-artifact 0.1.1` |
| 真值与揭示 | `truth-reveal 0.1.0` |
| 审核与最终报告 | `run-report 0.1.0` |

正式任务的 `output_schema` 指向原始回答 Schema，`assembled_output_schema` 指向 `role-submission 0.1.2`。来源编码、来源审核与第二道投影审核任务不使用盲测回答装配器。第二道审核必须使用 `projection_audit_task_packet`，输出沿用 `role-submission 0.1.2` 的 `source_fidelity_audit`／`source_audit` 审核信封，并覆盖唯一变量、不变量、引用闭包、第二阶段输入闭包、两种投影的等价闭包、派发对称性、最终构建准备完整性、身份泄漏与答案暗示；任务必须直接散列绑定机械生成器、投影规范及两份生成视图，`projection_fidelity` 与 `atomic_projection_equivalence` 必须同时检查生成逻辑和输出，任务 ID 与输入散列集合必须逐项闭合。

## 4. 门前冻结集合

门前必须冻结：

- README、来源包、通过审核的规范编码与来源审核；
- 投影规范、两个中性视图及其机械生成器；
- 三案的来源身份、兼容补丁、观察补丁、唯一规则变体、冻结正式输入、夹具锁和比较器；
- 三案全部通过的最终构建准备记录；历史 `toolchain-probe-v0.1.2` 只保留准备证据，不代替最终记录；
- 执行计划、容差、不变量、停止边界与负对照；
- 两阶段任务、第二道投影审核任务、结构模板和中性变体信封；信封必须用匿名字段自包含三案的初态、完整有序正式输入、中性不变量定义、结构化容差和停止点定义，并在预测任务中逐项同值绑定；裸 ID 或直接派发来源专用夹具 JSON 都不构成第二阶段输入闭包；
- 八份逐席惰性派发模板、派发／提交装配工具、人工放行凭据 Schema，以及执行许可的 Schema、物化器与只读校验器；实际人工放行凭据只能在提交 B 和一次性人工门之后追加，执行许可只能在四席预测冻结之后机械派生，两者都不进入各自引用的冻结集合；
- 四席 actor 计划，但不包含真实会话 ID；
- 真值承诺，不包含明文真值、密钥或条件映射；
- 所有被引用 Schema 与工具的路径和精确散列；
- 冻结集合规范前像与根摘要。

`fixture-lock.json` 必须把每案的兼容、观察与规则变体实现分别列出；每类实现如实标明 `patch`、`not_applicable` 或 `configuration_only`，不得用空白或伪造补丁填位。三类实际补丁文件不得重叠。只有规则变体可使用 `configuration_only`，且必须绑定同案已锁定的正式输入或通用夹具制品；这种绑定不把通用制品重新归类成变体补丁。每个冻结正式输入使用通用的类型化静态字段和有序输入事件表达，并在门前声明 `authorization_state=withheld`、`execution_status=not_executed`、`formal_input_executed=false` 与 `formal_result_created=false`。

`formal-build-readiness-v0.1.0.json` 必须逐案、逐配置记录通过的构建证据、仓库外构建输出的散列和所用夹具，并明确 `formal_input_executed=false` 与 `formal_result_produced=false`。它通过 `supersedes_probe` 绑定历史探针，但只有自身三案全通过的 `overall_status=passed` 才满足人工门；旧探针中的许可阻断或中性探针通过都不能被解释成最终通过。

`stage2-variant-envelope.json` 是盲测者可见制品，不得包含来源路径、来源身份、作品名、条件映射、rich／atomic 标签或预期结果。每案公开中性变量与两种配置，并以匿名字段自包含初态、时间基准、完整有序正式输入、中性不变量、观测、停止边界和结构化容差；这些字段提供执行语义，不提供来源身份或预期结果。

以下只能在门后追加：

- 实际 actor 与 `session_id`；
- 原始首答、机器信封、派生提交和无效首答；
- 预测集合规范前像、摘要与由其机械派生的正式执行许可；
- 正式原始执行输出、轨迹与结果；
- 明文真值、密钥、条件映射、揭示审核与最终报告。

## 5. 两提交冻结

冻结不尝试让一个提交引用自身：

```text
候选包校验通过
→ 提交 A：冻结锚点
→ 取得 A 的 Git SHA
→ 只更新 manifest
→ 提交 B：清单定稿
→ 人工门
→ 新建并校验 human-gate-authorization.json
→ 第一阶段逐席派发
→ 四席第二阶段预测冻结
→ 机械生成并校验 formal-execution-permit.json
→ 正式执行与比较
```

提交 A 必须首次包含全部冻结制品的精确字节。提交 B 的 `freeze_commit` 等于 A；提交 B 不能改变任何 `included_in_frozen_set=true` 的文件。人工放行凭据在 B 后创建，反向绑定清单中的 A 锚点提交、根摘要、真值承诺，以及最终构建记录、夹具锁、投影审核、授权 Schema、派发器、执行许可 Schema／物化器／校验器与只读准备门校验器；它不绑定整个仍会演进的清单文件散列，也不加入冻结清单，从而避免哈希循环并允许门后阶段索引追加。合成授权分支只服务于系统临时目录中的隔离自检，生产物化策略必须拒绝。

`human-gate-authorization.json` 是预测产生前的一次人工授权，所以不得伪造或预填未来的 `prediction_set_digest`。四席 `p01-stage2.json`—`p04-stage2.json` 全部成为首次有效、规范且连续的预测提交后，保管设施按席位顺序生成唯一的 `prediction-set-preimage.tsv`，再从人工授权与该前像机械派生 `execution/formal-execution-permit.json`。执行许可同时绑定人工授权散列、预测前像散列、预测集合摘要、三案范围和“正式执行／正式比较”两个操作；并按 `CA-R1`、`CA-R2`、`CA-R3` 固定顺序绑定每案正式运行器、正式输入、测试体、比较器、支持制品与轨迹 Schema 的精确路径和 SHA-256。运行包内的目标引用必须与人工授权所绑定清单中的同路径、同散列、已冻结条目闭合。物化时仍须证明正式输入未执行、正式结果未产生。它不需要第二次人工批准，但任何运行器和比较器都必须在接触正式输入、轨迹或输出之前调用同一个只读校验器。

若 B 前发现冻结制品错误，修订仍在 `preparing` 状态进行并重新生成提交 A。若 B 后改变冻结制品，`continuous-001` 失效，修订进入新轮次。

## 6. 执行者身份

`inputs/actor-plan.md` 冻结四个席位的：

- `condition-v01`／`condition-v02` 分配；
- 模型、版本和推理强度；
- 第一阶段与第二阶段必须由同一会话继续；
- 空白上下文、工具禁令、网络禁令和共享工作区禁令。

人工放行后才创建真实会话。保管者随即保存 actor 描述；`capture-envelope` 读取该描述并绑定真实 `session_id`。actor 描述不是门前输入，也不加入冻结根摘要。

## 7. 执行证据链

正式执行的最短结构链为：

```text
execution plan
  ↓
human authorization + frozen prediction set
  ↓
formal execution permit
  ↓
invocation record + raw stdout/stderr/test result
  ↓
trace bundle
  ↓
comparator output
  ↓
execution result
  ↓
truth reveal
  ↓
run report
```

每一箭头都必须由结构化 SHA-256 引用实现。每份原始轨迹和每个比较器输出还必须直接记录同一个非零 `execution_permit_sha256`、`formal_input_sha256` 与 `prediction_set_digest`；仅在进程环境里短暂出现、仅由调用方提供一个文件散列，或只在最终报告中转述都不构成绑定。案例比较器在解释机制语义前，必须先通过通用原始轨迹校验器完成许可复验、执行目标选择、案例 Schema 校验和输入散列闭合。Git 顺序提供时间证据，但不替代文件级引用；报告文字可以解释，不得补造缺失的散列边。

## 8. 门前准备门

人工门前必须全部通过：

1. 所有 JSON 与 Markdown 制品通过其声明 Schema；
2. JSON 使用规范字节格式，路径不越过仓库根；
3. 每项 Schema 与工具散列可复算；
4. 来源定位、编码引用、投影与任务输入闭包完整；每个受控变量在规范编码中、并在 rich 视图中至少被一个结构关系或规则角色精确引用；rich 视图还必须把中性正式输入 ID、时间基准及匿名输入／初态字段连接到结构关系；
5. rich／atomic 视图由同一编码确定性生成；atomic 可按投影规范删除受控变量的职责边，但 rich 不得只在案例边界中声明变量而没有结构引用；
6. 两视图、任务和模板无作品身份或答案暗示；
7. 三案未修改基线均可构建，兼容、观察与规则实现彼此分离，实际补丁引用集合互不重叠；
8. 最终构建准备记录三案、两配置全部通过，且准备性 smoke 不运行冻结正式输入，也不产生正式精确结果；
9. 真值承诺可在仓库外复算，明文未进入共享工作区；
10. 冻结前像、根摘要、提交 A 与 manifest 的 `freeze_commit` 一致。

来源审核分成两道记录：第一道只裁定规范编码能否忠实表达冻结来源；通过后才生成视图。第一道通过记录不能替代后来发现的引用闭包缺口：若受控变量只出现在 `case_scope`，必须修正规范编码并重新审核。第二道直接审计机械生成器、投影规范与生成视图，再裁定投影忠实度、唯一变量、不变量、引用闭包、第二阶段输入闭包、两种投影的等价闭包、派发对称性、身份泄漏和答案暗示。两道都通过，生成器、编码与视图才可进入冻结集合。

只读校验器 `tools/verify-formal-readiness.py` 检查门前必备制品全集、专用 Schema、散列闭包、夹具补丁分离、最终构建准备记录、中性初态／正式输入／不变量／容差定义、受控变量和输入字段的结构引用闭包、变体信封盲化、预测模板的配置—观测笛卡尔积、第二道审核通过记录和正式输入未执行状态。第二阶段任务只允许派发中性信封和回答模板，不得直接加入来源专用夹具 JSON。第二道审核任务必须直接绑定机械生成器、投影规范、两份生成视图、最终夹具锁、执行计划和最终构建准备记录；审核结果再直接绑定该任务及任务的全部输入。这个单向顺序避免锁定哈希循环：

```text
fixture components
→ final build-readiness record
→ fixture lock
→ execution plan
→ projection-audit task
→ projection-audit result
→ manifest
```

校验器只读取文件并调用包校验器，不调用夹具、比较器或任何正式输入。候选包先运行：

```text
python research/calibration-tests/continuous-action-pilot/tools/verify-formal-readiness.py research/calibration-tests/continuous-action-pilot/runs/continuous-001/manifest.json --repo-root .
```

两提交冻结完成后再加 `--require-frozen`。任一次失败都不得请求人工门。

任何一项失败都留在 `preparing`，不得请求人工正式派发门。

## 9. 当前边界

本契约完成后仍不表示：

- 三个正式案例已经构建成功；
- 规范编码或来源审核已经完成；
- 投影视图、夹具、比较器或密封真值已经产出；
- 正式盲测或正式执行已经获准；
- CA-01 或 CA-SR 0.1 获得证据支持。

下一顺序固定为：来源包 → 来源编码任务 → 独立编码 → 独立审核 → 投影与夹具 → 全包校验 → 两提交冻结 → 一次性人工门。
