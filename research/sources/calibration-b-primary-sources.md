# 第一轮校准门 B：一手资料与版本冻结

> 状态：研究资料包，不是完整案例，也不是定稿章节
> 核验日期：2026-07-21
> 对象：2026 WSOP Event #65 Freezeout 无限注德州扑克；2016 英文版 *Agricola Revised Edition* 四人基础游戏
> 目的：冻结两个可复核的规则对象，为后续比较“隐藏信息与下注”和“工人放置与多系统编排”提供证据；本文不提前给出原语、机制或体验结论。

## 0. 证据约定

本文显式区分以下内容：

- **来源事实**：固定版本的一手资料直接陈述的内容。
- **研究判断**：本项目为控制案例边界所作的选择，不冒充来源原话。
- **项目夹具**：为使实验可复现而额外指定的合法状态或参数；它不自动属于现实赛事／产品规则。
- **待证问题**：当前材料不能唯一回答，不能用常识补齐。
- **排除项**：本轮明确不纳入的规则、扩展、变体或分析层次。

来源地位如下：

| 级别 | 含义 | 本文用法 |
|---|---|---|
| N1 | 直接管辖本案例的官方规则或赛事结构 | 决定本轮对象实际采用什么规则 |
| N2 | 被 N1 明文纳入的次级规则 | 仅在 N1 指定的范围和优先级下补缺 |
| F | 权利方／主办方发布的产品、赛程或结果资料 | 确认版本、组件与事件身份，不取代规范正文 |
| C | 外部规范性参照 | 用于比较冲突和可选方案；没有被采用时不得混入案例 |
| P | 项目自行冻结的实验参数 | 用于复现；必须标明不是官方事实 |

这里特别避免一种常见做法：从多个“看起来都很标准”的规则集中各取一条，拼成一个并不存在的通用规则。若官方语料仍有空白，本文保留空白，或把补充内容明确标作 **P 级项目夹具**。

---

## 1. 对象 B1：2026 WSOP Event #65 Freezeout 无限注德州扑克

### 1.1 三种冻结方案的比较

| 方案 | 优点 | 无法直接解决的问题 | 本轮结论 |
|---|---|---|---|
| **2026 WSOP Event #65**：$1,500 Freezeout NLHE | 标题明确 Freezeout；没有 re-entry、赏金或混合牌种；结构表明确起始筹码、时长、盲注与大盲前注 | 结构表没有标明桌型；通用规则允许桌数和座位容量因运营需要调整 | **采用**，作为较少赛事外层变量的现实规则对象 |
| **2026 WSOP Event #94**：$10,000 6-Handed NLHE Championship | 赛事标题明确六人桌；结构也完整 | Championship 的参赛层与本轮核心手牌机制无关；同样存在普通牌组／牌型和现场裁量缺口 | 不采用；保留为固定桌型的后续对照 |
| **2024 Poker TDA + 项目赛事参数** | 条款结构清楚，便于搭建教学模拟 | TDA 自称补充各 house 的规则，并承认监管规则优先；没有给出一个具体赛事结构，也没有完整定义 NLHE 基础游戏 | 仅作 **C 级比较**，不与 WSOP 混用 |

**研究判断**：首个下注案例先采用 Event #65，是为了减少 re-entry、赏金、混合牌种和特殊资格等赛事外层变量。代价是官方材料没有锁定桌上人数。本文保留这一缺口：后续每个具体手牌把“实际被发牌人数”作为观察／实验参数记录，不从“Freezeout”或常见 WSOP 桌制推断一个数字。

### 1.2 范围卡

