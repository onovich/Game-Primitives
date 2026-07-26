# CA-R3 osu 中性构建探针 v0.1.0

- 状态：通过
- 证据性质：人工门前的构建可行性证据，不是正式输入、正式控制或正式结果
- 首次运行窗口：2026-07-27 03:56:35–04:00:03（Asia/Shanghai）
- 冻结来源：`https://github.com/ppy/osu.git`
- 冻结提交：`5da71008b082d1a77e4bb301dc98886f1f24b895`

## 边界

本探针只恢复和构建冻结提交中已有的 `osu.Game.Tests`，然后使用
`dotnet test --list-tests --no-build --no-restore` 做测试发现。它不执行测试体，也没有：

- 创建或运行 0/75 ms 正式输入；
- 创建或运行 HitAnimations 正式对照；
- 采集或记录正式 RawTime；
- 运行 `TestCircleHitCentre` 哨兵；
- 调用 Node、WMI 或 CIM；
- 修改 `PATH`、`global.json` 或冻结源码；
- 把 NuGet 包、`bin` 或 `obj` 写入本仓库。

`run-osu-neutral-probe-v0.1.0.ps1` 还会硬拒绝非官方 HTTPS remote、非冻结提交、dirty
工作树、与冻结 SHA-256 不同的 `dotnet.exe`、非 8.0.100 SDK、非空或与仓库/源码重叠的缓存目录、
缓存路径中的 reparse point、源码中的 `bin/obj`、意外出现的 `packages.lock.json`、缺失的
0 warning / 0 error 摘要、非 5407 的发现计数，以及未退出的便携 `dotnet.exe` 进程。

## SDK 与隔离

| 项目 | 身份 |
| --- | --- |
| SDK | .NET SDK `8.0.100`，commit `57efcf1350` |
| workload manifest | `8.0.100-manifests.6c33ef20` |
| host | `8.0.0`，commit `5535e31a71` |
| SDK 压缩包 SHA-512 | `69ee73c56c78c94c186c0fd1b06ce1a7325979f7680857dc1a05d516feb9f0ffe990c2c0441caed1de98a0d0ae3923cc3e04525f91d96306d611e481a24f9fb4` |
| `dotnet.exe` SHA-256 | `b9eace03c8471717e3f98873527005dbd9a92367b954f8c48484d2b7b78efbac` |
| `global.json` SHA-256 | `e4967d6bdcf576fad6f8fbc5e0790ba9912cd1a6371e7d359d5bcfab7b648016` |
| `global.json` Git blob | `789bff3bd0c281c81b2f6e99aa0d2bc4379f830a` |

首次运行使用以下隔离目录：

```text
SourcePath       D:\GamePrimitivesToolchains\sources\osu-5da71008
DotnetPath       D:\GamePrimitivesToolchains\dotnet-8.0.100\dotnet.exe
CacheRoot        D:\GamePrimitivesToolchains\cache\osu-neutral
DOTNET_CLI_HOME  D:\GamePrimitivesToolchains\cache\osu-neutral\dotnet-home
NUGET_PACKAGES   D:\GamePrimitivesToolchains\cache\osu-neutral\nuget-packages
TEMP / TMP       D:\GamePrimitivesToolchains\cache\osu-neutral\temp
artifacts        D:\GamePrimitivesToolchains\cache\osu-neutral\artifacts
```

## 实际命令与结果

工作目录均为 `D:\GamePrimitivesToolchains\sources\osu-5da71008`。

```powershell
D:\GamePrimitivesToolchains\dotnet-8.0.100\dotnet.exe restore osu.Game.Tests\osu.Game.Tests.csproj --packages D:\GamePrimitivesToolchains\cache\osu-neutral\nuget-packages -p:UseArtifactsOutput=true -p:ArtifactsPath=D:\GamePrimitivesToolchains\cache\osu-neutral\artifacts -v:minimal

D:\GamePrimitivesToolchains\dotnet-8.0.100\dotnet.exe build osu.Game.Tests\osu.Game.Tests.csproj --no-restore --configuration Debug --artifacts-path D:\GamePrimitivesToolchains\cache\osu-neutral\artifacts --verbosity minimal

D:\GamePrimitivesToolchains\dotnet-8.0.100\dotnet.exe test osu.Game.Tests\osu.Game.Tests.csproj --no-build --no-restore --configuration Debug --artifacts-path D:\GamePrimitivesToolchains\cache\osu-neutral\artifacts --list-tests --logger "console;verbosity=minimal"
```

