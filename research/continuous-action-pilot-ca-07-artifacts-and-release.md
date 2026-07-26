# 连续行动组 CA-07：制品、增量彩排与正式放行

- 状态：已冻结；授权准备制品与增量彩排，不授权正式盲测或真实结果执行
- 日期：2026-07-27
- 来源决定：[CA-01](continuous-action-pilot-ca-01.md)–[CA-06](continuous-action-pilot-ca-06-execution-and-verdicts.md)
- 接受记录：[ADR 0115](../docs/adr/0115-freeze-continuous-action-artifacts-rehearsal-and-release.md)
- 彩排后修订：[ADR 0116](../docs/adr/0116-separate-blind-payloads-from-generated-submission-envelopes.md)
- 正式工作区：`research/calibration-tests/continuous-action-pilot/`

## 1. 决策摘要

连续行动试验采用一个可追加、不可回写的正式轮次包 `continuous-001`，保存：

```text
来源编码
→ 来源审核
→ rich / atomic 独立重构
→ 同一执行者继续预测
→ 保管者确定性执行
→ 真值揭示
→ 分轴报告
```

逻辑组已经验证的承诺、盲化、哈希和 Git 顺序继续复用。正式轮次前只增量彩排本轮新增的链条：

```text
第一阶段重构已冻结
→ 才派发第二阶段变体
→ 全部预测已冻结
→ 才执行精确结果
→ 执行结果已冻结
→ 才揭示真值
```

CA-07 的冻结授权：

- 建立 Schema 和工作区；
- 制作来源包、规范编码、生成规则、夹具和比较器；
- 完成来源编码与忠实度审核；
- 执行虚构材料的增量彩排；
- 做工具链与非正式输入的准备性构建检查。

CA-07 不授权：

- 派发四名正式盲测执行者；
- 运行三案的冻结正式输入；
- 产生或查看正式精确结果；
- 揭示真值；
- 召开校准门 D。

## 2. 工作区