| 字段 | 本轮冻结值 | 性质 |
|---|---|---|
| 案例标识 | `NLH-WSOP26-E65-L1-TABLE-TBD` | **项目夹具** |
| 赛事 | 2026 World Series of Poker，Event #65 | **来源事实** |
| 游戏／桌型 | $1,500 Freezeout No-Limit Hold’em；赛事桌型未在结构表明示 | 前半为**来源事实**，后半为**待证问题**；结构表 PDF p.75 |
| 地点与规则期 | Horseshoe／Paris Las Vegas；2026 WSOP | **来源事实** |
| 赛事结果状态 | 2,617 entries；Ciro Gonzalez 获胜 | **来源事实**，官方赛事页；仅确认事件身份，不用于机制推断 |
| 参赛次数 | Freezeout；不允许淘汰后重新参赛 | **来源事实**，结构表标题及 Rules 2、13 |
| 起始筹码 | 每名参赛者 25,000 | **来源事实**，结构表 PDF p.75 |
| 级别时长 | Day 1 每级 40 分钟；Days 2–3 每级 60 分钟 | **来源事实** |
| 首级强制下注 | BB ante 100；small blind 100；big blind 100 | **来源事实** |
| 首手实验状态 | Level 1、每名新参赛者起始 25,000；具体被发牌人数、座次与按钮待观察／配置 | **来源事实＋待配置**；不预填桌人数 |
| 按钮与座次 | 按 Rules 34、65、85 分配；具体桌号、座位、实体 dealer 位置和按钮座位仍须写入每个实验记录 | **来源事实＋待配置** |
| 规则层级 | Event #65 structure → 2026 WSOP Official Tournament Rules → 未覆盖时才查 2026 WSOP Live-Action and House Rules → 仍未覆盖时由 Rule 51 裁决 | **来源事实**，Rule 129 |
| 纳入 | 常规高牌 NLHE；按钮、盲注、BBA、下注、全下、边池、摊牌和赛事级别变化 | **研究判断** |
| 排除 | Short Deck、PLO、现金桌 straddle、run it twice、赏金、shot clock（结构表未规定）、TDA RP、线上实现与 re-entry | **排除项** |
| 行为／体验 | 不从规则书推断诈唬频率、范围、GTO、心理压力或观赏性 | **排除项**；这些需要牌谱、录像或实验 |

保存的规范身份：

```text
2026 WSOP Official Tournament Rules
41 pages
SHA-256 EC87C297C9C99BF7C320AD34DDC57E80259782A7785BD5218151EEFAE742AD14

2026 WSOP Bracelet Structures All-In-One
116 pages
Event #65 on PDF p.75
SHA-256 0E92BD62B25A174EF1F2FBE7EDFBA79CD30B2E097A40324B7529E6F5209DACAD

2026 WSOP Official Live Action Rules
31 pages
SHA-256 BD291AD3A639742736499D06841FF2BAC496508F081E1A3C5B12BBA73BFC2F06
```

哈希是本项目在 2026-07-21 对当前官方 URL 下载文件的测量值，不是 WSOP 公布的校验值。

### 1.3 来源矩阵

