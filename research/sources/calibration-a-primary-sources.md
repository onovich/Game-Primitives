# 第一轮校准门 A：一手资料与版本冻结

> 状态：研究资料包，不是完整案例，也不是定稿章节
> 核验日期：2026-07-21
> 对象：FIDE 标准国际象棋；1989 年 Game Boy《Tetris》的单人 A-Type
> 目的：先冻结“究竟研究哪个对象”，再为后续的原语、语法与机制分析提供可定位、可复核的依据。

## 0. 证据约定

本文只记录四种内容，并显式区分它们：

- **来源事实**：来源直接陈述，或可从固定版本的规则／程序指令直接读出。
- **研究判断**：本项目为保证分析边界清楚、实验可复现而作的选择；不是来源原话。
- **待证问题**：现有材料不足以回答，不能用常识补齐。
- **排除项**：明确不属于本轮对象，避免把别的版本、模式或实现混入案例。

来源按证据地位分级：

| 级别 | 含义 | 本文用法 |
|---|---|---|
| N | 制定机构发布的现行规范文本 | 用于确认规则是什么 |
| F | 权利方、发行方或制定机构发布的说明与历史材料 | 用于确认版本状态、产品描述和发布语境，不替代规范正文 |
| A | 同时代第一方制品的可核查复制件 | 例如 Nintendo 1989 年说明书扫描；正文是一手制品，但当前托管方不是 Nintendo |
| M | 对实体制品所作、保留照片和日志的可复核测量 | 例如卡带 PCB 与 ROM dump 记录；是保存者的直接测量，不是权利方声明 |
| R | 可重建到指定制品哈希的逆向工程材料 | 可用于提出和复核实装假设；不是官方源代码，也不能证明设计意图 |

没有把攻略、百科、论坛帖子、媒体回忆或二手机制总结纳入证据矩阵。R 级材料是为满足“可复现实装”的最低例外；所有由它得出的结论都必须经指定 ROM 与硬件／模拟器实验复核。

---

## 1. 对象 A1：FIDE 线下标准国际象棋

### 1.1 范围卡

| 字段 | 本轮冻结值 | 性质 |
|---|---|---|
| 作品／传统 | 国际象棋的 FIDE 线下竞赛规则形态 | **研究判断** |
| 规则集 | *FIDE Laws of Chess taking effect from 1 January 2023*，Handbook E012023 | **来源事实** |
| 批准与生效 | 2022-08-07 批准；2023-01-01 生效 | **来源事实**，Handbook 标题元数据与 §0.1 |
| 当前性 | 截至 2026-07-21，FIDE Rules Commission 仍把 2023 版列作 current version；2024—2026 的重写材料尚属草案／提案 | **来源事实** |
| 权威语言 | 英文 | **来源事实**，§0.1 |
| 场景 | over-the-board；Basic Rules 与 Competitive Rules | **来源事实**，§0.1 |
| 速率类别 | standard chess，即每位玩家至少 60 分钟 | **来源事实**，Glossary；但这不是完整时间控制 |
| 具体时间控制 | 尚未冻结；必须在涉及棋钟的实验前另行规定时限、增益／延时与阶段 | **待证／待配置**，§6.3.1 要求预先规定 |
| 纳入 | 正文 Articles 1–12；需要时使用 Appendix C 记谱；以官方 Arbiters' Manual 辅助理解执行 | **研究判断** |
| 排除 | Rapid、Blitz、Chess960、在线棋、国家协会变体、休闲约定，以及未被案例配置采纳的 Guidelines | **排除项** |
| 具体对局 | 暂无；本文件冻结规则集而非某一局棋 | **研究判断** |

推荐保存的规范身份：

```text
FIDE Laws of Chess, 2023 edition
Handbook chapter: E012023
English authentic text
Approved: 2022-08-07
Effective: 2023-01-01
Verified current: 2026-07-21
Official PDF currently linked by RCC:
20230101Laws-of-Chess.pdf (35 pages)
```

### 1.2 当前版本结论

**来源事实**：FIDE Handbook 的当前条目标题、元数据与 §0.1 明确给出上述批准日、生效日、线下适用范围和英文权威性。FIDE Rules Commission 的 Documentation 页面称其收录由该委员会负责的 current versions，并仍把“2023 Laws of Chess”作为规则入口。

**来源事实**：2025 年委员会报告仍把重写文本描述为准备提交、讨论和审批的草案，并建议把批准推迟到 2026 General Assembly；2026 年委员会报告仍使用“will propose amendments”等未来表述。因此这些材料不能覆盖 2023 版。

