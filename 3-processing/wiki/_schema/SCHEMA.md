# WAIC LLM Wiki Schema v0.4

## 目标

把历年 WAIC 资料转成可积累、可追溯、可质疑的个人知识库。Wiki 保存已经形成的理解；需要核实时，回查原始来源。

## 知识对象

| 类型 | ID 前缀 | 用途 |
|---|---|---|
| question | `Q` | 用户真实问题及阶段性答案 |
| source | `SRC` | 已摄取来源的身份、质量和版本关系 |
| topic | `TP` | 稳定主题下的问题、判断、冲突、来源与观察信号导航 |
| claim | `C` | 可判断真伪或适用范围的原子主张 |
| tension | `T` | 主张之间的冲突、差异或时间变化 |
| synthesis | `SYN` | 跨来源比较、趋势和当前判断 |
| concept | `K` | 被多个问题或综合反复调用的分析概念 |
| briefing | `BRF` | 围绕问题和时间截面的版本化研究简报 |
| roundtable | `RT` | 基于冻结证据包的多 Agent 结构化讨论记录 |
| release | `REL` | Wiki 结论与报告、PDF、PPT、图表之间的发布映射 |

`concept` 只在确有复用价值时建立；`entity` 暂不独立建模，不为扩大图谱而建页。`topic`、`briefing`、`roundtable` 和 `release` 都是导航、分析或发布对象，不是来源。

## 对象最小字段

| 类型 | 必填字段 |
|---|---|
| question | `id`、`type`、`status`、`as_of`、`event`、`years` |
| source | `id`、`type`、`status`、`registry_source_id`、`canonical_source_id`、`evidence_lineage_id`、`assessment_id`、`topic_ids`、`question_ids`、`as_of` |
| topic | `id`、`type`、`status`、`question_ids`、`claim_ids`、`as_of` |
| claim | `id`、`type`、`status`、`question_ids`、`source_ids`、`scope`、`as_of` |
| tension | `id`、`type`、`status`、`question_ids`、`claim_ids`、`as_of` |
| synthesis | `id`、`type`、`status`、`question_ids`、`claim_ids`、`as_of` |
| concept | `id`、`type`、`status`、`claim_ids`、`as_of` |
| briefing | `id`、`type`、`status`、`question_ids`、`claim_ids`、`source_ids`、`as_of`、`evidence_pack_hash`、`review_status`、`generation_version` |
| roundtable | `id`、`type`、`status`、`question_ids`、`claim_ids`、`source_ids`、`briefing_ids`、`as_of`、`evidence_pack_hash`、`review_status` |
| release | `id`、`type`、`status`、`synthesis_ids`、`output_paths`、`as_of` |

数组字段即使没有成员也必须写成 `[]`，不得省略。首期 Brief 可不写 `previous_briefing_id`；后续版本必须指向上一期。Release 可以用 `briefing_ids` 补充其内容真源，但不得只指向未复核 Brief。

## 对象边界

### Source

- Source 页面是已接受来源的可读视图，`registry_source_id` 必须能回到 `source-registry.jsonl` 中的具体版本。
- `canonical_source_id` 表示跨版本的来源身份；`evidence_lineage_id` 表示独立证据谱系。同源转载、摘要、翻译和同一活动的不同转写不得重复计算为独立证据。
- 已评分 Source 还应记录 `assessment_id`、`assessment_status`、`sqs`、`confidence_band`、`source_class` 与 `fidelity`；`published_at`、`captured_at`、`ingested_at` 只按已知事实分别记录，不得互相代填。
- Source 页面可以概括“能证明什么”和“不能证明什么”，但页面本身不增加来源的可靠度。

### Topic

- Topic 聚合 Question、Claim、Tension、Synthesis、Source、Brief 和观察信号，回答“这个领域当前怎么看”。
- Topic 只保存导航与阶段判断；事实性内容必须下钻到 Claim 和 Source。
- Joe 主动收录一条资料只提高处理优先级，不提高 Source 的 SQS，也不自动改变 Claim 的 CCS。

### Briefing (`BRF`)

- Brief 是不可覆盖的时间快照，必须冻结 `source_ids`、`claim_ids`、`as_of` 与 `evidence_pack_hash`。
- 正文至少包含当前判断、本期变化、加强/削弱/限定/替代的 Claim、最强反证、未知项、实际含义与下一观察信号。
- `review_status` 至少区分 `ai-provisional` 与 `joe-reviewed`。只有 `joe-reviewed` Brief 才能作为正式 PPT/PDF 的主要内容真源。
- 无实质知识变化时可以返回“判断未变”，但不创建空洞的新 BRF 版本。

### Roundtable (`RT`)

