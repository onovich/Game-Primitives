# 0106 逻辑解谜先行组采用版本化 JSON 测试轮次

- 状态：已接受
- 日期：2026-07-22
- 来源决定：D2-5b

## 决策

逻辑解谜先行组的结构化测试制品采用 JSON 作为唯一数据来源；Markdown 只承载给人的说明、任务文本和生成后的阅读视图，不手工复制一份平行的结构数据。未来早期网页可读取同一 JSON 呈现测试材料，但网页不是测试真值来源。

### 序列化约定

所有进入测试轮次的 JSON 制品统一使用：

- UTF-8，无 BOM；
- LF 换行、两个空格缩进、恰好一个末尾换行；
- ASCII 小写 `snake_case` 字段名；
- 对象键按 Unicode 码点升序排列；
- 显式 `schema_version` 或 `protocol_version`，不得依赖未记录的解析器默认值；
- 每个正式制品在轮次清单中记录相对路径、制品类型、版本和 SHA-256。

散列和**答案承诺**都作用于仓库实际保存或事后揭示的精确文件字节，而不是解析后再序列化的抽象对象。格式化工具若改变字节，就必须重新计算校验值并在**首次提交**前更新版本。

JSON Schema 固定使用 Draft 2020-12 描述机器约束。D2-5b 阶段先建立轮次清单与**答案承诺** Schema，没有用空泛 Schema 预先掩盖尚未决定的问题；D2-5c 冻结字段后，已继续建立输入信封、提交、真值与报告 Schema。

### 目录与轮次

测试工作区固定为：

```text
research/calibration-tests/logic-pilot/
├── README.md
├── schema/
└── runs/
    └── logic-001/
        ├── README.md
        ├── manifest.json
        ├── instructions/
        ├── inputs/
        ├── commitments/
        ├── submissions/
        ├── reveal/
        └── reports/
```

Git 只在目录首次拥有真实制品时跟踪它，不用 `.gitkeep` 制造空目录。`logic-001` 是本轮首个正式轮次标识；任何在**首次提交**后改变任务语义、输入或承诺的修订都必须创建新轮次，不能原地覆盖。

目录职责如下：

| 目录 | 进入时间 | 内容边界 |
| --- | --- | --- |
| `instructions/` | 测试冻结前 | Markdown 任务说明、测试本地允许术语表和可见范围 |
| `inputs/` | 测试冻结前 | 中性编号的重构输入与匿名夹具 JSON |
| `commitments/` | 测试冻结前 | 不含随机数或答案的公开承诺 JSON |
| `submissions/` | 收集期间 | 每位测试者不可覆盖的**首次提交**与显式追加勘误 |
| `reveal/` | 预定提交全部冻结后 | 答案 JSON、`secret_nonce`、中性编号映射和承诺复算 |
| `reports/` | 揭示后 | 差异比较、污染记录、通过／失败判断及方法修订 |

答案、映射和 `secret_nonce` 在揭示前没有仓库内的 `private/`、`hidden/` 或被忽略副本；它们继续由测试保管者保存在仓库外。这避免未来代理把未跟踪目录误当作普通项目材料。

### 版本纪律

- 轮次清单状态依次使用 `preparing`、`frozen`、`collecting`、`revealed`、`reported`；若程序错误使轮次不可解释，则使用 `invalidated` 并保留原制品。
- 首次提交前的改变同时更新制品版本、轮次清单和 SHA-256。
- 首次提交后，说明、输入、承诺和首次提交均不得覆盖；勘误、新分析和共识稿只能新增文件。
- 任何会改变测试者可能答案的输入修订都创建新轮次，而不是作为“错别字修复”静默进入旧轮次。

## 依据

YAML 较适合手写注释，但隐式类型、解析差异和序列化变化会给精确字节散列增加不必要歧义。把同一结构同时手工维护在 Markdown 与 JSON 中又会产生漂移。严格 JSON 加人类说明层既适合校验、承诺和未来网页生成，也保留了研究者直接阅读任务的便利。

按轮次封装比按文件类型跨项目堆放更容易保留“输入—承诺—提交—揭示—报告”的完整证据链，也允许组间方法复核后以 `logic-002` 重跑，而不回写第一次试验。

## 影响

- [第二轮校准协议](../../research/calibration-cycle-2-protocol.md)和[校准门 D](../../research/calibration-gates/gate-d-second-cycle-method-pilot.md)将逻辑组启动条件第 8 项记为已满足。
- [逻辑先行组测试工作区](../../research/calibration-tests/logic-pilot/README.md)与 `logic-001` 轮次骨架建立，但尚无测试输入或提交。
- D2-5c 已由 [ADR 0107](0107-freeze-logic-pilot-verdicts-contamination-and-scope.md)冻结事前通过／失败标准、污染字段、近邻隔离变量、行为边界，以及输入／提交／真值／报告 Schema。
- 第二轮仍未启动完整取证。
