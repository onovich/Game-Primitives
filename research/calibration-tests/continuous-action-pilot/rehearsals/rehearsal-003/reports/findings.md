# rehearsal-003 结论

本轮在任何盲测派发前停止，是一次准备阶段失败，不产生理论证据。

## 已修复并验证

- 冻结集合的规范 TSV 前像被保存为不参与自身根摘要的审核制品。
- 只读校验器同时复算单项文件、Schema、前像字节和根摘要。
- 9 项冻结集合的根摘要 `df684dec1bd2c896a63744cc129d99ba24ee467725f28b133c29815136d2b35f` 与规范前像文件完全一致。

## 阻止派发的问题

机械复制任务包后，虽然更新了 `run_id` 和路径，却没有更新包内的目标文件散列：

| 任务包 | 声明散列 | 实际散列 |
| --- | --- | --- |
| `reconstruction-condition-v01.task.json` | `020e6458…` | `293f7560…` |
| `reconstruction-condition-v02.task.json` | `d38db6f…` | `d9e09f15…` |
| `prediction-neutral.task.json` | `edee576a…` | `e871c4ae…` |

JSON Schema 能检查散列格式，却不能独自证明跨文件引用指向正确字节。由于任务包已经进入冻结提交，本轮不能回写修正。

## 后续修正

1. 保留 `rehearsal-003` 不变，不派发执行者；
2. 扩展只读准备校验，使其检查任务包 `input_artifacts`、`target_view_sha256` 和实际文件的引用闭包；
3. 在新编号 `rehearsal-004` 中先通过引用闭包，再冻结、派发并重跑完整链。