**研究判断**：本轮应把 E012023 冻结为规范对象。后续即使新版获批，也不能静默替换；应新增一张版本差异卡，再决定案例是否迁移。

### 1.3 来源矩阵

| 级别 | 来源、版本／日期与 URL | 定位 | 可以支持 | 不能支持 |
|---|---|---|---|---|
| N | [FIDE Handbook E012023](https://handbook.fide.com/chapter/E012023) | 标题元数据；§§0.1–0.2；Articles 1–12；Appendices；Glossary | 现行规则内容、适用范围、批准／生效日期、英文权威文本 | 某赛事的具体配置；真实裁判是否一致执行；玩家策略与体验；历史设计意图 |
| N | [Rules Commission：2023 Laws of Chess](https://rcc.fide.com/2023-laws-of-chess/) 与其当前链接的 [35 页 PDF](https://rcc.fide.com/wp-content/uploads/2022/12/20230101Laws-of-Chess.pdf) | 下载页；PDF pp.1–35 | 可冻结、可按条款和 PDF 页码引用的正式文本 | 未来 URL 不会被替换；玩家行为；软件实现 |
| F | [2022 FIDE General Assembly 决议](https://www.fide.com/2022-fide-general-assembly-list-of-decisions/) | GA-2022/17 | 审批机关与批准事项 | 每一条规则的完整语义 |
| N/F | [官方变更表](https://rcc.fide.com/wp-content/uploads/2022/12/20230101Laws-of-Chess_tableofchanges.pdf)，2022-12，5 页 | 按条款列出 2018→2023 的修改 | 明确列出的版本变更与编号修订 | 代替完整正文；证明表中未列出的任何解释结论 |
| F | [2023 FIDE Laws of Chess published](https://www.fide.com/2023-fide-laws-of-chess-published/)，2023-01-04 | 正文首段 | 行政校对已完成；E012023 为 final reviewed version | 精确条款解释；新闻摘要自身存在条款号误写，应回到正文与变更表 |
| F | [Rules Commission Documentation](https://rcc.fide.com/documentation/)，核验于 2026-07-21 | “current versions”说明及 Laws of Chess 入口 | 截至核验日的当前版本状态；Regulations 与 Guidelines 的地位区别 | 新版未来何时批准；条款细节 |
| F | [Arbiters' Manual 2025](https://arbiters.fide.com/wp-content/uploads/Publications/Manual/Arbiters_Manual_2025.pdf)，355 页 | PDF p.3 修订记录；p.13 版本说明；pp.15 起规则与裁判注释 | FIDE 裁判委员会公开的执行说明和案例语境 | 取代 Laws；证明所有裁判在现场采取同一种裁量 |
| F | [2024 Rules Commission：Re-write the Laws of Chess](https://rcc.fide.com/2024/12/27/questions-answers-n-5-december-2024-re-write-the-laws-of-chess/) | 全文 | 全面重写正在进行 | 重写文本已经生效 |
| F | [2025-07-09 重写进度报告](https://doc.fide.com/docs/DOC/2FC2025/CM2-2025_18.pdf) | PDF p.2 | 新文本仍待提交、讨论和审批；建议推迟批准 | 新规则已经批准或适用于比赛 |
| F | [2026 Rules Commission 报告](https://doc.fide.com/docs/DOC/2026_1FC/CM1-202614.pdf) | PDF p.3 | 仍在提出 amendments | 已有 2026 版现行 Laws |
| F | [2022-12-05 Rules Commission 会议纪要](https://rcc.fide.com/wp-content/uploads/2022/12/20221205-minutes-1.pdf) | PDF p.2，item 4 | 当时仍在修正错字、内引和编号；解释为何 2022-11 文件不能作为冻结正文 | 规则本身的完整语义 |
| N | [Chess Equipment regulations，effective 2026-03-01](https://handbook.fide.com/chapter/ChessEquipmentWithoutElectronicComponenets032026) | 标题元数据与器材条款 | 若案例研究实体器材，可确认当前棋盘、棋子、棋钟等竞赛要求 | 棋子的合法移动与胜负条件；它不是 Laws 的替代品 |

### 1.4 可定位的规则问题

以下只是一张“以后去哪里查”的索引，不是机制拆解。

| 研究问题 | 正文定位 | 来源可直接支持的事实 |
|---|---|---|
| 参与者、先后手与目标 | §§1.1–1.5，PDF pp.2–3 | 两名对手；白先；交替行动；将死目标；双方均不可能将死时和棋 |
| 棋盘与初始状态 | §§2.1–2.4，PDF pp.3–4 | 8×8、64 格、棋盘朝向、32 枚初始棋子、初始布置、file／rank／diagonal |
| 通用移动、吃子与“攻击” | §§3.1–3.1.3，PDF p.4 | 不得落到己方棋子格；吃子与移除是同一步的一部分；规则对“攻击格”的定义 |
| 象、车、后、马 | §§3.2–3.6，PDF pp.4–5 | 各棋子的移动关系；长程棋子不得越子 |
| 兵的常规移动与吃子 | §§3.7.1–3.7.3，PDF pp.5–6 | 前进一格、首次可前进两格、斜向吃子及空格前提 |
| 吃过路兵 | §§3.7.3.1–3.7.3.2，PDF p.6 | 对方兵刚从原位前进两格时的特殊吃法；仅紧接的一步有效 |
| 升变 | §§3.7.3.3–3.7.3.5；§§4.4.4、4.6、4.7.3 | 必须在同一步换成同色后／车／象／马；选择不受已被吃棋子限制；新棋子立即生效；实体操作何时固定 |
| 王车易位 | §§3.8.2–3.8.2.2；§§4.4、4.7.2 | 一步涉及王与车；永久失权、暂时受阻条件；王与车依次释放时的物理提交状态 |
| 将军、合法着与非法局面 | §§3.9–3.10，PDF pp.8 | 不得让己王仍受攻击；合法着、非法着和不可由合法序列达到的非法局面 |
| 触子与物理行动 | §§4.1–4.8，PDF pp.8–10 | 单手、调整棋子、触子义务、放手与一步棋已走出（made）的条件 |
| 基本终局 | §§5.1.1–5.2.3，PDF p.10 | 将死、认输、逼和、死局、协议和棋及立即终局 |
| “已走出”与“已完成” | §4.7；§§6.2.1–6.2.2；Glossary 的 made／completed move | 棋盘动作的提交与通常还需按钟的完成是不同事件；立即终局等有例外 |
| 时限与超时 | §§6.1–6.3、6.8–6.10 | 双显示互锁、按钟、预先规定时限、落旗认定、超时结果与故障处理 |
| 非法着的恢复与处罚 | §§7.5.1–7.5.5，PDF p.13 | 按钟后非法着才 completed；恢复局面；未完成升变、空按钟、双手走一步；重复非法着的处罚 |
| 三次重复 | §§9.2–9.2.3 | 需要正确申诉；“同一局面”还取决于行棋方、棋子种类／颜色／格位与可能着法 |
| 历史权利影响局面身份 | §§9.2.3.1–9.2.3.2 | 吃过路兵机会与王车易位权会使视觉上相同的盘面不构成规则上的同一局面 |
| 50 着与 75 着 | §§9.3–9.6 | 50 着为申诉条件；75 着为自动和棋；最后一步将死优先 |
| 计分 | §§10.1–10.2 | 默认胜 1、和 ½、负 0；赛事规程可以另定正常计分体系 |
| 裁判权责与裁量 | §0.2；Article 12 | Laws 不声称覆盖所有情形；裁判在未精确规定处需参考类似规则并运用判断 |

一个后续分析必须保留的规则区别是：

```text
made：棋盘上的一步已经形成
completed：通常还完成了按钟这一竞赛程序
```

这是**来源事实**，不是项目自创术语。它说明同一个日常动词“走一步”在正式规则中可以分成不同的时间槽位；至于如何把它表示为原语和语法，仍是后续的**研究判断**。

### 1.5 版本与文本歧义

1. **现行版不是“2026 版”**。2024—2026 的重写和 amendments 仍是工作材料；核验日的现行规范是 2023 edition。
2. **不要使用旧直链** `https://fide.com/FIDE/handbook/LawsOfChess.pdf`。该 URL 仍可能打开，但内容是 2009 年生效的旧规则。
3. **不要冻结 2022-11 预最终稿** [Laws_of_Chess-2023.pdf](https://rcc.fide.com/wp-content/uploads/2022/11/Laws_of_Chess-2023.pdf)。12 月会议纪要证明它之后还进行过行政校对。
4. **同一官方服务器存在两个 2022-12 PDF 名称**：[当前下载页实际链接的文件](https://rcc.fide.com/wp-content/uploads/2022/12/20230101Laws-of-Chess.pdf) 与 [文件名含 final 的副本](https://rcc.fide.com/wp-content/uploads/2022/12/20230101Laws-of-Chess_final.pdf)。二者不应只凭文件名视作同一字节对象。案例包应保存实际采用的 URL、获取日和文件哈希；本轮以当前下载页所指向的 35 页文件为准。
5. **Congress 编号曾有冲突**。2022-11 的预告写过第 91 届；最终 PDF、Handbook 与 General Assembly 资料均为第 93 届，采用后者。
6. **新闻摘要不能代替条款定位**。2023-01-04 新闻把快速棋处罚和 §12.2.7 混写；正式变更表把快速棋处罚放在 Appendix A.3，而 §12.2.7 是 Fair-Play 措辞。
7. **正文与 Glossary 的旧交叉引用残留**。最终正文把吃过路兵编号为 §§3.7.3.1–.2、升变编号为 §§3.7.3.3–.5；Glossary 的 First Reference 仍出现旧编号。引用规则时以正文编号和条文内容为准。
8. **Guidelines 不是自动生效的 Laws 本体**。官方 Documentation 页面明确区分 Regulations 与 Guidelines；没有被具体案例采用的建议不能悄悄成为规则。
9. **“standard chess”不是一个完整、可复现的时钟配置**。Glossary 只给出每位玩家至少 60 分钟；§6.3.1 仍要求具体时限及附加时间预先规定。

### 1.6 证据缺口

| 维度 | 现有来源能告诉我们什么 | 仍不能告诉我们什么 |
|---|---|---|
| 规则 | 正文的规范要求、终局、申诉、处罚和裁判边界 | 某一赛事的时间控制、迟到时间、协议和棋限制；所有未预见情形的唯一答案 |
| 实现／执行 | Arbiters' Manual 提供官方裁判语境；Laws 规定实体操作和按钟程序 | 某个软件引擎怎样编码规则；现场裁判是否一致执行；只凭棋谱无法还原触子、放手与按钟 |
| 设计意图 | Preface 表明规则选择保留裁判判断空间 | 各条规则为何历史形成、制定者期望何种体验、修改背后的全部取舍 |
| 玩家行为 | Rules 规定允许、禁止和必须做什么 | 开局原则、棋子经验价值、战术／战略、计算深度、紧张感、公平感以及真实申诉频率 |

不能把“完全信息”“零和”“有限状态机”等分析标签写成 FIDE 原话。它们可以是依据规则作出的模型化结论，但必须标为**研究判断**并说明前提。

### 1.7 后续实验与夹具

在完整案例撰写前，优先建立以下可复核材料：

1. 保存当前官方 PDF、获取日期与 SHA-256；不要只依赖可变 URL。
2. 另建赛事配置卡：具体时间控制、增益／延时、迟到时间、协议和棋限制、棋钟型号、记录方式与裁判配置。
3. 为局面夹具保存的不应只有棋盘图；至少还要有行棋方、易位权、吃过路兵机会、无兵移动／无吃子计数、重复历史、双方时钟、非法着次数、触子／放手／按钟阶段和申诉状态。
4. 实体演示普通着的 `made` 与 `completed`，以及将死一步未按钟便立即终局的例外。
5. 演示易位的中间态：王已释放、车尚未释放时，规则义务如何变化。
6. 用王／车移动后回原位的局面测试“盘面相同”与“规则状态相同”的区别。
7. 测试吃过路兵仅在紧接一步有效、四种升变及升变即时能力。
8. 测试未换升变棋子便按钟、空按钟、双手完成一步，以及首次／第二次 completed illegal move。
9. 成对比较三次／五次重复、50／75 着的“申诉触发”与“自动触发”；另测第 75 着同时将死时的优先级。
10. 测试超时或认输时“对手无法以任何合法序列将死”的和棋例外。
11. 若制作规则检查器，用上述夹具验证它与条款的一致性；检查器通过测试只能证明该实现满足所选样例，不能反过来证明 Laws 已被完全形式化。
12. 若研究真实行为，必须另采录像、裁判记录或受控实验；最终棋谱不足以重建触子和按钟过程。

---

## 2. 对象 A2：1989 Game Boy《Tetris》单人 A-Type

### 2.1 范围卡

这个对象不能只写成“经典俄罗斯方块”。同名作品、地区 ROM、修订、模式、硬件和现代发行包装都会改变可观察行为。

| 字段 | 本轮冻结值 | 性质 |
|---|---|---|
| 作品 | Nintendo Game Boy 版 *Tetris*，1989 | **来源事实**：1989 年 Nintendo of America 说明书；Nintendo 当前经典游戏页列作 1989 |
| 消费者地区／语言 | 北美英语制品语境，以 Nintendo of America 英文说明书为规则面材料 | **研究判断**，由说明书出版者与文本语言限定 |
| 目标卡带标签 | `DMG-TR-USA` | **研究判断**；保存数据库把该标签列入 World Rev 1 组，但本轮尚无自有卡带 dump 链 |
| 目标程序修订 | `DMG-TRA-1` / World Rev 1，32 KiB，SHA-1 `74591cc9501af93873f9a5d3eb12da12c0723bbc` | **M 级测量事实**；不是 Nintendo 发布的官方哈希 |
| 模式 | 1-player、A-Type | **来源事实／研究判断**：说明书定义该模式；本项目选择它作为案例 |
| 起始设置 | Level 0、正常速度、NEXT 显示开启 | **研究判断**，用于建立统一基线；不是“所有玩家的默认玩法”主张 |
| 音乐 | 暂不作为规则冻结条件；涉及节奏或危险反馈时必须把 A／B／C／OFF 单独记录 | **研究判断** |
| 基准硬件 | 原始 DMG-01 Game Boy；实机合法 dump 为最终复现实验基准 | **研究判断** |
| 可接受辅助实现 | 固定 commit 的可重建反汇编；经过独立校验的高精度模拟器 | **研究判断**，不得冒充官方实现 |
| 排除 | B-Type、2-player、日本 Rev 0、NES *Tetris*、*Tetris DX*、隐藏 heart 高速模式、3DS VC／Nintendo Switch Online 包装功能、后来的 Tetris Guideline | **排除项** |
| 具体 play session | 暂无；本文件冻结制品、模式与实验基线 | **研究判断** |

需要特别保留一条限制：

> **研究范围已经锁到北美英语语境与 World Rev 1，但“某一枚 `DMG-TR-USA` 卡带 → 上述哈希”的自有证据链尚未完成。**

保存数据库的详细 dump 样本来自 `DMG-TR-FAH` 卡带；数据库把多个 `DMG-TR-USA` 实物条目归在同一 `DMG-TRA-1 / World Rev 1` 组。这足以形成高可信候选身份，但正式案例仍应对自有或获授权的北美卡带合法 dump 并校验哈希。

### 2.2 来源矩阵

| 级别 | 来源、版本／日期与 URL | 定位 | 可以支持 | 不能支持 |
|---|---|---|---|---|
| A | [Nintendo of America《Tetris》Game Boy Instruction Booklet 扫描](https://www.videogamemanual.com/gameboy/Tetris%20%28USA%29.pdf)，©1989，20 页 | PDF p.2 版权；pp.3–7 规则、控制与 A-Type；pp.14–16 消行、选项与计分 | 同时代第一方对玩家公开的规则、目标、控制、模式、显示项、得分和可选功能 | CPU 级实现、精确帧数、随机算法、完整边界情况；当前托管方不是 Nintendo，需保留这一溯源限制 |
| A/M | [The Strong 馆藏中的说明书对象记录](https://artsandculture.google.com/asset/instruction-booklet-nintendo-game-boy-tetris-instruction-booklet-nintendo/0AGPujAxJh-jcA?hl=en)，object ID 109.12983 | 对象元数据 | Nintendo、1989、纸质 instruction booklet 的制品身份旁证 | 扫描正文的每项规则；ROM 版本；程序行为 |
| F | [Nintendo UK：TETRIS / Game Boy](https://www.nintendo.com/en-gb/Games/Game-Boy/TETRIS--275924.html) | 产品描述，尤其 A-Type／B-Type 段；页面标明 description provided by publisher | 发行方对两个主要模式的概述；A-Type 是不断消行、速度提高并追求高分的 endurance game | 1989 原始二进制、精确时序、地区修订差异；该页形成于 3DS Virtual Console 发行语境 |
| F | [Nintendo：Game Boy – Nintendo Classics](https://www.nintendo.com/us/store/products/game-boy-nintendo-classics-switch/) | Tetris 条目“1989”；Suspend Points、Rewind、screen styles | Nintendo 当前把 Game Boy *Tetris*列为 1989 作品；现代包装额外提供暂停点、倒带与显示样式 | 这些包装功能属于 1989 原版；NSO 的时序与原始 DMG-01 必然一致 |
| F | [The Tetris Company：The History of Tetris](https://tetris.com/news/the-history-of-tetris) | 1989 与 1996 时间线 | 掌机权利授予 Nintendo、Game Boy 与 Tetris 在 1989 年结合；Tetris Guidelines 在 1996 年形成 | Game Boy Rev 1 的逐帧行为、随机器、锁定规则；开发者为何采用某一实现 |
| M | [Game Boy hardware database：Tetris (World) (Rev 1)](https://gbhwdb.gekkio.fi/cartridges/DMG-TRA-1/) | Variants 与多个实物条目；包括 `DMG-TR-USA` | 保存者对卡带标签、PCB、ROM 芯片和组别关系的直接记录；区分 `DMG-TRA-0` 与 `DMG-TRA-1` | Nintendo 官方版本命名政策；每个地区卡带绝无不同；设计意图 |
| M | [详细实体与 dump 记录：DMG-TRA-1 / 3615Retro #1](https://gbhwdb.gekkio.fi/cartridges/DMG-TRA-1/3615retro-1.html)，dumped 2024-10-24 | Board、Parts、ROM dump 与 log | 32 KiB、无 mapper、无 SRAM、Revision 1、World/English、CRC/MD5/SHA-1/SHA-256，以及采集工具与日志 | 该具体样本是北美 `DMG-TR-USA`；Nintendo 官方认可这些哈希；游戏设计理由 |
| R | [kaspermeerts/tetris 固定 commit `b95c668…`](https://github.com/kaspermeerts/tetris/tree/b95c66859339f5523e80213de5857eefc1c7703f)；[README](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/README.md)；[`rom.sha1`](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/rom.sha1)；[`Makefile`](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/Makefile) | README 的目标 ROM 与完整性说明；构建脚本与哈希清单 | 在合法持有目标 ROM、构建成功且输出哈希一致时，提供可定位的程序表示；README 明说反汇编完整但并非所有 routine 已文档化 | 官方源代码、符号名与注释的历史真实性、开发者意图；没有重建和实机验证时不能把注释直接当事实 |

ROM 身份的保存测量值：

```text
Size:    32768 bytes (32 KiB)
CRC-32:  46df91ad
MD5:     982ed5d2b12a0377eb14bcdc4123744e
SHA-1:   74591cc9501af93873f9a5d3eb12da12c0723bbc
SHA-256: 0d6535aef23969c7e5af2b077acaddb4a445b3d0df7bf34c8acef07b51b015c3
Header:  TETRIS / Revision 1 / Game Boy / no SRAM / no mapper
```

这些是**M 级保存测量事实**，不是 Nintendo 公布的校验值。项目不保存或分发 ROM；复现者需自行合法取得制品并生成 dump。

### 2.3 说明书定位

| 研究问题 | 说明书定位 | 第一方制品直接陈述的事实 |
|---|---|---|
| 制品身份 | PDF p.2 | Nintendo Game Boy Tetris Game Pak；©1989 Nintendo of America Inc. |
| 基本对象与目标 | p.3，“What is Tetris?” | 七种四格形状依次下落；可左右移动和旋转；完整横行消失并得分；堆到顶部则结束 |
| 模式边界 | p.3 | endurance game A、以第 25 行为终点的 game B、2-player |
| 输入 | p.4 | 左右移动、下方向加速下落、A 顺时针旋转、B 逆时针旋转 |
| 选择流程 | p.6 | 1-player 中选择 A-Type／B-Type、音乐和 LEVEL；HIGH 只用于 B-Type |
| A-Type | p.7 | 目标是尽可能多消行并取得高分；LEVEL 越高下落越快；过程中 LEVEL 逐渐增加；堆到顶部结束 |
| 可见反馈 | p.7 | SCORE、LEVEL、LINES、NEXT、FIELD 的显示意义 |
| 消行与下落 | p.14 | 无空隙完整行消失；剩余方块下降一行；一次完成 2／3／4 行得分更高 |
| 其他操作 | p.15 | START 暂停；组合键重置；SELECT 开关 NEXT；标题画面可进入更快的隐藏模式 |
| 计分 | p.16 | 软降高度影响 drop points；Single／Double／Triple／Tetris 分值随 level 变化；表格等价于基础值 40／100／300／1200 × (level + 1) |

**边界提醒**：说明书是面向玩家的操作契约，不是完整形式规范。它没有规定逐帧重力、输入采样、自动横移、出生位置、旋转碰撞回退、锁定时机、随机器或所有 top-out 边界。

### 2.4 可复现实装定位

下表中的链接固定到 commit `b95c66859339f5523e80213de5857eefc1c7703f`。符号名与自然语言注释由逆向工程者添加，只有汇编指令及重建后的哈希对应关系可以进入实装证据链。

| 实装问题 | 固定代码定位 | 从指令可提出的可检验事实／假设 |
|---|---|---|
| 每帧主顺序 | [`tetris.asm` L4405–L4421](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L4405-L4421) | 常规 gameplay state 依次调用暂停／演示、旋转与横移、下落、满行检查、锁入背景、消行后下移、加分等 routine |
| 重力表 | [L4240–L4283](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L4240-L4283) | level 0–20 的 frames-per-drop 表为 52, 48, 44, 40, 36, 32, 27, 21, 16, 10, 9, 8, 7, 6, 5, 5, 4, 4, 3, 3, 2；heart mode 会改索引 |
| 消行得分 | [L4992–L5037](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L4992-L5037) | A-Type 路径选择 40／100／300／1200，并重复累加 level+1 次，与说明书表一致 |
| 场地高度线索 | [L5039–L5047](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L5039-L5047) | 场地填充 routine 的计数为 18 行；需与内存布局和画面实验共同确认 |
| 下一块与随机候选 | [L5078–L5164](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L5078-L5164) | 预览块变为活动块；候选读取 `rDIV`，经映射与有限次数重试后接受；注释中的分布解释仍须独立验证 |
| 软降、重力与接触 | [L5167–L5264](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L5167-L5264) | 软降计时、drop counter、重力计时、碰撞后回退及锁定流程起点可被逐帧测试 |
| 满行检测 | [L5301–L5355](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L5301-L5355) | 每行检查 10 格；循环从场地第三行地址开始并检查 16 行；“顶部两行不能消除”是强实装假设，仍应在目标 ROM 上验证 |
| 消行后下移 | [L5498–L5550](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L5498-L5550) | 每个被清行之上的内容按 10 格宽向下复制，随后清空顶行 |
| 旋转与碰撞回退 | [L5910–L5963](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L5910-L5963) | A／B 选择相反旋转方向；旋转后检测碰撞，失败时恢复原 orientation |
| 碰撞与锁入场地 | [L6030–L6107](https://github.com/kaspermeerts/tetris/blob/b95c66859339f5523e80213de5857eefc1c7703f/tetris.asm#L6030-L6107) | 非空背景格构成碰撞；锁定 routine 把四个活动块写入背景，并推进锁定状态 |

**研究判断**：这组代码定位足以形成实验问题，却不足以直接宣布“游戏的机制就是这些 routine”。routine 是实现分块；机制边界仍需由玩家可调用行动、前提、状态变化、时序和反馈共同论证。

### 2.5 版本与实现歧义

1. **Game Boy *Tetris* 不是 NES *Tetris***。Nintendo 当前经典游戏页同时收录多个版本，不可因标题相同而混用规则、速度表或随机器。
2. **`DMG-TRA-0` 与 `DMG-TRA-1` 并存**。保存数据库分别列出 Japan Rev 0 与 World Rev 1；现有第一方资料没有给出完整行为差异表。
3. **外壳标签不等于已经验证的 ROM 字节**。`DMG-TR-USA` 是发行标签；`DMG-TRA-1` 是 ROM 标识。当前详细 hash 样本来自 FAH 卡带，仍需北美实物 dump 补齐链条。
4. **说明书也可能存在印刷／包装修订**。当前扫描可确认文本与 ©1989，但尚未记录印刷代码、纸本来源链和文件哈希；引用时必须保留扫描 URL 与页码。
5. **A-Type 仍有可配置状态**。起始 level 0–9、NEXT 开关、音乐选择与隐藏 heart 高速模式都会改变信息或节奏；不记录设置就无法精确复现。
6. **原始硬件与后续兼容硬件／模拟器不是同一执行语境**。DMG-01、Game Boy Pocket、Game Boy Color、GBA、3DS VC 与 Nintendo Switch Online 至少在显示、输入包装或系统功能上不同；时序是否等价需测量。
7. **NSO 的 Suspend Points、Rewind 与 screen styles 是现代包装功能**。它们必须从 1989 基线排除，除非研究问题专门比较版本。
8. **1996 年形成的 Tetris Guidelines 不能倒投到 1989 实现**。现代术语和通行实现习惯不能自动证明 Rev 1 已采用相同规则。
9. **社区反汇编不是官方源码**。符号名、`TODO`、“bug”与意图说明是逆向工程者注释；只有目标哈希重建成功后，汇编指令与观测结果才可作为实现证据使用。

### 2.6 证据缺口

| 维度 | 现有来源能告诉我们什么 | 仍不能告诉我们什么 |
|---|---|---|
| 规则 | 说明书给出目标、输入、A-Type 进程、消行、结束、NEXT 与得分 | 精确出生／锁定／top-out 条件、逐帧时序、输入优先级、自动横移、随机器、level 提升阈值和全部异常情况 |
| 实现 | 保存 dump 给出候选 ROM 身份；固定反汇编提供可重建、可定位的指令表示 | Nintendo 官方源代码；北美目标卡带的自有 hash 链；反汇编是否在本项目环境成功重建；实机与模拟器是否逐帧一致 |
| 设计意图 | 说明书把 A-Type 描述为 endurance／high-score，并提供“Technique” | Game Boy 移植者为何选择这些速度、随机器、场地高度和反馈；说明书营销措辞不等于开发者意图 |
| 玩家行为 | 说明书给出推荐技巧，程序含演示数据／流程线索 | 玩家实际如何堆叠、何时冒险、怎样学习；推荐技巧和脚本演示都不是行为观察 |

当前没有找到可同时满足“第一方、针对 1989 Game Boy 移植、明确讨论具体实现取舍”的开发者访谈。这个空白应保留，不应由后来的 Tetris 通用历史材料补写。

### 2.7 后续实验与夹具

1. 对目标 `DMG-TR-USA` 卡带进行合法 dump，保存卡带正反面、PCB、ROM 芯片、工具版本、完整日志与 SHA-256；确认是否匹配本文件的 World Rev 1 候选哈希。
2. 在隔离环境固定反汇编 commit、RGBDS 版本与构建命令；确认重建输出与 SHA-1／SHA-256 完全一致，再引用代码行为。
3. 以 DMG-01 实机为基准，在高精度模拟器录制同一输入脚本；比较逐帧下落、输入响应、消行和锁定节奏。
4. 实测 level 0–20 的自然重力，与 `FramesPerDropTable` 对照；heart mode 单独测试，不混入基线。
5. 测量左／右按住后的首次移动、延迟与重复率；测试同帧左／右／下／A／B 组合时的输入优先级。
6. 测试软降速度、drop points 的起算／中断／落地条件，以及说明书“按下落高度计分”的边界。
7. 以受控启动和输入时序记录长序列，复核 `rDIV` 候选、重试条件与实际七种块分布；不得只采用逆向注释给出的随机器解释。
8. 建立七种块的出生位置、初始 orientation、A／B 旋转序列、墙边／堆叠碰撞与失败回退夹具。
9. 测量第一次接触地面到锁入背景的准确帧序，以及接触期间横移／旋转是否仍可能；把“锁定”与“出生下一块”分开记录。
10. 测试 top-out：出生即碰撞、锁定后触顶、部分块位于顶部、顶部两行参与／不参与消行等边界。
11. 逐一验证 Single／Double／Triple／Tetris、soft-drop points、level 变化与分数显示；对照说明书表与汇编路径。
12. 验证 10×18 场地、满行检测范围、清行顺序、剩余内容下移与多行同时清除；特别复核代码显示的顶部两行边界。
13. 分别记录 NEXT 开／关、Pause、Reset、普通／heart 模式；这些是独立配置，不应聚合成一个模糊的“A-Type”。
14. 若研究声音／视觉反馈，分别测试音乐 A／B／C／OFF、危险状态音乐变化、DMG LCD 残影与不同显示包装；这些属于感知条件，不是纯规则文本。
15. 只把 3DS VC／NSO 作为独立实现比较；Suspend、Rewind 或 screen style 不得进入 1989 基线。
16. 玩家策略、学习曲线和体验需要另行招募、录像和编码；程序 trace 只能描述系统发生了什么，不能代替玩家为何如此行动。

---

## 3. 跨对象的校准门结论

### 3.1 来源事实

- FIDE 案例有制定机构维护的规范文本，但规范明确保留现场裁量，并把赛事配置放到 Laws 之外。
- Game Boy *Tetris* 有同时代玩家说明书，却没有公开的 Nintendo 官方源码；精确行为必须借助实体测量、固定 ROM、可重建反汇编与实验。
- 因而，“规则文本充分”与“程序行为可观察”是两种不同的证据优势，不能用同一套材料标准假装完全对称。

### 3.2 研究判断

这对案例适合校准《游戏原语》的方法，不是因为二者都“简单”，而是因为它们迫使模型同时处理：

```text
规范规则 ≠ 实体执行 ≠ 程序实现 ≠ 设计意图 ≠ 玩家行为
```

后续机制分析若无法指出一个结论属于上述哪一层，就不应进入稳定术语库。

### 3.3 进入完整案例前的通过条件

- [ ] 两个对象均保留不可变版本身份：FIDE PDF 的本地哈希；目标 Game Boy 卡带的合法 dump、日志与哈希。
- [ ] 每条规则／实装主张都能回到条款、页码、固定 commit 行号或实验记录。
- [ ] 不用规则书推断玩家心理，不用程序指令推断开发者意图，不用说明书补写缺失的逐帧算法。
- [ ] FIDE 的具体时间控制与 Tetris 的起始 level／NEXT／heart mode／硬件条件写入实验配置。
- [ ] 至少完成一组“正常路径”和一组“边界路径”夹具，确认当前原语与语法表示不会只适配理想流程。

满足这些条件后，才适合分别撰写案例中的原语候选、槽位语法、规则句、机制边界与运行循环；本资料包本身不提前给出这些结论。
