# 连续行动先行组：正式轮次包契约

- 状态：已冻结；允许制作 `continuous-001` 门前制品，不授权正式派发或执行
- 日期：2026-07-27
- 决策记录：[ADR 0117](../docs/adr/0117-freeze-the-formal-run-package-contract.md)
- 上游规则：[CA-07](continuous-action-pilot-ca-07-artifacts-and-release.md)
- 回答接口：[盲测回答接口修订](continuous-action-pilot-blind-response-interface.md)

## 1. 契约目的

本文只回答一个问题：在请求一次性人工放行前，`continuous-001` 必须长成什么样，哪些内容已经冻结，哪些内容只能在放行后追加。

它不替代 CA-01–CA-07 的理论、选案、变体和判定规则。

## 2. 正式目录

```text
research/calibration-tests/continuous-action-pilot/runs/continuous-001/
├── README.md
├── manifest.json
├── source/
│   ├── source-packet.json
│   ├── canonical-encoding-v0.1.0.json
│   ├── encoding-audit-v0.1.0.json
│   └── projection-audit-v0.1.0.json
├── inputs/
│   ├── source-encoding-packet.json
│   ├── source-audit-packet.json
│   ├── projection-spec.json
│   ├── stage1-view-v01.json
│   ├── stage1-view-v02.json
│   ├── stage1-condition-v01.task.json
│   ├── stage1-condition-v02.task.json
│   ├── stage2-variant-envelope.json
│   ├── stage2-prediction.task.json
│   ├── actor-plan.md
│   ├── reconstruction-response.template.json
│   └── prediction-response.template.json
├── fixtures/
│   ├── fixture-lock.json
│   ├── r1/
│   ├── r2/
│   └── r3/
├── execution/
│   ├── execution-plan.json
│   ├── raw/
│   ├── trace-bundle.json
│   └── execution-result.json
├── submissions/
│   ├── actors/
│   ├── raw/
│   ├── envelopes/
│   ├── invalid/
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

目录只在有真实制品时创建。`submissions/raw/` 与 `submissions/envelopes/` 采用和派生提交相同的提交 ID；无效首答进入 `submissions/invalid/`，不得覆盖或修补。

## 3. 版本矩阵

| 职责 | 正式版本 |
| --- | --- |
| 清单与阶段索引 | `run-manifest 0.1.1` |
| 来源、编码、投影与视图 | `ca-sr-artifact 0.1.0` |
| 正式任务包 | `task-packet 0.1.1` |
| 原始回答与机器信封 | `blind-response-interface 0.1.0` |
| 派生角色提交 | `role-submission 0.1.2` |
| 执行计划、轨迹与结果 | `execution-artifact 0.1.1` |
| 真值与揭示 | `truth-reveal 0.1.0` |
| 审核与最终报告 | `run-report 0.1.0` |

正式任务的 `output_schema` 指向原始回答 Schema，`assembled_output_schema` 指向 `role-submission 0.1.2`。来源编码与来源审核任务不使用盲测回答装配器。

## 4. 门前冻结集合

门前必须冻结：

- README、来源包、通过审核的规范编码与来源审核；
- 投影规范、两个中性视图及其机械生成器；
- 四案的来源身份、兼容补丁、观察补丁、唯一规则变体、输入、夹具锁和比较器；
- 执行计划、容差、不变量、停止边界与负对照；
- 两阶段任务、结构模板和中性变体信封；
- 四席 actor 计划，但不包含真实会话 ID；
- 真值承诺，不包含明文真值、密钥或条件映射；
- 所有被引用 Schema 与工具的路径和精确散列；
- 冻结集合规范前像与根摘要。

以下只能在门后追加：

- 实际 actor 与 `session_id`；
- 原始首答、机器信封、派生提交和无效首答；
- 预测集合摘要；
- 正式原始执行输出、轨迹与结果；
- 明文真值、密钥、条件映射、揭示审核与最终报告。

## 5. 两提交冻结

冻结不尝试让一个提交引用自身：

```text
候选包校验通过
→ 提交 A：冻结锚点
→ 取得 A 的 Git SHA
→ 只更新 manifest
→ 提交 B：清单定稿
→ 人工门
```

提交 A 必须首次包含全部冻结制品的精确字节。提交 B 的 `freeze_commit` 等于 A；提交 B 不能改变任何 `included_in_frozen_set=true` 的文件。

若 B 前发现冻结制品错误，修订仍在 `preparing` 状态进行并重新生成提交 A。若 B 后改变冻结制品，`continuous-001` 失效，修订进入新轮次。

## 6. 执行者身份

`inputs/actor-plan.md` 冻结四个席位的：

- `condition-v01`／`condition-v02` 分配；
- 模型、版本和推理强度；
- 第一阶段与第二阶段必须由同一会话继续；
- 空白上下文、工具禁令、网络禁令和共享工作区禁令。

人工放行后才创建真实会话。保管者随即保存 actor 描述；`capture-envelope` 读取该描述并绑定真实 `session_id`。actor 描述不是门前输入，也不加入冻结根摘要。

## 7. 执行证据链

正式执行的最短结构链为：

```text
execution plan
  ↓
invocation record + raw stdout/stderr/test result
  ↓
trace bundle
  ↓
comparator output
  ↓
execution result
  ↓
truth reveal
  ↓
run report
```

每一箭头都必须由结构化 SHA-256 引用实现。Git 顺序提供时间证据，但不替代文件级引用；报告文字可以解释，不得补造缺失的散列边。

## 8. 门前准备门

人工门前必须全部通过：

1. 所有 JSON 与 Markdown 制品通过其声明 Schema；
2. JSON 使用规范字节格式，路径不越过仓库根；
3. 每项 Schema 与工具散列可复算；
4. 来源定位、编码引用、投影与任务输入闭包完整；
5. rich／atomic 视图由同一编码确定性生成；
6. 两视图、任务和模板无作品身份或答案暗示；
7. 三案未修改基线均可构建，兼容、观察与规则补丁彼此分离；
8. 准备性 smoke 不运行冻结正式输入，也不产生正式精确结果；
9. 真值承诺可在仓库外复算，明文未进入共享工作区；
10. 冻结前像、根摘要、提交 A 与 manifest 的 `freeze_commit` 一致。

来源审核分成两道记录：第一道只裁定规范编码能否忠实表达冻结来源；通过后才生成视图。第二道再裁定投影视图、唯一变量、不变量、身份泄漏和答案暗示。两道都通过，编码与视图才可进入冻结集合。

任何一项失败都留在 `preparing`，不得请求人工正式派发门。

## 9. 当前边界

本契约完成后仍不表示：

- 三个正式案例已经构建成功；
- 规范编码或来源审核已经完成；
- 投影视图、夹具、比较器或密封真值已经产出；
- 正式盲测或正式执行已经获准；
- CA-01 或 CA-SR 0.1 获得证据支持。

下一顺序固定为：来源包 → 来源编码任务 → 独立编码 → 独立审核 → 投影与夹具 → 全包校验 → 两提交冻结 → 一次性人工门。
