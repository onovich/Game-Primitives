# CA-R1 独立夹具方法记录 v0.1.0

## 方法结论

`CA-R1` 的被测规则不要求启动 Unity Editor。独立夹具可由 .NET 8 直接编译冻结提交
`7eaaad799bb7912625c15af9407c2c67e6305d75` 中的原始 `Fighter.cs` 及其必要原始数据类型，
同时以单独兼容层提供 Unity 值类型、标记特性与无副作用音频边界。

该路径满足以下边界：

- `Fighter.cs` 按冻结字节直接进入编译，不复制、不翻译、不生成替代实现；
- `FighterData.cs`、`ActionData.cs`、`InputData.cs` 及必要容器类型同样使用冻结原字节；
- `canCancelOnWhiff` 每次运行都从隔离 checkout 的 `Assets/Fighter/F00/F00.asset` 读取；
- 基线保持冻结 checkout 干净；变体只应用既有
  `footsies-r1-whiff-cancel-v0.1.0.patch` 的一行资产修改；
- `CommonActionID` 覆盖的 17 个 F00 动作都由冻结 Unity YAML 资产严格投影，
  不在兼容层重写取消判定、动作请求或状态转换；
- 门前 smoke 固定为六次 synthetic 更新，明确不同于七事件正式输入；
- synthetic 可执行文件没有正式输入路径参数或通用输入模式，并拒绝正式执行环境变量；
- 构建脚本不读取正式输入，不调用正式 runner／comparator，不创建授权、许可、预测或正式结果。
- 正式七事件体由单独的 `FootsiesR1Formal.csproj` 编译；构建门只静态编译，
  不调用该可执行体；
- `run-footsies-r1-standalone-formal-v0.1.0.ps1` 先验证正式执行许可，
  许可成功后才允许解析来源、工具链、正式输入、输出或绑定夹具。

## 兼容层的允许职责

兼容层只承担三类工作：

1. 提供 `Vector2`、`Rect`、`Time.deltaTime` 等冻结源码编译所需的 Unity API 表面；
2. 将冻结文本资产投影到原始 `FighterData`／`ActionData` 对象；
3. 将声音服务保留为无副作用调用边界。

所有与缓冲、取消资格、动作请求和动作切换有关的判断仍只发生在冻结 `Fighter.cs` 中。

## 门前命令

```powershell
.\run-footsies-r1-standalone-build-smoke-v0.1.0.ps1 `
  -SourcePath D:\GamePrimitivesToolchains\sources\footsies-7eaaad79 `
  -DotnetPath D:\GamePrimitivesToolchains\dotnet-8.0.100\dotnet.exe `
  -CacheRoot D:\GamePrimitivesToolchains\replays\r1-standalone-build-smoke-<new-id>
```

`CacheRoot` 必须位于项目仓库和来源 checkout 之外，且必须尚不存在或为空。
输出证据只证明独立编译和 synthetic 分支 smoke 成功，不等同于正式执行授权。

## 两个可执行面的边界

构建门生成两类独立二进制：

- `FootsiesR1Standalone.dll` 只接受固定的六事件 synthetic smoke 模式；
- `FootsiesR1Formal.dll` 只接受正式 runner 注入的许可摘要、预测集摘要、
  七事件输入哈希和路径环境；它在构建门中仅编译，绝不运行。

两类二进制共享冻结 `Fighter.cs`、冻结数据类型、17 个动作资产投影、
`UnityCompatibility.cs`、`FrozenSourceContract.cs` 与 `UnityYamlAssetLoader.cs`。
只有 synthetic 二进制编译 `Program.cs`；只有正式二进制编译 `FormalProgram.cs`。
