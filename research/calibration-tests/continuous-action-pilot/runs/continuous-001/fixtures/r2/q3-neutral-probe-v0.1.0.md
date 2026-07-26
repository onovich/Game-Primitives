# Q3 Windows x64 中性兼容探针 v0.1.0

## 状态与边界

这是正式校准运行之前的夹具兼容性证据，不是正式试验结果。

- 构建：PASS
- 零输入 smoke：PASS
- 正式 `25 × 8 ms` usercmd 轨迹：未运行
- 输入变量矩阵：未运行
- 正式坐标或速度：未输出
- 仓库内不保存 `.exe`、`.obj` 或 `.map`

被检验的工作假设是：在固定官方源码、ABI、浮点选项和中性回调的前提下，可以在 Windows x64 上建立一个不会提前进入正式输入空间的 `Pmove` 夹具。

## 冻结来源与工具链

- 官方仓库：`https://github.com/id-Software/Quake-III-Arena.git`
- 提交：`dbe4ddb10315479fc00086f08e25d968b4b43c49`
- 原始运行 UTC：`2026-07-26T20:02:08.4874995Z` 至 `2026-07-26T20:02:12.1395929Z`
- 原始运行中国标准时间：`2026-07-27 04:02:08` 至 `04:02:12`
- 目标：Windows x64
- MSVC 工具集：`14.50.35717`
- C/C++ 编译器：`19.50.35723`
- 固定 C 选项：`/TC /Od /W4 /fp:precise /DWIN32`
- 禁止宏：`Q3_VM`、`MISSIONPACK`

实际参与链接的源码只有：

1. 本目录的冻结中性 harness；
2. 官方 `code/game/bg_pmove.c`；
3. 官方 `code/game/bg_slidemove.c`；
4. 官方 `code/game/q_math.c`。

三个官方 C 编译单元均保持未修改；`q_shared.h`、`bg_public.h` 和 `bg_local.h` 仅作为官方头文件进入编译。

## 原始实际命令

编译：

```text
"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.50.35717\bin\Hostx64\x64\cl.exe" /nologo /Bv /TC /Od /W4 /fp:precise /DWIN32 /ID:\GamePrimitivesToolchains\sources\q3-dbe4ddb1\code\game D:\GamePrimitivesToolchains\probes\q3-neutral\neutral_harness.c D:\GamePrimitivesToolchains\sources\q3-dbe4ddb1\code\game\bg_pmove.c D:\GamePrimitivesToolchains\sources\q3-dbe4ddb1\code\game\bg_slidemove.c D:\GamePrimitivesToolchains\sources\q3-dbe4ddb1\code\game\q_math.c /FeD:\GamePrimitivesToolchains\probes\q3-neutral\build\q3_neutral_probe.exe /link /INCREMENTAL:NO /MAP:D:\GamePrimitivesToolchains\probes\q3-neutral\build\q3_neutral_probe.map
```

零输入 smoke：

```text
D:\GamePrimitivesToolchains\probes\q3-neutral\build\q3_neutral_probe.exe
```

两个命令的退出码均为 `0`。本目录保存的 build/smoke 日志是该次实际原始日志的 UTF-8、LF 规范化文本；只改变行尾，不改日志内容。build 日志中的 `System.Management.Automation.RemoteException` 是原记录器合并 MSVC stderr 时保留的对象类型文字，构建命令本身退出码仍为 `0`。

## SHA-256

### 官方源码

| 文件 | SHA-256 |
| --- | --- |
| `bg_pmove.c` | `3CED04AED8686D3DA051887DC8C4ACE88A24B45A6D0BB4E4D5238CD53CB7A7FC` |
| `bg_slidemove.c` | `327FA83A0C523DA8A7E8B4FBBBBA40CF8870A28613459289EF0E8A865E6BD903` |
| `q_math.c` | `0BCA11954EFA4741C53C5B49492BF671FCBFC70925FD7DCCA09C7AB0D7FF0C29` |
| `q_shared.h` | `7C356992D3F8B722EEB0160C44A0515BD5A83538FFB86190CA138E352E874115` |
| `bg_public.h` | `29679E04BA6F0F730C5CA200410330E057609DA59E563E36D101F329FAFD09E7` |
| `bg_local.h` | `1F8953894410D670367A0BC68A687C4F27958F825E4987B6FCD2F77CA0D40FB1` |

### 夹具、二进制与日志

| 制品 | SHA-256 | 说明 |
| --- | --- | --- |
| 原始通过版及本目录 `q3-neutral-harness-v0.1.0.c` | `28BA4E1F7B256533EA240D44E7FAA8D614BD780EFEEACCA6DACDF9914E05315D` | 两者逐字节一致 |
| 本目录 `run-q3-neutral-probe-v0.1.0.ps1` | `50E307640BC47AB15581D7D6E505DF59EF86A9AFDA87475D0B8F1F5DD458963C` | 参数化 repo-local runner |
| 原始通过二进制 | `0CE5619FA114B4787783E52278AA079245F6700786A19A5EF529192CF5E3D0DD` | 仅存于外部工具链目录 |
| 原始 `build.log` | `B6CB29E069A4773FC6F1E763A46A9D9439315879D73B6FED6226027ADBE8158B` | 原 CRLF 字节 |
| 本目录 `q3-neutral-build-v0.1.0.log` | `98AB379D46C5324CB8761BEBCC7EDB9905E34903991C25F24FC30FCD7A777DE4` | 同内容、规范 LF |
| 原始 `smoke.log` | `213222B399A882D93D8650587FF69A2E5A2AAC1726C9CBCAF97D8DBEF7583DD9` | 原 CRLF 字节 |
| 本目录 `q3-neutral-smoke-v0.1.0.log` | `FE647BED84FDCBBD92F6BAAD36AD89C32236F779AC1A5DA014DC6099CC965518` | 同内容、规范 LF |
| 原始 `probe-run.log` | `CF1E2D9B74278E617AA6FFBEA7CBF090ED8012B795A4D53445D3ACF3A66DC9E5` | 命令与退出码 |