```text
research/calibration-tests/continuous-action-pilot/
├── README.md
├── schema/
│   ├── run-manifest-0.1.0.schema.json
│   ├── ca-sr-artifact-0.1.0.schema.json
│   ├── task-packet-0.1.0.schema.json
│   ├── role-submission-0.1.0.schema.json
│   ├── execution-artifact-0.1.0.schema.json
│   ├── truth-reveal-0.1.0.schema.json
│   └── run-report-0.1.0.schema.json
├── rehearsals/
│   └── rehearsal-001/
└── runs/
    └── continuous-001/
        ├── README.md
        ├── manifest.json
        ├── source/
        │   ├── source-packet.json
        │   ├── canonical-encoding-v0.1.0.json
        │   └── source-audit-v0.1.0.json
        ├── inputs/
        │   ├── source-encoding-packet.json
        │   ├── source-audit-packet.json
        │   ├── projection-spec.json
        │   ├── stage1-view-v01.json
        │   ├── stage1-view-v02.json
        │   └── stage2-variant-envelope.json
        ├── fixtures/
        │   ├── fixture-lock.json
        │   ├── r1/
        │   ├── r2/
        │   └── r3/
        ├── execution/
        │   ├── execution-plan.json
        │   ├── trace-bundle.json
        │   └── execution-result.json
        ├── submissions/
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

目录只在产生真实制品时创建，不用 `.gitkeep` 预造空层级。JSON 保存结构化事实真值；Markdown 只负责导航、任务说明和生成阅读视图。

## 3. 七个 Schema 家族

不为三款游戏、两种视图或四名执行者复制格式：

| Schema | 覆盖范围 |
| --- | --- |
| `run-manifest` | 状态、阶段、制品索引、哈希、可见范围和承诺 |
| `ca-sr-artifact` | 来源包、规范编码、机械视图和投影规则 |
| `task-packet` | 编码、审核、重构和预测的自包含派发信封 |
| `role-submission` | 来源审核、重构、预测和揭示后制品审核 |
| `execution-artifact` | 执行计划、轨迹包和执行结果 |
| `truth-reveal` | 密封真值、映射、别名见证、随机数揭示和承诺复算 |
| `run-report` | 每角色 `CA-H01`–`CA-H04` 向量与组级结论 |

每个 Schema 使用 `artifact_type` 作为封闭判别器，并以 `oneOf` 区分同家族 payload。禁止 `custom`、任意 `parameters` 和未声明属性。

Schema 文件名携带版本。正式轮次一旦引用，对应文件不再修改；语义变化发布新版本。轮次清单直接记录根工作区 Schema 的路径和 SHA-256，不复制 Schema 到每个轮次。

## 4. 字节与散列约定

全部结构化制品：

- UTF-8 无 BOM；
- LF；
- 两空格缩进；
- 按冻结规则递归排序 JSON 键；
- 单一末尾换行；
- SHA-256 对精确文件字节计算，不对重排后的“语义等价内容”计算。

Manifest 中每项至少记录：

```json
{
  "artifact_id": "input-stage1-v01",
  "path": "inputs/stage1-view-v01.json",
  "artifact_kind": "task_packet",
  "artifact_version": "0.1.0",
  "sha256": "...",
  "schema_path": "research/calibration-tests/continuous-action-pilot/schema/task-packet-0.1.0.schema.json",
  "schema_sha256": "...",
  "audience": ["condition-v01"],
  "release_stage": "reconstruction",
  "decision_relevant": true
}
```

冻结制品集合的根摘要：

```text
按 path 排序
path + TAB + file_sha256 + LF
→ SHA-256
→ frozen_artifact_set_digest
```

`manifest.json` 不列入该集合，避免自引用。后续可以追加新制品并更新状态或阶段，但冻结集合、单项散列与根摘要不得改变。

真值承诺继续使用：

```text
SHA-256(secret_nonce_bytes || exact_truth_bundle_bytes)
```

承诺值直接进入冻结 manifest；不另建只有一行信息的文件。明文真值、条件映射和 `secret_nonce` 在揭示前保存在仓库外。

## 5. 证据链

```text
stage-1 submission SHA
        ↓ prior_submission_sha256
stage-2 prediction
        ↓ prediction_set_digest
execution result
        ↓ execution_result_sha256
truth reveal
        ↓
