# `logic-001` 来源编码修订记录

- 状态：预审计；尚未交给来源忠实度审核者
- 编码者：`logic-source-encoder-01`，`gpt-5.6-sol`，`high`
- 表示：`GP-SR 0.1`
- 来源包 SHA-256：`b1152e06450e41867715ac9009d3399a233be858d1df8f88fc7a780470fb8277`

## 派发勘误

首次内联派发时，保管者把 `source-anchor-04` 中 `(8,15)` 的 `STOP` 对象的 `object_kind` 误抄为 `STOP`。冻结来源包中的值始终是 `text`；保管者在编码者提交任何输出前，以消息明确更正为 `text`。这属于传输勘误，不是来源不确定性，也没有改变冻结来源包及其哈希。

## `v0.1.0`

- 文件：`inputs/source-encoding-v0.1.0.json`
- SHA-256：`a64ba48ce114e39bc85e2402048ca94d130956142bf7466727af006c6a350922`
- 性质：编码者首次完整输出；原始 JSON 由编码者在首次输出后机械归档，没有由保管者改写。
- 结果：Schema 失败，不得进入来源忠实度审核。
- 已定位问题：根对象含 Schema 不允许的 `source_packet_sha256`；case 含不允许的 `case_id`；`scope` 为对象而非字符串；部分空槽位的文字前缀与 `encoding_status` 不一致；`rule_id` 与 `ref_id` 不符合冻结前缀模式。

编码者第一次报告“无法机械归档”之后，先前已发出的长补丁延迟完成，文件最终出现并通过 JSON 解析。保管者以文件实际字节计算上述哈希；没有把会话中的人工重抄文本冒充为原始输出。

## `v0.1.1`

- 文件：`inputs/source-encoding-v0.1.1.json`
- SHA-256：`c51abd87352204959f197b10e322805b429a51cebb2824b7389e36b0aa51fbe9`
- 性质：编码者依次返回四个完整 case；保管者只添加冻结根信封并按返回顺序机械组装。
- 已修复：删除额外根字段和 case 字段；把 `scope` 压成字符串；使空槽位状态与文字前缀一致。
- 结果：JSON 解析通过，仍因 ID 前缀失败。编码者使用 `s01-rule-*` 与 `s01-ref-*` 一类 ID，而 Schema 分别要求 `rule-*` 与 `ref-*`。

## 下一版纪律

编码者以 `{"decision":"approved","reason":"该迁移仅机械调整 ID 前缀并递增制品版本，不改变编码语义。"}` 明确批准 `v0.1.2` 的一一对应 ID 机械迁移：

```text
sNN-rule-X -> rule-sNN-X
sNN-ref-X  -> ref-sNN-X
```

不得借此修改规则语义、来源判断、中性化内容、槽位状态或组合关系。

## `v0.1.2`

- 文件：`inputs/source-encoding-v0.1.2.json`
- SHA-256：`d45f994e21d87a56ae42a0fc44cb85d05f2c926c1bacf02d9eede203af244525`
- 性质：把 `v0.1.1` 按上述映射机械迁移，并把制品版本改为 `0.1.2`；没有改变其他语义字段。
- 已通过：冻结 JSON Schema、四案计数、递归键序、引用闭包、source／blind 的规则与引用同构、状态前缀检查。
- 结果：盲化禁词扫描失败，不得进入来源忠实度审核。`source-anchor-04` 的共享 ID 仍包含来源词 `features`、`stop` 与 `win`；即使正文已经中性化，ID 也可能向重构者泄漏来源词。

编码者随后明确批准只把上述共享 ID 映射为 `rule-set`、`active-rule-set`、`obstruction` 与 `success` 等中性 ID，并把下一制品版本递增为 `0.1.3`。这次迁移同样不得改动 statement、类型、槽位状态或组合关系语义。
