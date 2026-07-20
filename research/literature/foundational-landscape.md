# 基础理论与文献地图：从游戏定义到可执行描述

> 状态：Phase 1 开放研究稿
> 更新日期：2026-07-20
> 研究范围：游戏定义、规则、ontology、ludeme、game grammar / game description language、mechanics / dynamics、gameplay design patterns、agency、emergence、feedback / economy、rules–play–culture、formal abstract design tools
> 编辑约束：本文以“原语 → 机制 → 玩法模板 → 游戏”为既定的简洁编辑主干，只做文献定位、压力测试与后续研究规划，不提议在此改写主干。

## 1. 研究问题、证据标签与结论边界

本文不再逐项摘要 `research/foundations/structural-models.md` 已覆盖的模型，而是回答五个更基础的问题：这些概念从哪些问题意识中长出来；同一个词在不同谱系中为何指向不同对象；各理论用什么证据判断自己成功；它能回答什么、不能回答什么；它与本项目四段链究竟是同构、互补，还是只提供一个侧面视图。

本文只使用原始论文、作者或项目官方资料、大学出版社页面、官方语言参考与课程材料。行文采用以下标签：

- **[来源事实]**：来源明确陈述的定义、范围、方法或结果。
- **[综合判断]**：根据多个来源作出的比较或项目定位，不冒充原作者结论。
- **[工作假设]**：可进入项目后续案例测试、但尚未被本项目证实的命题。
- **[开放问题]**：当前证据不足，或不同理论尚无共同判准的问题。

下文表格或小节中未重复贴标签的“能回答 / 不能回答 / 四段链接口”栏，均属于基于相邻来源所作的 **[综合判断]**，不归给原作者。

### 1.1 核心结论

