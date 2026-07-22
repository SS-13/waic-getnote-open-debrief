# Question-Driven Ingestion Protocol v1.0

## 入口

每次摄取必须绑定一个已有 question，或先新建一个 question。禁止以“把某年全部摘要化”为目的进行无问题的批量写入。

## 分层队列

| 队列 | 进入条件 | 处理目标 |
|---|---|---|
| A：高优先级证据 | 完整逐字稿、重复被问题命中的来源、能提供反证的来源 | 优先人工复核并形成 claim。 |
| B：问题相关摘要 | 与当前 question 高相关但保真度较低 | 提供候选 claim 与检索线索。 |
| C：库存来源 | 暂无明确问题关联 | 只注册，不预先摘要。 |

## 摄取步骤

1. **Register**：重建注册表，确认 `sourceId`、指纹、来源层与事件年份。
2. **Triage**：按 question、保真度、反证价值和跨年可比性进入 A/B/C 队列。
3. **Extract**：提取候选 claim，记录源文件、段落定位、说话者、证据模式和适用范围。
4. **Resolve**：优先匹配既有 entity、concept 与 claim；不一致内容进入 tension。
5. **Integrate**：更新 question、claim、synthesis 和来源索引，并标明 `asOf`。
6. **Review**：执行结构 lint 与语义 lint；高影响判断须回查高保真来源。
7. **Release**：只有通过门禁的 synthesis 可以进入 `4-outputs/`。

## claim 最小要求

每条关键 claim 至少要有：

- 可判断的陈述，而非主题标签。
- 时间、范围和主体。
- 一个可定位来源。
- 明确的证据模式：直接引文、来源摘要、来源方主张或 Wiki 推断。
- 支持、反驳或未知项之一。

## 冲突处理

新的来源不能覆盖旧结论，除非主体、谓词、范围和时间都明确相同，并且有充分理由标注 `supersedes`。其余差异建立或更新 tension。

