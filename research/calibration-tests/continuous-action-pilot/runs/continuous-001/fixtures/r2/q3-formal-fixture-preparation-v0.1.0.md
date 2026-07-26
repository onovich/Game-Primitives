# CA-R2 正式夹具门前准备 v0.1.0

## 状态

- 正式来源：id Software 官方 GPL 仓库提交 `dbe4ddb10315479fc00086f08e25d968b4b43c49`
- 平台范围：MSVC 19.50 x64，`/fp:precise`
- 构建：通过
- 基线非正式自检：通过
- 变体非正式自检：通过
- 虚构比较器自检：通过
- 两份夹具的无许可环境拒绝测试：通过
- 正式 `25 × 8 ms` 输入执行：否
- 正式轨迹或结果生成：否

本记录只证明门前夹具能够从冻结来源重建，拒绝门有效，并且比较器能拒绝虚构的结构错误。它不是正式实验结果，也不包含正式问题的答案。

正式 runner 与比较器已改为先统一验证 `formal_execution_permit` 及其中冻结的 `execution_target`。本轮门前重建编译了能够在轨迹中携带执行许可、正式输入与预测集三份摘要的测试体，运行了两配置的非正式自检与无许可环境拒绝路径，并运行了只使用合成数据的比较器自检。正式执行时，runner 会在每份 R2 JSONL 产出后先调用共享的严格 raw-trace verifier，比较器也会在读取四份轨迹前逐份重新验证。门前重建没有创建或使用正式执行许可，没有启动正式 runner，也没有执行正式输入；许可与 raw-trace 验证器的正负例由隔离的合成流水线另行验证。

## 可复现命令

以下命令只进行来源核验、补丁应用、编译、自检和拒绝路径测试；构建器没有传递正式授权环境或 `--formal` 参数的代码路径。

```powershell
& "D:\Articles\Game Primitives\research\calibration-tests\continuous-action-pilot\runs\continuous-001\fixtures\r2\build-q3-formal-fixture-v0.1.0.ps1" `
  -SourcePath "D:\GamePrimitivesToolchains\sources\q3-dbe4ddb1" `
  -InputPath "D:\Articles\Game Primitives\research\calibration-tests\continuous-action-pilot\runs\continuous-001\fixtures\r2\r2-formal-input-v0.1.0.json" `
  -OutputPath "D:\GamePrimitivesToolchains\replays\q3-r2-binding-selftest-20260727-02" `
  -VcVarsPath "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
```

最终外部、可丢弃的构建目录：

```text
D:\GamePrimitivesToolchains\replays\q3-r2-binding-selftest-20260727-02
```

构建证据：

| 项 | 值 |
| --- | --- |
| 完成时间 | `2026-07-26T22:59:22.4137436Z` |
| `build-evidence.json` SHA-256 | `6ce9fdb607286cef8786fa1e5e237716ef57dc9bb8b321fcb5c9e080eea711f4` |
| 正式输入已执行 | `false` |
| 正式结果已创建 | `false` |
| 编译日志 warning/error 命中 | `0` |
| 外部输出中的 `.jsonl` | `0` |

源码树在构建前后均为 clean。仓库内没有保存 `.exe`、`.obj`、`.map` 或正式轨迹。

## 来源与工具链身份

来源文件在构建前逐一核验：

| 来源文件 | SHA-256 |
| --- | --- |
| `code/game/bg_pmove.c` | `3ced04aed8686d3da051887dc8c4ace88a24b45a6d0bb4e4d5238cd53cb7a7fc` |
| `code/game/bg_slidemove.c` | `327fa83a0c523da8a7e8b4fbbbba40cf8870a28613459289ef0e8a865e6bd903` |
| `code/game/q_math.c` | `0bca11954efa4741c53c5b49492bf671fcbfc70925fd7dcca09c7ab0d7ff0c29` |
| `code/game/q_shared.h` | `7c356992d3f8b722eeb0160c44a0515bd5a83538ffb86190ca138e352e874115` |
| `code/game/bg_public.h` | `29679e04ba6f0f730c5ca200410330e057609da59e563e36d101f329fafd09e7` |
| `code/game/bg_local.h` | `1f8953894410d670367a0bc68a687c4f27958f825e4987b6fcd2f77ca0d40fb1` |

工具链：

| 项 | 值 |
| --- | --- |
| 编译器 | `C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.50.35717\bin\Hostx64\x64\cl.exe` |
| 编译器 SHA-256 | `a560c2e6d5c3c30bf563ba5285576e9423f18d44165e1398539d912866a4daab` |
| 文件版本 | `19.50.35723.0` |
| 工具集 | `14.50.35717` |
| 关键选项 | `/TC /Od /W4 /fp:precise /DWIN32` |