| 级别 | 来源、版本与 URL | 定位 | 可以支持 | 不能支持 |
|---|---|---|---|---|
| N1 | [2026 WSOP Official Tournament Rules](https://assets.wsopcdn.com/wsop/1a72ba28-781c-409d-a9c3-5ca13c4c5718.pdf)，41 页 | Rules 2、13、34、51、68–75、79、85–105、129；Sections VIII–IX；Glossary | 赛事通用程序、下注、摊牌、边池、NLHE 发牌流程及规则层级 | 所有现场问题都有纯算法答案；标准牌型的完整定义；玩家策略 |
| N1 | [2026 WSOP Bracelet Structures All-In-One](https://assets.wsopcdn.com/wsop/449960d6-f34d-406d-8424-ff84f5ae51c3.pdf)，116 页 | Event #65，PDF p.75 | Freezeout、起始筹码、级别时长、盲注／BBA 结构 | 赛事桌型、每手实际座位、牌序、筹码面额 |
| N2 | [2026 WSOP Official Live Action Rules](https://assets.wsopcdn.com/wsop/853ee602-e1e9-4019-a0cf-381419d805c6.pdf)，31 页 | General Rule 14；Rules 143–157；Texas Hold’em，PDF pp.12–14 | Tournament Rule 129 指定的次级补缺资料；按钮／盲注、摊牌请求、常规 Hold’em 与异常流程 | 把现金桌 straddle、run it twice 等规则自动带入赛事；覆盖 N1 |
| F | [2026 WSOP 赛事页](https://www.wsop.com/tournaments/2026-57th-annual-world-series-of-poker/) | Event #65 条目与结果入口 | 赛事确实举行、参赛数与获胜者 | 逐手规则、实际牌序、玩家为什么采取某行动 |
| C | [Poker TDA 2024 Rules v1.0 longform](https://www.pokertda.com/view-poker-tda-rules/)，2024-10-09；[下载说明页](https://www.pokertda.com/poker-tda-rules/) | Rules 1、16–21、23、32、40–57；RP-11；Illustration Addendum 序言 | 行业程序的对照、规则冲突、另一种 BBA 处理建议 | WSOP 已经采用这些规则；一个无需 house rules 的完整 NLHE 游戏 |

**文本身份提醒**：2026 Live-Action PDF 的浏览器／PDF 标题可能仍显示 “2010”，但文件页眉和正文明确写有 “2026 World Series of Poker Official Live Action Rules”。冻结时应使用 URL、页数、正文年份和哈希共同识别，不能只信元数据标题。

### 1.4 可定位的关键规则

| 研究问题 | 官方定位 | 来源可直接支持的事实 |
|---|---|---|
| 参赛与 re-entry | Tournament Rules 2、13，PDF pp.1、5；Event #65 p.75 | 只有具体结构表指定才可 re-entry；#65 标题明确 Freezeout |
| 桌上人数 | Rule 34，PDF p.8；Section IX “Flop Games”，p.29；Event #65 p.75 | 通用 flop games 可有 2–10 人，运营方还保留临时增座权；这些只是许可范围，#65 的结构表没有给出其赛事桌型 |
| 按钮与 heads-up | Rules 85、87，PDF p.19 | 初始按钮位置、dead button；heads-up 时小盲在按钮，翻牌前先行动、以后最后行动 |
| 新级别何时生效 | Rule 79，PDF p.18 | 新级别适用于下一手；“一手开始”的边界由首次 riffle 或自动洗牌机按钮定义 |
| 常规 Hold’em 时序 | Section IX.1，PDF p.29 | 每人两张暗牌；preflop、flop、turn、river 四轮下注；每条公共牌街前烧一张；从暗牌与牌面任选五张，也可全用牌面 |
| 行动起点 | Section IX “Flop Games”，PDF p.29；Live-Action “Button and Blind Use”，PDF pp.11–12 | 首张牌发给按钮左侧；两盲时翻牌前由大盲左侧开始，以后由按钮左侧首位仍在手中的玩家开始 |
| 无限注边界 | Section VIII “No-Limit”，PDF p.29；Rules 95–96，p.22 | 最低下注等于大盲；最高为面前全部筹码；加注至少等于本轮上一次完整 bet／raise 的增量；不足完整加注的 all-in 通常不重新开放加注权 |
| 下注表达 | Rules 90–99，PDF pp.20–23 | 口头与筹码动作、call、raise、under-call、单枚大额筹码、多筹码及 string raise 的解释规则 |
| 全下和边池 | Rules 70、74，PDF pp.17–18；Glossary “ALL-IN”“POT (SIDE POT)”，pp.35、39 | 所有下注结束且有人 all-in 时亮牌；玩家只能赢得其有资格争夺的金额；每个边池独立结算 |
| 摊牌与牌面 | Rules 69–75，PDF pp.17–18 | cards speak；最后一轮最后主动下注者先亮；无人下注则应先行动者先亮；共同牌成手也须亮出全部暗牌；奇数筹码有位置规则 |
| 未覆盖情形 | Rules 51、129，PDF pp.12、28 | 先查 Tournament Rules，再查 WSOP Live-Action and House rules，仍无规则则由主办方按赛事最佳利益与完整性裁决 |

### 1.5 为什么不采用 “TDA + 零散常识”

TDA 是有价值的比较规范，但其官方 Illustration Addendum 明说：TDA Rules **补充**具体 house 的规则，发生冲突时监管规则优先。因此它不是一个无需配置即可运行的完整扑克游戏。它也没有为本案例指定赛事、桌型、起始筹码、盲注表或普通高牌型定义。

至少存在两处不能静默合并的差异：

| 问题 | 2026 WSOP | 2024 TDA | 本轮处理 |
|---|---|---|---|
| 要求查看对手已弃暗牌 | Tournament Rule 129 引入的 Live-Action Rule 14／147：只有怀疑串通且 floor 在场才可请求 | Rule 18B：河牌跟注者在保留／亮出自己牌时，有不可剥夺的权利要求最后进攻者亮牌 | 采用 WSOP；TDA 条款不进入本案例 |
| 大盲前注遇到短筹码时的扣除顺序 | #65 结构给出 BBA 数额，但当前 Tournament Rules 未找到 “big-blind-first” 的明确计算条款 | RP-11 推荐 BBA 且按 big blind first 计算；但 RP 是 policy suggestion，不是通用 Rule | 记录为 WSOP 证据缺口；不把 RP-11 冒充 WSOP 规则 |

另外，Live-Action Rules 允许现金桌 straddle 和某些 run-it-more-than-once 处理；Rule 129 只让其在 Tournament Rules 未覆盖时补缺，并不把所有现金桌选项变成赛事选项。

### 1.6 文本陷阱与证据缺口

1. **Short Deck 的牌型表不是普通 Hold’em 牌型表。** Tournament Rules PDF pp.29–30 的 36 张牌、`Flush > Full House` 和 button ante 段落位于 Short Deck 小节；不得倒灌到 Event #65。
2. **普通牌组没有被完全枚举。** 当前三份 WSOP 文档能推知不使用 joker、同花色同点数重复牌会使牌组 fouled，但没有找到一段明确枚举标准 52 张牌的规范正文。
3. **普通高牌型没有完整的规范定义。** 文档多次写 “best five-card poker hand” 和 cards speak，却没有在普通 NLHE 小节逐级定义 high card 至 royal／straight flush 及同类牌型的逐项比较。Short Deck 和其他变体的表不能代替它。
4. **BBA 的短筹码优先级未锁定。** 结构表能确定 Level 1 的 BBA=100，却不能唯一回答大盲只剩少于 ante+blind 时先扣哪一项。
5. **Event #65 的桌上人数没有冻结。** 通用规则给出的 2–10 人许可范围不能证明赛事以几人桌开始；淘汰、迟到、平衡和临时增座还会改变逐手人数。后续只能记录观察到或实验指定的 `dealt-in count`。
6. **洗牌没有可复现算法。** 实体赛事追求不可预测和公正，不会公布可重放的 PRNG；若做模拟，必须另定牌组输入顺序、洗牌算法和种子，并标作 P 级。
7. **筹码面额未在 #65 结构表中冻结。** 起始总值和后续 color-up 级别已知，但仅靠结构表不能重建每名玩家拿到哪些实体面额。
8. **规则明确保留裁量。** Rule 51、下注歧义条款和可识别弃牌的追回等，都不能被诚实地改写成一个永远唯一输出的纯函数。

所以，本轮已经冻结了一个**可引用的现实规则对象**，但还不能声称获得了“WSOP 官方完整可执行规格”。标准牌组／牌型若在后续模拟中由项目补齐，必须逐项标作 **P 级定义**，而不能制造一个不存在的 “universal WSOP poker rules”。

### 1.7 后续复现清单

1. 保存三份 PDF 的字节、URL、获取日和上述 SHA-256；网页改版时不静默替换。
2. 每个实验先记录实际桌容量与本手 `dealt-in count`，再记录所有座位、按钮、小盲、大盲、行动顺序、在场／离座状态和各自精确筹码面额。
3. 正常路径夹具固定 Level 1：每名新参赛者起始 25,000，BBA 100、SB 100、BB 100；桌人数必须来自案例观察或另行标明的 P 级实验配置。
4. 若使用实体牌，保存完整发牌与烧牌序列；若使用程序，保存 52 张输入序、洗牌算法、版本和种子。只记种子不足以复现。
5. 在补齐标准高牌型 evaluator 前，先把其定义来源和项目地位写入夹具；不得引用 Short Deck 表。
6. 记录每个动作的 actor、面对金额、口头声明、筹码移动、最终裁定、时间点和当前 street，而不只记录最终下注额。
7. 记录每个 all-in 的有效投入、主池／边池资格、未跟注退回、摊牌顺序、tabled／mucked 状态及奇数筹码去向。
8. 至少测试：所有人弃牌到一人、多人正常摊牌、平分底池、三人不同深度 all-in、短 all-in 是否重开、playing the board、首级中途切换到新级别、heads-up 按钮变化。
9. 对 BBA 短筹码、规则文本歧义和 floor discretion 建立“需裁判输入”的夹具，不伪造唯一答案。
10. 策略、诈唬、位置价值和玩家体验另采官方牌谱／转播录像或受控实验；规则只定义可做什么，不证明玩家通常怎么做。

---

## 2. 对象 B2：2016 英文版 *Agricola Revised Edition* 四人基础游戏

### 2.1 范围卡

| 字段 | 本轮冻结值 | 性质 |
|---|---|---|
| 案例标识 | `AG-R16-EN-4P-BASE` | **项目夹具** |
| 游戏 | *Agricola (Revised Edition 2016)* | **来源事实** |
| 语言 | English | **研究判断**；冻结英文规则和附录，避免翻译差异 |
| 出版者／设计者 | Lookout GmbH／Uwe Rosenberg | **来源事实** |
| 产品身份 | EAN / UPC `4-260402-315287`；release year 2016 | **来源事实**，官方产品页 |
| 玩家数 | 4 | **研究判断**；产品支持 1–4 人 |
| 牌池 | 基础盒 48 Occupations + 48 Minor Improvements；四人局全部职业人数标记均合法 | **来源事实**，Rules pp.2–3 |
| 初始手牌 | 每人随机 7 Occupations + 7 Minor Improvements | **来源事实** |
| 行动空间牌 | 14 张按 Stage 1–6 分组；同阶段内洗混，再按阶段依次叠放 | **来源事实** |
| 初始家庭 | 每人两间木屋、两个已在场家庭成员；另有三个成员在个人供应区 | **来源事实** |
| 起始玩家／食物 | 随机决定；起始玩家 2 食物，其余各 3 食物 | **来源事实** |
| 纳入 | 四人面游戏板扩展、10 张公开 Major Improvements、完整基础手牌、14 轮和标准计分 | **研究判断** |
| 排除 | 5–6 人扩展、*Farmers of the Moor*、Artifex／Bubulcus／Corbarius／Dulcinaria／Consul Dirigens、推广卡、十五周年版附加物 | **排除项** |
| 排除的官方变体 | Drafting、Quick Drafting、Living Hand、Beginner’s Variant without Hand Cards、Side Job、额外行动格和 suggestion markers | **排除项**；附录收录不等于基础规则启用 |
| 具体对局 | 尚未冻结；本文件冻结规则与组件身份，具体随机结果另建 session fixture | **研究判断** |

文档身份：

```text
Agricola Revised Edition English Rules
© 2016 Lookout GmbH, 12 pages
SHA-256 1AA612ED43BDDE109A0BFFF900CF9322BAE02E5B53F4EE3FE9F37D264CA8BC70

Agricola Revised Edition English Appendix
© 2016 Lookout GmbH, 12 pages
SHA-256 AFB1C374982E290317A290DE3D109132D52424EC1EC7B310220D9F04EB1A7967
```

以上哈希是 2026-07-21 对 Lookout 当前下载文件的测量值。PDF 没有醒目的印刷版次号；后续引用应保留 URL、页码和哈希，而不只写“2016 规则”。

### 2.2 来源矩阵

| 级别 | 来源、版本与 URL | 定位 | 可以支持 | 不能支持 |
|---|---|---|---|---|
| N1 | [Lookout English Rules](https://www.lookout-spiele.de/upload/en_agricolare.html_Rules_Agricola-RE_EN.pdf)，©2016，12 页 | pp.2–3 setup；pp.4、6–12 course of play、harvest、cards、end | 基础盒组件、四人设置、回合流程、行动、支付、收获、手牌优先级、终局 | 未公开卡面的全部逐字规则；玩家策略、平衡性或感受 |
| N1 | [Lookout English Appendix](https://www.lookout-spiele.de/upload/en_agricolare.html_Appendix_Agricola-RE_EN.pdf)，©2016，12 页 | pp.1、3–9、11–12 | 术语细则、四人空间、可选变体、完整计分表 | 把所有附录变体同时视为基础规则；扩展卡内容 |
| F | [Lookout 产品页](https://www.lookout-spiele.de/en/games/agricolare.html) | Overview、Components、FAQ | Revised Edition 2016、EAN、1–4 人、120 张卡及新旧版混用警告 | 精确行动时序；页面上的约 90 分钟替代规则书 |
| F | [Lookout Consul Dirigens 产品页](https://www.lookout-spiele.de/en/games/agricolare_consuldirigens.html) | Description | 官方把基础盒手牌称作 “96 starting cards”；该产品是扩展 | Consul Dirigens 卡进入本轮基础牌池；96 张基础卡的完整卡号清单 |

### 2.3 可定位的关键规则

| 研究问题 | 官方定位 | 来源可直接支持的事实 |
|---|---|---|
| 组件与个人初始状态 | Rules p.2 | 每色 5 人、4 马厩、15 栅栏；两人位于两间木屋；基础盒 14 行动牌、10 major、48 occupation、48 minor |
| 四人公共设置 | Rules p.3 | 使用对应人数的游戏板扩展；随机起始玩家；2／3 食物；major 公开；手牌分别洗混并发 7 张 |
| 行动空间进入顺序 | Rules p.3 | 14 张牌洗混后按背面阶段号组成 6 叠，Stage 1 在最上方，之后依次出现 |
| 总体结构 | Rules p.4 | 共 14 轮；玩家轮流每次放一名家庭成员；每个行动空间每轮只容一人；全部放完前不取回 |
| 准备与积累 | Rules p.6 | 翻开本轮行动空间；发放轮次格物品；带赭色箭头的 accumulation space 每轮补充，即使仍有剩余 |
| 工作与回家 | Rules p.6 | 从起始玩家顺时针每次放一个尚在家的成员并立即执行；成员少者用完后被跳过；工作阶段后全部回家 |
| 房屋与家庭增长 | Rules p.7；Appendix pp.4、7 | 通常只有房间多于家庭成员才可增长；新生本轮不行动、下轮起增加一次放置；后期另有无房增长空间 |
| 收获 | Rules p.9 | 第 4、7、9、11、13、14 轮末收获；依次田地、喂养、繁殖；每块田收一个作物；成人 2 食物、新生 1 食物；缺 1 食物拿 1 begging marker；满足容纳条件时每种动物繁殖 1 只 |
| 卡牌修改规则 | Rules p.11 | 手牌未打出时无效；打出后可改规则；卡面文字优先于规则书；游戏中不再补抽 |
| 终局 | Rules p.12；Appendix pp.11–12 | 第 14 轮最终收获后结束；按农场、作物、动物、房间、家庭、卡牌与乞讨等项目计分；最高分胜，之后按剩余建材破同分，再同分共享名次 |
| 可选变体的地位 | Rules p.3；Appendix pp.1、8–9 | Side Job 等不是 base game 必需；Drafting 和无手牌玩法被明确列作 variants |

一个值得后续形式化保留的区别是：

```text
规则书把每轮叙述为四阶段；
但 Harvest 只在 4、7、9、11、13、14 轮执行。
```

**研究判断**：若将其写成状态机，Harvest 应是由轮次条件开启的阶段，而不是十四轮都无条件运行的同一段流程。这个建模结论不是规则书术语。

### 2.4 版本歧义与证据缺口

1. **产品页的 “ca. 90 min.” 与规则书的 “~30 minutes per player” 不同。** 这是元数据差异，不影响规则流程；不能用其中任一句证明真实四人局总是某个时长。
2. **官网展示 “3D box (2023)” 不等于 2023 规则版。** 同一页面仍把产品标作 Revised Edition 2016，EAN 也未因此变成新的规则身份。
3. **PDF 的版权年与文件生成时间不同。** 两份正文均为 ©2016，而文件元数据可晚于出版；因此保留哈希比只记文件日期可靠。
4. **旧版与 Revised Edition 不能随意混件。** 官方 FAQ 说总体 mechanics 没变，但措辞、卡牌和图形都经过重做，并警告混用可能造成问题。
5. **附录中的流行玩法仍是变体。** Drafting 很常见，也不能因为常见就被写进本轮标准设置。
6. **官方公开下载没有基础盒 96 张手牌的完整卡号／卡面档案。** 规则又明确卡面优先于规则书；要穷尽卡牌如何改写行动、成本、时序和计分，仍须对冻结的实体盒逐卡清点、拍照或取得权利方可核查的完整清单。
7. **随机设置不是一局。** 只知道“同阶段洗混”和“每人 7+7”不能复现任何具体局面；随机种子也只有在输入牌序和洗牌算法都冻结时才有意义。
8. **规则文本不能证明策略与体验。** “家庭增长通常很重要”“抢位很紧张”“乞讨令人挫败”“某卡过强”等都可能是研究假设，但需要对局日志、赛事资料或受控实验。

### 2.5 后续复现清单

1. 保存规则、附录、URL、获取日和上述哈希；记录实体盒 EAN、语言、印刷标记、卡牌与组件照片。
2. 清点基础盒 48 Occupations 与 48 Minor Improvements 的全部卡号；确认没有混入扩展、推广卡或其他语言／修订。
3. 记录四名玩家座次、起始玩家随机结果、每人的起始食物与全部个人组件。
4. 记录 14 张行动空间卡在每个 Stage 内的确切次序；不要只写“随机”。
5. 记录每人 7+7 张起始手牌、其分配顺序和未发牌；若用程序洗牌，保存输入序、算法、版本和种子。
6. 每个行动至少记录 round、phase、actor、所占空间、支付、立即效果、可选分支、触发卡、资源前后状态和下一个起始玩家状态。
7. 每轮记录所有 accumulation spaces 的补充前值、补充量、拿取者和拿取后值，以测试跨轮保留与“必须全部拿走”。
8. 每次家庭增长记录房间检查、新生状态、当轮是否行动、喂养需求及下一轮可用成员数。
9. 每次 Harvest 依次记录田地、喂养、begging、动物容纳与繁殖；不要只保存轮末总分。
10. 记录所有已打出卡牌的精确文本、优先级冲突与裁定；未打出的手牌不应污染公共规则状态。
11. 至少建立：无人争抢的正常轮、多人争同一空间、积累跨轮、房间不足的家庭增长、食物不足、动物无容纳空间、卡牌改写基础规则、最终同分判定等夹具。
12. 玩家路线、阻挡意图、卡牌估值和情绪另作行为研究；规则 trace 不能替代玩家解释。

---

## 3. 跨对象的校准门结论

### 3.1 已经冻结的内容

- NLHE 不再指向模糊的“标准德州扑克”，而是指向 Event #65 的结构表及其 2026 WSOP 内部规则层级；桌上人数仍显式待观察／配置。
- *Agricola* 不再指向混合了旧版、扩展和常用 Draft 的泛称，而是指向 EAN `4-260402-315287` 的 2016 英文 Revised Edition 四人基础规则。
- 两案均明确区分官方事实、项目夹具、外部比较规范和仍未补齐的证据。

### 3.2 尚未得到的内容

```text
规则对象已冻结
≠ 一局具体游戏已经冻结
≠ 完整可执行形式规格已经完成
≠ 玩家行为与体验已经得到证明
```

NLHE 仍缺官方正文中的普通 52 张牌／完整高牌型定义、BBA 短筹码顺序及具体牌序；*Agricola* 仍缺基础盒 96 张手牌的完整一手卡面档案和具体随机设置。这些缺口不妨碍开始有限范围的案例分析，但会限制“穷尽”“可执行”“完整”等主张。

### 3.3 进入完整案例前的通过条件

- [x] 两个对象都有明确版本、官方规则入口和排除项；《农场主》人数已冻结，NLHE 桌上人数则已明确登记为待观察／配置字段。
- [x] 核心流程能定位到条款或页码，WSOP 的规则优先级也已显式记录。
- [x] 已记录 WSOP 与 TDA 的实质冲突，不混成虚构的通用规则。
- [x] 已记录官方文件哈希；网页事实保留直接 URL 和核验日。
- [ ] 为 NLHE 的标准牌组／高牌型找到能进入所选规则层级的材料，或把项目 evaluator 逐项声明为 P 级。
- [ ] 明确 NLHE BBA 遇短筹码的实验处理，并保留“WSOP 未明文”的标签。
- [ ] 完成 *Agricola* 基础盒 96 张手牌的实体卡号／卡面审计。
- [ ] 两案各建立至少一个正常路径和一个边界路径的完整 session fixture。
- [ ] 任何关于策略、学习、紧张感、公平感或设计意图的结论，另有行为或历史来源支持。

达到这些条件后，后续文档才适合分别提出原语候选、槽位语法、机制边界和循环模型；本资料包只负责保证我们分析的是同一个对象。
