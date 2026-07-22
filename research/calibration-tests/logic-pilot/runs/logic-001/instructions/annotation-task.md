# `logic-001` 独立夹具标注任务

## 任务边界

你只依据派发消息中内联的冻结材料工作：本说明、测试本地术语表、标注输入、标注 payload Schema、标注 response Schema 与通用 submission Schema。

不得调用工具、读取文件或网页、检索原型、联系其他执行者、创建子代理，或查看包外项目材料、答案、映射、案例角色、配对关系、预期标签和其他提交。不要尝试把项目按相似性配对；逐项独立判断。若凭既往知识认出某个原型，在 `pollution` 中如实登记，但仍只按题面规则作答。

## 每项输出

输入包含八个随机排序、使用无语义 ID 的匿名项目；同源对照不会相邻。每项有两道题，`allowed_answers` 固定为：

- `yes`：题面足以肯定；
- `no`：题面足以否定；
- `indeterminate`：题面不足以肯定或否定。

不得用置信度代替答案。每个回答都要给出只依赖题面规则与状态的简短理由，并把额外假设放入 `assumptions`。每个 `response` 必须符合 `inputs/annotation-response.schema.json`。

## 提交信封

最终只输出一个符合通用 `logic-submission.schema.json` 的 JSON 对象，不使用 Markdown 代码围栏或额外说明。派发消息会给出你的 `submission_id`、`tester.identifier`、模型名和精确 `input_sha256`；必须原样使用。

- `responses` 必须与输入项目一一对应，保持输入顺序；
- `task_kind` 固定为 `annotation`；
- 每项 `answers` 必须各含一次 `q1` 与 `q2`；
- 对象键按 Unicode 码点升序，使用两个空格缩进；
- 首次完整 JSON 即为不可回写的**首次提交**；之后只允许另行追加勘误，不得替换首次字节。

若没有调用工具或接触包外材料，污染字段应如实使用 `none`、`not_applicable` 与空数组；不要把“按题面推理”登记成外部检索。
