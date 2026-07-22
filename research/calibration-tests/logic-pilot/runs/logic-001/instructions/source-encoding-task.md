# `logic-001` 来源编码任务

本任务把冻结来源包转写为 `GP-SR 0.1` 结构描述。它是测试准备工作，不是重构、夹具标注或理论判定。

## 可见材料

- `inputs/source-packet.json` 的精确内容；
- `GP-SR 0.1` 的十种基础类型、十一项规则槽位、八种组合关系与四种来源编码状态；
- `schema/source-encoding.schema.json` 规定的输出结构。

不得读取包外项目文件、既有案例分析、受控夹具、预期标签、答案或下游提交；不得调用工具、浏览网页、联系其他执行者或创建子代理。

## 输出职责

对四个 `source_anchor_id` 分别产生：

1. `source_encoding`：可以保留作品身份、来源术语和来源定位，用 `GP-SR 0.1` 忠实表达本轮声明范围；
2. `blind_encoding`：保持与 `source_encoding` 相同的结构语义、`rule_id` 与 `ref_id`，但把作品名、商标、制作者、原角色名和来源专有术语改为中性名称；
3. 明确记录来源无法确定的内容、事前范围排除、表示缺口和无法消除的身份泄漏风险。

每个编码视图必须：

- 只使用 `entity`、`state`、`relation`、`condition`、`action`、`process`、`rule`、`goal_evaluation`、`feedback_observation`、`context_scope` 十种引用类型；
- 每条规则都显式填写 `context`、`trigger`、`preconditions`、`actor`、`target`、`action`、`cost`、`resolution`、`effects`、`feedback`、`goals_evaluation`；
- 空槽位使用 `not_applicable`、`source_underdetermined` 或 `scope_excluded`，不得让下游执行者用作品常识补全；
- 多条规则之间只使用 `sequence`、`parallel`、`nesting`、`gating`、`feedback`、`mutual_exclusion`、`conversion`、`coupling`；
- 凡会改变动作许可、状态变化、规则生效或完成判断的语义都进入正式槽位，不只写在说明区；
- 不增加来源没有给出的唯一性、最优性、策略、难度、体验、界面功能或精确调度；
- 不因为当前项目偏好而隐藏 `source_underdetermined` 或 `representation_gap`。

`source_encoding` 与 `blind_encoding` 中同一 `ref_id` 必须承担同一语义职责；同一 `rule_id` 必须表达同一规则。中性化只允许改名和删除身份定位，不允许删减规则。

最终只输出一个符合 `source-encoding.schema.json` 的 JSON 对象，不使用 Markdown 代码围栏或额外说明。对象键按 Unicode 码点升序排列，使用两个空格缩进。保管者归档时只追加一个末尾 LF，不重排或改写内容。
