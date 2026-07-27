# actor 派发计划开发范围事件（2026-07-28）

状态：已记录、已隔离、已修订并完成独立静态复核；原始五文件不得作为正式派发或“未接触旧轮次”的证据。

## 事件性质

约在 2026-07-28 04:18–04:23（UTC+8），开发任务
`/root/implement_actor_dispatch_plan` 在制作门前 actor 派发计划时执行了三次超出
授权读取边界的文本扫描。其 session ID 与 thread ID 不可得。

```powershell
Get-ChildItem -Recurse -File -LiteralPath 'research/calibration-tests/continuous-action-pilot' | Select-String -Pattern 'requested_model_alias|requested_reasoning_effort|observed_model_build' -Encoding utf8 | Select-Object -First 80 Path,LineNumber,Line
```

```powershell
Get-ChildItem -Recurse -File -LiteralPath 'research/calibration-tests/continuous-action-pilot' | Select-String -Pattern 'condition-rich|condition-atomic|"rich"|"atomic"' -Encoding utf8 | Select-Object -First 60 Path,LineNumber,Line
```

```powershell
Get-ChildItem -Recurse -File -LiteralPath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/inputs' | Select-String -Pattern '"rich"|"atomic"|condition-rich|condition-atomic' -Encoding utf8 | Select-Object -First 30 | ForEach-Object { "$($_.Path):$($_.LineNumber):$($_.Line.Trim())" }
```

前两次扫描可能读取整个 pilot 下的正式材料字节，输出仅为路径或匹配行；第三次明确
扫描 `continuous-001/inputs`。已知涉及正式输入目录的输出只有：

- `generate-continuous-views-v0.1.0.py` 第 120、122 行中的 `rich`、`atomic`；
- `projection-spec.json` 第 63、65 行中的 `rich`、`atomic`。

没有输出正式输入值、sealed truth 或结果值；没有写入正式目录，没有执行正式输入、
runner 或 comparator，也没有启动 Node。尽管如此，本事件仍按“可能读取旧轮次材料”
处理，不能记为未读取。

## 受影响的原始草案

下列散列只标识独立复核前、受污染开发过程产生的原始字节：

| 文件 | 原始 SHA-256 | 原始写入时间（UTC+8） |
| --- | --- | --- |
| `schema/formal-actor-dispatch-plan-0.1.0.schema.json` | `fd93b3a2b85c1f0740f58a9ef2a2dfc1fcfdde5d3f63a7bf080d5822572f844f` | 04:21:46 |
| `tools/formal_actor_dispatch_plan_contract.py` | `3ebe06b9149fda06c72e7f2415e8e5eb51aaf3b083b4eade827eeea9ed56c7ce` | 04:22:46 |
| `tools/materialize-formal-actor-dispatch-plan-v0.1.0.py` | `987af7b7f87d3496d67c782bf0a8bb03911394564699c4220faf70a5dcaf47ae` | 04:19:19 |
| `tools/verify-formal-actor-dispatch-plan-v0.1.0.py` | `46790bddbd691a5993d669360e55ce07f0c2d590b716bf95acf9fafa3cb6a433` | 04:19:31 |
| `tools/self-test-formal-actor-dispatch-plan-v0.1.0.py` | `79ec100df2966e38ede829c9d674df41493678944658373478771051770e5f81` | 04:23:21 |

独立复核判定原始草案不可正式采用：三个 body 参数可读取任意仓库相对文件；
Stage 1 有效性与运行隔离只有政策声明；路径规范化、悬空符号链接和写后回滚存在缺口。

## 隔离与修订

原始草案未物化任何 production output。修订版采取以下措施：

1. 删除三个任意路径 CLI 参数，只允许三条固定的
   `continuous-002/source/dispatch-bodies/**` 来源路径；
2. 在 plan 中记录三份来源的路径、长度与 SHA-256；
3. 拒绝非规范路径和所有符号链接组件；
4. 由固定来源重新生成提示词并逐字节验证，不能用同步修改提示词及其散列绕过来源绑定；
5. 文件一经独占创建就立即纳入回滚集合，检查短写，并把写后自验证置于同一事务边界；
6. 对运行标识赋值进行收敛式转义规范化与整值检查，但仍只把扫描器视为纵深防御；
7. 将实际执行的 core、materializer 与 verifier 路径绑定到调用者声明的同一仓库根，拒绝跨根工具替另一个仓库声明散列；
8. 用 49 项负控覆盖来源伪造、真实短写／部分异常回滚、跨行包装、尾随标识、嵌套转义与跨仓库错绑等攻击；
9. 明示 Stage 1 机械验证在门前不可用，Stage 2 在未来验证器完成认证前保持阻断。

修订版五文件的 SHA-256 为：

- Schema：`208e12288bc7ec32f09d7cbc76bf2b23d40c122ddf3903df9029f5b541d2efa3`
- 共享契约核：`ab0d13ded868a6f7d35302407ab3d6ea5b7889a7be91a35f26c95119bea1ca72`
- materializer：`18861a62eb4d72f35a223e3ac58270922dd084438a2592290498cd17f62aac3f`
- verifier：`31da31213adb5fd718cb66da25669d471bba4d731e643ef4b3d2a41e0a225797`
- self-test：`8a9b56a61f04a9cb40bfaf43a0f456dab7b8c76a1ce58ea56ead3f3ff0f345a6`

隔离自测通过 10 项正控与 49 项负控；它只使用系统临时目录，没有创建实际
Codex task、thread、session 或 dispatch。独立复核确认已知阻断均闭合，且没有
读取正式输入、运行 runner/comparator 或启动 Node。修订版仍只是门前静态计划，
不是运行证明；required-component 依赖闭包和门后验证器未完成前，正式候选包仍
必须失败关闭。
