# 连续行动先行组：盲测回答接口修订

- 状态：方法已实现；等待聚焦彩排
- 日期：2026-07-27
- 依据：[rehearsal-004 报告](calibration-tests/continuous-action-pilot/rehearsals/rehearsal-004/reports/findings.md)
- 决策记录：[ADR 0116](../docs/adr/0116-separate-blind-payloads-from-generated-submission-envelopes.md)

## 1. 修订目的

完整 `role-submission` 同时混合了三类责任：

| 内容 | 应由谁决定 |
| --- | --- |
| 对材料的重构、预测与污染自报 | 盲测执行者 |
| 运行、任务、条件、执行者、时间与输入散列 | 保管者 |
| Schema 校验、前阶段连续性、规范字节与散列绑定 | 确定性工具 |

让盲测者自由手写三类内容，会把格式熟练度混入重构与预测结果。修订后的接口只把第一类留给盲测者。

## 2. 制品关系

```text
冻结任务包
  ├─ output_schema → blind-response-interface 0.1.0
  └─ assembled_output_schema → role-submission 0.1.2

原始首次 payload
  + actor 描述
  + 任务包
  + 前阶段提交（仅预测）
  ↓
机器信封
  ↓ 确定性字段复制
role-submission 0.1.2
```

建议正式目录：

```text
submissions/
├── raw/
│   └── <submission-id>.payload.json
├── envelopes/
│   └── <submission-id>.envelope.json
└── <submission-id>.json
```

原始 payload、信封与派生提交都不可回写。模板不是回答，不进入首次提交散列。

## 3. 任务包 0.1.1

盲测任务新增两个字段：

- `allowed_configurations`：预测必须使用的配置 ID；重构为空数组；
- `assembled_output_schema`：机器装配后的完整提交 Schema。

`output_schema` 改为原始 payload Schema。预测任务必须显式列出 `config.baseline` 与 `config.variant`；盲测者不再从示例或命名惯例猜测配置 ID。

## 4. 原始 payload

重构 payload 顶层只有固定协议头、`pollution` 与 `reconstruction_answers`；预测 payload 对应为 `pollution` 与 `prediction_answers`。固定协议头由结构模板预置，不携带运行身份或答案。

盲测者不能填写：

- 运行、任务或条件 ID；
- actor、session 或模型配置；
- 提交时间；
- 输入与前阶段散列；
- 空审核数组；
- 正式提交版本。

模板使用非法占位符而不是候选答案。若占位符残留，首次回答直接失效；装配器不得替换。

## 5. 机器信封

`capture-envelope` 在原始回答到达后执行。它：

1. 验证任务包和全部输入散列；
2. 验证 actor 描述；
3. 预测阶段核对前阶段的 actor、session、条件与运行；
4. 记录任务、输入和前阶段散列组成的 `dispatch_artifacts`；
5. 记录当前 UTC `received_at`；
6. 绑定响应 Schema、输出 Schema 与装配工具的精确字节散列。

信封使“执行者实际获准看见什么”成为可复算的派发记录。它不能证明运行环境绝对隔离，但比只依赖任务禁令和执行者自报更强。

## 6. 确定性装配

`assemble` 先验证原始 payload，再检查：

- 案例集合与任务完全相同；
- 主预测与每个相容替代恰好覆盖全部配置—观察量对；
- 观察量类型与容差没有越过任务许可；
- 不确定预测至少列出两个相容替代；
- 信封绑定精确任务与输入。

通过后，工具只复制：

```text
pollution
reconstruction_answers | prediction_answers
```

其余字段来自信封。输出使用 UTF-8 无 BOM、LF、递归排序键、两空格缩进和单一末尾换行。`verify` 会重新装配并比较 JSON 值、规范字节、工具散列、信封散列与原始 payload 散列。

## 7. 首次提交纪律

```text
收到原始首答
→ 原样保存
→ Schema / 跨文件约束检查

失败：保留原文件，执行者链退出
通过：捕获信封并装配
```

不允许把错误信息发回同一执行者后取得“修正版首次提交”。如果结果执行尚未开始，可以由新的空白会话从第一阶段替补；否则按既有失效规则处理。

## 8. 聚焦彩排判据

聚焦彩排不运行夹具、不揭示真值，只检查接口：

1. 重构原始首答直接有效；
2. 重构提交重复装配逐字节相同；
3. 同一空白会话继续给出预测原始首答，且直接有效；
4. 预测信封精确绑定前阶段并保持 actor/session 连续；
5. 两阶段派生提交都直接绑定原始 payload、信封、任务、Schema 与工具；
6. 预测提交重复装配逐字节相同。

任一项失败都永久保留该次聚焦彩排，并在新编号修订。通过只解除“盲测回答接口不可操作”的阻断，不产生理论证据，也不替代正式人工门。
