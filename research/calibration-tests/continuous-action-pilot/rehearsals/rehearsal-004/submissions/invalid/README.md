# 无效提交

首批两个重构提交的 `actor.reasoning_effort` 使用了输出 Schema 不允许的值 `inherited`。错误来自派发模板，而不是执行者对条件材料的判断。

这些首次尝试原样保留，但不得进入预测阶段。替补执行者必须从新的空白会话重新完成第一阶段。

第一次 v02 替补又使用了 Schema 不允许的 `recovery_status: directly_stated`；它同样原样保留，并由新的空白替补重新完成第一阶段。

第二次 v02 替补把必填字段 `claim` 写成了未声明字段 `statement`；该尝试也不进入后续阶段。

第三次 v02 替补的重构有效，但预测在每个 `compatible_alternatives` 对象中增加了未声明字段 `supporting_record_ids`。依照第二阶段失效规则，该执行者的两阶段链不进入有效配置；新的空白替补必须从第一阶段重做。

第四次 v02 替补没有沿用指定的顶层制品结构，输出了 `schema_version`、`input_records` 等另一套字段；该提交在第一阶段即失效。