final report
```

第二阶段提交必须引用同一执行者第一阶段提交的 SHA-256。执行结果必须引用预测集合摘要；揭示必须引用执行结果摘要；报告引用全部上游制品。

## 6. 中性条件与派发面

两个视图只称为 `condition-v01` 和 `condition-v02`。rich／atomic 映射进入密封真值，不能出现在文件名、字段名或盲测说明中。

- 两人收到逐字节相同的 `stage1-view-v01.json`；
- 两人收到逐字节相同的 `stage1-view-v02.json`；
- 四人使用 CA-06 冻结的同模型、同参数和不同空白会话；
- 同一执行者在第二阶段继续自己的原会话，只能看见自己的第一阶段回答；
- 四人收到逐字节相同的 `stage2-variant-envelope.json`；
- 变体信封不得包含预期结果、来源名称、条件含义或带答案倾向的 ID。

重构和预测都允许 `indeterminate`。作品猜测、市场名称和外部术语不能替代结构恢复。

## 7. 正式顺序

### 7.1 阶段 A：来源制作

1. 冻结来源包、编码任务和 CA-SR Schema；
2. 一名**来源编码者**提交规范编码；
3. 一名来源忠实度审核者依据冻结定位审核；
4. 审核拒绝时保留旧版本，编码者新增版本；
5. 只有 `approved` 版本可以生成下游视图。

### 7.2 阶段 B：机械生成与准备

6. 从同一规范编码机械生成两个中性视图；
7. 审核规范编码、两视图和投影规则的引用闭包与一致性；
8. 制作统一变体信封、执行计划、比较器、夹具锁和密封真值；
9. 可以做工具链、未修改基线编译、变体编译及不跨越受测边界的中性 smoke；
10. 任一案例无法通过准备门时，在冻结前按 CA-03 的停止与备选规则处理。

### 7.3 阶段 C：冻结与人工门

11. 所有测试者可见制品和全部结论规则通过 Schema、哈希与盲化审核；
12. 提交并推送首个 `frozen` Git 提交；
13. 向作者一次性展示人工门材料，等待明确放行。

### 7.4 阶段 D：重构

14. 状态进入 `collecting`，阶段为 `reconstruction`；
15. 四个空白会话取得各自冻结输入；
16. 四份回答全部返回前，不把任何回答写入共享工作区；
17. 四份**首次提交**一起归档、散列、提交并推送。

### 7.5 阶段 E：预测

18. 只有上一阶段提交已冻结的同一执行者才收到变体信封；
19. 每份预测绑定自己的第一阶段 SHA-256；
20. 四份预测全部返回前继续彼此隔离；
21. 四份预测一起归档并推送，生成 `prediction_set_digest`。

### 7.6 阶段 F：执行

22. 保管者只使用冻结来源、补丁、工具链、输入、时钟、停止边界与比较器；
23. 不得根据预测修改夹具、容差或执行顺序；
24. 原始轨迹与派生结果分别保存；
25. 执行结果绑定预测集合摘要，并在揭示前单独提交、推送。

### 7.7 阶段 G：揭示与报告

26. 写入真值和揭示制品，复算承诺；
27. 来源审核者可以在其来源审核冻结后兼任揭示后的制品链审核；
28. 报告逐角色保留 `CA-H01`–`CA-H04`，分别报告 CA-01 压缩命题和 CA-SR 0.1 表示能力；
29. 熟悉度与完整性污染分开记录；
30. 不作玩家技能、难度、策略或体验主张。

## 8. 增量彩排

`rehearsal-001` 只使用一个没有游戏意义的虚构确定性更新系统，不使用 *FOOTSIES*、id 移动源码、osu!lazer 或其规则。

只需要两个空白会话：

- 一人收到 `condition-v01`；
- 一人收到 `condition-v02`；
- 两人在第一阶段提交冻结后继续各自原会话完成第二阶段。

彩排只检查六项新增能力：

1. 第一阶段提交全部冻结前，第二阶段信封没有派发；
2. 第二阶段确由原执行者继续，并绑定自己的第一阶段哈希；
3. 执行者看不到另一条件或他人提交；
4. 全部预测冻结并推送后，确定性执行才开始；
5. 执行结果冻结并推送后，真值才揭示；
6. Manifest、Git 历史和散列可以从冻结输入一路复算到报告。

逻辑组已经验证的相同输入、首次提交保存、密钥承诺、Schema 校验和 Git 揭示顺序不再作为“新增九项”重复宣称，但彩排仍必须复用这些基础设施。

任一项失败：

- 永久保留 `rehearsal-001`；
- 报告失败原因；
- 修复进入 `rehearsal-002`；
- 不覆盖首次失败；
- 不进入人工正式派发门。

## 9. 冻结与失效纪律

| 情况 | 处理 |
| --- | --- |
| `frozen` 前发现错误 | 新增制品版本并重新审核，不称轮次失效 |
| `frozen` 后改变可见内容、投影、变体、比较器、容差或真值 | `continuous-001` 失效；修订进入 `continuous-002` |
| 第一阶段提交失效 | 该执行者不得进入第二阶段；结果执行前的替补必须从第一阶段重做 |
| 第二阶段提交失效 | 该执行者两阶段证据均不进入最低有效配置；结果执行前的替补重做完整链 |
| 泄漏到尚未提交的全部执行者 | 整轮失效 |
| 预测错误、压缩预测成功、丰富重构失败 | 都是有效研究结果，不是流程失效 |
| 来源不足或 `representation_gap` | 形成理论／表示结果，不是流程失效 |
| 冻结计划下无法构建或执行 | 对应案例不可评价，不能现场改计划 |
| 使用未冻结补丁、输入或比较器 | 对应案例失效；影响全组时整轮失效 |
| 确定性复跑超出冻结容差 | 对应案例结论不定，保留全部轨迹 |
| 负对照出现机制状态差异 | 不产生支持证据；受影响的 `CA-R3` 链不能通过 |
| 承诺无法复算、真值不符或冻结提交被覆盖 | 整轮失效 |
| 揭示后审核发现问题 | 追加失效或修订报告，不改写原报告 |

Manifest 的主状态继续使用：

```text
preparing
frozen
collecting
revealed
reported
invalidated
```

另用 `stage` 记录 `source_encoding`、`source_audit`、`reconstruction`、`prediction`、`execution` 等工作阶段，不扩张主状态机。

## 10. 一次性人工正式派发门

人工门只出现一次，展示：

- 冻结 Git 提交；
- manifest 与冻结集合根摘要；
- CA-SR 规范、Schema 和哈希；
- 通过审核的来源编码与审核哈希；
- 两个匿名视图和投影规则哈希；
- 变体信封哈希；
- 夹具锁、执行计划、比较器和准备性构建状态；
- 真值承诺；
- 增量彩排报告及提交顺序；
- 四名执行者配置、派发面、污染边界和已知限制。

必须取得类似“放行正式连续行动试验”的明确指令。此前泛化的“继续”不替代这一次门。

放行后，正式阶段按协议连续执行，不再逐阶段请求批准；只有轮次失效、来源切换或需要扩大权限时才停下。

## 11. 为什么这比逻辑组更精简

- 不设置独立夹具标注角色；
- 不按作品复制 Schema；
- 不把根 Schema 复制到轮次；
- 不另建承诺文件；
- 不重复完整流程彩排；
- rich／atomic 各只使用一个三案例输入包；
- 重构与预测复用同一四名执行者；
- 执行轨迹集中在一个 trace bundle；
- Markdown 只作说明和生成阅读视图。

来源、视图、首次提交、预测、执行与揭示之间仍保持逐字节证据链。当前设计不增加任何**共享术语**，也不改变公开理论主线。

## 12. 彩排结果与接口修订

四次保留的虚构彩排依次发现：

1. `rehearsal-001`：预测值没有配置寻址；
2. `rehearsal-002`：根摘要不能按冻结算法复算；
3. `rehearsal-003`：任务包仍引用旧输入散列；
4. `rehearsal-004`：六项阶段链全部通过，但自由手写完整提交信封产生大量格式失效；
5. `rehearsal-005`：可确定与不确定条件的四份原始首答均直接有效，机器装配逐字节可重复。

`rehearsal-004` 的 `procedure_pass` 只确认入选有效链的冻结、执行与揭示顺序，不确认理论，也不证明原提交接口可用于正式盲测。

ADR 0116 对第 3、5、6、7 节作以下窄修订：

- 盲测执行者提交阶段专用原始 payload，不再手写完整 `role-submission`；
- `task-packet 0.1.1` 同时声明原始 payload Schema、允许配置与装配后 Schema；
- 保管工具在收到首答后生成时间、actor、任务、输入与前阶段散列信封；
- `role-submission 0.1.2` 是从原始 payload 与信封确定性派生的机器制品；
- 无效原始首答仍使该执行者链退出，工具不得语义纠错；
- 正式阶段仍须收齐同一阶段后一次归档，彩排中的增量重试不成为正式先例。

修订的完整契约见[盲测回答接口修订](continuous-action-pilot-blind-response-interface.md)。聚焦接口彩排已经通过，接口阻断解除；现在可以继续制作正式包。第 10 节人工门仍须等全部正式材料冻结后召开，并取得一次明确放行。
