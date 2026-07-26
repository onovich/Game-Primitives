# CA-R1 中性构建探针 v0.1.0

- 状态：`blocked_license_activation`
- 运行时间：2026-07-27
- 正式输入：未执行
- 正式结果：未产生

## 冻结身份

- 官方仓库：`https://github.com/hifight/Footsies.git`
- 提交：`7eaaad799bb7912625c15af9407c2c67e6305d75`
- 工作树：探针前后均 clean
- `ProjectSettings/ProjectVersion.txt`：`m_EditorVersion: 2018.1.1f1`
- 该文件 SHA-256：`88145313e98e6d845cbc728e7e6d9feaae5fd47d083aaeb1846e86dc5f44e955`
- `Packages/manifest.json` SHA-256：`714e111b01efb49e32eb290878a8e89eb214cc6c3b6d003e6757b3dd3d54e8ae`

## 工具链取得与核验

- 官方安装包：
  `https://download.unity3d.com/download_unity/b8cbb5de9840/Windows64EditorInstaller/UnitySetup64-2018.1.1f1.exe`
- 字节数：`595189032`
- 安装包 SHA-256：`9da5ca964575a48c6f4c026f581a08a12f345f8af75066b1e908e8f1e6579fa3`
- Authenticode：`Valid`
- 签名者：`Unity Technologies SF`
- 安装位置：`D:\GamePrimitivesToolchains\unity\2018.1.1f1`
- `Editor/Unity.exe` 文件版本：`2018.1.1.12110773`
- `Editor/Unity.exe` SHA-256：`3972bacc7abfe37dadf4d09cf6ce095efa558649547d32adba81addbf101ffe0`

安装器 PID `66508` 自然退出。安装后没有遗留该安装器进程。

## 中性导入命令

```text
Unity.exe
  -batchmode
  -nographics
  -quit
  -projectPath <frozen-clean-worktree>
  -logFile <neutral-import-log>
```

该命令只尝试导入并编译未修改工程，不增加测试脚本，不打开场景，不执行输入，不运行基线或变体。

## 结果

编辑器在读取工程前报告：

```text
BatchMode: Unity has not been activated with a valid License.
DisplayProgressbar: Unity license
```

规范化归档日志：
`fixtures/r1/footsies-neutral-import-v0.1.0.log`

归档日志使用 LF 与单一末尾换行，SHA-256：
`fb9cee283cbb593c2cbd8852aa048226867da5ac8c92ce4ee18b54d1ee4fbf1b`

外部探针保存的原始 CRLF 日志 SHA-256：
`c01875af555bb9da79dabca990a14befe938fae12c385f7bac267f8d53a24a63`

中性导入 PID `26632` 在确认许可阻断后按精确可执行路径终止。两次按 Unity 2018.1 官方参数创建手动激活文件的尝试也没有产生 `.alf`，第二次在 30 秒边界终止；相关 PID `66596`、`75176` 均已结束。没有终止其他 Unity 会话，探针安装路径下没有遗留本次子进程。

## 当前结论

精确版本的编辑器已可取得、签名有效并可隔离安装；`CA-R1` 仍未满足“未修改基线可构建”，唯一已观察到的当前阻断是 Unity 2018.1.1f1 许可激活。不得用 Unity 6000 打开或迁移工程，也不得把本记录解释为源码编译通过。

下一次重试必须先提供合法的 Unity 2018.1.1f1 许可，再使用本目录的 `run-footsies-neutral-probe-v0.1.0.ps1`。若导入通过，仍只得到中性构建证据，不授权正式输入或正式结果。
