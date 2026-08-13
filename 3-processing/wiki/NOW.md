---
id: VIEW-NOW
type: navigation-view
status: active
as_of: 2026-08-03
derived: true
---

# NOW · 最近有效变化

> 内容截至：2026-08-03
> 本页只显示会影响阅读路径的变化，不把文件数量、转载热度或 Agent 共识当作知识变化。

<!-- workbench:now:auto:start v1 -->
## 自动接入状态

<!-- workbench:now:manifest {"assessed":1,"baselineVersions":5,"dataEvidenceRecords":28,"generatedFrom":"3-processing/index/intake-batches.jsonl","intakeBatches":3,"intakeRecords":7,"integrated":0,"knowledgeAsOf":"2026-08-03","latestBatchId":"BATCH-GETNOTE-0c0c5422cd079fd1","missingRequiredAssessments":0,"newSourceVersions":2,"ordinaryNoteIdentities":7,"pendingTriage":6,"rawEvidenceRecords":843,"registryRecords":871,"requiredAssessments":1,"revisionVersions":0,"routed":1,"schemaVersion":"1.0","subscriptionRecords":0} -->

- 最近实质批次：`BATCH-GETNOTE-0c0c5422cd079fd1`
- 知识截止：`2026-08-03`
- 证据库存：Raw `843`，Data `28`，Registry `871`
- 普通笔记：身份 `7`，已存版本 `7`，历史基线 `5`，新增来源 `2`，修订 `0`
- 分流状态：pending `6`，routed `1`，integrated `0`
- 评分状态：已评分 `1`，必须评分 `1`，缺失 `0`

> `pending` 表示尚未完成主题分流，不要求为了填表而虚构 SQS；进入 `routed` 或 `integrated` 后必须完成来源评分。零变化扫描不会新增批次或改写本区块。

### 最近接入版本

| 版本 | 类型 | 分流 | SQS |
|---|---|---|---|
| 148｜如何看AI泡沫：叙事、营销、押注和不敢退出的竞争 · [查看 Raw](<../../1-raw/Joe主动收录/AI资讯/2026-08-03__148｜如何看AI泡沫：叙事、营销、押注和不敢退出的竞争__124760__b48f31c9e8c6.md>) | 新增来源 | `pending` | 待分流，不要求 SQS |
| 149｜投资人眼中AI相关的股市预期判断，和科学家认为的两个冲击 · [查看 Raw](<../../1-raw/Joe主动收录/AI资讯/2026-08-03__149｜投资人眼中AI相关的股市预期判断，和科学家认为的两个冲击__287328__ff77bb6da34e.md>) | 新增来源 | `pending` | 待分流，不要求 SQS |
| AI前沿部署工程师（FDE）行业落地实战深度研报：需求本质、生意逻辑与本土化路径 · [查看 Raw](<../../1-raw/Joe主动收录/AI资讯/2026-07-22__AI前沿部署工程师（FDE）行业落地实战深度研报：需求本质、生意逻辑与本土化路径__900416__75d128468d02.md>) | 历史基线 | `pending` | 待分流，不要求 SQS |
| AI原生时代学习能力的核心逻辑：以认知主权锚定人机协作边界 · [查看 Raw](<../../1-raw/Joe主动收录/AI资讯/2026-07-22__AI原生时代学习能力的核心逻辑：以认知主权锚定人机协作边界__393344__2d1e850ed077.md>) | 历史基线 | `pending` | 待分流，不要求 SQS |
| 开源大模型前沿技术进展深度研报：三维度缩放范式与Kimi 2.5核心创新解析 · [查看 Raw](<../../1-raw/Joe主动收录/AI资讯/2026-07-22__开源大模型前沿技术进展深度研报：三维度缩放范式与Kimi_2.5核心创新解析__376864__766497144a35.md>) | 历史基线 | `pending` | 待分流，不要求 SQS |

<!-- workbench:now:auto:end -->

## 当前状态

Get笔记白名单 `JVl2k6DY` 已完成普通笔记全量基线。准确库存、批次和分流状态以上方自动接入区块为准；订阅博主、订阅内容和直播不属于输入范围，不会出现在来源数、评分或简报候选中。

