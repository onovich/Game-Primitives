# `logic-001` 独立重构任务

## 任务边界

你只依据派发消息中内联的冻结材料工作：本说明、测试本地术语表、重构输入、重构 payload Schema、其依赖的来源编码 Schema、重构 response Schema 与通用 submission Schema。

不得调用工具、读取文件或网页、检索原型、联系其他执行者、创建子代理，或查看包外项目材料、答案、映射、夹具、预期标签和其他提交。即使你凭既往知识认出某个原型，也必须先完成结构重构，并在 `pollution` 中如实登记。

## 每项输出

输入包含四个随机排序、使用无语义 ID 的结构项目。对每项都要：

1. 重述关键**实体**、**状态**、**关系**与作用域；
2. 重构动作或系统过程的触发、前置条件、许可、结算与效果；
3. 重构完成、终止或其他评价条件；
4. 说明规则之间的组合关系和时间方向；
5. 明确列出不能等同处理的结构判断，以及无法由输入唯一确定的分叉；
6. 只引用题面中的 `rule-*` 与 `ref-*` ID，不补写作品身份或来源术语。

每个 `response` 必须符合 `inputs/reconstruction-response.schema.json`。`structural_distinctions` 写你从题面恢复出的非等价判断或边界，不要求复述任何项目术语。若整体无法判断，仍需填写可恢复部分并令 `indeterminate: true`。

## 提交信封

最终只输出一个符合通用 `logic-submission.schema.json` 的 JSON 对象，不使用 Markdown 代码围栏或额外说明。派发消息会给出你的 `submission_id`、`tester.identifier`、模型名和精确 `input_sha256`；必须原样使用。

- `responses` 必须与输入项目一一对应，保持输入顺序；
- `task_kind` 固定为 `reconstruction`；
- `response` 必须通过重构 response Schema；
- 对象键按 Unicode 码点升序，使用两个空格缩进；
- 首次完整 JSON 即为不可回写的**首次提交**；之后只允许另行追加勘误，不得替换首次字节。

若没有调用工具或接触包外材料，污染字段应如实使用 `none`、`not_applicable` 与空数组；不要把“按题面推理”登记成外部检索。
