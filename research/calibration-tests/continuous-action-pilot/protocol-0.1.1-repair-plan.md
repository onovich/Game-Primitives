# 连续行动盲测协议 0.1.1 修复计划

> 状态：已完成；门前合成验收与 `rehearsal-006` 四席空白 actor 两阶段首答均通过
> 来源：`continuous-001` 门后阻断事故  
> 目标：先修复参与者接口，再建立新的彩排与正式轮次

## 不可更改的处置

1. 不修改 `continuous-001` 已冻结的任务、模板、Schema、清单或原始回答。
2. 不把保管者归一化后的对象冒充参与者提交。
3. 不为 `continuous-001` 生成预测集合前像或正式执行许可。
4. 不复用 `continuous-001` 的第二阶段回答进入新轮次。
5. 新的正式尝试必须使用新轮次编号、新冻结摘要、新真值承诺和新人工授权。

## 修复目标

参与者只凭实际派发材料，就必须能够构造每一条协议允许分支的 Schema 有效回答。这里的“能够”不是指模型有机会猜中隐藏约束，而是指：

- 字段形状可见；
- 枚举可见；
- 条件规则可见；
- ID 格式可见；
- 单位策略可见；
- 任务指令、模板和 Schema 相互一致。

## 0.1.1 参与者接口

### 1. 让不确定主预测的单位分支可达

对于有量纲观察量，主 `expectations[*].value.unit` 不再写成不可改动的固定字符串，而写成明确的选择占位符：

```json
{
  "serialized_value": "<required-string>",
  "unit": "<null|count>",
  "value_type": "<integer|status>"
}
```

规则为：

- `prediction_status=indeterminate` 时：
  - `expectation_kind=status`
  - `serialized_value=indeterminate`
  - `value_type=status`
  - `unit=null`
- `prediction_status=determinate` 时：
  - 使用观察量允许的值类型；
  - `unit` 等于中性信封声明的单位；
  - 无量纲观察量仍为 `null`。

`compatible_alternatives` 表达的是具体相容世界，因此继续保留观察量的声明单位。

### 2. 派发参与者可见的完整回答契约

回答模板包装器新增机器派生的 `participant_contract`，至少列出：

- `local_id_pattern`
- `integrity_exposure_item_shape`
- 污染枚举
- 每阶段必填字段
- `determinate` / `indeterminate` 条件规则
- 观察量到允许值类型、单位和容差的映射
- 主预测与相容替代的笛卡尔积要求

该契约必须由 Schema 与任务机械生成或复核，不能靠手写摘要独立漂移。

### 3. 明确“替换占位符”与“选择分支”

旧指令只说“替换占位符”，却没有区分：

- 字符串占位符替换；
- JSON `null` 的类型替换；
- 条件分支下允许删除、清空或扩展的数组。

0.1.1 必须把模板定义为“带类型的选择模板”，并在任务中明确哪些值是冻结常量，哪些值是参与者必须选择的槽位。

`confidence_percent` 同样是参与者必须选择的类型化槽位：

```json
{
  "confidence_percent": "<integer-0-100>"
}
```

任务必须明确要求把它替换为 0 至 100 的 JSON 整数；模板不得用超出响应 Schema 范围的哨兵值冒充冻结常量。

## 新增门前检查

[`verify-prediction-template-contract-v0.1.0.py`](tools/verify-prediction-template-contract-v0.1.0.py) 是第一道新增检查。它现在能够：

- 复核任务、模板和响应 Schema 的散列绑定；
- 复核每案配置—观察量笛卡尔积；
- 复核相容替代保留声明单位；
- 在 Schema 要求 `unit=null` 时，拒绝有量纲主预测中的固定单位；
- 拒绝没有向参与者说明 `indeterminate → unit=null` 的任务。

当前冻结材料应稳定得到 `21` 项失败：

```text
python research/calibration-tests/continuous-action-pilot/tools/verify-prediction-template-contract-v0.1.0.py verify \
  --repo-root . \
  --task research/calibration-tests/continuous-action-pilot/runs/continuous-001/inputs/stage2-prediction.task.json \
  --template research/calibration-tests/continuous-action-pilot/runs/continuous-001/inputs/prediction-response.template.json \
  --response-schema research/calibration-tests/continuous-action-pilot/schema/blind-response-interface-0.1.0.schema.json
```

其中一项是缺少参与者可见的单位指令，另外二十项是不可达的固定单位分支。工具自身的无文件写入自检为：

```text
python research/calibration-tests/continuous-action-pilot/tools/verify-prediction-template-contract-v0.1.0.py self-test
```

0.1.1 不覆盖这组事故复算材料，而是新增阶段专用检查：

- [`verify-prediction-template-contract-v0.1.1.py`](tools/verify-prediction-template-contract-v0.1.1.py) 从任务、响应 Schema 与角色 Schema 机械派生预测参与者契约，并逐字段复核模板、分支、单位和配置—观察量笛卡尔积；
- [`verify-reconstruction-template-contract-v0.1.1.py`](tools/verify-reconstruction-template-contract-v0.1.1.py) 机械派生重构参与者契约，并拒绝第二阶段观察规则泄漏；
- [`build-role-submission-v0.1.1.py`](tools/build-role-submission-v0.1.1.py) 只接受参与者原始 payload，校验前序重构和前序任务的显式绑定，再确定性生成机器信封与 0.1.2 提交；
- [`materialize-rehearsal-006-prompts.py`](tools/materialize-rehearsal-006-prompts.py) 生成并复核四席 projectless 会话使用的逐字节两阶段操作提示与派发计划；
- [`verify-rehearsal-006.py`](tools/verify-rehearsal-006.py) 在不含 `runs/` 的临时白名单仓库镜像中重放全部正例、负控和契约检查。

验收条件 1—7、9、10 已在冻结前通过并记录于
[`participant-interface-readiness.json`](rehearsals/rehearsal-006/inputs/audits/participant-interface-readiness.json)。
条件 8 已在冻结后由四个全新 projectless 会话完成：四席都在无追加格式提示、无工具调用的情况下连续完成两阶段首答，结果与逐字节绑定见
[`rehearsal-006` 验收报告](rehearsals/rehearsal-006/reports/findings.md)。

## `rehearsal-006` 的验收条件

在新的正式包冻结前，先建立 `rehearsal-006`，且同时满足：

1. 最小重构回答通过。
2. 带非空 `integrity_exposures` 的重构回答通过。
3. 大写本地 ID 的负控被拒绝，并在参与者材料中能找到对应规则。
4. 确定预测分支通过。
5. 不确定预测分支通过。
6. 两个完整相容替代通过。
7. 固定有量纲单位的旧模板负控被新增检查拒绝。
8. 四个隔离的空白 actor 首答直接有效；不能依赖保管者追加格式提示。
9. 彩排不读取或运行任何正式输入。
10. 新的 readiness 检查把参与者契约、分支闭合检查及其 Schema 纳入冻结集合。

上述十项现已全部通过。可以建立 `continuous-002` 的增量契约与门前候选包；这不授权创建正式 actor、派发盲测、运行冻结输入、生成预测集合／执行许可或揭示真值。

## 方法上的一般化

本次事故区分了三个经常被混为一谈的性质：

1. **数据 Schema 有效**：某个对象可以通过校验。
2. **模板分支闭合**：模板能表达 Schema 允许且任务可能要求的所有对象。
3. **参与者可构造**：参与者只凭派发材料就知道如何选择并表达这些对象。

正式盲测需要三者同时成立。今后的准备门不能再用一个由工具直接改写字段的合成载荷，替代对模板分支闭合和参与者可构造性的检查。
