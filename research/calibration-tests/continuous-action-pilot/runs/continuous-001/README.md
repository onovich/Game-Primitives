# 连续行动正式轮次 continuous-001

- 状态：`preparing`
- 日期：2026-07-27
- 正式包契约：[连续行动先行组：正式轮次包契约](../../../../continuous-action-pilot-formal-package-contract.md)
- 人工门：尚未召开
- 正式盲测：未派发
- 冻结正式输入：未执行
- 真值：未揭示

## 当前进度

本目录是连续行动组第一个正式轮次包。当前只制作人工门之前允许的来源、编码、投影、夹具、比较器、任务、承诺和验证制品。

来源规范编码及第一道独立来源审核已经通过。两份候选中性视图已从同一规范编码机械生成，并只以 `condition-v01`、`condition-v02` 暴露条件身份。第一轮第二道独立审核正确发现输出 Schema 的离线依赖未闭合，结论为 `revision_required`；该失败尝试已保存。修订后，第二轮审核在隔离工作区完成了 61 项输入、20 份绑定 Schema、437 条 `$ref`、机械投影、派发面和构建链的独立复核，11 项检查全部通过，结论为 `approved`。

密封真值与 32 字节随机数现保存在仓库外；`manifest.json` 只保存 `SHA-256(secret_nonce_bytes || exact_truth_bundle_bytes)` 承诺。明文真值、条件映射和随机数均未进入 Git，正式结果也仍不存在。冻结集合尚未完成两次提交锚定，因此人工门仍未召开。

三个来源身份已于 2026-07-27 直接通过官方 Git 远端复核：

| 案例 | 官方引用 | 冻结提交 |
| --- | --- | --- |
| `CA-R1` | `hifight/Footsies` 标签 `1.5.0` | `7eaaad799bb7912625c15af9407c2c67e6305d75` |
| `CA-R2` | `id-Software/Quake-III-Arena` 的官方 GPL 仓库 HEAD | `dbe4ddb10315479fc00086f08e25d968b4b43c49` |
| `CA-R3` | `ppy/osu` 标签 `2026.726.0-lazer` | `5da71008b082d1a77e4bb301dc98886f1f24b895` |

上述身份复核只证明引用指向指定提交，不证明工程已经在正式工具链上构建，也不证明任何项目变体能够运行。

人工门前的中性构建与边界证据另行保存：`CA-R1` 已由不依赖 Unity 编辑器许可的独立封装完成基线/变体只构建验证，并通过“无执行许可即拒绝”的守卫探针；`CA-R2` 的 Windows x64 基线/变体构建准备已经通过；`CA-R3` 的隔离恢复、两次确定性构建和测试发现已经通过。三者都没有运行正式输入，也没有产生正式结果。

`execution/execution-plan.json` 当前是 `execution-artifact 0.1.1` 的最终门前执行计划，绑定 `CA-R1`、`CA-R2`、`CA-R3` 及负控 `NEG-01` 的精确 runner、比较器、正式输入字节散列、原始轨迹 Schema、构建证据、停止边界与输出根。它记录全部正式执行状态为 `false`，并固定“一次人工门 → 四席预测冻结 → 机械生成并校验执行许可 → 正式执行”的后续顺序。它不嵌入正式输入内容，也不授权盲测或执行。

## 第二道投影审核任务

`inputs/projection-audit.task.json` 已在最终构建准备记录、夹具锁和最终执行计划之后重新生成，当前精确绑定 61 个输入制品。第一轮独立审核结果保存在 `source/projection-audit-attempt-01-revision-required-v0.1.0.json` 和对应 Git 历史中；它不是通过的审核记录，也不属于当前正式清单。该轮发现 `role-submission 0.1.2` 的基础 Schema 未被任务绑定。修订后的任务显式绑定 `role-submission 0.1.1`、`task-packet 0.1.0` 与 `variant-envelope 0.1.0`，并机械拒绝任何不完整的传递 Schema 依赖闭包。

第二轮隔离审核产物为 `source/projection-audit-v0.1.0.json`。它精确镜像任务的 61 项输入并额外绑定任务自身，共 62 项；审计结论为 `approved`，11 项要求全部为 `passed`。事件记录仍如实保留 `formal_input_byte_read=true`：该事件只涉及一次 R3 正式输入的字节完整性散列，没有语义解释、执行或结果暴露，但仍须在之后的人工门中显式接受，不能被轮次级布尔值抹除。

门前工具 `tools/materialize-projection-audit-task.py` 把上述顺序做成失败即关闭的机械约束：

```text
python research/calibration-tests/continuous-action-pilot/tools/materialize-projection-audit-task.py self-test --repo-root .

python research/calibration-tests/continuous-action-pilot/tools/materialize-projection-audit-task.py materialize \
  --repo-root . \
  --run-dir research/calibration-tests/continuous-action-pilot/runs/continuous-001 \
  --created-at <UTC-秒级时间>

python research/calibration-tests/continuous-action-pilot/tools/materialize-projection-audit-task.py verify \
  --repo-root . \
  --run-dir research/calibration-tests/continuous-action-pilot/runs/continuous-001
```

`materialize` 只有在 readiness 校验器要求的全部输入、输出 Schema 及其全部本地传递依赖都存在且显式绑定时才写入任务；任一前置缺失、路径越界、输入集合漂移、散列不闭合或 Schema 依赖漏绑都会拒绝生成。它只散列声明性制品，不调用夹具、构建器、正式 runner、轨迹校验器、比较器或正式输入。任务生成并通过 `verify` 后，才可派发给与来源编码者及第一道审核者隔离的独立审核者；正式审核的 actor 角色必须是 `source_auditor`，其 `identifier` 与 `session_id` 都不得复用第一道审核记录。工具和任务都不构成审核结论、授权或正式执行许可。

## 追加纪律

- `manifest.json` 在门前冻结前保持 `preparing`；
- 来源编码与两道来源审核均通过后，才把正式匿名视图纳入冻结集合并允许派发；
- 真实 actor、原始回答、机器信封和派生提交只能在人工放行后追加；
- 一次人工授权只允许盲测派发，并预先同意“四份预测全部冻结后才可正式执行”；它不包含尚未产生的预测摘要；
- 四份预测全部冻结后，须先机械生成并校验绑定人工授权、预测集合摘要与三案精确执行目标的 `formal-execution-permit.json`；正式轨迹和比较器输出都必须记录同一个许可散列、正式输入散列与预测摘要，比较器在语义判定前还须通过通用严格轨迹校验；
- 失败制品保留，修订新增版本，不覆盖旧文件。

## 当前不构成的证据

本目录当前不支持 CA-01、CA-SR 0.1 或任何新**原语**。来源包、任务包和构建探针都是方法准备制品。