- Roundtable 必须冻结问题、范围、`as_of`、证据清单与 `evidence_pack_hash`，并保留各席位发言、最强异议、未知项、裁决与回流建议。
- 事实性发言必须引用 Claim 或 Source；无引用内容只能标为 `hypothesis`。
- 裁决状态使用 `supported`、`conditional`、`contested`、`insufficient` 或 `rejected`，不得以多数票决定事实。
- Agent 共识只表示推理收敛，不增加 SQS、CCS 或独立证据谱系。Joe 复核前，圆桌建议不得直接改写正式 Claim 或 Release。

## 接入与评分账本边界

| 位置 | 性质 | 保存内容 | 不保存什么 |
|---|---|---|---|
| `index/source-registry.jsonl` | 可重建库存 | 来源版本、路径、哈希、canonical identity | 人工评分与长期处理判断 |
| `index/intake-ledger.jsonl` | 持久接入账本 | 上游 ID、知识库白名单、首次发现、版本哈希、路由与处理状态 | SQS、CCS 与事实结论 |
| `index/source-assessments.jsonl` | 持久评分账本 | SQS 维度分、等级、谱系、限制、复审条件与审核状态 | Claim 的结论置信度 |
| `index/claim-confidence.jsonl` | 持久评分账本 | CCS、来源集合、独立谱系、惩罚、影响级别与审核状态 | 新的来源身份 |
| `wiki/sources/` | 派生可读视图 | 来源身份、评分边界、路由与回查链接 | 账本的替代副本 |

- 自动接入只接受 `JVl2k6DY` 中 Joe 主动保存的普通笔记；订阅博主、订阅内容和直播在入口排除，不登记、不评分。
- `note_id` 按字符串保存。同一笔记修订后生成新的 registry source 版本，但沿用 canonical source 与 evidence lineage；Raw 历史不得覆盖。
- Intake 成功只说明资料已进入系统，不代表资料为真，也不自动产生 Claim。
- Source assessment 评估来源对特定事实边界的可靠度；它不替代 Claim assessment，也不因 Joe 主动保存而加分。
- Source 页面展示的分数和状态必须来自评分账本；可重建 registry 不承载人工判断。

## 时间字段

- `event_date`：事件或大会实际发生时间。
- `published_at`：来源首次发布的时间。
- `ingested_at`：来源进入本地 Wiki 的时间。
- `as_of`：某条 claim 或 synthesis 所针对的时间点。

不得用文件名前的采集日期代替大会年份或事件时间。

## 证据规则

1. 每条关键 claim 必须记录 `source_id`、源文件路径和段落定位。
2. 必须区分直接引文、来源摘要、来源方主张和 Wiki 推断。
3. AI 摘要不能被改写成发言人的逐字原话。
4. 同一活动的转载、摘要和完整稿属于同一证据谱系，不能冒充多个独立来源。
5. 新来源与旧结论不一致时，先建立 tension；不得静默覆盖。
6. 没有足够证据的内容标为 `hypothesis` 或 `unknown`。
7. `topic`、`briefing`、`roundtable`、`release` 以及 PDF、PPT、figure 只能组织、推理或发布既有证据，均不得写入 Claim 的 `source_ids`，也不得反向成为 Claim 证据。
8. 报告修订影响核心判断时，先更新 claim/synthesis，再更新 release 映射和交付物。
9. 来源保真度与来源可靠度不同：`fidelity` 描述表达距离，SQS 描述其对直接事实的可靠度。
10. Claim 的 CCS 必须在独立账本中记录谱系去重、反证惩罚、复审条件和审核状态；A/B、核心和发布级 Claim 未获 Joe 复核时不得作为新的正式 release 的独立依据。

## 来源保真度

来源保真度描述“离原始表达有多近”，不代表内容一定真实：

| 等级 | 典型来源 |
|---|---|
| `verbatim` | 完整逐字稿、现场录音实录 |
| `structured` | 人工整理稿、官方完整报告 |
| `summary` | AI 摘要、媒体摘要 |
| `pointer` | 只有链接或活动提示的笔记 |

## 摄取流程

1. 在 intake ledger 登记上游身份、版本、白名单状态和路由，再以只读 Raw 新版本落盘。
2. 重建 source registry，并为正式接受的来源建立或更新 Source 页面。
3. 先判断 `new-source`、`duplicate`、`same-lineage`、`new-version`、`corroboration`、`scope-update`、`conflict` 或 `no-impact`。
4. 计算 provisional SQS；围绕活跃 Topic/Question 选择少量高相关来源。
5. 抽取候选 Claim，并保留来源定位；对受影响 Claim 提出 CCS 变化。
6. 登记 Tension、未知项和反证，更新 Topic、Question 与 Synthesis 的 `as_of`。
7. 执行结构 lint、语义 lint 与 Joe 门禁；A/B、核心及 release 级判断必须由 Joe 确认。
8. 从已复核知识对象派生 Brief、Roundtable 和 Release；派生对象不得回流为证据。

## 回答格式

回答一个 question 时，应至少包含：

- 当前判断
- 分阶段证据
- 反证或替代解释
- 普通人可观察的信号
- 仍然未知的部分
- 来源与 `as_of`