1. **[综合判断]** 现有文献中没有一个得到广泛接受、且与“原语 → 机制 → 玩法模板 → 游戏”完全同构的前身。四段链的差异化价值，恰在于把四类经常彼此错位的问题压缩为一条可教学、可分析、可设计的路线：可复用词汇是什么；组合怎样成为可运行规则；哪些组合反复形成决策与反馈结构；这些结构怎样被内容、界面、材料和情境实例化为具体游戏。代表性对照见 [Game Ontology Project](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf)、[Ludii](https://doi.org/10.3233/FAIA200120) 与 [Gameplay Design Patterns](https://doi.org/10.26503/dl.v2003i1.60)。
2. **[综合判断]** 文献争论最常见的根源不是“层数不同”，而是**研究对象、观察尺度和成功判准不同**。定义理论划游戏/非游戏边界；ontology 组织概念；typology 给完整游戏定位；描述语言要求可执行或可推理；模式库记录反复出现的交互；模拟工具追踪量化过程；设计工具和经验法则辅助判断。把它们排成同一层级，会制造伪冲突。各类产物的原始判准可对照 [Stenros 的定义综述](https://doi.org/10.1177/1555412016655679)、[Stanford GDL](https://logic.stanford.edu/ggp/chapters/chapter_02.html)、[Machinations](https://doi.org/10.1609/aiide.v7i3.12477) 与 [Church 的 FADT](https://www.gamedeveloper.com/design/formal-abstract-design-tools)。
3. **[综合判断]** 四段链可以继续保持简洁，但每个案例至少需要附带四类校验信息：分析尺度、动作发起者与自动过程、玩家可感知的反馈、社会与材料规则。它们是横切检查项，不必升级成新的主干层级。判据来源分别见 [ontological meta-model](https://doi.org/10.26503/dl.v2018i1.973)、[Sicart](https://gamestudies.org/0802/articles/sicart)、[Agency Reconsidered](https://eis.ucsc.edu/papers/nwf-C7-digra09-agency.pdf) 与 [The Rule Book](https://doi.org/10.7551/mitpress/14730.001.0001)。
4. **[工作假设]** “原语”最稳妥的研究方向不是寻找跨一切媒介都不可再分的终极原子，而是寻找**对给定语料、分析任务和表达语言足够小、能稳定组合、还能保留设计意义的相对单位**。Game Ontology Project 的中层生长法和 Ludii 的类型化构造器都支持这种方向，但都不能证明存在唯一的自然原子表。[Game Ontology Project 原始论文](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf)；[Ludii Language Reference](https://ludii.games/downloads/LudiiLanguageReference.pdf)

## 2. 先区分研究产物：它们不是同一种“游戏语言”

| 产物类型 | 它首先回答的问题 | 典型输出与检验方式 | 一手例子 | 与四段链的关系 |
| --- | --- | --- | --- | --- |
| 游戏定义（definition） | 什么算游戏，边界案例为何进或出？ | 必要/充分条件、家族相似性或诊断问题；用边界案例反驳 | [Suits 1967](https://doi.org/10.1086/288138)、[Juul 2003](https://doi.org/10.26503/dl.v2003i1.65)、[Stenros 2016](https://doi.org/10.1177/1555412016655679) | 检查“游戏”端的覆盖边界，不提供从原语生成游戏的词表 |
| Ontology / ontological meta-model | 某领域里有哪些概念，它们如何上下位或组成？不同本体又在描述游戏的哪个层面？ | 概念条目、层级、part-of 关系、强弱实例，或用于比较本体的描述坐标；靠新案例持续修订 | [Game Ontology Project](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf)、[Aarseth 与 Grabarczyk 2018](https://doi.org/10.26503/dl.v2018i1.973) | 候选原语、机制及其关系的采集方法与尺度检查；不是执行语义 |
| Typology / 分类坐标 | 完整游戏在若干维度上如何异同？ | 一组正交或半正交维度及取值；看能否区分和预测组合 | [Aarseth、Smedstad、Sunnanå 2003](https://doi.org/10.26503/dl.v2003i1.66) | 横切“游戏”实例作比较；轴上的取值通常不是原语 |
| 可执行描述语言（DSL） | 规则能否被机器解析、运行、推理或供代理游玩？ | 语法、形式语义、编译/解释器、测试游戏；以执行和性质验证 | [Stanford GDL](https://logic.stanford.edu/ggp/chapters/chapter_02.html)、[Ludii](https://doi.org/10.3233/FAIA200120)、[PyVGDL](https://people.idsia.ch/~schaul/publications/pyvgdl.pdf) | 为“语法 → 机制”提供最强的可检验范本，但每种语言都有领域边界 |
| 生成式 grammar | 怎样用改写规则产生任务、空间或其他内容结构？ | 产生式、起始符、终止条件与生成样本；检验可生成性和约束满足 | [Dormans 2010](https://pcgworkshop.com/archive/dormans2010adventures.pdf) | 多数服务于“玩法模板 → 游戏”的内容实例化，而不是完整规则系统 |
| 模拟/系统记法 | 资源与状态如何随时间流动，反馈环怎样影响稳定性？ | 可运行图、参数扫描、轨迹与平衡结果 | [Machinations 原始论文](https://doi.org/10.1609/aiide.v7i3.12477) | 深入机制编排与部分玩法动态；不能自动覆盖意义、身体技巧与文化 |
| 设计模式库 | 哪些交互结构在多个游戏中反复出现，彼此怎样促进、冲突、实例化？ | 带条件、后果、关系和实例的模式条目；跨案例复核 | [Björk、Lundgren、Holopainen 2003](https://doi.org/10.26503/dl.v2003i1.60) | 与“玩法模板”最接近，但模式不等于任意机制集合，也不保证实际出现 |
| 形式抽象工具 / 启发式 | 设计者怎样精确交流问题、检查意图或作局部决策？ | 可解释概念、问题清单、经验法则；以设计诊断的实用性检验 | [Church 1999](https://www.gamedeveloper.com/design/formal-abstract-design-tools)、[The 400 Project](https://www.finitearts.com/Pages/400page.html) | 可用于全链路审查；不是构成游戏的砖块，也不是数学形式系统 |
| 解释性视角 | 规则、游玩、文化或表征之间如何互相构成意义？ | 概念视角、细读与比较；以解释力而非可执行性检验 | [Lantz 与 Zimmerman](https://ericzimmerman.com/assets/pdfs/RulesPlayCulture.pdf)、[Operational Logics](https://escholarship.org/uc/item/3cv133pn) | 提醒四段链遗漏了哪些关系；更适合作为横切视角而非新增一段 |

**[综合判断]** 上表给出一个重要的术语卫生原则：**能命名，不等于能组合；能组合，不等于能执行；能执行，不等于能预测玩家；能预测一类量化动态，也不等于解释了游玩意义。** 后续引用任何理论时，都应同时说明它产生的是哪一种研究产物。

## 3. 文献谱系：多条支流，而非一条继承线

下表只标出时间与问题支流。除非来源明确说明受到某项工作的影响，否则不把先后关系写成因果继承。

| 时段 | 规则、游戏与文化支流 | 设计词汇与玩家关系支流 | 形式描述、生成与模拟支流 |
| --- | --- | --- | --- |
| 1938–1967 | Huizinga 把 play 置于文化生成中；Caillois 区分 competition / chance / simulation / vertigo 与 paidia–ludus 连续体；Suits 以目标、受限手段和自愿接受限制定义 game-playing。[《Homo Ludens》出版社页](https://www.routledge.com/Homo-Ludens-ILS-86/uizinga/p/book/9780415487559)；[Caillois 出版社页](https://www.press.uillinois.edu/books/?id=p070334)；[Suits 1967](https://doi.org/10.1086/288138) |  |  |
| 1999–2005 | Lantz 与 Zimmerman 提出 rules–play–culture 三种互联视角；Juul 把游戏定义拆成形式系统、玩家—游戏、游戏—世界三组关系，并以 emergence / progression 讨论规则与实际局次的关系。[Rules, Play and Culture](https://ericzimmerman.com/assets/pdfs/RulesPlayCulture.pdf)；[Juul 2002](https://jesperjuul.net/text/openandtheclosed.html)；[Juul 2003](https://doi.org/10.26503/dl.v2003i1.65) | Church 提出 FADT；Björk 等发展 gameplay design patterns；MDA 连接 mechanics、runtime dynamics 与审美反应；GOP 以案例归纳概念层级。[Church 1999](https://www.gamedeveloper.com/design/formal-abstract-design-tools)；[Patterns 2003](https://doi.org/10.26503/dl.v2003i1.60)；[MDA 2004](https://aaai.org/papers/ws04-04-001-mda-a-formal-approach-to-game-design-and-game-research/)；[GOP 2005](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf) | Stanford GDL 为 general game playing 建立运行时规则描述；Dormans 等随后把 grammar 用于任务与空间生成。[GDL 原始论文](https://logic.stanford.edu/ggp/readings/aaai.pdf)；[Dormans 2010](https://pcgworkshop.com/archive/dormans2010adventures.pdf) |
| 2007–2011 |  | Cook 的 skill atom 把动作、模拟、反馈、心智模型连成学习环；Järvinen、Sicart 分别从玩家操作和 agent-invoked method 收紧 mechanic；Wardrip-Fruin 等把 agency 定位为玩家欲求与系统支持的关系；operational logics 连接抽象过程与人类理解。[Cook](https://www.gamedeveloper.com/design/the-chemistry-of-game-design)；[Järvinen 博士论文记录](https://pure.itu.dk/en/publications/games-without-frontiers-theories-and-methods-for-game-studies-and/)；[Sicart](https://gamestudies.org/0802/articles/sicart)；[Agency Reconsidered](https://eis.ucsc.edu/papers/nwf-C7-digra09-agency.pdf)；[Operational Logics](https://escholarship.org/uc/item/3cv133pn) | GDL-II 扩展随机性与不完全信息；BIPED / LUDOCORE 连接可玩原型与形式推理；PyVGDL 面向二维电子游戏；Machinations 面向资源流与内部经济。[GDL-II](https://cgi.cse.unsw.edu.au/~mit/Papers/AAAI10a.pdf)；[BIPED](https://doi.org/10.1609/aiide.v5i1.12344)；[LUDOCORE](https://adamsmith.as/papers/ieeecig10_ludocore.pdf)；[PyVGDL](https://people.idsia.ch/~schaul/publications/pyvgdl.pdf)；[Machinations](https://doi.org/10.1609/aiide.v7i3.12477) |
| 2016–2024 | Stenros 回顾六十余种游戏定义，把“定义什么、为何定义”本身变成研究对象；Stenros 与 Montola 将规则分为 formal、internal、social、external、material 五类。[Stenros 2016](https://doi.org/10.1177/1555412016655679)；[The Rule Book](https://mitpress.mit.edu/9780262547444/the-rule-book/) | Aarseth 与 Grabarczyk 提出 ontological meta-model，用描述层级比较既有本体与研究对象，而非再给一份元素清单。[原始论文](https://doi.org/10.26503/dl.v2018i1.973) | Ludii 以高层、可读 ludeme 描述和运行传统策略游戏，并在明确的有限广延式游戏范围内论证表达普适性；GDL-III 引入知识与内省，同时证明终止性变为不可判定；formal game grammar 以 game tree 变换研究等价性。[Ludii 2020](https://doi.org/10.3233/FAIA200120)；[Ludii universality](https://arxiv.org/abs/2205.00451)；[GDL-III](https://www.ijcai.org/proceedings/2017/177)；[Formal Game Grammar](https://ieee-cog.org/2020/papers/paper_74.pdf) |

**[综合判断]** 这张谱系显示，四段链不是某条支流的缩写。它更像一座桥：左岸是描述单位和规则形式，桥面是机制编排与可复用交互，右岸是具体作品、实际游玩与文化处境。

## 4. 主题地图：分歧、能力边界与四段链接口

### 4.1 游戏定义与规则：定义的是 artifact、activity，还是一种关系？

#### 4.1.1 三种定义策略

- **[来源事实] 分析定义。** Suits 把 game-playing 定义为：朝向某个特定事态，使用规则许可、且比没有规则时更受限的手段；接受限制的理由正是使该活动成为可能。后来《The Grasshopper》把它凝练为“自愿尝试克服不必要的障碍”。这一定义把目标、构成性限制和接受限制的态度绑在一起。[Suits 1967，pp. 148–156](https://doi.org/10.1086/288138)；[Broadview Press 官方书页](https://broadviewpress.com/product/the-grasshopper-third-edition/)
- **[来源事实] 经典模型。** Juul 的六项特征是 rules、variable and quantifiable outcome、valorization of outcome、player effort、player attachment to outcome、negotiable consequences；他又把它们分成游戏作为形式系统、玩家与游戏的关系、游戏与世界的关系。因此，这不是一份纯规则清单。[Juul 2003，论文 PDF](https://dl.digra.org/index.php/dl/article/download/65/65/62)
- **[来源事实] 元定义/问题清单。** Stenros 在回顾六十余种定义后，把定义工作本身拆成一组问题：研究者究竟在定义 artifact 还是 activity，是寻找必要本质还是家族相似性，定义服务于什么用途。[The Game Definition Game](https://doi.org/10.1177/1555412016655679)；[作者大学存档页](https://researchportal.tuni.fi/en/publications/the-game-definition-game-a-review/)

#### 4.1.2 规则的范围分歧

**[来源事实]** 早期形式主义常把规则看成规定合法行动和状态变化的明确结构；但 Stenros 与 Montola 在 2024 年区分五类规则：正式陈述（formal）、玩家给自己的内部限制与目标（internal）、游玩社群的社会规范（social）、外部社会的规制（external）、由物体与环境实现的材料规则（material）。这不是说五类规则都能写入同一种程序，而是指出“什么在实际约束游玩”比规则书更宽。[The Rule Book 官方开放获取页面](https://mitpress.mit.edu/9780262547444/the-rule-book/)；[开放获取 DOI](https://doi.org/10.7551/mitpress/14730.001.0001)

**[来源事实]** Game Ontology Project 刻意把 goals 与 rules 分开：其官方 FAQ 的理由是 rules 会被执行并限制行动，而 goals 更“软”，玩家也可能自定目标。这与“目标只是终止规则的一种”形成有生产力的分歧。[GOP FAQ](https://www.gameontology.com/index.php/Frequently_Asked_Questions)

#### 4.1.3 能回答、不能回答、如何接入

| 问题 | 能回答 | 不能单独回答 | 对四段链的意义 |
| --- | --- | --- | --- |
| 为什么自愿接受低效限制仍可构成有意义活动？ | Suits 给出目标—限制—态度关系 | 不能枚举具体游戏由哪些结构组成，也不直接处理开放式玩具与无明确目标的游玩 | 提醒“游戏”端不只是规则实例，还包括参与者对限制的采纳 |
| 哪些特征让经典游戏跨媒介成立？ | Juul 把形式系统、玩家关系、现实后果放在同一模型 | 对电子游戏、角色扮演和边界对象，作者自己承认会超出经典模型 | 四段链可描述结构生成，但不应被误称为完整的游戏定义 |
| 实际游玩由哪些规则约束？ | 《The Rule Book》覆盖形式、内部、社会、外部、材料规则 | 不能把所有规则都自动编译成同一种状态转换系统 | 在“游戏”实例记录中增加规则来源标签，而非在主链中硬加五层 |

**[综合判断]** 对本项目最重要的不是选择一个定义并宣布胜出，而是每次先声明分析对象：规则文本、可执行系统、一次 play session、被社群持续实践的 game，还是文化对象。否则“同一游戏”“同一机制”“规则外行为”都没有稳定指称。

### 4.2 Ontology、typology 与 ludeme：三种不同的“拆游戏”

#### 4.2.1 Game Ontology Project：概念层级不是游戏分类表

**[来源事实]** GOP 从大量具体游戏中抽象概念，借用 prototype theory 和 grounded theory，以 middle-out 方式迭代生长；早期顶层包括 interface、rules、goals、entities、entity manipulation。论文明确区分 ontology 与 taxonomy：前者组织游戏元素本身，后者按特征组织完整游戏；也明确说 GOP 不是“如何做出好游戏”的设计法则。[Zagal 等 2005，pp. 1–4](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf)

**能回答：** 某个跨游戏概念的父子关系、part-of 关系、强例与弱例；相似机制是否只是表面主题不同；一套词汇是否仍扎根于真实案例。

**不能回答：** 某条规则能否执行；一个模式会否在玩家中出现；某个游戏是否“好”；被作者主动括起的表征、题材和文化意义。GOP 原文明确说其结构分析会 bracket representational details，深入理解具体游戏仍需其他方法。[GOP 论文，pp. 4–5](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf)

**[综合判断]** GOP 对“原语”研究最有价值的是方法而非现成顶层表：从中层、可观察、可对照的概念起步；记录强弱实例和模糊边界；让新案例改变层级。它反对从词源或直觉一次性演绎“完整原语表”。

#### 4.2.2 多维 typology：坐标轴不是组成件

**[来源事实]** Aarseth、Smedstad、Sunnanå 的多维类型学以 Space、Perspective、Time、Teleology 等维度比较“发生在虚拟环境中的游戏”，目标是比产业 genre 更严格地描述差异，并尝试用未出现过的取值组合预测可能的新游戏。其原始范围明确排除了 poker、blackjack 这类“纯抽象”游戏。[A Multidimensional Typology of Games](https://doi.org/10.26503/dl.v2003i1.66) 后续版本把模型描述为开放分类，并讨论它如何服务设计与半形式方法。[Elverdam 与 Aarseth 2007](https://doi.org/10.1177/1555412006286892)

**[综合判断]** “实时/回合制”“有限/无限”等轴值可以成为案例元数据或语法约束，但通常不是可直接组成机制的原语。把 typology 轴值塞进原语目录，会混淆“这个游戏位于哪里”和“这个游戏由什么构成”。

#### 4.2.3 Ontological Meta-Model：比较本体的坐标，不是另一份零件表

**[来源事实]** Aarseth 与 Grabarczyk 把游戏视为可在多个描述层级分析的机制，并提出 physical、structural、communicational、mental 四层 ontological meta-model；每层再分三个子层。它的目标是说明不同研究传统究竟在谈游戏的哪一部分、哪一层抽象，从而让既有本体和分析方法可比较，而不是宣称四层是一条制作顺序。[An Ontological Meta-Model for Game Research](https://doi.org/10.26503/dl.v2018i1.973)

**能回答：** 两套理论的“对象”“规则”“机制”是否其实位于不同描述层；某项研究把硬件、计算、界面、意义、经验或社会实践中的哪一些纳入对象；不同分析结果是否具备可比尺度。

**不能回答：** 应采用哪些具体原语；一条规则怎样执行；哪个层对另一个层具有充分因果解释；四层是否是自然、唯一或穷尽的本体划分。

**[综合判断]** 对本项目而言，这个 meta-model 最适合作为“尺度声明”工具：在四段链的每个条目旁注明当前证据位于物理、结构、传播或心智描述中的哪里。它不能替代四段链，也不要求把四段链扩写成四层。

#### 4.2.4 Ludeme：历史用语与工程构造器不是同一个承诺

**[来源事实]** David Parlett 追溯该词时，把 ludeme 解释为与物件不同的“play element”，典型上接近规则概念，也承认主题性 ludeme；他强调这个词的历史归属和使用并不整齐，采用它主要因为跨游戏比较时实用。[Parlett，What’s a ludeme?](https://www.parlettgames.uk/gamester/whatsaludeme.html)

**[来源事实]** Ludii 则给 ludeme 一个工程上严格得多的角色：游戏描述以 `(game ...)` 构造器开始，其参数可以是字符串、布尔、整数、浮点或其他 ludemes；语言参考把运行所需的核心逻辑与 info / graphics / AI 等 metadata 分开。[Ludii Language Reference，pp. 22、327–329](https://ludii.games/downloads/LudiiLanguageReference.pdf) Ludii 的“普适性”证明覆盖任意**有限、非确定、非完美信息的广延式游戏**，不是对所有身体性、社会性或无限持续游戏的无条件覆盖声明。[Soemers 等 2022/2024](https://arxiv.org/abs/2205.00451)

| “ludeme”用法 | 单位是什么 | 判准 | 风险 |
| --- | --- | --- | --- |
| 历史/比较用法 | 可跨游戏传播的玩法、目的或主题元素 | 比较解释是否有用 | 边界与粒度依作者和语境改变 |
| Ludii 工程用法 | 类型化、可嵌套、具有解释器语义的语言构造器 | 能否编译、运行并产生预期游戏 | 原子性相对于 Ludii 语言和目标领域，而非世界本体 |
| 本项目候选“原语” | 对当前语料和分析任务足够小、可复用、可组合的语义单位 | 跨案例稳定性、组合可解释性、反例压力 | 若不声明尺度，容易把动作、规则、属性、反馈甚至模式混入同一层 |

**[工作假设]** 本项目可以把 Ludii 当作“相对原语 + 类型化组合 + 可执行检验”的强范例，把 Parlett 当作“术语不可天然获得唯一边界”的历史警示；两者共同支持保留“原语相对尺度”的现有立场。

### 4.3 Game grammar 与 game description language：“语法”至少有四种任务

| “grammar”含义 | 代表工作 | 它实际操作什么 | 最适合回答 | 明确不能推出 |
| --- | --- | --- | --- | --- |
| 设计交流与图解隐喻 | Koster 的 game grammar、Bura 的 game diagrams | 设计概念、资源、转移和关系的简图 | 团队能否跨游戏谈底层原则、迅速画出结构 | 可判定语义、完备性、唯一分解。Koster 的 2005 演讲展示了以 ludeme 和嵌套关系分析 gameplay 的设想，后来又明言早期文章已不代表其当前理解；Bura 也称工作仍是初步描述工具。[Koster 2005 演讲稿](https://www.raphkoster.com/gaming/atof/grammarofgameplay.pdf)；[Koster 的后续说明](https://www.raphkoster.com/2012/01/24/an-atomic-theory-of-fun-game-design/)；[Bura](https://www.stephanebura.com/diagrams/) |
| 生成式改写语法 | Dormans 的 mission graph grammar 与 spatial shape grammar | 任务节点图和空间形状 | 怎样从产生式生成多样又受约束的关卡结构 | 完整游戏规则、玩家理解或机制本体。[Dormans 2010，§4–5](https://pcgworkshop.com/archive/dormans2010adventures.pdf) |
| 可执行/可推理 DSL | GDL、GDL-II/III、BIPED、LUDOCORE、PyVGDL、Ludii | 状态、行动、合法性、转移、观察、终止或领域构造器 | 描述能否被运行、搜索、模拟或形式分析 | 超出语言领域的身体实践、社会规范、表征意义，以及仅靠语法无法保证的良好玩法 |
| 数学等价与变换 grammar | Riggins 与 McPherson | 有限离散游戏的 game trees 及保持 meaningful agency 的变换 | 两个形式游戏何时等价/相近，怎样忽略表面差异 | 隐藏信息、无限或连续系统、文化与语义等价。[Formal Game Grammar and Equivalence](https://ieee-cog.org/2020/papers/paper_74.pdf) |

#### 4.3.1 可执行语言的能力边界

- **Stanford GDL。** **[来源事实]** GDL 是受限逻辑程序语言，规则在运行时交给 general game player；限制确保逻辑蕴涵问题可判定，并用 `role`、`init`、`legal`、`next`、`goal`、`terminal` 等关系描述有限状态游戏。[官方课程 Chapter 2](https://logic.stanford.edu/ggp/chapters/chapter_02.html) GDL-II 增加随机角色与玩家感知，以表达非确定和不完全信息。[官方课程 Chapter 17](https://logic.stanford.edu/ggp/chapters/chapter_17.html) GDL-III 再引入依赖玩家知识的 epistemic games；作者同时证明表达力上升后，终止性变得不可判定。[IJCAI 2017](https://www.ijcai.org/proceedings/2017/177)
- **BIPED 与 LUDOCORE。** **[来源事实]** BIPED 用一份简洁定义同时给出可玩原型和形式规则系统，让设计者一边从人类试玩看到迟疑、投入或乐趣，一边用自动分析寻找 emergent properties、exploits 和 puzzle solutions；范围偏 board-game-like prototypes。[BIPED 原始论文](https://doi.org/10.1609/aiide.v5i1.12344) LUDOCORE 以 event calculus 连接设计者理解的规则与 AI 逻辑，能够生成 gameplay traces、作时序/结构查询并驱动实时图形原型。[LUDOCORE 原始论文，pp. 1–2](https://adamsmith.as/papers/ieeecig10_ludocore.pdf)
- **PyVGDL。** **[来源事实]** PyVGDL 面向二维街机式电子游戏，以 level mapping、sprite classes、碰撞 interaction 和 termination 四块描述游戏，并可迅速实例化为可玩程序；作者明确把二维空间和当时的单玩家接口作为范围选择。[Schaul 2013，pp. 1–4](https://people.idsia.ch/~schaul/publications/pyvgdl.pdf)
- **Ludii。** **[来源事实]** Ludii 用高层 ludemes 压缩传统策略游戏描述，兼顾人类可读、AI 运行和历史游戏重建；宏、options 和 rulesets 增加复用与变体表达，但语法符合并不自动保证语义编译成功。[Ludii Language Reference，pp. 22、401–409、497](https://ludii.games/downloads/LudiiLanguageReference.pdf)

**[综合判断]** 这些语言共同证明：“语法”一旦有明确领域、类型/逻辑语义和执行器，就可以从比喻变成可证伪工具；它们也共同证明，表达力、可读性、运行效率、可判定性和领域覆盖之间存在真实取舍。不存在只靠扩充词表就同时最大化所有目标的免费方案。

**[工作假设]** 本项目四段链中的“语法”目前最接近“约束原语如何填充角色、前提、目标、时序、作用域和效果的类型化规则表达”，而不是生成关卡的 grammar，也不是 Koster 式通用图解。后续若使用“形式化”，必须再说明是“精确定义”“机器可执行”“数学可证明”三者中的哪一种。

### 4.4 Mechanics、dynamics 与 agency：争论的是动作边界，不只是术语偏好

#### 4.4.1 四种 mechanic 不是同一粒度

| 来源 | mechanic / atom 的定义重心 | 谁发起、包含什么 | 它能回答 | 它不能单独回答 |
| --- | --- | --- | --- | --- |
| MDA | 特定游戏组件，在数据表示和算法层面；dynamics 是 mechanics 对玩家输入和彼此输出随时间作用产生的运行行为 | 定义较宽，动作、行为、控制与后台计算均可能进入 mechanics | 设计者如何从机制调参，经运行动态指向期望审美；为何设计者与玩家观察方向相反 | 单个 mechanic 的稳定识别边界；社会/材料规则；实际玩家一定会产生何种体验。[MDA 原始论文](https://cdn.aaai.org/Workshops/2004/WS-04-04/WS04-04-001.pdf) |
| Järvinen | 游戏系统提供给玩家、用来追求规则集目标的手段 | mechanics 是玩家驱动操作；procedures 是系统响应玩家、按规则运行的操作 | 玩家输入与系统响应如何分工；动作怎样连接组件、环境、界面和目标 | 无目标 sandbox 行为会给定义施压；AI agent 的动作边界不如 Sicart 宽。[博士论文记录](https://pure.itu.dk/en/publications/games-without-frontiers-theories-and-methods-for-game-studies-and/)；[官方论文 PDF](https://trepo.tuni.fi/bitstream/handle/10024/67820/978-951-44-7252-7.pdf) |
| Sicart | agent 为与 game state 交互而调用的方法 | 人类或人工 agent 均可调用；rules 规定可能空间和状态转移，mechanics 面向 agency | 精确列出动作动词、触发、输入映射、上下文条件和 agent 差异 | 不能由形式 mechanic 清单预测一局会怎样玩、玩家如何挪用动作或最终体验。[Sicart 2008](https://gamestudies.org/0802/articles/sicart) |
| Cook | skill atom 是 Action → Simulation → Feedback → Modeling 的学习反馈环 | 单位跨越玩家动作、系统更新、感知反馈和玩家心智模型 | 玩家怎样习得可用知识；技能怎样链接成 skill chain | 不是规则 ontology，也没有证明每个游戏都存在唯一的 skill-atom 分解。[The Chemistry of Game Design](https://www.gamedeveloper.com/design/the-chemistry-of-game-design) |

**[来源事实]** Sicart 明确把 rules 与 mechanics 作本体区分：规则定义/调节可能空间和状态转移，mechanics 是 agent 与 game state 实际交互的调用方法；他的概括是 rules “modeled after agency”，mechanics “modeled for agency”。他也明确承认形式分析最多描述可能路径，玩家会挪用机制，不能由此决定实际 play。[Defining Game Mechanics，§Defining Game Mechanics、结论](https://gamestudies.org/0802/articles/sicart)

**[综合判断]** 四种用法没有必要被强行统一，因为它们服务不同测量任务：MDA 适合设计迭代的因果方向；Järvinen 适合区分玩家操作和系统过程；Sicart 适合动作接口与 agent 权限分析；Cook 适合学习、反馈与教学节奏。真正需要统一的是每次使用“机制”时都说明：

1. 发起者是玩家、AI、环境、时钟，还是规则裁判；
2. 它是一个可调用动作、自动过程、规则簇，还是动作—反馈闭环；
3. 粒度是瞬时输入、一次有结果的操作、循环，还是跨局经济；
4. 识别依据是规则文本、实现、可观察行为，还是玩家理解。

**[工作假设]** 本项目现有“机制 = 可重复运行的规则结构”可以保留其广义和教学简洁性；案例记录应把“玩家/agent 发起的机制”与“系统自动过程”标注为两种角色，而不是让同一个词在段落中悄悄换义。

#### 4.4.2 Dynamics 是运行结果、可观察模式，还是设计者想要的行为？

**[来源事实]** MDA 把 dynamics 定为 mechanics 对玩家输入和彼此输出随时间产生的 run-time behavior；Järvinen 则把 dynamics 放在从 mechanics 和系统 procedures 到 gameplay 的状态变化中；Juul 的 emergence 研究又强调规则与实际 game sessions 之间不能直接等同。[MDA](https://cdn.aaai.org/Workshops/2004/WS-04-04/WS04-04-001.pdf)；[Järvinen 博士论文，Chapter 12](https://trepo.tuni.fi/bitstream/handle/10024/67820/978-951-44-7252-7.pdf)；[Juul](https://jesperjuul.net/text/openandtheclosed.html)

**[综合判断]** 后续研究至少要区分三件事：

- **设计上可供（afforded）的动态**：规则与界面允许、模拟可得到的轨迹集合；
- **设计者意图（intended）的动态**：希望玩家发现或维持的行为；
- **实证观察（observed）的动态**：真实玩家群体在具体情境中反复做出的行为。

只模拟规则可以支持第一项，设计文档支持第二项，录像、日志、访谈或规则实践记录才支持第三项。三者重合是待验证结果，不是命名后自动成立。

#### 4.4.3 Agency 的谱系：从“有选择”转向“欲求与系统支持匹配”

**[来源事实]** Wardrip-Fruin、Mateas、Dow、Sali 回顾了两条一度分离的谱系：学术侧常从 Janet Murray 1997 年“有意义行动并看到结果”的经验定义出发；设计侧常从 Doug Church 1999 年的 intention 与 perceivable consequence 出发。Church 所说 intention 是玩家基于当前局面和对玩法选项的理解形成可执行计划；perceivable consequence 是游戏世界对玩家动作给出清晰反应。[Agency Reconsidered，pp. 1–2](https://eis.ucsc.edu/papers/nwf-C7-digra09-agency.pdf)；[Church 原文](https://www.gamedeveloper.com/design/formal-abstract-design-tools)

**[来源事实]** 该论文进一步把 agency 定位为玩家与游戏共同形成的现象：玩家想做的行动包含在底层模型支持的行动中，反向也成立。它明确反对把 agency 等同于自由意志或“什么都能做”，并把表征、界面、计算模型、玩家预期和游玩的即兴性都纳入设计问题。[Agency Reconsidered，摘要与 pp. 4–7](https://eis.ucsc.edu/papers/nwf-C7-digra09-agency.pdf)

**能回答：** 为什么两个拥有相同合法动作数的系统，agency 体验可能完全不同；为什么清晰反馈、世界暗示、动作解释与玩家目标必须彼此匹配；为什么“实际有因果”但玩家看不出因果，不构成同等的可感知后果。

**不能回答：** agency 是否越多越好；某个具体玩家在任何时刻想做什么；社会权力、身份与可进入性如何分配 agency，除非加入额外经验研究。

**[综合判断]** agency 最适合作为“机制 → 玩法模板”和“玩法模板 → 游戏”两处的质量校验，而不是原语或第五层。它要求玩法模板不仅列“可做决定”，还要说明游戏怎样诱发目标、怎样让选项可理解、怎样反馈后果。

### 4.5 Gameplay design patterns、emergence 与 feedback/economy

#### 4.5.1 Gameplay pattern：反复出现的交互，不是任意机制包

**[来源事实]** Björk、Lundgren、Holopainen 最初把 game design patterns 定义为“与 gameplay 有关的反复出现的 interaction 描述”，并用结构框架说明组件怎样被玩家或计算机使用、从而影响 gameplay。[Game Design Patterns 2003](https://doi.org/10.26503/dl.v2003i1.60) 作者的设计示例进一步表明，模式要在具体语境中实例化；模式间存在支持、调制、冲突、子模式和实例化关系，设计者可以用这些关系生成、发展或压力测试概念。[作者书摘](https://www.gamedeveloper.com/design/book-excerpt-i-patterns-in-game-design-i-using-design-patterns)

**能回答：** 哪种交互在多个游戏中反复出现；它依赖哪些结构；通常带来哪些后果；和哪些模式协同或冲突；改变一个模式可能怎样改变 gameplay。

**不能回答：** 某次玩家一定会执行该模式；模式是由哪一组唯一机制推导；模式库是否穷尽设计空间；模式存在是否等于设计质量。

**[工作假设]** 本项目的“玩法模板”可以从 pattern 文献吸收四个最低字段：前提、核心交互/决定、典型后果、与其他模板的关系；同时保留本项目强调的循环、资源—风险、反馈—成长、失败与结束。一个“机制清单”只有在说明这些关系后，才足以升格为玩法模板候选。

#### 4.5.2 Emergence：规则与轨迹的关系，不是一个可装入游戏的零件

**[来源事实]** Juul 把 emergence 描述为少量简单规则组合出大量、有趣且不显然的变化，把 progression 描述为串行呈现的预设挑战；多数实际游戏可以混合两者。他借 weak emergence 指出，高层性质原则上来自底层规则，但可能只有通过模拟才可导出。[The Open and the Closed，§Emergence and progression、§Introducing emergence](https://jesperjuul.net/text/openandtheclosed.html)

**[来源事实]** Juul 还反对用“设计者没有预见”作为 emergence 的分析判准：是否预见取决于作者传记事实；一个规则后果即使容易推导，也不因设计者没想到就自动成为理论意义上的涌现。[同文 §Emergence in games](https://jesperjuul.net/text/openandtheclosed.html)

**[综合判断]** 本项目在记录 emergence 时应分开：

- **组合复杂性**：多个机制相互作用，状态空间扩张；
- **轨迹规律**：模拟或证明发现稳定策略、循环、崩溃、锁死等；
- **玩家实践**：社群反复采用、命名或规范化的玩法；
- **设计者惊讶**：历史事实，可作为开发研究证据，但不是涌现定义。

因此，“玩法模板是机制编排的结果”是一条发现路径，不是决定论。机制能供给某模板，不代表它在所有玩家、参数和文化情境中都会稳定出现。

#### 4.5.3 Feedback 与 economy：至少有系统控制环和玩家学习环

**[来源事实]** Machinations 用图表示 tangible / abstract resources 的流动，视其为游戏内部经济，并让设计者在实现前模拟、平衡。官方当前文档列出 pools、sources、drains、converters、traders、gates 六类基础节点，以及 resource connections 和改变节点状态的 state connections。[Dormans 2011](https://doi.org/10.1609/aiide.v7i3.12477)；[Machinations Framework Basics](https://machinations.io/docs/framework-basics)

**[来源事实]** Cook 的 skill atom 则关注另一种 feedback：玩家行动改变 simulation，游戏把改变反馈给玩家，玩家更新 mental model；多个 atom 可以连成技能学习图。[Cook，§Skill Atoms、§Chaining of Game Mechanics](https://www.gamedeveloper.com/design/the-chemistry-of-game-design)

| feedback 类型 | 被反馈的对象 | 典型问题 | 合适工具 | 盲点 |
| --- | --- | --- | --- | --- |
| 系统/控制反馈 | 资源量、速率、概率、状态变量 | 经济会膨胀、枯竭、振荡还是稳定？ | Machinations、状态机、仿真 | 玩家是否看懂、在乎或改变策略 |
| 玩家感知反馈 | 动作后可见、可听、可触的结果 | 玩家能否把后果归因于自己的行动？ | Church 的 perceivable consequence、可用性测试 | 长期经济是否平衡 |
| 学习反馈 | 玩家心智模型与技能掌握 | 何时形成、修正、迁移一个操作模型？ | Cook 的 skill atoms、教学实验 | 不能替代完整规则形式化 |
| 社会反馈 | 评价、声望、报复、规范执行 | 群体如何奖励、惩罚和稳定某种玩法？ | 观察、访谈、社群材料 | 纯系统图通常看不见非编码规范 |

**[综合判断]** “反馈”若不声明被反馈对象和时间尺度，会同时指 UI 提示、学习、控制论回路和社群反应。玩法模板至少要标注其关键反馈属于哪一类；Machinations 对量化经济很强，但不应把“所有游戏系统皆是资源流”的工具主张当成本项目的无条件 ontology。

#### 4.5.4 Operational logics：过程与表征之间的桥

**[来源事实]** Wardrip-Fruin 等把 operational logic 界定为一种 authoring / representational strategy：它由抽象过程或更低层逻辑支持，使系统行为能被特定受众理解为对某个领域的表征。也就是说，同一个状态变化只有通过合适表现和观众知识，才会被理解为“碰撞”“重力”“资源管理”或“社交”。[Defining Operational Logics](https://escholarship.org/uc/item/3cv133pn)

**[综合判断]** Operational logics 填补四段链中的一个横向缺口：原语和机制说明过程如何构成，operational logic 检查这个过程为何会被玩家读成某种有意义的操作。它不应替代机制层，也不等于美术包装；它连接可执行结构和解释。

### 4.6 Rules–play–culture：三个观察镜头，不是三个制作阶段

**[来源事实]** Lantz 与 Zimmerman 把 games as rules、games as play、games as culture 称为彼此关联、边界会模糊的理论模块：rules 给游戏形式身份；play 是规则系统被玩家选择和行动启动后的经验，包含策略、审美、心理、社会和材料面；culture 追问游戏对玩家与非玩家意味着什么，以及它与历史、政治、符号系统怎样连接。[Rules, Play and Culture，pp. 1–5](https://ericzimmerman.com/assets/pdfs/RulesPlayCulture.pdf)

| 镜头 | 典型证据 | 它看到什么 | 它容易漏掉什么 |
| --- | --- | --- | --- |
| Rules | 规则书、代码、裁判程序、状态转换 | 合法性、结构身份、可能空间 | 玩家挪用、情绪、身体差异、社会压力 |
| Play | 录像、日志、观察、访谈、比赛记录 | 实际决策、技巧、即兴、惯例、感受 | 未被玩到的可能空间；更广文化制度 |
| Culture | 历史档案、社群材料、制度与媒介分析 | 意义、身份、规范、传播、权力与非玩家关系 | 若缺少规则细读，容易把游戏只当主题文本 |

**[综合判断]** 这三个镜头与四段链不是竞争模型。四段链主要回答结构如何由小到大组织；rules–play–culture 回答同一对象从哪种证据和尺度观察。最合适的接入方式是在每个完整游戏案例中至少保留三栏证据，而不是把 culture 放到链末，误写成结构完成后才附着的“背景”。

**[工作假设]** 对传统运动、桌面角色扮演、派对游戏、赌博、现场角色扮演和渗透式游戏，social / material rules 可能直接构成机制能否运行，而非仅属于最终表现层。这个假设应以跨媒介案例压力测试，不应从数字游戏外推后直接定论。[The Rule Book](https://mitpress.mit.edu/9780262547444/the-rule-book/)

### 4.7 Formal abstract design tools：这里的 formal 不是“数学形式化”

**[来源事实]** Church 对 FADT 的拆词非常明确：formal 是“能精确定义并向别人解释”，abstract 是跨越具体游戏或 genre 的底层想法，tool 是共同设计词汇。他特别警告：抽象工具不是搭游戏的砖块或调味料；不同工具会冲突，是否使用取决于设计目标。[Formal Abstract Design Tools，§Examining the phrase、§What Could Possibly Go Wrong?](https://www.gamedeveloper.com/design/formal-abstract-design-tools)

**[来源事实]** Church 的两个核心例子是 intention 与 perceivable consequence。前者要求玩家能基于局面和理解形成自己的可执行计划；后者要求游戏世界对动作有清晰可归因的反应。真实代码中存在因果，却不代表玩家感知到了因果。[同文，§Mario 64 Game Play、§Same Tools, Different Games](https://www.gamedeveloper.com/design/formal-abstract-design-tools)

**[来源事实]** The 400 Project 采取另一条实践路线：收集带 attribution、scope、trumping 信息的设计经验法则。项目作者公开承认这些规则适用范围大小不同、彼此冲突甚至矛盾；其价值是“智慧胚芽”，不是统一公理系统。[Hal Barwood 官方页面](https://www.finitearts.com/Pages/400page.html)

**[综合判断]** 本项目应明确区分以下词汇角色：

- **原语**：构成性词汇候选；问“规则结构由什么表达”。
- **模式/模板**：经多个案例支持的反复交互；问“怎样的编排反复出现”。
- **设计工具**：分析和决策镜头；问“设计者要检查什么”。
- **经验法则**：带范围和优先级的建议；问“在什么条件下倾向怎样做”。

把 intention 当“原语”会丢失其关系性；把“永远给玩家清晰反馈”当普遍规则会抹掉悬疑、推理和有意不透明设计。FADT 与 400 Project 最有价值的共同点，是要求记录**用途、作用域、冲突和例外**。

## 5. 理论能力矩阵：选工具前先选问题

| 理论/工具 | 首要分析单位 | 最强问题 | 主要验证材料 | 四段链主要触点 | 不应据此声称 |
| --- | --- | --- | --- | --- | --- |
| Suits / Juul / Stenros 定义研究 | game-playing、经典游戏特征、定义问题 | 游戏边界和定义用途 | 边界案例、概念论证、定义史 | 游戏 | 已得到游戏内部的组成词表 |
| The Rule Book | 五类规则约束 | 哪些规则实际构成/约束游玩 | 跨媒介案例、规则实践 | 机制、游戏；横切全链 | 所有规则都能编码为状态转换 |
| GOP | 概念条目及上下位/部分关系 | 跨游戏元素如何组织 | 强弱实例、案例归纳 | 原语、机制 | ontology 已是可执行 grammar 或好设计处方 |
| Aarseth–Grabarczyk meta-model | 物理、结构、传播、心智层的描述位置 | 不同本体和研究方法是否在谈同一层对象 | 跨理论映射、分层案例编码 | 横切全链的尺度检查 | 四层是一条制作链，或已给出具体元素表 |
| 多维 typology | 完整游戏的维度取值 | 游戏间结构差异与潜在组合 | 跨游戏编码 | 游戏 | 轴值就是构成原语 |
| GDL / Ludii / PyVGDL / LUDOCORE | 形式状态、行动、规则或领域构造器 | 能否解析、运行、推理、生成轨迹 | 编译、执行、形式性质、测试套件 | 原语、语法、机制 | 语言外的身体、社会、文化现象已被解释 |
| Dormans generative grammar | 任务图、空间形状 | 怎样生成关卡内容 | 生成样本、约束与可玩测试 | 玩法模板、游戏 | 已生成完整玩法或玩家体验 |
| MDA | mechanic–dynamic–aesthetic 的设计方向 | 设计调参如何经运行行为指向体验目标 | 原型、迭代、玩家反馈 | 机制、玩法模板、游戏 | mechanics 已有唯一边界，aesthetic 一定被产生 |
| Sicart / Järvinen | agent/player 操作与系统过程 | 玩家动作、规则、状态和 procedure 怎样分工 | 规则、输入、状态追踪 | 机制 | 能从动作表预测实际玩法 |
| Gameplay Design Patterns | 反复交互及其关系 | 跨游戏复用、组合、冲突、变体 | 多案例、关系与后果 | 玩法模板 | 模式穷尽、唯一分解或必然出现 |
| Agency Reconsidered / FADT | 玩家欲求、计划、模型支持和可感知后果 | 选择为何有/无意义，界面与模型是否匹配 | 玩家行为、预期、反馈理解 | 机制→模板→游戏的横切检查 | 选项越多 agency 越高，或 agency 越高游戏越好 |
| Juul emergence | 规则与实际局局变化的关系 | 简单规则怎样产生复杂变化，progression 怎样混合 | 推导、模拟、局局记录 | 机制→玩法模板 | “作者没想到”就是涌现，或涌现是一个组件 |
| Machinations | 量化资源流与状态影响 | 经济、反馈环、平衡和崩溃 | 模拟、参数扫描 | 机制、玩法模板 | 所有玩法都可无损约化为资源流 |
| Operational logics | 抽象过程 + 表征策略 | 过程为何被玩家理解为某领域行为 | 代码/过程、界面、受众解释 | 横切原语、机制与实例化 | 表征只是一层可互换皮肤 |
| Rules–play–culture | 三种观察镜头 | 形式、实际游玩、文化意义如何互联 | 规则、游玩资料、文化资料 | 横切全链 | 它是一条从 rules 到 culture 的制作流水线 |

## 6. 对四段链的压力测试：加判据，不加层级

以下问题是研究记录的最低校验集，不是对核心模型的替换。

### 6.1 原语

1. **尺度声明**：它在输入、规则句、状态变量、动作、资源关系还是玩家理解层面“足够小”？
2. **语料范围**：候选单位来自棋盘游戏、实时电子游戏、运动、角色扮演还是跨媒介语料？
3. **类型与槽位**：它能充当 actor、target、condition、action、effect、feedback 中哪个角色？哪些组合无意义？
4. **同义与等价**：两个表面词是否产生同一状态变换；同一形式变化在不同表征中是否仍被玩家理解为同一操作？
5. **反例**：是否存在一个看似同类的游戏，使该单位必须拆分、合并或改变粒度？

### 6.2 语法与机制

1. **发起者**：动作由玩家、AI、环境、时钟、裁判还是社群触发？
2. **规则种类**：这是正式、内部、社会、外部还是材料规则？它由谁执行？
3. **状态语义**：前置状态、合法性、成本、随机/隐藏信息、效果顺序、作用域和终止怎样表达？
4. **执行证据**：规则只可自然语言理解，还是可模拟、可编译、可证明某性质？
5. **表达取舍**：扩充表达力后，可读性、效率或可判定性付出什么代价？GDL-III 的终止性结果提供了具体警示。[GDL-III](https://www.ijcai.org/proceedings/2017/177)

### 6.3 玩法模板

1. **模式证据**：它在至少哪些不同游戏/局次中反复出现？相似来自结构、玩家策略，还是 genre 命名？
2. **三态分离**：这是设计者意图、规则可供，还是实证观察到的模式？
3. **决策与 agency**：玩家想做的、能做的、看得懂的、后果可归因的行动是否匹配？
4. **反馈类型**：关键回路是系统经济、感知反馈、学习反馈还是社会反馈？时间尺度多长？
5. **关系与失败**：模板依赖、促进、冲突、阻断哪些其他模板；在哪些参数、技能或社群条件下不出现？

### 6.4 游戏

1. **实例化边界**：规则集、一次 match/session、具体发行版本、平台实现和社群实践中，哪一个是当前“游戏”？
2. **媒介与身体**：输入设备、材料阻力、空间、身体技能是否改变了机制，而非只改变呈现？
3. **表征可读性**：玩家如何把抽象过程理解为行动、对象与后果？
4. **社会与文化**：非编码规范、外部制度、玩家自定目标是否改变合法性、风险和胜负意义？
5. **同一性判准**：换主题、界面、参数、随机源或社会约定后，何时仍是同一游戏、同一模板或同一机制？

**[综合判断]** 这套校验让核心链保持短，同时把文献中最有力的反例变成可操作研究字段。链负责讲清结构关系，校验字段负责防止它越界声称“已经解释全部游戏现象”。

## 7. 可检验的工作假设与开放问题

### 7.1 工作假设

1. **[工作假设 H1：相对原语]** 一个单位成为“原语”，取决于分析任务、目标语料和表达语言；可接受的判准是跨案例稳定、组合后仍保留因果/设计解释力、继续拆分不再帮助当前问题，而不是宣称本体上绝对不可分。GOP 的 prototype/grounded 方法和 Ludii 的构造器体系提供两种不同支持。[GOP](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf)；[Ludii Language Reference](https://ludii.games/downloads/LudiiLanguageReference.pdf)
2. **[工作假设 H2：语法分级验证]** 自然语言规则句、类型化半形式表示和可执行 DSL 可以是同一规则的三个验证级别；它们不必在主链中成为三层，但案例应注明当前达到哪一级。BIPED 与 LUDOCORE 证明可玩原型和形式分析可以共享一份规则模型，但其领域限制也说明不能默认普适。[BIPED](https://doi.org/10.1609/aiide.v5i1.12344)；[LUDOCORE](https://adamsmith.as/papers/ieeecig10_ludocore.pdf)
3. **[工作假设 H3：机制角色]** “玩家/agent 发起”与“系统自动运行”是机制内部最值得优先记录的角色差异；它比把所有动词、公式和循环平铺成同级条目更能解释 agency 与 gameplay。该假设需用 sandbox、零玩家游戏、自动战斗和体育裁判案例测试。[Järvinen](https://pure.itu.dk/en/publications/games-without-frontiers-theories-and-methods-for-game-studies-and/)；[Sicart](https://gamestudies.org/0802/articles/sicart)
4. **[工作假设 H4：模板的三重证据]** 玩法模板条目应同时保存“设计者意图—规则可供—实证观察”三类证据；至少两类一致、并有跨游戏对照时，才可暂时称为稳定模板。Patterns 和 emergence 文献分别支持“反复交互”和“规则—局次不等同”的两半论证。[Gameplay Design Patterns](https://doi.org/10.26503/dl.v2003i1.60)；[Juul emergence](https://jesperjuul.net/text/openandtheclosed.html)
5. **[工作假设 H5：实例化不只是换皮]** 平台、界面、身体材料和社会规则有时会改变可调用动作、信息与成本，因此能改变机制身份；“内容/UI/美学/技术/叙事/社会情境”的实例化需要区分装饰变化与结构变化。GOP 的 interface 分析、operational logics 与《The Rule Book》提供三个互补判准。[GOP](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf)；[Operational Logics](https://escholarship.org/uc/item/3cv133pn)；[The Rule Book](https://mitpress.mit.edu/9780262547444/the-rule-book/)
6. **[工作假设 H6：等价是多判准而非单判准]** “同一机制/同一游戏”至少可能指状态转换等价、策略/agency 等价、玩家理解等价、社会实践等价。Formal Game Grammar 能严格处理其中一部分，但不应自动推广到表征和文化层。[Riggins 与 McPherson](https://ieee-cog.org/2020/papers/paper_74.pdf)

### 7.2 开放问题

1. **[开放问题 O1]** 原语目录的首个 reference class 应是什么：传统策略游戏、跨媒介游戏，还是按媒介分别建立、再做映射？若一开始追求跨一切媒介，可能只剩过度抽象词；若按媒介分开，又可能失去本书的统一解释力。
2. **[开放问题 O2]** “机制”是否必须可被 agent 调用？重力、昼夜循环、自动资源增长、元游戏配对与裁判流程应归为机制、procedure、环境规则还是机制的组成条件？
3. **[开放问题 O3]** 一个玩法模板需要多少不同作品、多少独立局次和哪些反例，才足以从“设计意图”升级为经验上稳定的 pattern？Patterns 文献提供结构字段，却没有给统一样本阈值。[Björk 等 2003](https://doi.org/10.26503/dl.v2003i1.60)
4. **[开放问题 O4]** 如何同时表示实时连续动作、身体技能、模拟物理与社会协商，而不把表达语言做得不可读、不可判定或不可运行？GDL-III 的不可判定结果和 PyVGDL 的领域限定说明这是结构性取舍，不只是工程尚未完成。[GDL-III](https://www.ijcai.org/proceedings/2017/177)；[PyVGDL](https://people.idsia.ch/~schaul/publications/pyvgdl.pdf)
5. **[开放问题 O5]** agency 应怎样进入模板证据：以合法选择、策略差异、玩家意图陈述、因果归因准确率，还是行为轨迹多样性测量？现有关系定义指出构成条件，但没有给跨游戏统一量表。[Agency Reconsidered](https://eis.ucsc.edu/papers/nwf-C7-digra09-agency.pdf)
6. **[开放问题 O6]** 社会规则改变到什么程度会改变游戏身份？house rules、speedrun 规范、竞技禁用表、角色扮演安全工具和平台服务条款分别位于“同一游戏变体”与“另一游戏”的哪一侧？
7. **[开放问题 O7]** 何时把资源当作通用建模抽象是有损但有用，何时会遮蔽核心玩法？Machinations 的工具强项明确，但“资源”能否覆盖空间、时机、知识、信任、注意力和身体疲劳，需要逐类反例测试。[Machinations 原始论文](https://doi.org/10.1609/aiide.v7i3.12477)
8. **[开放问题 O8]** 从规则可供到社群稳定玩法之间，需要何种中介概念：策略、惯例、技法、meta、规范，还是多个并列概念？把它们全部叫“玩法模板”可能损失因果阶段。

## 8. 后续精读清单（按项目优先级）

优先级按“能否直接澄清四段链的术语和验证方式”排序，不按学术史重要性或引用量排序。

### P0：先读，直接决定项目词汇和记录格式

| 顺序 | 一手材料与定位 | 精读焦点 | 应形成的项目输出 |
| --- | --- | --- | --- |
| 1 | [Zagal 等，Towards an Ontological Language for Game Analysis，尤其 pp. 1–8](https://expressiveintelligence.github.io/papers/OntologyDIGRA2005.pdf) | prototype theory、grounded theory、middle-out 生长、strong/weak examples、ontology 与 taxonomy/pattern 的区分 | 原语候选条目模板；明确父子、part-of、强弱实例和反例字段 |
| 2 | [Sicart，Defining Game Mechanics](https://gamestudies.org/0802/articles/sicart) + [Järvinen，Games without Frontiers，Chapter 12，pp. 250–278](https://trepo.tuni.fi/bitstream/handle/10024/67820/978-951-44-7252-7.pdf) | agent-invoked method、player mechanic vs system procedure、规则与状态、sandbox 反例 | 一份“机制发起者/触发/状态/反馈”判定表；列出术语不能统一处 |
| 3 | [Björk、Lundgren、Holopainen 2003](https://doi.org/10.26503/dl.v2003i1.60) + [作者当前模式库入口](https://virt10.itu.chalmers.se/index.php/Main_Page) | recurring interaction、结构框架、模式关系、实例化条件与后果 | 玩法模板最小 schema；从已有案例反向试填 3–5 个模板 |
| 4 | [Ludii 2020](https://doi.org/10.3233/FAIA200120) + [Language Reference，pp. 22、327–329、401–409、497–499](https://ludii.games/downloads/LudiiLanguageReference.pdf) + [universality paper](https://arxiv.org/abs/2205.00451) | ludeme 类型、嵌套、宏/变体、逻辑与 metadata 分离、普适性定理的确切定义域 | 抽取一组“相对原语 + 类型签名 + 组合”的正例；写出不可外推清单 |
| 5 | [Stanford GGP Chapter 1](https://logic.stanford.edu/ggp/chapters/chapter_01.html)、[Chapter 2](https://logic.stanford.edu/ggp/chapters/chapter_02.html)、[Chapter 17](https://logic.stanford.edu/ggp/chapters/chapter_17.html)、[GDL-III](https://www.ijcai.org/proceedings/2017/177) | state graph、合法动作、next/goal/terminal、随机/感知/知识，以及表达力—可判定性取舍 | 把本项目基础规则句映射到 GDL 概念；记录无法自然表达的案例 |
| 6 | [Wardrip-Fruin 等，Agency Reconsidered，尤其 pp. 1–5](https://eis.ucsc.edu/papers/nwf-C7-digra09-agency.pdf) | Murray / Church 两条谱系、欲求—行动匹配、界面/模型/预期、即兴 | 给玩法模板增加 agency 检查题；设计同动作数但 agency 不同的对照例 |
| 7 | [Juul，The Open and the Closed](https://jesperjuul.net/text/openandtheclosed.html) + [Dormans，Simulating Mechanics to Study Emergence](https://doi.org/10.1609/aiide.v7i3.12477) | emergence/progression、weak emergence、作者惊讶的错误判准、规则模拟与经济反馈 | 建立“设计意图/可供动态/模拟轨迹/观察实践”四栏记录 |
| 8 | [Stenros 与 Montola，The Rule Book](https://doi.org/10.7551/mitpress/14730.001.0001) | formal/internal/social/external/material 五类规则的定义、边界与跨媒介案例 | 给每个游戏案例增加 rule-kind 与 enforcement source 字段；挑数字/桌面/运动各一例试填 |

### P1：第二轮，补齐定义、体验与形式原型之间的桥

| 顺序 | 一手材料与定位 | 精读焦点 | 应形成的项目输出 |
| --- | --- | --- | --- |
| 9 | [Suits 1967，pp. 148–156](https://doi.org/10.1086/288138)、[Juul 2003 全文 PDF](https://dl.digra.org/index.php/dl/article/download/65/65/62)、[Stenros 2016](https://doi.org/10.1177/1555412016655679) | 目标、限制、态度；经典模型六特征；定义对象和用途 | 一组边界案例矩阵；明确四段链不是游戏必要充分定义 |
| 10 | [Hunicke、LeBlanc、Zubek，MDA](https://cdn.aaai.org/Workshops/2004/WS-04-04/WS04-04-001.pdf) | designer/player 反向观察、mechanics/dynamics/aesthetics 定义、八类 aesthetic vocabulary | 用同一案例同时按 MDA 与四段链编码，标出信息增益和损失 |
| 11 | [Lantz 与 Zimmerman，Rules, Play and Culture，pp. 1–5](https://ericzimmerman.com/assets/pdfs/RulesPlayCulture.pdf) | 三者作为互联 lenses 而非阶段；play 的策略、审美、心理、社会、材料面 | 为游戏案例建立 rules/play/culture 三栏证据，不改动主链 |
| 12 | [Church，Formal Abstract Design Tools](https://www.gamedeveloper.com/design/formal-abstract-design-tools) + [Cook，The Chemistry of Game Design](https://www.gamedeveloper.com/design/the-chemistry-of-game-design) | formal 的非数学含义；intention、perceivable consequence；skill atom 的学习回路 | 区分 design tool、pattern、primitive；形成玩家反馈与学习检查表 |
| 13 | [Wardrip-Fruin 等，Defining Operational Logics](https://escholarship.org/uc/item/3cv133pn) | 抽象过程、authoring strategy、domain representation、audience understanding | 对两个形式近似但表征不同的游戏做 operational-logic 对照 |
| 14 | [BIPED](https://doi.org/10.1609/aiide.v5i1.12344) + [LUDOCORE](https://adamsmith.as/papers/ieeecig10_ludocore.pdf) + [PyVGDL](https://people.idsia.ch/~schaul/publications/pyvgdl.pdf) | 同一规则模型怎样同时支持试玩、轨迹生成和自动分析；各自领域限制 | 选一个小型机制，比较三种表示需要哪些原语与默认假设 |
| 15 | [Riggins 与 McPherson，Formal Game Grammar and Equivalence](https://ieee-cog.org/2020/papers/paper_74.pdf) | meaningful agency 等价、game-tree 变换、有限离散且无隐藏信息的范围 | 起草“同一机制/模板/游戏”的多判准等价表 |

### P2：第三轮，扩充历史、生成与实践边界

| 顺序 | 一手材料与定位 | 精读焦点 | 应形成的项目输出 |
| --- | --- | --- | --- |
| 16 | [Huizinga，Homo Ludens 出版社页](https://www.routledge.com/Homo-Ludens-ILS-86/uizinga/p/book/9780415487559) + [Caillois，Man, Play and Games 出版社导览](https://www.press.uillinois.edu/books/?id=p070334) | play 与文化秩序；agon/alea/mimicry/ilinx；paidia–ludus | 防止把动机/游玩形态分类误作结构 ontology；挑身体与即兴反例 |
| 17 | [Aarseth、Smedstad、Sunnanå 2003](https://doi.org/10.26503/dl.v2003i1.66) + [Elverdam 与 Aarseth 2007](https://doi.org/10.1177/1555412006286892) + [Aarseth 与 Grabarczyk 2018](https://doi.org/10.26503/dl.v2018i1.973) | typology 的维度/取值与 meta-model 的描述层级有何不同；开放分类、研究对象定位与设计组合 | 建立游戏级 metadata 与理论尺度栏，检查它们是否被误当作原语目录 |
| 18 | [Dormans 2010，§4–6](https://pcgworkshop.com/archive/dormans2010adventures.pdf) | mission graph grammar 与 shape grammar 的分工、生成物怎样耦合 | 用一个玩法模板生成两种任务图和空间实例，验证“实例化”含义 |
| 19 | [Koster 的历史自述](https://www.raphkoster.com/2012/01/24/an-atomic-theory-of-fun-game-design/) + [Bura 的 game diagrams](https://www.stephanebura.com/diagrams/) | 设计 grammar 的实践起点、作者自我修正、napkin 图的表达与盲点 | 写“设计图解不等于形式语法”的术语旁注；抽取可迁移图示约定 |
| 20 | [The 400 Project](https://www.finitearts.com/Pages/400page.html) | scope、attribution、trumping、冲突与矛盾的记录方式 | 为本项目未来的设计建议建立“适用条件/冲突/例外/证据”格式 |

## 9. 建议的精读卡片格式

为保留从来源到假设的路径，每次精读建议只新增研究卡片或文献笔记，不直接改写核心模型。每张卡片至少包含：

```text
来源：作者、标题、年份、稳定链接、页码/章节
产物类型：definition / ontology / typology / DSL / pattern / simulation / tool / lens
来源事实：作者明确声称什么
分析单位：规则、动作、状态、玩家、局次、完整游戏、社群实践……
适用范围：媒介、玩家数、信息条件、时间模型、有限性等
成功判准：可执行、可判定、解释案例、设计实用、跨案例复现……
不能回答：作者明示限制 + 本项目识别的外推风险
概念分歧：同名异义或异名近义
四段链接口：原语 / 语法 / 机制 / 玩法模板 / 游戏 / 横切检查
反例与边界：至少一个
综合判断：本项目如何使用，但不归给原作者
工作假设 / 开放问题：下一步如何被案例证伪
```

## 10. 当前结论

**[综合判断]** 基础文献并不要求本项目把四段链扩写成百科全书式总模型。相反，它们支持一种更克制的架构：

```text
原语 --类型化组合与规则语义--> 机制 --跨机制编排与反馈--> 玩法模板 --媒介、内容与情境实例化--> 游戏
          ↑                         ↑                                  ↑
   可执行性/作用域检查       agency/动态/模式证据              rules–play–culture 检查
```

上图中的下排不是新层。它们是三组横切判据：左侧防止“语法”停留在比喻；中间防止从规则直接断言玩家行为；右侧防止把具体游戏约化为封闭代码。由此，四段链仍保持清晰、简洁、差异化和实用性，同时对 ontology、DSL、玩家经验和社会材料规则的已有研究保持可检验的开放。