## 三类补丁

| 角色 | 制品 | SHA-256 | 作用边界 |
| --- | --- | --- | --- |
| 兼容 | `q3-msvc-x64-compatibility-v0.1.0.patch` | `f435cf87bd2b222da5da09b02306c00a61a3b96a958d049e1638ae7b75e82b79` | 只选择项目自建的 MSVC x64 空世界、ABI 与最近偶数舍入兼容层 |
| 观察 | `q3-observation-v0.1.0.patch` | `c24e2ca8d6ad3893002060e6829a521b6f5f2dcb48933a19d663325b42cdf5bb` | 只增加分支与空中期望方向的只读回调 |
| 变体 | `q3-entry-latch-variant-v0.1.0.patch` | `1a276587cd763eeb593cb4af78f11acc3bd21bcb191a85ae014f4729ff5b23f2` | 只把活动输入策略常量从逐步重采样改为入口锁存 |

构建器机械确认基线与变体 harness 只有一行源码差异。两种策略都先完整复制 `usercmd_t`；入口锁存仅替换 `forwardmove` 和 `rightmove`，逐步保留 `serverTime`、三个角度、`buttons`、`weapon` 与 `upmove`。

## 仓库内夹具散列

| 制品 | SHA-256 |
| --- | --- |
| `r2-formal-input-v0.1.0.json` | `5ce6cb8eb8b9ef9669059b1e504154c643f644abce7988b1896e45c56b600b7e` |
| `q3-formal-fixture-v0.1.0.h` | `2ada739f42ccb24758d7aca22908ba74583a976f1ac180662929d131c24c5acd` |
| `q3-formal-compatibility-v0.1.0.c` | `c1211b6eca0dd9807ba8c5d633ff454dc7882d9a2d74d720b3ed2ee662d1b485` |
| `q3-formal-harness-v0.1.0.c` | `cffcbcfd63e5b99a4d73047756d318abeb2743c6f1f5b156e5b708e2096d7bbb` |
| `q3-msvc-x64-compatibility-v0.1.0.patch` | `f435cf87bd2b222da5da09b02306c00a61a3b96a958d049e1638ae7b75e82b79` |
| `q3-observation-v0.1.0.patch` | `c24e2ca8d6ad3893002060e6829a521b6f5f2dcb48933a19d663325b42cdf5bb` |
| `q3-entry-latch-variant-v0.1.0.patch` | `1a276587cd763eeb593cb4af78f11acc3bd21bcb191a85ae014f4729ff5b23f2` |
| `compare-q3-formal-traces-v0.1.0.ps1` | `655e1ed263eee4cbedf668b7a0dfec9bc8e58caafb3416e0f62749114d2386c9` |
| `build-q3-formal-fixture-v0.1.0.ps1` | `f8fae44f5c75deac2818558a82940f5127bc6252cea6c2eaa2bc065fb967e431` |
| `run-q3-formal-guarded-v0.1.0.ps1` | `1eb7eea4675cb00cf9fb2d0d0a66c634814f716ee8ac30dea3e2ab0bb3284332` |

正式输入通过 `formal-input-trace 0.1.0` Schema，绑定中性输入 `o.b.0002`、时间基准 `o.b.0015` 与停止边界 `o.b.0030`，并明确记录 `authorization_state=withheld`、`formal_input_executed=false`、`formal_result_created=false`。

## 外部构建产品

外部产品是可重建的校验输出，不作为仓库内 fixture-lock 的直接制品引用：

| 产品 | SHA-256 |
| --- | --- |
| 生成输入头 | `ab3985f5ffcd6d5817164be47b9f0fe5f131ed16ca4810b143a01e2d226bdb6b` |
| 兼容模式头 | `9be501604109b8f4aceaaa8cc583f98e583965fa0e02bfb6c95b25b87060855b` |
| 已观察化 `bg_pmove.c` | `62b87db49b72d9823fb51b5f247d354c65940abd885d65eec1a5876175a897ce` |
| 基线可执行文件 | `be6fde5e8d58d396c35db3eb51890627ba2dc93bb501d89cb3dd6882a78f0650` |
| 变体可执行文件 | `794d17aac9ee9b87e13c3c426f28ede366c4e408d2d79f4752d98dd876d49529` |

汇总 fixture-lock 应只冻结仓库内来源、补丁、fixture 源码、runner、比较器、正式输入与本准备记录的路径和散列。正式阶段必须从这些冻结制品重建到一个新的外部目录，并再次核验新构建证据，不能把本次临时绝对路径伪装成仓库内冻结制品。

## 进程与失败保留

外层 PowerShell 调用由 Codex shell 同步等待退出，未把其 PID 固化为证据字段。构建器直接启动并等待退出的 15 个进程如下：

