# 从资深玩家到原型设计者：小型原创玩法原型的渐进学习路径

> 文档类型：Phase 1 教学研究与课程假设  
> 研究对象：玩过很多游戏、但没有系统设计训练的学习者  
> 目标成果：一个经过外部测试、规则闭合、可独立运行的小型原创玩法原型  
> 研究日期：2026-07-20  
> 模型边界：本文不修改“原语 → 机制 → 玩法模板 → 游戏”，也不把它规定为唯一的创作顺序。

## 0. 证据标记与结论边界

本文使用以下标记，避免把“某课程这样教”误写成“这种教法已被证明最有效”。

- **[来源事实]**：一手材料明确记载的事实。
- **[实证线索]**：原始研究报告的数据或观察；仍须同时阅读其样本与方法限制。
- **[教学来源]**：大学课程、作业或教师一手反思中实际采用的方法；证明“有人这样实施过”，不单独证明因果效果。
- **[实践来源]**：教师、设计者或项目团队对自己实践的原始记录；可说明过程与经验，不能单独证明教学效果。
- **[项目约束]**：本项目已经确立、本文必须遵守的读者、模型或成果边界。
- **[项目综合]**：依据多项来源、结合本项目读者与结业目标提出的方案。
- **[工作假设]**：值得试行，但目前证据不足、需要在本项目教学实践中验证的具体门槛或剂量。
- **[开放问题]**：现有材料不能可靠回答的问题。

证据边界也很明确：本次检索没有找到能直接比较“案例分析、规则修改、纸面原型、系统建模、试玩、反思日志”整套顺序、且以成年资深玩家新手完成原创原型为结果的强因果研究。最贴近目标人群的研究多为教师访谈、课堂个案或学生自陈；最具体的教学路径主要来自公开课程。因此，本文给出的是**有一手教学材料和有限实证线索支撑的课程设计假设**，不是已被实验确认的唯一最佳路径。

## 1. 结论先行

**[项目综合] 核心教学问题不是让学习者“再知道更多游戏”，而是让他反复完成这条可核查的转换：**

```text
具体规则与游玩事件
        ↓ 解释
暂时的结构判断与体验假设
        ↓ 只改一个关键关系
可玩的低成本版本
        ↓ 外部观察
保留、撤回或重写判断
```

这条教学闭环有四个要点。