历史基线不表示资料在接入日首次发布，也不自动改变既有核心 Claim。每日权威任务在 Codex 独立 worktree 中运行；只有连接器明确返回 `zero-change` 且派生视图一致时，才可解释为“同步成功、零新增”，并且不会创建空 commit。

现有知识仍然可浏览：

- [按主题浏览现有判断](topics/README.md)
- [从当前问题生成简报](briefings/README.md)
- [查看 Joe 复核状态与排期项](reviews/README.md)

## 最近有效变化

### 2026-08-03 · 首条普通笔记贯通 Research Desk

[北京智能体政策解读](sources/SRC-AI-001-北京智能体政策解读.md)已完成 `Getnote → Raw → intake ledger → SQS → Source → Topic/Question` 的首条贯通。来源 SQS 为 `C / 60`、状态为 AI provisional。

它能证明卡兹克提出了这套政策解读，不能直接证明北京市政策原文、执行效果、行业普及或文中引用数字。当前路由到 [TP003 · AI 治理](topics/TP003-AI治理.md)、[TP004 · FDE 与企业 AI](topics/TP004-FDE与企业AI.md)、Q002 与 Q003；知识影响为“新增线索，核心判断未变”。

### 2026-08-03 · 四条核心 Claim 通过 Joe 门禁

Joe 确认 C008、C009、C010、C014 及各自 Boundary，CCS 分数保持不变，审核状态由 `AI provisional` 更新为 `Joe reviewed`。其中 C010 的证据口径同步修正为“两家公司、三个公开岗位页面”。

知识影响：核心 Claim 发布阻塞由 `4` 条降为 `0` 条；这些判断可以在既有范围内进入后续 Brief 和正式研究，但新证据或重大反证仍会触发复审。

### 2026-08-02 · FDE 国内部署假设获得新的结构化来源

[飞书社区《FDE 人才白皮书》](./_indexes/SRC-Q003-18-飞书社区FDE人才白皮书-解读与蜂巢评分.md)完成全文、表格与四张配图核读，来源 SQS 为 `C / 64`。它能够证明作者提出了这套框架，但不能单独证明招聘增速、薪资、融资、团队规模或行业普遍性。

该来源与既有企业岗位页和 WAIC 材料共同形成 [C015：半数字化企业中的业务翻译与最小闭环假设](claims/C015-半数字化企业中的业务翻译与最小闭环假设.md)，当前 CCS 为 `C / 63`、状态为 AI provisional，下次复审条件是出现独立中国项目证据或重要反证，最晚复审日为 2026-11-02。

知识影响：这是新的支持性假设，尚未改写 [SYN003](syntheses/SYN003-FDE中美企业AI部署与治理产业研判.md) 的核心结论。

### 2026-08-02 · 赫拉利治理表达进入外部观察池

[赫拉利达沃斯 AI 治理表达来源卡](../../2-data/外部研究资料/2026-07-27__赫拉利达沃斯AI治理表达__来源卡.md)已登记，SQS 为 `B / 76`。它适合用于理解演讲者在该场合的公开观点，并为 Agent 自主性、跨境责任、人工监督与儿童保护提供问题入口。

知识影响：当前没有由此形成的高影响 Claim；预测性观点不能当作事实结论。第三方上传并非达沃斯或演讲者官方来源，活动归属仍待更强原始来源确认。

### 2026-07-23 · 蜂巢评分进入发布治理

[蜂巢式知识置信度评分系统](releases/REL003-蜂巢式知识置信度评分系统发布映射.md)已经建立来源 SQS、Claim CCS、证据谱系去重和 Joe 门禁。截至 2026-08-03，账本含 28 条来源评估和 5 条 Claim 置信度记录。

知识影响：评分体系已经完成首批核心 Claim 的 Joe 门禁，后续新增 A/B、core 或 release 级判断仍按同一规则复核。

## 变化判定规则

只有以下事件进入 NOW：新增正式来源、既有来源新版本、Claim 被加强/削弱/限定/替代、新冲突、Joe 复核结果、新 Brief 或新 Release。

以下事件不进入 NOW：零变化扫描、同源重复、无问题关联的库存计数变化、输出文件的机械重建，以及订阅博主内容。

[返回 Research Desk](HOME.md)
