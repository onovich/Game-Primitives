# `rehearsal-001`

- 状态：`collecting`
- 冻结提交：`69c116376eb62b03b69ae75503aaa13577ebb739`
- Schema 内部轮次：`logic-000`（只为复用正式制品 Schema 的保留编号，不是正式证据轮次）
- 用途：用无理论意义的虚构材料彩排冻结、承诺、两份独立提交、揭示、复算与报告
- 正式证据：否；不得产生或替代**强检验结论**
- 执行模型：两个 `gpt-5.6-sol`、`high` 空白会话
- 决定：[ADR 0108](../../../../../docs/adr/0108-freeze-logic-pilot-execution-representation-and-rehearsal.md)

本目录将保留首次彩排的完整结果，无论成功或失败。虚构说明、输入和公开**答案承诺**现已冻结；两份**首次提交**收齐前，不把明文真值或任一提交写入共享工作区。

- 冻结输入 SHA-256：`1640a7cdfe5fd8b6c0cba6ef20295b09922765302fc196934bdcdf3415c89bba`
- 公开承诺：`c5be132854e586df8f2961c54baa3bb668ff8224cb9cedaedecd56f44ef0c30c`
- 精确真值包长度：`532` 字节
- 私有保存：真值使用随机密钥加密后保存在仓库外；密钥、32 字节 `secret_nonce` 与明文均未进入共享工作区

彩排只检查证据链是否可运行。它不使用数独、《仓库番》、Slitherlink、《Baba Is You》、`FX-L01`–`FX-L04` 或 `LC-01`–`LC-04` 的正式内容。
