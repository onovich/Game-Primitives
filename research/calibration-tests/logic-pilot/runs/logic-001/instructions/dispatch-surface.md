# `logic-001` 盲测派发面

本文件冻结每类执行者在**首次提交**前可以收到的材料。列出的文件在实际派发时逐字内联；执行者不通过文件系统读取。未列出的轮次制品一律不派发。

## 两名**重构者**

两人分别从空白会话启动，使用相同模型、参数、内容与顺序，只改变 `submission_id` 和 `tester.identifier`：

1. `instructions/reconstruction-task.md`
2. `instructions/glossary.md`
3. `inputs/reconstruction-input.json`
4. `inputs/reconstruction-payload.schema.json`
5. `inputs/source-encoding.schema.json`
6. `inputs/reconstruction-response.schema.json`
7. `inputs/logic-submission.schema.json`
8. 派发信封中的模型身份、执行者 ID、提交 ID 与输入 SHA-256

冻结输入 SHA-256：`59d5b07a5682fc38af20dcf5a4c9b8382d922922b53e135e7c385d03c8cc613b`。

## 两名**夹具标注者**

两人分别从空白会话启动，使用相同模型、参数、内容与顺序，只改变 `submission_id` 和 `tester.identifier`：

1. `instructions/annotation-task.md`
2. `instructions/glossary.md`
3. `inputs/annotation-input.json`
4. `inputs/annotation-payload.schema.json`
5. `inputs/annotation-response.schema.json`
6. `inputs/logic-submission.schema.json`
7. 派发信封中的模型身份、执行者 ID、提交 ID 与输入 SHA-256

冻结输入 SHA-256：`4c74dec698c8e60e0db278ad5f9b708110fc5bde5352635d658d8894573d14ce`。

## 明确排除

盲测派发不得包含完整 `GP-SR 0.1` 方法快照、来源包、来源视图、来源审核、修订记录、制作记录、清单、**答案承诺**、随机种子、逻辑映射、配对、真值、其他执行者消息或提交。完整方法快照中的词汇边界章节列出了禁止提示的项目术语，因此只能存档，不能误入重构者输入。

执行者不得调用工具、网络、文件系统或子代理。该限制是程序性边界；若执行者声明或暴露包外访问，按污染协议记录，不静默修补或重跑。
