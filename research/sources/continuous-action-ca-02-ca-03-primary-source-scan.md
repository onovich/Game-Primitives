# 连续行动组 CA-03：一手来源候选扫描

- 状态：候选扫描完成；正式选案见 [CA-03](../continuous-action-pilot-ca-03-case-selection.md)，正式变体见 [CA-05](../continuous-action-pilot-ca-05-variants.md)
- 日期：2026-07-27
- 前序决定：[CA-01 核心失真](../continuous-action-pilot-ca-01.md)、[CA-02 案例职责架构](../continuous-action-pilot-ca-02-case-roles.md)
- 研究范围：为 `CA-R1`–`CA-R3` 寻找来源可确定、边界可查询、变体可隔离、结果可复算的一手制品
- 明确排除：本稿不声称任何玩家体验、难度、策略或设计优劣；不把源码函数、帧或硬件采样自动提升为新原语

## 1. 证据口径

本文使用以下标签：

- **[来源事实]**：可由原作者、开发者、权利人仓库、正式规则或同仓库测试直接核对。
- **[项目变体]**：本项目为了反事实检验而设计的单变量修改，不是原作规则。
- **[事前预测]**：在执行变体前即可登记的结果差异；以后必须由冻结输入和输出复算。
- **[研究判断]**：依据来源质量、可反驳性与执行成本作出的选案判断。
- **[开放缺口]**：当前来源不能回答，或尚未经过干净构建、运行、散列和重放验证的事项。

“一手来源”不等于“所有事实都已确定”。代码可以确定某项实现关系，却不能单独证明玩家通常怎样操作；官方说明书可以证明公开规则，却不一定公开阈值、更新顺序或可修改实现。正式取证仍须保存源码快照、工具链、补丁、输入轨迹和运行输出。

> 本文保留候选扫描时提出的初步变体，作为研究路径记录。CA-03 后续把 *FOOTSIES* 的正式身份固定为 `1.5.0`，CA-05 又选择了污染更少的空振取消、过程采样和延迟裁定变体；凡与后两份冻结决定冲突，以后两份为准。

## 2. 结论先行

| CA-02 角色 | 首选制品 | 被隔离的边界 | 单变量变体 | 当前结论 |
| --- | --- | --- | --- | --- |
| `CA-R1` 识别—锁定入口 | *FOOTSIES* `1.5.0` 源码提交 `7eaaad7…` | 第二次攻击输入先被缓存，随后是否取得取消资格并转成新**规则动作** | 允许空振取消 `否 → 是` | **正式入选，待构建排练** |
| `CA-R2` 调制—轨迹运行 | id Software *Quake III Arena* GPL 源码提交 `dbe4ddb…`，源码自报 `Q3 1.32b` | 空中移动过程每步重新读取方向，还是只在进入过程时锁存方向 | **调制读取策略** `逐步重采样 → 进入时锁存` | **首选，条件入选**；以源码运动模块为制品，不冒充零售可执行文件 |
| `CA-R3` 候选—裁定出口 | osu!lazer `2026.726.0-lazer` 提交 `5da7100…` | 相同候选按下何时取得当前时间并形成正式**事件**结果 | 裁定调度 `立即 → 延迟 75 ms` | **正式入选，待构建排练** |
| `CA-R1` 替补 | *Celeste 64* `v1.1.1` 提交 `bfc7a3b…` | 离地后跳跃输入在宽限窗口内是否仍取得跳跃资格 | 离地宽限 `0.12 s → 0.08 s` | **替补**；来源与许可清楚，但需要为私有角色状态建立测试接缝 |

**[研究判断]** 三个首选不是按“每种类型各一个”配额选出，而是分别攻击 CA-01 链条中的入口、运行和出口。它们来自格斗、第一人称动作与节奏判定三个不同家族，可减少某一引擎惯例被误写成普遍结构的风险；但跨类型差异只是附带价值，不能替代 `CA-H01`–`CA-H04`。

**[研究判断]** 暂不触发条件角色 `CA-R4`。三个主选都能在现有角色中记录“正式效果／结果如何改变下一次合法响应机会”；只有以后发现**语义反馈**的观察者、内容、时机或保留方式无法在前三案中无混杂地隔离，才应另开案例。

## 3. 来源标识符与项目术语的映射

下列英文或代码名只用于精确指向来源。本文自己的分析继续使用中文**共享术语**，不把来源命名直接收入项目词表。