| 步骤 | 退出码 | 必要结果 |
| --- | ---: | --- |
| restore | 0 | 六个项目恢复到外部缓存；未观察到 warning 或 error |
| build | 0 | 六个项目构建；`0 Warning(s)`、`0 Error(s)` |
| list-tests | 0 | 列出 5407 项；测试体执行数为 0 |
| build-server shutdown | 0 | 便携 `dotnet.exe` 残留进程数为 0 |

冻结源码在结束时仍位于同一提交，`git status --porcelain=v1 --untracked-files=all` 为空，源码树内
没有生成 `bin` 或 `obj`。仓库只跟踪 `global.json` 这一项锁定类文件；
`packages.lock.json` 缺失。因此，下面的 `project.assets.json` 是这次恢复所得的路径绑定解析身份。

## 六份恢复资产身份

| 外部 `artifacts` 相对路径 | 字节 | SHA-256 |
| --- | ---: | --- |
| `obj\osu.Game.Rulesets.Catch\project.assets.json` | 475775 | `dba85be37cf06b6b876bf022d0a7bfe5717a6e3db344e1ee711eea244413dd5d` |
| `obj\osu.Game.Rulesets.Mania\project.assets.json` | 475775 | `a6dcfd0b242ebab25073c07fdf6b2e1cf68faece1b1c9130d9031b0fc0a84ebd` |
| `obj\osu.Game.Rulesets.Osu\project.assets.json` | 475763 | `ba981e8347522a44a4c1a15fc25d0393130140f55f8ee54906da64f4814cffac` |
| `obj\osu.Game.Rulesets.Taiko\project.assets.json` | 475775 | `2fc8e9b1f5bf62c98ef2f46f9c975e21ce7193b03ad5e367e52805a349f23787` |
| `obj\osu.Game.Tests\project.assets.json` | 565823 | `b5781971a65b2cbd4c178668ff62867d6cd80cecbe24f0f88304ff0b289f4906` |
| `obj\osu.Game\project.assets.json` | 478809 | `da6b7b77c2399b5361ce57d80b52e30e473c8ccebe2d2cb1d49a1c190fdafffc` |

这些文件嵌入绝对 `packagesPath` 和 `outputPath`；换用新的 `CacheRoot` 重放时，完整文件哈希会改变。
上表只绑定首次实际运行，不把路径差异误判为依赖差异。

## 包内日志身份

三份日志都是从首次实际原始日志提炼的 UTF-8（无 BOM）、LF 规范文本。

| 日志 | SHA-256 |
| --- | --- |
| `osu-neutral-restore-v0.1.0.log` | `0078226d16a9fc2a54ebc20f45761b5aa9b8442d616a369fc637499c8df1f78d` |
| `osu-neutral-build-v0.1.0.log` | `9a2dd9dd7f5bccf62cff2f28da4a324cc1e63141f11a51376af377f91c29334b` |
| `osu-neutral-list-tests-v0.1.0.log` | `3a01bfaceb19c4d5aaeeb7f9db15f58670cf5a4b3e8af93362128358ac979577` |

每份规范日志同时保留对应原始 command、exit、stdout 和 stderr 文件的 SHA-256，避免把提炼文本误作
未经处理的原始输出。

## repo-local runner 重放

添加 runner 后，又在全新的外部目录
`D:\GamePrimitivesToolchains\cache\osu-neutral-r3-replay-v0.1.0-r3` 重放一次：

```powershell
.\run-osu-neutral-probe-v0.1.0.ps1 `
  -SourcePath D:\GamePrimitivesToolchains\sources\osu-5da71008 `
  -DotnetPath D:\GamePrimitivesToolchains\dotnet-8.0.100\dotnet.exe `
  -CacheRoot D:\GamePrimitivesToolchains\cache\osu-neutral-r3-replay-v0.1.0-r3
```

- 重放窗口：2026-07-27 04:17:52–04:18:36（Asia/Shanghai）
- restore、build、list-tests、build-server shutdown 均退出 0；
- build 再次明确报告 0 warnings / 0 errors；
- runner 元数据与实际缩进测试名行均为 5407；
- 六份 `project.assets.json` 均生成在外部缓存；
- 测试体执行数为 0，Node/WMI/CIM 调用数为 0；
- 冻结源码仍干净且无源码内 `bin/obj`；
- 结束后便携 `dotnet.exe` 进程数为 0。

重放 `probe-runner.log` 的 SHA-256 为
`b30891f3ecc9a074417f17c90291c7666944cbb2bc8c350302c94fd3a4401ca3`；
完整测试发现日志 SHA-256 为
`1080c48fab963ec6d4eb4687d38e034a8fc50015ff4e8193cadeaa1b57484dd7`。