| 标签 | PID | 退出码 |
| --- | ---: | ---: |
| `git-origin` | `40320` | `0` |
| `git-head` | `73336` | `0` |
| `git-status` | `60132` | `0` |
| `git-apply-compatibility` | `73652` | `0` |
| `git-apply-observation` | `59848` | `0` |
| `git-apply-variant` | `73840` | `0` |
| `vcvars64` | `66160` | `0` |
| `baseline-compile` | `30524` | `0` |
| `baseline-self-test` | `66264` | `0` |
| `baseline-formal-refusal` | `14916` | `64` |
| `variant-compile` | `74424` | `0` |
| `variant-self-test` | `38324` | `0` |
| `variant-formal-refusal` | `73488` | `64` |
| `comparator-self-test` | `58404` | `0` |
| `git-status-after` | `72076` | `0` |

本轮没有启动正式 runner；两份新构建夹具都在没有执行许可环境且不带参数时以退出码 `64` 拒绝。最终通过 `Get-Process -Id` 复核上述 15 个已记录 PID，均已退出。

首次准备构建保留于外部目录 `q3-r2-formal-prep-v0.1.0-01`。旧版进程等待器在编译器已经返回后仍等待进程树，故人工终止仅由本项目启动的 PID `72968`；该次没有正式轨迹。`-02` 发现快速退出进程的退出码捕获缺口；`-03` 修正为直接进程句柄后首次完整通过。`-04`、`-05`、`-06` 依次补齐独立兼容补丁、证据引用和门前记录；`-07` 绑定中性停止边界与容差语义；`-08` 在观察矩阵与正式输入 ID 收口后重建；`-09` 在统一执行许可与预测摘要绑定完成后重建。随后，`q3-r2-binding-selftest-20260727-01` 验证 `execution_target` 与严格 raw-trace verifier 的首版接线；当前的 `q3-r2-binding-selftest-20260727-02` 又在比较器把“已严格验证的原始字节”绑定到自身实际读取字节后重建，并得到本节记录的当前散列。所有批次均未运行正式输入。

## 拒绝门

正式 runner 同时要求：

- 绝对路径指定的 `ExecutionPermitPath`；
- 共享验证器对 `formal_execution_permit`、冻结根、人工门、预测集和 CA-R2 `execution_target` 的一致性验证；
- `execution_target` 对正式 runner、正式输入、测试体、比较器、raw-trace Schema 与全部支持制品的固定路径和 SHA-256 绑定；
- 验证器返回的小写、非零执行许可摘要与预测集摘要，以及 `execution_target` 中冻结的正式输入摘要；
- SHA-256 完整的门前构建证据；
- 新且不存在的输出目录。

runner 必须先调用 `verify-formal-execution-permit.py verify --case-id CA-R2`，再把门前构建证据中的仓库制品逐项与 `execution_target` 交叉核对；任一验证失败时，不得执行正式输入，也不得创建正式轨迹或结果目录。正式输入摘要在构建时写入夹具，执行许可摘要与预测集摘要由 runner 注入；夹具因此在每份原始轨迹中同时记录三份摘要，无许可环境时以退出码 `64` 拒绝。

每份 R2 JSONL 产出后，runner 必须先调用 `verify-formal-raw-trace.py verify --case-id CA-R2`，严格验证恰好一个 header、25 个有序 step 和一个 stop，并核对 `execution_target`、配置及三份摘要，之后才允许进入比较。比较器会独立重验同一许可、自身和全部目标制品，再对四份轨迹逐份调用同一严格验证器；它只解析与验证器返回的 raw SHA-256 完全一致的那批字节，最终结果也显式记录 `formal_input_sha256`。

这些是程序性防误执行措施，不是安全沙箱。正式执行仍必须等待一次性人工门、预测冻结和据此生成的执行许可。

## 比较语义与证据边界

比较器直接使用中性信封的两条规则：

- `tol.b.0001`：离散标识、计数和有序串精确相等；
- `tol.b.0002`：停止边界第二水平轴的值映射为 `-1`、`0`、`1` 方向类别；`+0` 与 `-0` 等价，不使用 epsilon，任一非零值都映射为绝对整数值 `1` 的非零类别。

硬判据检查停止边界的第二水平轴速度和位置：逐步重采样配置必须为非零类别，入口锁存配置必须为零类别。它不把跨平台末位差异误写成规则差异。

本夹具只覆盖固定 MSVC x64 环境。`trap_SnapVector` 使用 SSE 最近偶数舍入，哨兵自检已通过，但这不证明历史 x87 与当前 x64 在全部浮点输入上逐位等价。若结论改为要求历史 x86 坐标零容差，必须停止并另建等价证据。本夹具也不声称任何玩家体验、技巧或零售可执行文件行为。