| 来源标识符 | 来源中的局部含义 | 本文映射 |
| --- | --- | --- |
| `N_ATTACK`、`N_SPECIAL` | *FOOTSIES* 的普通攻击与中立特殊攻击标识 | 两个不同的**规则动作** |
| `buffer`、`bufferActionID` | 在当前帧不能立即转换时保留请求 | **输入识别**后的待执行记录；不等同任意“缓冲”隐喻 |
| `execute`、`canCancelAttack()` | 来源的取消表字段与命中资格检查 | **锁定点**前后的许可关系 |
| `usercmd_t`、`PM_AirMove` | id 源码中的玩家命令与空中移动更新函数 | 重复到达的**输入**与同一有界**过程**的更新 |
| `pmove_fixed`、`pmove_msec` | 固定步长开关与步长 | **时间基准**配置 |
| `HitWindows.ResultFor` | osu!lazer 按时间偏移返回判定结果 | 候选输入到正式**事件分类**的**裁定** |
| `CoyoteTime`、`tCoyote` | *Celeste 64* 的离地跳跃宽限常量与剩余时间 | 临时**资格状态**及其时间作用域 |
| `VirtualButton.Buffer` | Foster 的按键输入保留时长 | 输入信号的**保留窗口** |

映射只承诺本案所需的局部同义关系。例如 `execute` 不是项目所有语境中的“执行”，`buffer` 也不是一种新原语。

## 4. `CA-R1` 首选：*FOOTSIES* 1.5.0

### 4.1 制品身份与来源等级

**[来源事实]**