1. **先从熟悉游戏取得分析距离，再要求原创。** 资深玩家的案例库存和动机是资产，但熟练游玩不等于能解释规则怎样产生玩家行为；教师访谈还记录了“把分析写成好恶或功能清单”“把擅长操作误认为具有设计洞察”等典型困难。[Zagal 与 Bruckman 的 12 名教师访谈](https://gamestudies.org/0802/articles/zagal_bruckman)提供了最直接但仍属定性研究的依据。
2. **先做受控修改，再承担空白页。** MIT 与 CMU 的入门课程都把“修改既有游戏”放在团队原创项目前；MIT 还要求学习者比较两个版本与预先声明的体验目标。[MIT CMS.301 A/B 试玩作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/51c8e0a79962c8957bcd32eb9d0619b2_MITCMS_301S16_Assigment7.pdf)、[CMU 53-110 课程说明](https://courses.ideate.cmu.edu/53-110/n2020/index.html%3Fp%3D8.html)。
3. **原型首先是回答问题的装置，不是缩小版成品。** Eric Zimmerman 的作者原文主张让第一版只覆盖主要不确定性；一项对 27 名从业者、学生和教师的定性访谈也发现，设计者常用原型聚焦某个具体功能或问题，而非代表整部游戏。[Zimmerman, *Play as Research*](https://www.ericzimmerman.com/assets/pdfs/Iterative_Design.pdf)、[Manker, 2011, PDF pp. 6–10](https://dl.digra.org/index.php/dl/article/download/598/598/595)。
4. **结业评价应看可运行性、证据和迭代理由，而不是画面完成度或教师主观觉得“好玩”。** MIT CMS.608 明确按团队协作、严谨迭代和对反馈的响应评价，而不按游戏最终是否“好玩”；其原创游戏作业还要求保留规则版本、测试问题与修改结果，并进行盲测。[MIT CMS.608 课程说明](https://ocw.mit.edu/courses/cms-608-game-design-fall-2010/pages/syllabus/)、[原创游戏作业](https://ocw.mit.edu/courses/cms-608-game-design-spring-2008/9ab6ae82308f2d0454f2477398f7a8f8_MITCMS_608s08_proj04.pdf)。

**[项目综合] 推荐主路径：**

```text
诊断 → 有目的的案例分析 → 单规则修改与 A/B → 机制重组
    → 纸面微原型与轻量系统图 → 小型原创 → 外部测试阶梯
    → 盲测与证据答辩
```

它是一条教学螺旋，不是对核心模型的改写。学习者会多次用“原语 → 机制 → 玩法模板 → 游戏”解释已有案例和自己的版本，但可以从体验意图、某个动作、材料限制或机制变体进入创作。本文采纳项目研究笔记提出的警告：**分析模型不等于设计流程**；参见[结构模型研究笔记](../foundations/structural-models.md)及项目的[案例驱动研究螺旋](../../docs/adr/0007-case-driven-research-spiral.md)。

## 2. 目标能力：结业者究竟要会什么

### 2.1 从“玩家经验”转化出的六项能力

**[项目综合]** 一个合格的入门设计者不必先掌握完整术语表，但应能展示以下六项可观察能力：

1. **描述**：把“我觉得爽/无聊”改写为具体规则、状态变化、可选行动和实际游玩事件。
2. **解释**：提出规则关系怎样促成决策、反馈和反复活动的暂时解释，同时承认替代解释。
3. **干预**：为了一个明确问题，只改变足够少的结构，而不是同时堆叠功能。
4. **外化**：用纸面原型、简化数字原型或局部系统图，把口头设想变成别人能接触、质疑和运行的对象。
5. **取证**：在不过度指导玩家的条件下观察，区分行为记录、玩家自述和设计者推断。
6. **修订**：用证据说明为什么保留、撤回或再次测试某项改变，并能指出尚未解决的问题。

这些能力与项目现有结业要求一致：成果应是“小规模、规则闭合、具有原创性、可实际试玩”的原型，并能解释结构组合、设计理由、测试证据和迭代过程；见[ADR-0002](../../docs/adr/0002-capstone-playable-prototype.md)。

### 2.2 这类学习者的特殊优势与风险

**[实证线索]** Zagal 与 Bruckman 访谈了来自 8 个国家、10 所高校的 12 名游戏研究课程教师。受访者认为既有游戏经验能提高动机并提供大量案例，但也可能让学习者难以退出“玩家/粉丝”位置，容易局限于熟悉类型、以成败或好恶代替分析，并难以说清玩法经验怎样形成。该研究是教师经验的定性归纳，研究对象主要是 game studies 课程，并未直接测量原创原型能力，故只能用来诊断起点，不能证明某条设计课程的效果。[原文的 Methods、Role of Prior Experience、Practices and Discourse of Play 三节](https://gamestudies.org/0802/articles/zagal_bruckman)。

**[实证线索]** Hullett、Kurniawan 与 Wardrip-Fruin 让一个自愿参加的小组连续八次接触并讨论德式桌游，前后调查显示其回答出现更多机制中心倾向；但作者明确承认小组自我选择、起点已经较高，结果“远非定论”。这只支持一个谨慎判断：让数字游戏资深玩家接触结构可见、由玩家亲自执行规则的桌面案例，可能有助于拉开分析距离，不能据此声称桌游训练必然改善设计能力。[原始论文，尤其 PDF pp. 5–6](https://dl.digra.org/index.php/dl/article/download/491/491/488)。

**[项目综合]** 因此，课程不应把玩家经验清零，也不应让它自动取得解释权。最合适的处理是把熟悉游戏当“锚点案例”，再加入跨媒介对照和边界案例，要求每个判断都回到规则或实际游玩证据。这也符合本项目的[跨媒介语料决定](../../docs/adr/0003-cross-media-research-corpus.md)与[多角色案例集决定](../../docs/adr/0008-use-multi-role-case-sets.md)。

## 3. 六种教学方法的比较

| 方法 | 最适合训练什么 | 一手教学或研究依据 | 主要失效方式 | 本路径中的位置 |
|---|---|---|---|---|
| 案例分析 | 从消费性评价转向规则—行为—体验解释；建立共享语言 | MIT 要求从实际游玩中提取 6–8 个机制，并写出玩家做什么及预期结果；教师访谈认为结构词汇、框架和游玩日志有助于具体化分析。[MIT *Takenoko* 分析作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/4fb5a04228b7fd2b2027c9cb9e674de9_MITCMS_301S16_Assigment2.pdf)、[Zagal & Bruckman](https://gamestudies.org/0802/articles/zagal_bruckman) | 写成评测、剧情复述或功能清单；先套术语后找证据；只分析熟悉类型 | 第一个正式台阶，并贯穿后续复盘 |
| 规则修改 | 让学习者第一次看到“局部规则变化—行为差异—体验差异”的因果链；降低空白页负担 | MIT A/B 作业要求修改既有游戏、预先声明体验结果、至少找 3 名目标玩家比较两个版本；CMU 入门课先个人修改既有游戏，再由小组原创。[MIT A/B 作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/51c8e0a79962c8957bcd32eb9d0619b2_MITCMS_301S16_Assigment7.pdf)、[CMU 53-110](https://courses.ideate.cmu.edu/53-110/n2020/index.html%3Fp%3D8.html) | 同时改多项；把“不同”当“更好”；事后才发明目标；测试版本不等价 | 案例分析之后、原创之前的第一座桥 |
| 纸面原型 | 低成本外化核心动作、回合、资源和信息关系；加快版本淘汰 | MIT 的纸面原型从玩家动词出发，限制说明与试玩时长，要求给团队外人员测试；Zimmerman 主张第一版只做足以回答最大不确定性的细节。[MIT 纸面原型作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/9b051e4b2b363f44bd2a072be200b09a_MITCMS_301S16_Assigment6.pdf)、[Zimmerman](https://www.ericzimmerman.com/assets/pdfs/Iterative_Design.pdf) | 把纸面版本当成最终媒介的等价物；无法代表实时控制、物理手感、隐蔽信息或自动化复杂度；制作组件反而过精 | 规则修改/重组之后，用于回答首要不确定性 |
| 系统建模 | 显示资源流、状态、门槛和反馈环；让讨论定位到具体关系 | Dormans 在五年课程实践中先让学生建模已有游戏，再建模自己的原型；即使图不准确，也能启动更精确的设计讨论。但作者明确说没有收集量化效果数据，并指出掌握图示需要时间。[Dormans 2012, ch. 8.3, PDF pp. 5–9](https://pure.uva.nl/ws/files/1167843/102095_13.pdf) | 把图当作游戏本身或真理；先学复杂符号再做可玩物；模型只覆盖内部经济，却误称覆盖全部玩法 | 纸面版本已能运行之后，以“局部问题图”加入，而非先修门槛 |
| Playtest（试玩测试） | 发现设计者无法直接推演的涌现行为；练习从玩家视角看规则 | MIT、CMU 都以多轮内部—外部测试推进项目；一项 16 名高中生、两个小组的探索性个案发现，设计本身不会自动带来玩家视角，试玩能促发视角采择，但较复杂反思需要教师支架。[MIT 项目流程](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/88a0f75c6b17e7d57011835c7e0ec236_MITCMS_301S16_Assigment8.pdf)、[CMU final project](https://courses.ideate.cmu.edu/53-110/n2020/index.html%3Fp%3D27.html)、[Dishon & Kafai 2020](https://doi.org/10.1016/j.compedu.2020.103810) | 设计者现场教学或辩护；只问“好玩吗”；用熟人赞美代替观察；被单个意见牵着振荡；太晚才测 | 从第一个变体起每轮出现，最后升级为盲测 |
| 反思日志 | 保存假设—版本—观察—决定链；把失败变成可复用知识 | GameLog 在两门大学课程中的研究发现，学生主观认为反思写作有助于退出纯玩家立场，文本也呈现计划/假设、实验、比较和分析等多种方式；证据主要是课堂文本与学生感知，不是原型质量的对照试验。[2007 年先导报告](https://doi.org/10.1145/1274940.1274950)、[2011 年扩展研究](https://doi.org/10.1162/ijlm_a_00063)。MIT CMS.608 也要求项目成员持续记录修改、反馈与迭代应用。[课程说明](https://ocw.mit.edu/courses/cms-608-game-design-fall-2010/pages/syllabus/) | 写成流水账、成功叙事或事后合理化；没有版本号、原始观察和替代解释；只记录“改了什么” | 从诊断期开始，每次测试后填写结构化短日志 |

### 3.1 为什么不能只选一种

**[项目综合]** 六种方法形成的是互补回路，而不是排行榜：案例分析提供语言，规则修改提供受控干预，纸面原型提供可接触对象，系统图提供局部结构视角，试玩提供外部证据，日志保存推理链。删掉任一环节都有典型后果：只分析而不做，会停留在解释；只做而不测，会把作者意图当玩家经验；只测而不记，会重复同一争论；只建模而不玩，会把表示误作对象。

**[来源事实]** MIT CMS.301 的实际课程结构也采用了相近的前后关系：前半段用短作业训练分析、机制、原型和测试方法，后半段连续推进一个项目，并通过多次讲评（critique）与外部测试迭代。[课程日历](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/pages/calendar/)、[教师反思](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/pages/instructor-insights/)。这仍是课程设计先例，不是顺序效果的实验验证。

### 3.2 三项更贴近课堂过程的研究线索

**[实证线索]** Wetzel 在 12 次课堂干预、合计 164 名学生中使用四个受约束的“game design games”，让学生修改关卡、数值或机制。归纳式主题分析显示，学生会遇到小改动带来的意外复杂性、开始重视实验，但仍难以从自身玩家视角切换到设计者视角。研究无对照组，也没有测量迁移到独立原创项目的效果；它支持把受约束修改用作早期练习，却不能证明其优于其他方法。[Wetzel 2025](https://doi.org/10.1145/3723498.3723713)。

**[实践来源]** Larsen 与 Majgaard 基于五年本科课程反思指出，完全开放的“设计一个电脑游戏”容易造成挫败和失焦；其课程改用明确媒介/玩家/交互限制，先让小组提出至少三个概念并做纸面原型，再滚动互测、择一开发，并安排至少五次测试。作者把工作定位为面向实践的理论贡献，依据反思实践、学生评价和作品案例，不是受控效果研究。[Larsen & Majgaard 2016，Didactical Approach](https://designsforlearning.nu/articles/dfl.68)。因此，“三个概念”“明确约束”“多次测试”在本文中是有教学先例的综合方案，仍不是普遍有效的科学阈值。

**[实证线索]** Majgaard 对一门面向无编程经验、但自幼长期玩游戏的一年级课程进行了设计型研究，并对 6 名学生做定性邮件访谈。目标群体测试暴露了设计者难以从自测中发现的教程难度、意外策略和意义理解；作者同时认为，仅在制作中行动不足以形成清楚的分析表达，还需要展示、讨论和事后反思。样本小、课程同时教授编程，不能分离各环节效果，但与本项目目标人群和“试玩后结构化反思”的问题高度贴近。[Majgaard 2014，pp. 271–280](https://files.eric.ed.gov/fulltext/EJ1035649.pdf)。

## 4. 适合本项目的渐进学习路径

**[工作假设]** 以 8 个学习台阶、约 40–60 小时为首轮试行基准。台阶不按周历硬切；学习者只有在完成“最小通过证据”后才进入下一阶。制作与记录可以由个人完成，但从台阶 2 起就要接触测试者，台阶 6–7 必须使用不了解设计意图的外部玩家。具体时长和测试数量需要通过首批学习者校准。

| 台阶 | 核心任务 | 唯一主要学习目标 | 必交证据 | 最小通过标准 | 依据性质 |
|---|---|---|---|---|---|
| 0. 起点诊断 | 选一款非常熟悉的游戏，写一页“为什么它有效”，再把同一段重写为规则—行为—体验证据卡 | 暴露评测语言、类型偏见与结构表达缺口 | 原文、重写稿、自评差异 | 至少把一项好恶判断改写为可观察事件和可核对规则 | **[项目综合]**；问题诊断来自[Zagal & Bruckman](https://gamestudies.org/0802/articles/zagal_bruckman) |
| 1. 有目的的案例分析 | 用一个熟悉锚点、一个跨媒介对照、一个边界案例回答同一结构问题 | 学会以问题组织比较，而非罗列相似点 | 三张证据卡、一条暂时结论、一个反例 | 结论同时包含规则依据、游玩观察和替代解释；不靠类型名称代替解释 | **[项目综合]**；练习先例来自[MIT 分析作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/4fb5a04228b7fd2b2027c9cb9e674de9_MITCMS_301S16_Assigment2.pdf)及[ADR-0008](../../docs/adr/0008-use-multi-role-case-sets.md) |
| 2. 单规则修改与 A/B | 对一个短小、规则清楚的既有游戏只改一个关键关系；先写预测，再比较原版与变体 | 建立“干预—结果”的基本纪律 | 版本差异表、测试脚本、至少 3 名目标玩家的观察、决定 memo | 能说明哪些结果支持/反驳预测；没有把所有差异都归因于改动 | **[教学来源]** 直接取自[MIT A/B 作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/51c8e0a79962c8957bcd32eb9d0619b2_MITCMS_301S16_Assigment7.pdf) |
| 3. 可追溯的机制重组 | 从两款规则简单的游戏各取一个可明确描述的关系，做成 5–10 分钟新变体 | 在“改动”和“原创”之间练习组合 | 父项来源图、删改清单、可玩版本、一次设计者/设计团队之外的测试 | 两个来源可追溯，但新原型有自己的核心决策，不是换主题拼盘 | **[教学来源 + 项目综合]**；来自 MIT 的[*Scrabbleship* 作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/4faebe488c9944a5d272cdc6d036204a_MITCMS_301S16_Assigment3.pdf) |
| 4. 纸面微原型与局部系统图 | 从一个玩家动词和一个最大不确定性出发，做 5–10 分钟纸面原型；能玩后再画一张只覆盖该问题的状态/资源/反馈图 | 学会让表示服务于测试问题 | v0 原型、问题句、系统图、一次试玩后的图与规则修订 | 原型能回答一个问题；图中每条关键关系能指回具体规则或观察 | **[教学来源 + 项目综合]**；[MIT 纸面原型](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/9b051e4b2b363f44bd2a072be200b09a_MITCMS_301S16_Assigment6.pdf)、[Dormans ch. 8.3](https://pure.uva.nl/ws/files/1167843/102095_13.pdf) |
| 5. 三案择一的小型原创 | 先提出三个概念，每个只写玩家反复做什么、关键关系、目标体验、最大不确定性和最小可玩范围；按可测试性与范围择一 | 从结构问题而非内容愿望启动原创 | 三张概念卡、选择理由、v0 规则、首次内部测试 | 10–20 分钟内能经历核心循环；至少一项核心决策关系不是既有游戏的原样复制 | **[项目综合]**；“先多案再选、低保真互测”的先例见[MIT final project](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/88a0f75c6b17e7d57011835c7e0ec236_MITCMS_301S16_Assigment8.pdf)及[Larsen & Majgaard 2016](https://designsforlearning.nu/articles/dfl.68) |
| 6. 测试阶梯与两轮实质迭代 | 先内部查可运行性，再由不了解设计意图者外测，最后让目标玩家在设计者不提示的条件下盲测规则 | 学会从外部证据而非辩护推进版本 | 每轮脚本、事件记录、玩家自述、版本差异、决策 memo | 至少 2 次内部测试、2 次外部会话、外部玩家合计不少于 3 人；至少一次为盲测；产生两个有实质差异的版本 | 数量为 **[工作假设]**；测试阶梯依据[CMU final project](https://courses.ideate.cmu.edu/53-110/n2020/index.html%3Fp%3D27.html)与[MIT final report](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/a6b60b47fd07af965827d37a94e766ae_MITCMS_301S16_Assign8_Stp4.pdf) |
| 7. 结业盲测与证据答辩 | 陌生玩家只靠最终规则启动并结束一局；设计者随后用证据解释当前版本与边界 | 把原型、模型和迭代史交给他人核查 | 最终原型、规则、结构说明、测试档案、版本史、反思与下一问题 | 通过下文全部硬门槛，并在 rubric 中达到合格 | **[项目综合]**；盲测先例见[MIT 2008 原创游戏作业](https://ocw.mit.edu/courses/cms-608-game-design-spring-2008/9ab6ae82308f2d0454f2477398f7a8f8_MITCMS_608s08_proj04.pdf) |

### 4.1 “原创”的可教、可评定义

**[项目综合]** 入门结业不要求不可证明的“世界首创”。这里把原创性操作化为**可追溯的结构性贡献**：学习者能公开主要参考，并指出自己在哪个核心行动、规则关系、反馈结构或机制编排上作了有意改变；该改变使玩家面对的决策或反复活动产生可观察差异。仅换美术、故事名词或题材不算；有来源的重组、变形或跨媒介迁移可以算。

这个定义同时避免两端：一端是把 reskin 当原创，另一端是因害怕“以前一定有人做过”而拒绝完成。MIT 的机制重组作业同样把来源影响的可追溯、作品自身身份与简洁性列为评价点，但本文的具体门槛仍是本项目综合。[MIT *Scrabbleship* 作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/4faebe488c9944a5d272cdc6d036204a_MITCMS_301S16_Assigment3.pdf)。

### 4.2 “经过测试”的最低含义

**[工作假设]** “经过测试”不等于已证明市场适配或统计显著。入门结业只要求形成足以支持一次设计判断的证据链：

- 至少两个内部测试，先排除无法开始、无法继续或无法结束的问题；
- 至少两个外部测试会话，外部玩家合计不少于三人；
- 至少一次盲测，玩家只依赖当前规则或游戏内教学，设计者不提供策略性提示；
- 至少两个有实质差异的版本，并能把一项改变指回先前证据；
- 报告不隐去失败、异议或未解决问题。

数量综合了 MIT A/B 作业的“至少 3 名目标玩家”、CMU final project 的多轮内部测试与至少两次外部会话、以及 MIT 原创作业的陌生玩家盲测要求。[MIT A/B](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/51c8e0a79962c8957bcd32eb9d0619b2_MITCMS_301S16_Assigment7.pdf)、[CMU final](https://courses.ideate.cmu.edu/53-110/n2020/index.html%3Fp%3D27.html)、[MIT blind test](https://ocw.mit.edu/courses/cms-608-game-design-spring-2008/9ab6ae82308f2d0454f2477398f7a8f8_MITCMS_608s08_proj04.pdf)。这些数量只用于训练迭代纪律，不能支持普遍玩家结论。

## 5. 练习库：每次只训练一个主要动作

### 5.1 规则—行为—体验证据卡

**[项目综合]** 每张卡只回答一个问题：

| 字段 | 要求 |
|---|---|
| 可核对规则 | 引用规则书、游戏内规则或准确记录当前版本 |
| 游玩事件 | 谁在什么状态下做了什么，随后发生什么 |
| 结构解释 | 哪个原语经何种约束/关系形成机制，又怎样参与反复活动 |
| 体验推断 | 玩家可能面临何种压力、选择或预期；不得冒充玩家自述 |
| 替代解释/反例 | 还有什么因素可能产生同一现象；何种情况会推翻判断 |

它把本项目的结构语言用于“提出可检查解释”，而不是要求学习者先给全部元素分类。MIT 的分析作业要求同时描述玩家行动、机制的预期结果和跨游戏实例；本卡在此基础上加入证据与反例栏，以符合本项目的证据纪律。[MIT 分析作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/4fb5a04228b7fd2b2027c9cb9e674de9_MITCMS_301S16_Assigment2.pdf)、[ADR-0006](../../docs/adr/0006-evidence-informed-working-theory.md)。

### 5.2 单变量规则手术

**[项目综合]** 给一款 5–15 分钟的公共规则游戏做一次“规则手术”：删除一条规则、把一个参数乘/除以二、改变执行顺序，或只改变一个对象之间的关系。先写“如果 X，则玩家会更常/更少做 Y，因为 Z”，再做 A/B。MIT 的纸面原型讲义把“删规则、倍增/减半参数、改顺序或交互”列为快速修订策略，其循环从可证伪问题开始。[MIT CMS.611J *Paper Prototyping and Playtesting*](https://ocw.mit.edu/courses/cms-611j-creating-video-games-fall-2014/348ee58d265e61e4760d196bd97b1ad1_MITCMS_611JF14_Paper_Prot.pdf)。

### 5.3 不确定性优先原型

**[项目综合]** 在动手前补完一句话：“如果只能从这版学到一件事，我要知道 ______。”原型只能实现回答它所需的部分。Manker 的访谈资料显示，从业者把原型视为聚焦特定设计空间、具体功能或问题的过滤器；Zimmerman 也主张第一版先处理主要不确定性。[Manker 2011](https://dl.digra.org/index.php/dl/article/download/598/598/595)、[Zimmerman 2003](https://www.ericzimmerman.com/assets/pdfs/Iterative_Design.pdf)。

### 5.4 局部系统图

**[项目综合]** 只画本轮问题涉及的：

- 对象、资源或关键状态；
- 玩家可执行的动作；
- 产生、消耗、转换、门槛和信息关系；
- 至少一条可能的正/负反馈路径；
- 图中仍无法表示的实时手感、空间、社交协商或叙事信息。

图完成后必须回答“它将指导哪项改动或测试”；答不出就缩图或不用。Dormans 的教学反思支持建模对精确讨论和内部经济/反馈分析的价值，也明确承认学习成本与未做量化验证；因此本文不把 Machinations 或任何正式记法设为入门前置。[Dormans 2012, pp. 201–205](https://pure.uva.nl/ws/files/1167843/102095_13.pdf)。

### 5.5 盲规则传递

**[教学来源 + 项目综合]** 把规则和组件交给从未玩过该版本的人，设计者只观察，不补规则。记录：第一次停顿、误解的目标、非法操作、询问、回查位置和自行恢复方式。MIT 2008 原创作业与 2016 final report 都要求由未接触项目的人仅靠规则学习或测试。[MIT 2008](https://ocw.mit.edu/courses/cms-608-game-design-spring-2008/9ab6ae82308f2d0454f2477398f7a8f8_MITCMS_608s08_proj04.pdf)、[MIT 2016](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/a6b60b47fd07af965827d37a94e766ae_MITCMS_301S16_Assign8_Stp4.pdf)。

## 6. 反馈与记录协议

### 6.1 一次 playtest 的四个阶段

**[项目综合]** 每次测试都用同一协议，降低“试玩会”变成推销会的风险。

1. **测试前——锁定问题。** 写版本号、目标玩家、一个主要问题、预测、支持/反驳信号，以及本轮明确不测什么。
2. **测试中——先记事件。** 观察者记录时间、行动、停顿、回退、规则询问、关键状态和原话；主持人不教策略，不解释设计意图。Valve 的第一方流程资料同样强调外部测试、模拟家庭环境、不给提示，并警告不要只依赖问答。[Speyrer & Jacobson, Valve GDC 2006](https://steamcdn-a.akamaihd.net/apps/valve/2006/GDC2006_HL2DesignProcess.pdf)。
3. **测试后——先回忆，后评价。** 先问“你以为什么是目标？”“何时不知道下一步？”“当时考虑了哪些行动？”“你预计该动作之后会发生什么？”，最后才问主观感受；避免“这个奖励是不是太少？”之类暗示答案的问题。MIT A/B 作业要求观察两个版本并在分开的半结构访谈中追问。[MIT A/B 作业](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/51c8e0a79962c8957bcd32eb9d0619b2_MITCMS_301S16_Assigment7.pdf)。
4. **测试后处理——分开事实和决定。** 先合并重复事件，再列至少两个解释，最后选择“保留 / 撤回 / 改后再测 / 暂不处理”。不要把玩家给出的解决方案直接等同于问题诊断。

**[实证线索]** Dishon 与 Kafai 的探索性个案提醒：仅仅让学生设计并不会自动产生玩家视角；试玩中的“失败”怎样被框定，以及教师是否支架反思，会影响学习者是否进行更复杂的视角采择。其样本只有 16 名 14–15 岁学生，重点是 perspective-taking 而非设计熟练度，所以这里仅据此支持“试玩后需要引导解释”，不外推为成年课程的确定效果。[论文摘要、Highlights 与案例方法](https://doi.org/10.1016/j.compedu.2020.103810)。

### 6.2 同伴讲评（critique）的语言格式

**[项目综合]** 反馈者按四句式发言：

```text
我观察到……（行为、状态或原话）
我暂时解释为……（可被反驳）
我不确定……（缺失证据或替代解释）
下一轮若只验证一件事，可以……（测试建议，不替设计者定方案）
```

设计者先复述自己听到的问题，再回答，不现场辩护。主持人轮流点名、限制发言时长，并主动邀请不同游戏背景的测试者。MIT CMS.301 的教师反思指出，同伴反馈本身是学习目标，且需要小组化和主持，以免强势声音支配讨论。[MIT Instructor Insights](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/pages/instructor-insights/)。NYU 的公开试玩活动也明确欢迎不同专业程度和背景的设计者与玩家，说明“多样试玩者”是其正式反馈实践的一部分；这不是效果研究。[NYU Playtest Thursdays](https://gamecenter.nyu.edu/events/playtest-thursdays/)。

### 6.3 迭代日志模板

**[项目综合]** 日志应短、同步填写、可追溯；每次测试一页即可。

```markdown
## 版本 / 日期 / 测试对象
- 本轮问题：
- 变更：
- 预测与反驳信号：
- 观察：行为 / 状态 / 原话（与推断分开）
- 我的解释：
- 替代解释或异常案例：
- 决定：保留 / 撤回 / 修改后再测 / 暂缓
- 决定依据：
- 下一问题：
```

反思日志的价值不在字数，而在保存“当时的预测”和失败路径，阻止结业报告事后把一切写成必然成功。MIT 的写作指南要求说明意图、实际测试、改动与原因，并建议保留失败、具体例子、反例和可复现过程。[MIT *Writing About Your Game*](https://ocw.mit.edu/courses/cms-608-game-design-spring-2008/f649475c2cdf807c3fce515330b7bd5f_games.pdf)。GameLog 研究则提供了反思写作能承载计划/假设、实验和洞察的有限课堂证据。[2007 年报告](https://doi.org/10.1145/1274940.1274950)、[2011 年扩展研究](https://doi.org/10.1162/ijlm_a_00063)。

## 7. 常见误区、诊断信号与干预

| 误区 | 可观察信号 | 教学干预 | 依据性质 |
|---|---|---|---|
| “我玩得多，所以我知道玩家会怎样” | 用个人策略和感受替代外部观察；拒绝低熟练玩家数据 | 先做陌生类型/跨媒介案例；要求所有体验判断标明“自述、观察或推断” | **[实证线索]** [Zagal & Bruckman](https://gamestudies.org/0802/articles/zagal_bruckman) |
| 把分析写成评测或功能列表 | 大量“好玩、平衡、打击感”，没有规则和事件 | 强制使用证据卡；每个形容词后补“在哪条规则、哪次游玩中可见” | **[实证线索 + 项目综合]** [同上](https://gamestudies.org/0802/articles/zagal_bruckman) |
| 把核心模型当装配流水线 | 先枚举原语，再机械拼装，无法说出要验证什么 | 允许从体验问题、动作、材料或机制变体起步；完成原型后再用模型解释和检查 | **[项目约束 + 项目综合]** [结构模型研究笔记](../foundations/structural-models.md) |
| 太早进入引擎、美术或内容生产 | 一周后仍没有可运行核心；讨论被工具问题占满 | 先用纸、卡片、骰子、表格或最熟悉的工具；规定第一版只回答一个问题 | **[教学来源]** [MIT 纸面原型](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/9b051e4b2b363f44bd2a072be200b09a_MITCMS_301S16_Assigment6.pdf)；教师一手反思也警告工具子任务会遮蔽设计概念，[Kalthoff 2021](https://www.gamedeveloper.com/design/lessons-learned-from-teaching-game-design) |
| 一版同时改很多东西 | 无法把差异归因到任何改动；每轮都“更丰富” | 回到单规则手术；一轮一个主问题，其余改动标为维修项 | **[教学来源 + 项目综合]** [MIT A/B](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/51c8e0a79962c8957bcd32eb9d0619b2_MITCMS_301S16_Assigment7.pdf) |
| 试玩只收“好不好玩”票数 | 只有评分和偏好，没有关键事件、条件或版本差异 | 测试前写预测；测试中观察；测试后先问目标、决策和预期 | **[实践来源 + 项目综合]** [Valve 2006](https://steamcdn-a.akamaihd.net/apps/valve/2006/GDC2006_HL2DesignProcess.pdf)、[MIT A/B](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/51c8e0a79962c8957bcd32eb9d0619b2_MITCMS_301S16_Assigment7.pdf) |
| 设计者在测试中教玩家 | 玩家“顺利”完成，但规则独立运行性未知 | 分开主持与观察；最终必须盲测；把每次提示记录为原型失败事件 | **[教学来源]** [MIT final report](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/a6b60b47fd07af965827d37a94e766ae_MITCMS_301S16_Assign8_Stp4.pdf) |
| 对一个测试者过度反应 | 下一版完全跟随最近意见，随后反向摆动 | 寻找重复模式；保留替代解释；不能追加测试时标为不确定，不伪装为结论 | **[实践来源]** Valve 建议观察趋势并避免过度修正，[Valve 2006](https://steamcdn-a.akamaihd.net/apps/valve/2006/GDC2006_HL2DesignProcess.pdf) |
| 系统图越复杂越专业 | 图无法指向测试；为每个例外造新符号 | 只画本轮问题；标注图外现象；图与实玩冲突时先修判断而非维护图 | **[实践来源 + 项目综合]** Dormans 记录了学习成本、复杂图和模型范围，[Dormans 2012](https://pure.uva.nl/ws/files/1167843/102095_13.pdf) |
| 日志变成成功宣传 | 没有原始预测、失败版本、反例或未决问题 | 测试当天填写；评分奖励撤回错误假设和保留失败证据 | **[教学来源 + 项目综合]** [MIT 写作指南](https://ocw.mit.edu/courses/cms-608-game-design-spring-2008/f649475c2cdf807c3fce515330b7bd5f_games.pdf) |
| 把原创等同于无来源 | 隐瞒参考，或因不可能证明“从未有人做过”而停工 | 要求来源图；评价结构性改变及其效果，不评价神话式首创 | **[项目综合]**；重组练习先例见[MIT *Scrabbleship*](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/4faebe488c9944a5d272cdc6d036204a_MITCMS_301S16_Assigment3.pdf) |

## 8. 结业成果与评价 rubric

### 8.1 必交成果包

**[项目综合]** 结业提交不是只有一个可执行文件或一盒组件，而是六件彼此可核对的材料：

1. 当前可玩原型与所需组件；
2. 陌生玩家可使用的规则或游戏内教学；
3. 一页结构说明：核心行动、规则关系、机制编排、反复活动、完整游戏边界，以及尚不能稳定归类之处；
4. 体验/行为目标与主要设计问题；
5. 带日期和版本号的测试记录、原始观察、外部玩家范围和版本差异；
6. 个人反思：最重要的错误判断、证据怎样改变设计、仍未解决的问题、下一次测试。

CMU Transformational Game Design Studio 的结课要求同时提交可由陌生人学会的原型、理论依据、过程文档、设计日志与个人反思；MIT 的 final report 同样要求呈现从概念到最终版本的过程、观察与决定。[CMU 官方 syllabus](https://hcii.cmu.edu/sites/default/files/attachments/tgdsyllabus.pdf)、[MIT final report](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/a6b60b47fd07af965827d37a94e766ae_MITCMS_301S16_Assign8_Stp4.pdf)。本文成果包是在这些先例上按本项目模型重新组织的综合。

### 8.2 五项硬门槛

以下任一项未满足，先返工，不以总分补偿。

1. **规则闭合**：有明确的开始、角色/权限、合法行动、状态变化、结束或停止/评价程序；目标不是传统胜负时也必须说明玩家为何及何时停止。
2. **可独立运行**：目标玩家能仅凭规则或游戏内教学启动并完成一次核心游玩段，设计者无需现场补充关键规则。
3. **外部测试**：满足第 4.2 节的最低测试证据，且没有把内部自测冒充外部验证。
4. **可追溯迭代**：至少两个实质版本；能把一个重要改变连回观察和先前假设，也保留失败或相反证据。
5. **结构性原创**：公开主要来源；至少一个核心行动关系、反馈结构或机制编排发生有意且可观察的改变，而非纯换皮。

### 8.3 100 分 rubric

**[项目综合]** 下表综合了 MIT 对过程、迭代和盲测的强调，以及 CMU 对核心循环、规则清晰度和过程证据的评价维度；权重与等级划分是本项目工作假设，尚未校准。[MIT CMS.608](https://ocw.mit.edu/courses/cms-608-game-design-fall-2010/pages/syllabus/)、[CMU 53-110 final](https://courses.ideate.cmu.edu/53-110/n2020/index.html%3Fp%3D27.html)。

| 维度 | 权重 | 优秀 | 合格 | 需返工 |
|---|---:|---|---|---|
| 范围、闭合与独立可学 | 15 | 核心段短而完整；陌生玩家几乎无需回查即可运行；例外少且规则一致 | 能独立完成；有少量回查或非关键歧义 | 需要设计者补规则；无法稳定开始、继续或结束 |
| 结构解释与模型使用 | 15 | 清楚区分原语、机制、玩法模板与完整游戏；解释组合关系并指出模型边界、反例或不确定项 | 能把关键规则、机制与反复活动连起来，不以题材/类型代替解释 | 主要是名词贴标签、功能列表或意图陈述，无法回到规则和游玩事件 |
| 核心决策、目标与原创贡献 | 15 | 核心行动形成可辨识的决策/互动；目标体验具体；来源透明，结构性改变及其效果清楚 | 有可辨识核心与非换皮改变，参考来源可追溯 | 没有稳定核心；目标只是“好玩”；主要是拼盘或换皮且不承认来源 |
| Playtest 设计与证据质量 | 20 | 问题、预测、对象和反驳信号匹配；行为、自述、推断分开；包含异议和异常案例 | 完成规定的内部、外部和盲测，记录足以支持至少一项判断 | 只收偏好；测试者/条件不清；设计者大量指导；结论超过证据 |
| 迭代推理 | 20 | 每个关键变更都能连回证据；考虑替代解释；敢于撤回假设，并设计下一次区分性测试 | 至少两版有实质差异，主要改动有明确理由 | 版本只是增加内容/打磨；按最近意见摇摆；事后编造理由或丢失旧版 |
| 反思、沟通与边界意识 | 15 | 具体说明错误、限制、未决问题和适用范围；材料使第三方可复核过程 | 能陈述主要得失与下一步，成果包基本完整 | 只作成功宣传；隐藏失败；无法区分来源事实、综合判断与假设 |

**[工作假设]** 75 分为合格，90 分以上为优秀，同时必须通过全部硬门槛。第一次试教后应检查评分者一致性、各维度是否重复，以及测试数量是否对单人/多人、回合制/实时、数字/桌面原型造成不公平负担。

**不直接评分的项目：** 视觉精致度、内容量、商业潜力、教师个人喜好和测试者“平均好玩分”。若学习者声明某种目标体验，则评价的是目标是否具体、测试是否能观察它、证据与修订是否连贯，而不是教师是否偏爱这种体验。此取向以 MIT CMS.608 的过程评价为教学先例。[课程说明](https://ocw.mit.edu/courses/cms-608-game-design-fall-2010/pages/syllabus/)。Tan 基于 Singapore-MIT GAMBIT 学生项目的教学反思也警告，过度聚焦成品会挤压短迭代习惯；这是一手经验总结，不是对照研究。[Tan 2010](https://doi.org/10.1504/IJART.2010.030496)。一项对 37 名自愿回应的 capstone 教师所作的调查还显示，部分教师接受项目成品失败、但要求学生展示学习；同一研究强调样本自我选择、不可统计代表整体，因此这里只用来说明“课程成功”与“商业级成品成功”可以分开，而不据此设定权重。[Zagal & Sharp 2011，PDF pp. 2–3、9–10](https://dl.digra.org/index.php/dl/article/download/590/590/587)。

## 9. 教师/导师的最小工作法

**[项目综合]** 导师不替学习者设计，主要做五件事：

1. 把大愿望压缩成一轮能回答的问题；
2. 追问证据层级：“这是规则事实、玩家自述、观察，还是你的解释？”
3. 在学生争论可直接测试的问题时，推动尽快做便宜版本；
4. 在反馈会中保护弱势声音，阻止最强势或最资深玩家垄断解释；
5. 评价推理链和诚实边界，奖励发现错误，而不是奖励把过程写成顺利成功。

MIT CMS.301 的教师反思强调短作业后进入连续项目、同伴反馈本身的学习价值，以及对小组 critique 的主持；Zimmerman 和 Valve 的一手流程材料都强调尽早用可玩实验替代可测试的口头争论。[MIT Instructor Insights](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/pages/instructor-insights/)、[Zimmerman](https://www.ericzimmerman.com/assets/pdfs/Iterative_Design.pdf)、[Valve](https://steamcdn-a.akamaihd.net/apps/valve/2006/GDC2006_HL2DesignProcess.pdf)。具体五项职责是本项目综合。

## 10. 需要在本项目中验证的开放问题

1. **[开放问题]** 对成年中文读者，8 个台阶和 40–60 小时是否足以完成，而不会把结业标准降成一次课堂玩具？
2. **[开放问题]** “至少 3 名外部玩家、2 次外部会话、1 次盲测”的门槛，对单人解谜、社交推理、持续在线或强动作手感原型是否同样合理？
3. **[开放问题]** 纸面原型向实时数字体验的迁移在哪些类型中最容易失真？何时应该直接使用数字灰盒？
4. **[开放问题]** 轻量系统图应在第几轮引入，才能提高规则讨论精度而不造成术语和工具负担？Dormans 明确未收集量化效果数据，因此需要本项目自己的前后作品与学习者访谈。[Dormans 2012, ch. 8.2–8.3](https://pure.uva.nl/ws/files/1167843/102095_13.pdf)。
5. **[开放问题]** rubric 对不同媒介、玩家数量、合作/竞争结构是否有评分偏差？“规则闭合”怎样容纳沙盒、玩具式和开放结束作品？
6. **[开放问题]** 结构性原创的评分者一致性有多高？是否需要一组“换皮 / 变体 / 重组 / 新核心关系”的锚定样例？
7. **[开放问题]** 反思日志带来的收益来自写作本身、教师提示、同伴可见性还是测试频率？现有 GameLog 研究不能分离这些因素。[Zagal & Bruckman 2011](https://doi.org/10.1162/ijlm_a_00063)。

首轮试教应保存：起点诊断、每阶耗时、退回次数、全部版本、导师介入类型、外部测试记录、rubric 双人评分和结业后三个月是否独立再做原型。这样才能把本文从“来源支持的课程假设”逐步变成本项目自己的教学证据。

## 11. 一手来源清单

以下仅列本文实际使用的一手来源；链接均于 2026-07-20 访问。

### 11.1 大学与机构官方课程、作业

1. MIT OpenCourseWare. *CMS.301 Introduction to Game Design Methods, Spring 2016*. [Syllabus](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/pages/syllabus/)、[Calendar](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/pages/calendar/)、[Instructor Insights](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/pages/instructor-insights/)。定位：课程目标、前后半段结构、每周 critique、同伴反馈。
2. MIT OpenCourseWare. CMS.301 assignments. [Board Game Analysis: *Takenoko*](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/4fb5a04228b7fd2b2027c9cb9e674de9_MITCMS_301S16_Assigment2.pdf)、[*Scrabbleship*](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/4faebe488c9944a5d272cdc6d036204a_MITCMS_301S16_Assigment3.pdf)、[Paper Prototype](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/9b051e4b2b363f44bd2a072be200b09a_MITCMS_301S16_Assigment6.pdf)、[A/B Playtest](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/51c8e0a79962c8957bcd32eb9d0619b2_MITCMS_301S16_Assigment7.pdf)、[Explorative Game Design Project](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/88a0f75c6b17e7d57011835c7e0ec236_MITCMS_301S16_Assigment8.pdf)、[Final Report](https://ocw.mit.edu/courses/cms-301-introduction-to-game-design-methods-spring-2016/a6b60b47fd07af965827d37a94e766ae_MITCMS_301S16_Assign8_Stp4.pdf)。定位：各作业的 learning goals、流程、测试人数和评价条件。
3. MIT OpenCourseWare. *CMS.608 Game Design, Fall 2010*. [Syllabus](https://ocw.mit.edu/courses/cms-608-game-design-fall-2010/pages/syllabus/)。定位：projects、evaluation、forum and project logging。
4. MIT OpenCourseWare. *CMS.608 Game Design, Spring 2008*. [Project 4: Original Game](https://ocw.mit.edu/courses/cms-608-game-design-spring-2008/9ab6ae82308f2d0454f2477398f7a8f8_MITCMS_608s08_proj04.pdf)、[*Writing About Your Game*](https://ocw.mit.edu/courses/cms-608-game-design-spring-2008/f649475c2cdf807c3fce515330b7bd5f_games.pdf)。定位：项目范围、版本记录、盲测、失败与反例写作。
5. MIT OpenCourseWare. *CMS.611J Creating Video Games, Fall 2014*, [*Paper Prototyping and Playtesting*](https://ocw.mit.edu/courses/cms-611j-creating-video-games-fall-2014/348ee58d265e61e4760d196bd97b1ad1_MITCMS_611JF14_Paper_Prot.pdf)。定位：question—rapid design—playtest—revise 循环与规则变异手段。
6. Carnegie Mellon University IDeATe. *53-110 Introduction to Game Prototyping, Summer 2020*. [Syllabus](https://courses.ideate.cmu.edu/53-110/n2020/index.html%3Fp%3D8.html)、[Final Project](https://courses.ideate.cmu.edu/53-110/n2020/index.html%3Fp%3D27.html)。定位：先改既有游戏再原创、多轮内外测试、规则独立可学、产品/过程评分。
7. Hammer, Jessica. Carnegie Mellon University. [*Transformational Game Design Studio* syllabus](https://hcii.cmu.edu/sites/default/files/attachments/tgdsyllabus.pdf)。定位：theory paper、process documentation、design journal、stranger-learnable rules、individual reflection。
8. NYU Game Center. [*Prototype Studio*](https://gamecenter.nyu.edu/courses/prototype-studio/)；[Playtest Thursdays](https://gamecenter.nyu.edu/events/playtest-thursdays/)。定位：每周约束原型、速度与范围、开放试玩者构成。前者有先修课，更适合作为后续流畅度训练先例，而非零基础起点。

### 11.2 原始研究论文

9. Zagal, José P.; Bruckman, Amy. 2008. [“Novices, Gamers, and Scholars: Exploring the Challenges of Teaching About Games.”](https://gamestudies.org/0802/articles/zagal_bruckman) *Game Studies* 8(2). 定位：Methods and Data Analysis；Role of Prior Experience with Videogames；Practices and Discourse of Play。样本：12 名教师、10 所机构、8 个国家；定性访谈，研究重心为 game studies 教学。
10. Zagal, José P.; Bruckman, Amy. 2007. [“GameLog: Fostering Reflective Gameplaying for Learning.”](https://doi.org/10.1145/1274940.1274950) Sandbox Symposium 2007, ACM. 定位：两门大学课程、学生感知、日志文本类型。限制：不是比较原型质量的随机或准实验。
11. Zagal, José P.; Bruckman, Amy. 2011. [“Blogging for Facilitating Understanding: A Study of Video Game Education.”](https://doi.org/10.1162/ijlm_a_00063) *International Journal of Learning and Media* 3(1), 7–27. 定位：两门大学课程中的重复日志、课堂材料与访谈。限制：质性研究，未比较原型成果或其他写作形式。
12. Hullett, Kenneth; Kurniawan, Sri; Wardrip-Fruin, Noah. 2009. [“Better Game Studies Education the Carcassonne Way.”](https://dl.digra.org/index.php/dl/article/download/491/491/488) DiGRA 2009. 定位：方法、前后调查、Discussion（PDF pp. 5–6）。限制：自愿小组自我选择且起点较高，作者称结果远非定论。
13. Dishon, Gideon; Kafai, Yasmin B. 2020. [“Making More of Games: Cultivating Perspective-Taking through Game Design.”](https://doi.org/10.1016/j.compedu.2020.103810) *Computers & Education* 148, 103810. 定位：Highlights、Context/participants、两个对照个案。样本：16 名高中一年级学生；多案例探索研究，结果不可直接外推到成年入门设计者。
14. Manker, Jon. 2011. [“Game Prototyping – The Negotiation of an Idea.”](https://dl.digra.org/index.php/dl/article/download/598/598/595) DiGRA 2011. 定位：Method、prototype functions、Dispositio、Memoria（PDF pp. 6–11）。样本：16 名设计师、10 名设计学生、1 名教师，均为男性且主要来自瑞典/波兰；定性内容分析，作者称其为概念发展而非理论验证。
15. Wetzel, Richard. 2025. [“Game Design Games: Designing Games for Teaching Game Design.”](https://doi.org/10.1145/3723498.3723713) FDG 2025. 定位：12 次课堂干预、164 名学生、归纳式主题分析。限制：质性反馈，无对照组或原创项目迁移测量。
16. Larsen, Lasse Juel; Majgaard, Gunver. 2016. [“Expanding the Game Design Space – Teaching Computer Game Design in Higher Education.”](https://designsforlearning.nu/articles/dfl.68) *Designs for Learning* 8(1), 13–22. 定位：Philosophy of Learning、Didactical Approach、Layer 1–4。性质：五年课程反思、学生评价和作品案例形成的实践理论，不是受控研究。
17. Majgaard, Gunver. 2014. [“The Playful and Reflective Game Designer.”](https://files.eric.ed.gov/fulltext/EJ1035649.pdf) *Electronic Journal of e-Learning* 12(3), 271–280. 定位：design-based research、课程过程、目标群体测试、reflection-in/on-games。限制：6 名学生定性访谈，课程同时包含编程教学。
18. Zagal, José P.; Sharp, John. 2011. [“A Survey of Final Project Courses in Game Programs: Considerations for Teaching Capstone.”](https://dl.digra.org/index.php/dl/article/download/590/590/587) DiGRA 2011. 定位：Methods、capstone goals、failure、student expectations（PDF pp. 2–3、9–10）。样本：37 名自愿回应者，不具统计代表性。

### 11.3 作者、教师与项目一手实践材料

19. Zimmerman, Eric. 2003. [“Play as Research: The Iterative Design Process.”](https://www.ericzimmerman.com/assets/pdfs/Iterative_Design.pdf) 作者公开章节。定位：iterative design、first prototype、core mechanic、playtesting。性质：设计者一手方法论，不是课堂效果实验。
20. Dormans, Joris. 2012. [*Engineering Emergence: Applied Theory for Game Design*, ch. 8](https://pure.uva.nl/ws/files/1167843/102095_13.pdf). University of Amsterdam dissertation. 定位：8.2 Validation、8.3 Teaching Game Design（PDF pp. 4–9；书页 200–205）。性质：五年课程与工作坊的一手反思；作者明确未收集量化效果数据。
21. Speyrer, David; Jacobson, Matt. 2006. [*The Design Process for Half-Life 2*](https://steamcdn-a.akamaihd.net/apps/valve/2006/GDC2006_HL2DesignProcess.pdf). Valve/GDC presentation. 定位：goals—experiment—evaluate loop、external playtests、observation and trends。性质：大型数字游戏项目的一手流程，不是教学效果研究。
22. Tan, Philip. 2010. [“Iterative Game Design in Education.”](https://doi.org/10.1504/IJART.2010.030496) *International Journal of Arts and Technology* 3(1), 118–123. 定位：短迭代纪律、测试者来源、反馈误读、成品导向。性质：Singapore-MIT GAMBIT 学生项目的一手教学反思。
23. Kalthoff, Lars. 2021. [“Lessons Learned From Teaching Game Design.”](https://www.gamedeveloper.com/design/lessons-learned-from-teaching-game-design) *Game Developer*. 定位：hidden tasks、familiar tools、explicit steps、constraints。性质：六个月教学后的一手反思，不是系统研究。
