# 案例目录

这里保存原语、机制、玩法模板和完整游戏的结构化分析。案例不是为了给作品贴唯一标签，而是为了检验理论能否解释差异、变体和反例。

## 记录格式

完整游戏与跨层案例采用[案例研究包模板 v0.3](CASE-PACKET-TEMPLATE.md)。模板同时支持速查、标准和深度三档，并区分可追溯的教学最小视图与研究充分视图：范围与规则事实始终必填，编排和玩家层按研究深度展开，完整证据账本、反例与设计变体只在深度案例中强制要求。v0.3 还按需记录来源语域、资源准入、观察后效、决策锁定、术语族，以及相互独立的结构校准与行为证据状态。

单独的原语候选、机制条目或玩法模板条目可以使用较短的专用格式，但必须至少说明：

- 规范名称、别名与英文名；
- 概念层级与分析尺度；
- 操作性定义和结构，而非相关词列表；
- 前置、输入、过程、效果、时间、信息与组合关系中适用的部分；
- 典型实例、边界反例、来源和开放问题。

同一个名称在不同分析尺度下可能指向不同对象。记录时必须写明尺度，不以目录位置代替论证。

## 第一轮校准案例

- [国际象棋：FIDE 桌面标准棋](cases/chess-fide-standard.md)（深度；校准门 A 已通过）
- [《俄罗斯方块》：Game Boy A-Type](cases/tetris-game-boy-a-type.md)（深度；校准门 A 已通过）
- 两案的已接受对照结论见[校准门 A 报告](../research/calibration-gates/gate-a-chess-tetris.md)。
- [无限注德州扑克：2026 WSOP Event #65](cases/holdem-wsop-2026-event-65.md)（深度；校准门 B 结构通过）
- [《农场主》：2016 英文修订版四人基础游戏](cases/agricola-revised-2016-four-player.md)（深度；校准门 B 结构通过）
- 两案的观察证据边界与已接受修订见[校准门 B 报告](../research/calibration-gates/gate-b-holdem-agricola.md)。
- [数独：Nikoli 标准 9×9 规则](cases/sudoku-nikoli-standard-9x9.md)（标准；结构通过，具体题面与行为证据待补）
- [《花火》：R&R Games 标准卡牌版四人五色基础局](cases/hanabi-rr-2013-four-player-five-color.md)（标准；结构通过，实体印次与行为证据待补）
- 两案共用的版本边界、术语映射与信息对照见[一手来源冻结包](../research/sources/calibration-sudoku-hanabi-primary-sources.md)。
- [《Dominion》：第二版二人 `First Game` 王国](cases/dominion-second-edition-first-game-two-player.md)（标准；结构通过，具体牌序与行为证据待补）
- [《Factorio》：2.0.77 基础游戏自由模式](cases/factorio-2.0.77-base-freeplay.md)（标准；结构通过，运行制品、工厂实例、测量与行为证据待补）
- 两案共用的版本、地图夹具、来源术语、资源／集合边界与反馈对照见[一手来源冻结包](../research/sources/calibration-dominion-factorio-primary-sources.md)。
- [《星际争霸：母巢之战》：1.23.10.13515 `(2) Eldritch Lake` 二人 `Melee`](cases/starcraft-brood-war-1.23.10-eldritch-lake-1v1.md)（标准；结构通过，客户端二进制、实机轨迹与行为证据待补）
- [《外交》：Hasbro 第四版七人标准局](cases/diplomacy-fourth-edition-seven-player-standard.md)（标准；结构通过，实体地图、具体命令批次与行为证据待补）
- 两案共用的清单／规则制品、命令生命周期、同时性、信息隐藏和容量结构对照见[一手来源冻结包](../research/sources/calibration-starcraft-diplomacy-primary-sources.md)。