## 已通过项

- x64 指针宽度、基础类型宽度及 `usercmd_t`、`playerState_t`、`pmove_t` 的 ABI/packing 断言；
- `WIN32` 已定义，`Q3_VM` 与 `MISSIONPACK` 未定义；
- 空世界 trace 返回 `fraction=1`、复制 `endpos`、无实体接触；
- `pointcontents` 返回零；
- 事件 stub 保留官方事件环写入与序号递增语义；
- `trap_SnapVector` 固定最近偶数舍入，并覆盖正值、负值及 `.5` 哨兵；
- 一次零输入 `8 ms` `Pmove`，无事件、武器、持有物、碰撞、水体或调试禁止路径；
- 编译器 `/W4` 未产生 warning 记录；
- 源码运行前后均为 clean；
- 原始运行结束后 `q3_neutral_probe`、`cl`、`link`、`c1`、`c2` 残留进程均为零。

smoke 的冻结 marker 为：

```text
FP_ENV_PASS
ABI_PACKING_PASS
SNAPVECTOR_PASS
EVENT_STUB_PASS
EMPTY_WORLD_PASS
NEUTRAL_PMOVE_PASS
SMOKE_PASS
```

## 首次获取失败记录

第一次获取尝试开始于 `2026-07-26T19:54:58.9817555Z`。Windows PowerShell 把 `git fetch` 写入 stderr 的正常进度提升为终止错误，记录器因此在写出 Git 退出码之前中止；这不是提交校验失败或编译失败。修正记录器后，同一官方远端成功获取并校验冻结提交。保留在外部工具链目录的首次失败日志 SHA-256 为：

```text
98A8C55660B1CA539F02F607441C2A728BD7AAE30A2E156B008CF18A607EB83D
```

## Repo-local runner 重放

重放命令：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Articles\Game Primitives\research\calibration-tests\continuous-action-pilot\runs\continuous-001\fixtures\r2\run-q3-neutral-probe-v0.1.0.ps1" -SourcePath "D:\GamePrimitivesToolchains\sources\q3-dbe4ddb1" -OutputPath "D:\GamePrimitivesToolchains\replays\q3-neutral-r2-v0.1.0-replay-20260727-01" -VcVarsPath "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
```

- 重放 UTC：`2026-07-26T20:07:45.6382095Z` 至 `2026-07-26T20:07:47.2132215Z`
- runner 退出码：`0`
- build：PASS
- smoke：PASS
- evidence SHA 复算：PASS
- marker：与冻结集合完全一致
- 源码前后状态：clean
- 编译器 warning：零
- 残留 `q3-neutral-probe-v0.1.0`、`cl`、`link`、`c1`、`c2` 进程：零
- 重放二进制 SHA-256：`854AEA69EB28338747C19261D465E01FF8517176C9FCB79AF5B95AEDBC9CAD83`
- 重放 build 日志 SHA-256：`3F2720293EFBD5DCD4A2FD6C2CE3D430FD9975B39E115386F3D22E13C6879F8A`
- 重放 smoke 日志 SHA-256：`FE647BED84FDCBBD92F6BAAD36AD89C32236F779AC1A5DA014DC6099CC965518`
- 重放命令日志 SHA-256：`255C4F9CA7BA011258DF25CFE6EE1A34C15705CD18BC552A749C4BE1374A9CC2`

runner 会硬拒绝错误提交、非官方远端、dirty source、官方文件或 harness SHA 不匹配、非 x64/非固定工具链、已有输出目录、仓库内输出目录以及任何不匹配的 smoke marker。它不接受运动输入，也不会调用正式轨迹。

另以仓库内 `OutputPath` 做了负向守卫检查：runner 退出码为 `1`，命中“输出必须位于仓库外”拒绝条件，且没有创建目标路径。

## 兼容性警告与停止条件

官方 Windows `Sys_SnapVector` 使用 x87 `fistp`；本夹具在 MSVC x64 上使用 SSE 转换并固定最近偶数舍入。正负值与 `.5` 哨兵已经通过，但这不是全部浮点输入上的形式证明，也不能证明历史 x86 与当前 x64 的逐坐标位级相同。

因此：

- 此结果只证明中性 x64 夹具可构建、可复算；
- 不得据此宣称零容差的 x87/x64 等价；
- 若正式阶段需要历史 x86 位级坐标，必须先建立独立等价证据，否则停止；
- 若触发持有物、攻击、换枪、事件、碰撞、水体或多线程路径，当前最小 stub 即失效，必须停止并重新审计。
