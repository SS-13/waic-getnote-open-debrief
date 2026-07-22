# Operating Cadence v1.0

| 节奏 | 动作 | 产物 | 负责人 |
|---|---|---|---|
| 每次 raw 增量后 | 重建注册表、比较指纹与新增来源 | `source-registry.jsonl`、快照差异 | 自动化 + Agent |
| 每周 | 为活跃 question 做 A/B/C 队列整理 | 来源队列、待核验清单 | 研究 Agent |
| 每两周 | 摄取高价值来源并更新 claim/tension | question 与 claim 变更记录 | 编辑 Agent |
| 每月 | 审查 synthesis 的过期性和冲突 | lint 报告、更新后的综合页 | 知识库 owner |
| 每季度 | 抽样审计来源、引用与输出 | 治理复盘、schema 变更说明 | 知识库 owner |

## 规模化指标

- 注册覆盖率：证据层中已注册来源占比。
- 活跃问题覆盖率：活跃 question 中有来源、claim、tension 和 synthesis 的比例。
- 可回溯率：抽样核心结论可回到具体来源定位的比例。
- 高保真占比：每个 synthesis 的核心结论中，来自 `verbatim` 或 `structured` 来源的比例。
- 过期率：超过审查周期仍未更新的 synthesis 比例。

指标服务于知识质量，不以页面数量、链接数量或图谱节点数为目标。