- 原作者 HiFight 的[官方仓库](https://github.com/hifight/Footsies)把作品描述为单按键二维格斗游戏。
- 官方项目页和 GitHub 发布页使用 `1.5.0`；标签 `1.5.0` 指向提交 [`7eaaad799bb7912625c15af9407c2c67e6305d75`](https://github.com/hifight/Footsies/tree/7eaaad799bb7912625c15af9407c2c67e6305d75)。
- 项目声明的 Unity 编辑器版本是 `2018.1.1f1`，见 [`ProjectVersion.txt`](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/ProjectSettings/ProjectVersion.txt)。
- 战斗主循环位于 `FixedUpdate`；工程固定步长为 `0.02` 秒，即本案默认每秒 50 个战斗更新，见 [`BattleCore.cs` L103–140](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/BattleCore.cs#L103-L140)与 [`TimeManager.asset`](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/ProjectSettings/TimeManager.asset)。
- 官方 README 说明普通招命中或被防御后可以取消为中立特殊招，也提供逐帧暂停和碰撞框显示键，见 [`README.md`](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/README.md)。

**[研究判断]** 同一提交还出现其他标签，且相关发布附件命名不一致。正式制品因此只写成“标签 `1.5.0` 的源码提交”，不在未做散列与行为比对前声称任何发布附件就是该源码的对应二进制。

### 4.2 可查询的规则边界

**[来源事实]**

1. `N_ATTACK` 的动作编号是 `100`，`N_SPECIAL` 是 `110`，见 [`Fighter.cs` L42–60](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/Fighter.cs#L42-L60)。
2. `N_ATTACK.asset` 声明该动作共 22 帧；真实攻击框在动作帧 4–5 有效；动作帧 1–3 允许把 `110` 写入取消缓存，动作帧 4–5 则把同一目标标为可执行，见 [`N_ATTACK.asset` L14–97](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Fighter/F00/Actions/N_ATTACK.asset#L14-L97)。
3. 输入历史在每次更新中移位，并由相邻样本计算按下边沿；普通攻击运行期间再次出现攻击边沿会请求 `N_SPECIAL`，见 [`Fighter.cs` L168–185](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/Fighter.cs#L168-L185)与[L199–253](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/Fighter.cs#L199-L253)。
4. `RequestAction` 在取消表允许缓存时只保留目标动作；当前动作取得取消资格后，下一次动作请求更新才把缓存目标设为当前动作。F00 的 `canCancelOnWhiff` 为假，资格来自当前动作已经命中，见 [`Fighter.cs` L467–510](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/Fighter.cs#L467-L510)、[L531–556](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/Fighter.cs#L531-L556)与 [`F00.asset`](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Fighter/F00/F00.asset)。
5. 每个战斗更新按“采集输入 → 动作帧递增 → 处理动作请求 → 更新移动和碰撞框 → 检查攻击框碰撞”的顺序运行；命中在末段增加攻击者命中计数，见 [`BattleCore.cs` L261–278](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/BattleCore.cs#L261-L278)与[L401–467](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/BattleCore.cs#L401-L467)。
6. 工程已有内存中的输入记录与上局重放路径，可作为正式夹具的起点，见 [`BattleCore.cs` L473–505](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/Assets/Script/BattleCore.cs#L473-L505)。

这里需要显式保存的不是“攻击有 22 帧”这个孤立事实，而是：

```text
第二次攻击输入被识别
→ 在动作帧 1–3 只形成待执行记录
→ 动作帧 4 的接触在本次更新末尾形成命中事实
→ 下一次动作请求更新重新检查取消资格
→ 待执行记录越过锁定点，进入 N_SPECIAL
```

若只保留“玩家攻击，然后发动特殊攻击”，缓存、命中资格、更新顺序和锁定点都无法独立恢复。

### 4.3 候选扫描时的初步变体（未采用）

下列“缩短缓存末帧”方案是来源扫描阶段的初稿。CA-05 已改用“允许空振取消 `否 → 是`”，以固定无命中轨迹并只改变缓存后的许可门。

扫描阶段建议的初步配置：

- Windows x64；Unity `2018.1.1f1` 源码构建；
- F00 对 F00，本地脚本输入，关闭 AI；
- 工程固定步长 `0.02 s` 保持不变；
- P2 全程零输入；
- 固定双方初始位置，使 P1 的 `N_ATTACK` 真实攻击框在动作帧 4 首次与 P2 受击框相交；
- P1 在片段开始按下攻击，释放后，在 `N_ATTACK` 当前动作帧 3 提交第二个攻击按下边沿；
- 记录每个固定更新的输入位、当前动作编号、当前动作帧、待执行动作编号、命中计数、碰撞结果和位置。

**[项目变体]** 只把 `N_ATTACK.asset` 第一条取消记录的 `startEndFrame` 从 `{1, 3}` 改为 `{1, 2}`。动作编号、输入轨迹、真实攻击框帧、命中规则、取消目标、固定步长、双方位置和伤害公式全部不变。

**[事前预测]**

- 基线：动作帧 3 的第二次攻击被保存在待执行记录中；动作帧 4 的接触在该更新末尾增加命中计数；下一次动作请求更新把当前动作改为 `N_SPECIAL`。
- 变体：动作帧 3 已在缓存窗口之外，同一输入不形成待执行记录；动作帧 4 仍按相同轨迹命中，但此后不会因为该输入进入 `N_SPECIAL`。

这项预测同时区分了**输入**、待执行记录、候选接触、命中事实、取消资格和新**规则动作**；它没有预言变体更难、更公平或更受欢迎。

### 4.4 复现与停止门槛

正式运行前必须补齐：

1. 从干净提交构建未修改基线，并记录 Unity 安装版本、平台模块和构建日志；
2. 用脚本输入而不是人工键盘时序喂入固定更新；
3. 把双方数值初始位置写入清单，并证明基线与变体在动作帧 4 前的轨迹逐项相同；
4. 保存规则补丁，机械检查除预登记的唯一逻辑变量外没有规则差异；
5. 若源码无法在声明版本下构建，或必须修改多项运行逻辑才能启动，则本案暂停，启用 *Celeste 64* 替补，不以发布附件行为代替源码对应关系。

### 4.5 许可与风险

- 仓库代码声明 [GPL-3.0](https://github.com/hifight/Footsies/blob/7eaaad799bb7912625c15af9407c2c67e6305d75/LICENSE.txt)。若分发修改后的完整构建或衍生代码，必须履行相应源码与许可证义务。
- 本项目优先公开补丁、输入轨迹、结构化日志和少量必要截图，不重新分发原作美术、音频或未经核验的发布压缩包。
- Unity 2018 工具链、旧资源导入和发布附件命名不一致是本案的主要实现噪声。

**[选案判断]** 条件入选 `CA-R1`。它比单纯改变一个输入容忍时间更直接地展示“已识别但未锁定”“取得资格”“下一更新提交”之间的区别；若源码构建失败，则不应为保住名作案例而放宽来源门槛。

## 5. `CA-R2` 首选：id *Quake III Arena* GPL 移动源码

### 5.1 制品身份与来源等级

**[来源事实]**

- id Software 的[官方仓库](https://github.com/id-Software/Quake-III-Arena)没有发布标签；本次冻结默认分支提交 [`dbe4ddb10315479fc00086f08e25d968b4b43c49`](https://github.com/id-Software/Quake-III-Arena/tree/dbe4ddb10315479fc00086f08e25d968b4b43c49)。
- 源码常量自报 `Q3 1.32b`，见 [`q_shared.h` L29–30](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/code/game/q_shared.h#L29-L30)。
- 官方 README 把仓库称为 GPL 源码发布，并明确它主要是源码材料而非带有商业数据的完整产品，见 [`README.txt`](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/README.txt)。

**[开放缺口]** “源码自报 `Q3 1.32b`”不能推出“本次编译物与某一零售平台可执行文件逐字节相同”。正式案例名称必须是“id GPL 源码快照的移动模块”，不得简称为“零售版《雷神之锤 III》实验”。

### 5.2 可查询的规则边界

**[来源事实]**

1. `bg_pmove.c` 自述接口为“输入玩家状态和玩家命令，返回修改后的玩家状态”，见 [`bg_pmove.c` L23–40](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/code/game/bg_pmove.c#L23-L40)。
2. 空中移动每次调用都从当前命令读取前后与左右分量，结合当前朝向得到期望方向和速度，再调用加速更新，见 [`PM_AirMove`, L597–637](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/code/game/bg_pmove.c#L597-L637)。
3. 加速函数读取当前速度在期望方向上的投影，并按 `加速度 × 本步时长 × 期望速度` 更新速度，见 [`PM_Accelerate`, L233–258](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/code/game/bg_pmove.c#L233-L258)。
4. 单步更新从命令时间与玩家状态时间之差计算步长，检查地面、水和移动模式，然后在非行走分支调用空中移动，见 [`PmoveSingle`, L1830–2000](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/code/game/bg_pmove.c#L1830-L2000)。
5. 外层 `Pmove` 可以用 `pmove_fixed` 与 `pmove_msec` 把较长命令区间切成固定子步，以避免依赖渲染帧率，见 [`Pmove`, L2019–2064](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/code/game/bg_pmove.c#L2019-L2064)；公开结构字段见 [`bg_public.h` L119–195](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/code/game/bg_public.h#L119-L195)。

在本案中，**过程**不是一条动画，而是“角色持续处于空中分支、命令流反复调制速度与位置”的有界状态轨迹。源码函数边界只是定位证据；真正接受检验的是“方向在每个过程更新重新读取”这一规则可观察关系。

### 5.3 冻结片段与单变量变体

建议使用不依赖商业数据的源码运动夹具：

- 编译提交 `dbe4ddb…` 的运动模块及其必要 GPL 依赖；
- 初始化普通存活玩家状态，原点与速度为零，固定视角，保证地面检查持续返回空中；
- `pmove_fixed = 1`，`pmove_msec = 8`；
- 所有按键、跳跃、武器、水体和碰撞输入关闭；
- `0–200 ms`：只提交最大前向分量；
- `208–400 ms`：只提交最大右向分量；
- 每 8 ms 记录命令、位置、速度、期望方向、空中／行走分支和接触结果；
- 片段在 `400 ms` 固定停止；正式排练不得把渲染帧或真实墙钟作为时间基准。

**[项目变体]** 增加且只改变一个逻辑配置：

```text
调制读取策略 =
    基线：每个空中子步读取当前命令
    变体：进入本段空中过程时锁存方向，直到片段结束前不再读取方向分量
```

这个逻辑变量可能需要修改多行源码或增加一个夹具状态字段；“单变量”指一个可命名的因果关系，而不是补丁只能有一行。加速度、固定步长、命令序列、初始状态、朝向、碰撞回调和积分公式必须保持相同。

**[事前预测]**

- 基线：在 `208 ms` 后，当前命令逐步把速度和位置轨迹转向右侧。
- 变体：`208 ms` 后的右向命令仍存在于冻结输入轨迹，却不会调制当前空中过程；轨迹继续按进入时锁存的前向方向演化。
- 两案可以都被粗略命名为“角色在空中移动”，但该标签不能恢复中途输入是否仍有许可，也不能预测相同输入轨迹的空间结果。

把 `pm_airaccelerate` 从 `1.0` 改成另一个数值只能证明轨迹依赖加速度大小，不足以单独隔离“何时重新读取输入”。它可用于夹具灵敏度检查，不作为正式 `CA-R2` 变体。

### 5.4 复现与停止门槛

正式运行必须：

1. 首先编译、执行未修改的 id 移动模块；若改用 ioquake3 或其他移植版，必须另建制品身份并提交逐项差异，不得静默替换；
2. 使用项目自建的空碰撞世界、初始化状态和命令文件，不读取商业关卡、美术或音频；
3. 保存 C 编译器版本、编译选项、结构体初始化字节、命令轨迹与每步输出；
4. 对基线与变体做机械差异审计，确认没有同时改变步长、加速度、碰撞或坐标精度；
5. 先登记轨迹差异方向，再运行；若旧代码在现代工具链下需要多项语义修改才能链接，则结论记为**不定**，回到 SuperTuxKart 备选，而不是把移植修复当成原作事实。

### 5.5 许可与风险

- `bg_pmove.c` 文件头允许按 GPL v2 或其后版本修改与再分发，见 [`bg_pmove.c` L1–20](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/code/game/bg_pmove.c#L1-L20)与仓库 [`COPYING.txt`](https://github.com/id-Software/Quake-III-Arena/blob/dbe4ddb10315479fc00086f08e25d968b4b43c49/COPYING.txt)。
- 商业游戏数据不在该许可范围内。本项目夹具不得打包零售数据；若发布链接后的修改模块与夹具，应保留声明并按 GPL 提供相应源码。
- 旧 C 工具链、平台相关依赖、速度量化与缺省结构体字段是实现噪声；它们必须在基线排练中显式控制。

**[选案判断]** 条件入选 `CA-R2`。它的价值不在“高速移动”或玩家熟悉度，而在于源码明确展示了当前命令、固定子步、期望方向、速度积分与空间轨迹之间的连续因果链。

## 6. `CA-R3` 首选：osu!lazer 2026.726.0

### 6.1 制品身份与来源等级

**[来源事实]**

- ppy 的[官方仓库](https://github.com/ppy/osu)发布标签 [`2026.726.0-lazer`](https://github.com/ppy/osu/releases/tag/2026.726.0-lazer)，指向提交 [`5da71008b082d1a77e4bb301dc98886f1f24b895`](https://github.com/ppy/osu/tree/5da71008b082d1a77e4bb301dc98886f1f24b895)。
- 仓库构建说明要求 .NET 8；冻结提交的 [`global.json`](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/global.json)锁定 `8.0.100` 并允许同特性带向前滚动。
- 本案只使用标准 osu! 规则集的判定窗口类和项目自建的一物件测试谱面，不使用在线成绩、玩家数据或商业音乐。

### 6.2 可查询的规则边界

**[来源事实]**

1. 通用判定窗口把时间偏移取绝对值，从较好结果向较差结果检查对应窗口；第一个容纳该偏移的结果成为返回值，见 [`HitWindows.cs` L37–109](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/osu.Game/Rulesets/Scoring/HitWindows.cs#L37-L109)。
2. 标准规则集给出“极佳”“尚可”“勉强”和“未命中”的窗口范围；难度 5 时，映射与向下取整后的半窗分别为 `49.5 ms`、`99.5 ms`、`149.5 ms`，未命中窗口固定为 `400 ms`，见 [`OsuHitWindows.cs` L10–64](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/osu.Game.Rulesets.Osu/Scoring/OsuHitWindows.cs#L10-L64)及[默认难度与区间映射](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/osu.Game/Beatmaps/IBeatmapDifficultyInfo.cs#L9-L72)。
3. 同仓库已有用单个圆形物件检查过早输入和未命中的测试场景，证明非整局、可执行的判定夹具路径已经存在，见 [`TestSceneMissHitWindowJudgements.cs` L20–64](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/osu.Game.Rulesets.Osu.Tests/TestSceneMissHitWindowJudgements.cs#L20-L64)。

本案的边界是：

```text
物件时间与输入时间形成偏移
→ 输入成为待分类候选
→ 判定窗口按优先顺序检查阈值
→ 返回一个正式事件结果
→ 结果进入后续计分与反馈
```

输入确实发生，不等于它已经被正式分类为“极佳”；分类也不等于所有后续计分、显示和玩家理解已经同时完成。

### 6.3 候选扫描时的初步变体（未采用）

下列“改变极佳窗口”方案是来源扫描阶段的初稿。CA-05 已改用“相同候选立即裁定／延迟 `75 ms` 裁定”，因为它更直接检验候选发生与正式结果提交的边界。

扫描阶段建议的初步配置：

- 冻结提交 `5da7100…`，.NET 8；
- 标准 osu! 规则集，整体难度 `5`；
- 项目生成的单个圆形物件，开始时间 `1000 ms`；
- 冻结重放在 `1045 ms` 提交一次有效输入，即偏移 `+45 ms`；
- 不启用会修改窗口或自动输入的模组；
- 同时运行纯判定单元测试与现有测试框架中的一物件集成测试；
- 记录难度值、各窗口、原始偏移、绝对偏移、遍历顺序、返回结果和后续命中结果。

**[项目变体]** 只把“极佳”窗口范围的中位参数从 `50` 改为 `40`；“尚可”“勉强”“未命中”、难度、物件、输入和遍历顺序不变。难度 5 下，“极佳”半窗相应从 `49.5 ms` 变为 `39.5 ms`。

**[事前预测]**

- 基线：`45 ≤ 49.5`，返回“极佳”。
- 变体：`45 > 39.5`，不再返回“极佳”；但 `45 ≤ 99.5`，因此返回“尚可”。
- 候选输入和其时间位置完全相同，只有候选到正式结果的阈值关系改变。

### 6.4 复现与停止门槛

1. 从干净提交恢复 NuGet 依赖，保存实际 SDK 和依赖锁定信息；
2. 新测试必须先在未改源码上得到“极佳”，再应用单参数补丁得到“尚可”；
3. 保存可直接调用 `ResultFor(45)` 的窄测试，以及一物件集成测试；两者结果若不一致，必须解释调度、模组或对象状态差异；
4. 保存补丁、测试命令、标准输出、测试结果文件和散列；
5. 若最新标签在依赖恢复上不可复现，可回退到另一个明确标签，但必须重做身份与窗口计算，不能只改文档中的版本号。

### 6.5 许可与风险

- 仓库源代码采用 [MIT 许可证](https://github.com/ppy/osu/blob/5da71008b082d1a77e4bb301dc98886f1f24b895/LICENCE)。正式制品保留许可证与版权声明。
- osu! 名称、品牌和仓库内资源不能因代码为 MIT 就一概视为可自由再分发。本项目只发布自建谱面、源码补丁和测试输出，避免打包原作音频、皮肤与品牌资源。
- 仓库更新频繁；标签、提交、SDK、依赖与测试命令必须一起冻结。

**[选案判断]** 入选 `CA-R3`。它已有测试工程和清楚的时间裁定路径，但正式排练顺序由 CA-07 决定，不能因工程看似容易而跳过统一冻结与增量彩排。

## 7. `CA-R1` 替补：*Celeste 64* v1.1.1

### 7.1 身份与来源事实

- EXOK 的[官方仓库](https://github.com/EXOK/Celeste64)说明这是原 *Celeste* 开发者制作的作品。
- 注释标签对象 `35bc30e48d5e70188635267956748f41a7c7ad04` 的 `v1.1.1` 解引用到提交 [`bfc7a3ba6f35d25bd11b4c4bad749398f70034e2`](https://github.com/EXOK/Celeste64/tree/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2)；工程文件同时声明版本 `1.1.1`、目标 `.NET 8` 与 Foster `0.1.18-alpha`，见 [`Celeste64.csproj`](https://github.com/EXOK/Celeste64/blob/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2/Celeste64.csproj)。
- 游戏启动时启用固定步长，见 [`Game.cs` L71–77](https://github.com/EXOK/Celeste64/blob/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2/Source/Game.cs#L71-L77)。对应 Foster 标签 [`v0.1.18-alpha`](https://github.com/FosterFramework/Foster/tree/351d20640cb6d6323a1490fa5f5254b8269f783c)的默认固定步长是 `1/60 s`，见 [`Time.cs`](https://github.com/FosterFramework/Foster/blob/351d20640cb6d6323a1490fa5f5254b8269f783c/Framework/Time.cs)。
- 角色常量把离地跳跃宽限设为 `0.12 s`；计时器每次更新递减，落地时恢复为该值，普通状态仅在剩余时间大于零并消费跳跃按下时调用跳跃，见 [`Player.cs` L20–39](https://github.com/EXOK/Celeste64/blob/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2/Source/Actors/Player.cs#L20-L39)、[L318–341](https://github.com/EXOK/Celeste64/blob/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2/Source/Actors/Player.cs#L318-L341)、[L393–420](https://github.com/EXOK/Celeste64/blob/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2/Source/Actors/Player.cs#L393-L420)与[L1152–1183](https://github.com/EXOK/Celeste64/blob/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2/Source/Actors/Player.cs#L1152-L1183)。
- 跳跃与冲刺按键还各自使用 `0.1 s` 的输入保留窗口，见 [`Controls.cs` L4–14](https://github.com/EXOK/Celeste64/blob/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2/Source/Data/Controls.cs#L4-L14)；Foster 的实现会在窗口内持续报告尚未消费的按下，见 [`VirtualButton.cs` L88–156](https://github.com/FosterFramework/Foster/blob/351d20640cb6d6323a1490fa5f5254b8269f783c/Framework/Input/VirtualButton.cs#L88-L156)与[L242–315](https://github.com/FosterFramework/Foster/blob/351d20640cb6d6323a1490fa5f5254b8269f783c/Framework/Input/VirtualButton.cs#L242-L315)。

### 7.2 可执行替补变体

建议用项目自建平面和无墙环境，让角色在最后一次落地更新后离开边缘，并在第六个固定更新提交一次跳跃按下：

- 基线 `0.12 - 6 × (1/60) > 0`，输入取得资格并调用跳跃；
- **[项目变体]** 只把 `CoyoteTime` 从 `0.12` 改为 `0.08`；
- **[事前预测]** 变体在相同输入到达时宽限已经耗尽，且无墙跳等替代路径，因此本段不调用跳跃。

这项替补隔离的是“信号到达时资格是否仍开放”，比 *FOOTSIES* 少了“已缓存 → 单独资格门 → 下一更新提交”的完整锁定链，因此只在首选工程不可用时替换 `CA-R1`。

### 7.3 许可与实现噪声

- 官方 README 明确区分：`Source` 目录除另有注明外采用 MIT；`Content` 属于 Maddy Makes Games, Inc；FMOD 目录含第三方绑定和二进制，见 [`ReadMe.md` 的 License 段](https://github.com/EXOK/Celeste64/blob/bfc7a3ba6f35d25bd11b4c4bad749398f70034e2/ReadMe.md#license)。
- 正式夹具应使用源代码、项目自建几何和结构化日志，不分发 `Content` 或 FMOD 资产。
- 角色字段和状态更新没有现成单元测试接缝；若为了测试必须重构大量角色逻辑，会增加变体污染风险。该风险低于不明版本，却高于 osu!lazer 的现成测试路径。

## 8. 已扫描但不占核心席位的候选

| 候选 | 一手制品 | 可用边界 | 暂不入选原因 |
| --- | --- | --- | --- |
| *VVVVVV* `2.4.4` | Terry Cavanagh 官方仓库提交 [`ea811e15bd5028cad344bf108934f4c67d927917`](https://github.com/TerryCavanagh/VVVVVV/tree/ea811e15bd5028cad344bf108934f4c67d927917)；输入和重力翻转见 [`Input.cpp`](https://github.com/TerryCavanagh/VVVVVV/blob/ea811e15bd5028cad344bf108934f4c67d927917/desktop_version/src/Input.cpp) | 按下保留计数与落地后重力翻转 | 可构造 `5 → 1` 更新的保留窗口变体，但源码许可含非商业限制；与 `CA-R1` 重叠且公开制品边界不如 MIT/GPL 案例简洁 |
| SuperTuxKart `1.5` | 官方仓库提交 [`1fb491f507216c5d181ccd85f29ff08eca003827`](https://github.com/supertuxkart/stk-code/tree/1fb491f507216c5d181ccd85f29ff08eca003827) | 原始转向输入经时间常量平滑为实际转向；主循环记录固定更新与物理顺序 | 是 `CA-R2` 的第一备选；完整工程和资源构建较重，先让较小的 id 运动模块接受可执行性排练 |
| Teeworlds `0.7.5` | 官方仓库提交 [`4fc25a17fef3e6c2bf4d52b0421e0d69ecaa1e79`](https://github.com/teeworlds/teeworlds/tree/4fc25a17fef3e6c2bf4d52b0421e0d69ecaa1e79)；官方[服务器调参文档](https://www.teeworlds.com/?page=docs&wiki=server_tuning) | 抓钩发射、附着、拉拽与释放状态机 | 长度、速度、阻力与状态转换相互耦合，首次单变量隔离成本高；适合作为后续反例压力，不作为最小首轮 |
| *Fantasy Strike* 练习模式 | 开发者[官方逐帧说明](https://www.fantasystrike.com/practice-mode) | 启动、有效、恢复帧及逐帧查看 | 教学来源优秀，但没有同等一手的可修改运行实现；只能解释边界，不能独立完成反事实夹具 |
| *Wii Sports: Tennis* | Nintendo [Wii 说明书入口](https://en-americas-support.nintendo.com/app/answers/detail/a_id/16890/~/wii-manuals)及官方手册 | 挥动时机、方向、上旋与高吊球的动作说明 | 公开材料没有识别阈值、传感器处理和可修改实现；适合具身输入讨论，不满足本轮 `CA-H04` |

这张表不是类型覆盖率结论。体育、体感、竞速、钩索和平台动作仍可在以后用来攻击首轮表示；当前只是不让“耳熟能详”替代可反驳性。

## 9. 版权与公开测试制品边界

| 制品 | 代码许可边界 | 不应随测试包再分发 | 建议公开内容 |
| --- | --- | --- | --- |
| *FOOTSIES* 源码标签 | GPL-3.0 | 未核验发布包、原作资产的独立复制件 | 提交身份、补丁、输入 CSV、日志、许可证、必要的低量截图 |
| id 移动模块 | GPL v2 或其后版本 | 零售关卡、美术、音频与其他商业数据 | 可构建的源码夹具、补丁、命令轨迹、逐步状态、GPL 声明 |
| osu!lazer | MIT 代码；品牌与资源另行审查 | 原作音乐、皮肤、在线数据和不必要品牌资源 | 测试源码、项目自建谱面、测试结果、MIT 声明 |
| *Celeste 64* | `Source` 原则上 MIT；`Content` 与 FMOD 另有边界 | `Content`、FMOD 二进制及品牌资产 | 最小源代码测试、项目自建几何、日志、MIT 声明 |

以上是研究制品的保守操作边界，不是法律意见。书中可以引用必要的短代码片段并链接完整来源；网页不应为了“可玩演示”自动打包原作资产。

## 10. CA-03 正式执行包

每个核心角色在运行前应生成同构清单：

```text
identity/
  source-url
  tag-or-release
  full-commit
  platform
  toolchain
  dependency-lock

fixture/
  initial-state
  input-trace
  time-base
  stop-boundary
  invariant-list

variant/
  one-logical-variable
  patch
  pre-registered-prediction

evidence/
  clean-build-log
  baseline-output
  variant-output
  replay-or-test-result
  file-hashes
  licence-notice
```

其中：

- `initial-state` 必须包含会改变资格、轨迹或判定的全部字段；
- `input-trace` 使用规则时间或固定步编号，不使用“约一秒后”；
- `invariant-list` 明列没有改变的输入、步长、碰撞、效果和反馈；
- `patch` 可以有多行，但只能实现一个预先命名的因果变量；
- `pre-registered-prediction` 必须在看见变体输出前写入；
- 散列、编译器小版本和依赖恢复结果当前仍是**开放缺口**，应由正式排练生成，而不是在来源扫描中臆造。

## 11. 候选扫描时的推进建议

本节保留扫描阶段建议；正式执行顺序与放行条件由 CA-07 统一冻结。

1. **先排练 osu!lazer。** 它能用现有测试工程验证整条证据管线，而无需先解决碰撞场景或旧引擎。
2. **再排练 id 移动模块。** 先证明未修改基线能在项目自建世界中运行，再加入“逐步重采样／进入时锁存”变体；若现代构建必须改动语义，转用 SuperTuxKart。
3. **最后排练 *FOOTSIES*。** 先锁定 Unity 版本与动作帧，再测定能在动作帧 4 稳定命中的数值位置；如构建或来源对应关系失败，立即切换 *Celeste 64*，不无限修复。
4. 三案都取得基线与变体输出后，才派发独立重构；重构者只能看到冻结的有类型描述、输入和结果字段，不能看到作品名、源码标识符或预期答案。
5. 独立重构通过后，CA-05 才能判断压缩表示是否发生别名化；来源扫描本身不构成对 CA-01 的支持。

## 12. 当前未解决问题

1. *FOOTSIES* 源码标签、发布附件和可构建二进制之间能否建立散列与行为对应？
2. *FOOTSIES* 哪组数值初始位置能在固定输入下首次于动作帧 4 命中，且不被推箱提前改位？
3. id 运动模块在现代 C 工具链下最小需要哪些非语义兼容补丁？这些补丁能否与正式变体完全分离？
4. “进入时锁存”需要怎样记录过程身份，才不会把研究者任意划段伪装成来源动作？
5. osu!lazer 的窄判定测试与一物件集成测试是否在冻结提交上给出完全一致的结果？
6. 三案的输出是否足以让独立重构者恢复**输入**、**规则动作**、**过程**、候选**事件**、正式**裁定**、**结算**和**效果**的边界，而无需作品专名？
7. 若当前有类型词汇仍不能无损编码差异，缺口究竟来自词汇、句式、时间作用域，还是测试描述遗漏？在回答前不新增“连续行动原语”。

## 13. 本轮结论

**[研究判断]** 候选扫描支持、且 CA-03 后续正式冻结的组合是：

```text
FOOTSIES
  → 已识别输入怎样等待资格并越过锁定点

id Quake III Arena 移动源码
  → 运行中的同一过程怎样持续接受输入调制并形成轨迹

osu!lazer
  → 同一候选输入怎样因裁定阈值不同成为不同正式结果
```

它们共同覆盖“输入被识别”到“效果／结果被提交”的三段，但不预设所有游戏都必须采用固定三阶段。*Celeste 64* 是来源清楚的入口替补；SuperTuxKart 是运行角色的第一备选。下一步应当是制作最小可执行夹具和预登记预测，而不是继续横向扩充作品名单。
