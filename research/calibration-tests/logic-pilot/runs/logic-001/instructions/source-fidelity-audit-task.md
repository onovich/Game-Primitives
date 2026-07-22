# `logic-001` 来源忠实度审核任务

本任务只审核来源编码是否忠实、完整、可盲化和未越界，不评价当前理论是否容易通过，也不参与重构或夹具标注。

## 可见材料

- 已冻结的 `inputs/source-packet.json`；
- 待审核的精确来源编码 JSON 及其 SHA-256；
- `GP-SR 0.1` 与 `schema/source-fidelity-audit.schema.json` 的输出要求。

不得读取包外项目文件、既有案例分析、受控夹具、预期标签、答案或下游提交；不得调用工具、浏览网页、联系其他执行者或创建子代理。

## 审核问题

逐案检查：

1. 是否存在与来源包冲突的事实；
2. 是否遗漏恢复关键规则所必需的来源事实、规则槽位或组合关系；
3. 是否把来源无法确定的事项写成确定事实，或用说明区偷偷承载正式语义；
4. `source_encoding` 与 `blind_encoding` 的 `ref_id`、`rule_id` 与结构语义是否一一对应；
5. `blind_encoding` 是否残留作品名、商标、制作者、原角色名、来源专有术语或不必要的来源定位；
6. 是否加入唯一性、最优性、策略、难度、体验、软件功能、商业版规则或精确调度等范围外内容；
7. 明确来源事实若无法由 `GP-SR 0.1` 承载，是否如实记录为 `representation_gap`。

每个异议必须绑定来源包中的 `locator`，归入 `fact_error`、`necessary_rule_omission`、`ambiguity`、`identity_leakage` 或 `scope_overreach`，并标明是否 `material`。不得用理论偏好或“更容易得到预期结果”作为理由。

- 没有实质异议时用 `approved`；
- 可由编码者依据来源修订的实质异议用 `revision_required`；
- 来源本身不能裁定或表示无法继续的实质问题用 `blocked`。

最终只输出一个符合 `source-fidelity-audit.schema.json` 的 JSON 对象，不使用 Markdown 代码围栏或额外说明。对象键按 Unicode 码点升序排列，使用两个空格缩进。保管者归档时只追加一个末尾 LF，不重排或改写内容。
