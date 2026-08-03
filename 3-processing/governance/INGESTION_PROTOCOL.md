# Question-Driven Ingestion Protocol v1.1

## 入口

机械捕获与语义摄取分开。Joe 主动保存到白名单知识库的普通笔记可以先以 `pending` 进入版本账本和观察池；只有进入 `routed` 或 `integrated` 时才必须绑定已有 question，或先新建 question。禁止以“把某年全部摘要化”为目的进行无问题的批量语义加工。

自动入口只接受 `JVl2k6DY` 普通笔记，不调用订阅博主、订阅内容或直播接口。Joe 主动保存提高处理优先级，不提高 SQS/CCS。

## 分层队列

| 队列 | 进入条件 | 处理目标 |
|---|---|---|
| A：高优先级证据 | 完整逐字稿、重复被问题命中的来源、能提供反证的来源 | 优先人工复核并形成 claim。 |
| B：问题相关摘要 | 与当前 question 高相关但保真度较低 | 提供候选 claim 与检索线索。 |
| C：库存来源 | 暂无明确问题关联 | 只注册，不预先摘要。 |

## 摄取步骤

1. **Capture**：识别 `note_id + versionHash`，新版本写入只读 Raw 和 intake ledger；既有版本不覆盖。
2. **Register**：在同一成功发布事务中重建 registry、batch、NOW 与 lint snapshot。
3. **Triage**：按 question、保真度、反证价值和跨年可比性进入 A/B/C 队列；未完成时保持 `pending`。
4. **Extract**：提取候选 claim，记录源文件、段落定位、说话者、证据模式和适用范围。
5. **Resolve**：优先匹配既有 entity、concept 与 claim；不一致内容进入 tension。
6. **Integrate**：更新 question、claim、synthesis 和来源索引，并标明 `asOf`。
7. **Review**：执行结构 lint 与语义 lint；高影响判断须回查高保真来源。
8. **Release**：只有通过门禁的 synthesis 可以进入 `4-outputs/`。

## 每日事务

- 初次全量扫描只有在列表明确完整、全部详情下载成功后才建立历史 baseline，不把历史库存伪装成扫描日新增。
- `intake-baseline.json` 是全量完成的唯一凭证；ledger 中已有 tracer、单条 baseline 或部分库存均不能替代它。marker 与 Raw/ledger 同事务提交，后续保持 write-once。
- `pending` 不要求为了通过 lint 而虚构 SQS；`routed` 和 `integrated` 必须有来源评分。
- 零变化不追加 batch、不改 NOW、不改 lint 时间戳、不创建 commit。
- 连接失败、单条下载失败或治理失败均返回非零状态，不能显示成“无新增”。
- 自动 Git 发布只在独立 worktree 中进行；路径白名单外的任何改动都会阻断发布。
- publish journal 在 pipeline 前持久化基础提交和运行阶段；中断后仅在路径、哈希和提交父节点均匹配时续跑。
- Raw、Registry、账本、NOW 与 lint 只有在同一个通过门禁的 Git commit 中才对远端可见；本地中间状态由事务 manifest 和 journal 恢复。

## claim 最小要求

每条关键 claim 至少要有：

- 可判断的陈述，而非主题标签。
- 时间、范围和主体。
- 一个可定位来源。
- 明确的证据模式：直接引文、来源摘要、来源方主张或 Wiki 推断。
- 支持、反驳或未知项之一。

## 冲突处理

新的来源不能覆盖旧结论，除非主体、谓词、范围和时间都明确相同，并且有充分理由标注 `supersedes`。其余差异建立或更新 tension。
