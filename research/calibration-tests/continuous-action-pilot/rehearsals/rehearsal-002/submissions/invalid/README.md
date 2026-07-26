# 无效首次尝试

两名原始重构者都正确理解了视图内容，但没有遵守 `role-submission 0.1.1` 的结构约束：

- `pollution` 缺少嵌套的 `familiarity` 对象并包含未声明字段；
- `case_id` 使用了不合法的 `ca-r2`；
- `uniqueness` 使用未声明枚举；
- `recovered_facts` 与 `compatible_branches` 使用字符串而非带稳定 ID 的对象。

两份原件永久保留且不被改写。因为真值、变体和另一条件尚未向它们暴露，本轮允许从新的空白会话取得替补首次提交；替补必须使用不同的 actor 与 submission ID。

第一次 v02 替补已经改正对象结构，但在 `supporting_record_ids` 中使用了大写 `CA-R2`，仍不符合局部 ID 约束；其原件保存为 `reconstruction-v02.r1.attempt.json`。
