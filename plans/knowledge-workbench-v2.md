# Plan: Joe AI Research Workbench v2

> Source PRD: 2026-08-02 至 2026-08-03 对话；得到大脑知识库 [ai 资讯](https://biji.com/topic/JVl2k6DY)，`topic_id=JVl2k6DY`

## 目标

把当前按证据加工程度组织的 WAIC 仓库，升级为一个既能保存证据、又能被日常使用的研究工作台：Joe 在得到大脑主动收录资料，系统每日增量同步、登记、评分和交叉验证；Joe 可以按“最近变化、主题、问题、判断和冲突”浏览，并从同一套证据生成简报、PPT 和 Agent 圆桌议程。

系统必须同时回答两个问题：

1. **看到**：今天有什么值得看、为什么值得看、它和已有认识有什么关系。
2. **生成**：围绕一个问题，当前能可靠地形成什么简报、PPT 或待决策材料。

## 用户故事

- **US01**：作为 Joe，我把一条有价值的信息保存到得到大脑后，下一次同步能在 GitHub 中找到它。
- **US02**：作为 Joe，我不需要翻阅 `1-raw/` 文件树，也能知道最近新增了什么、哪些判断发生变化。
- **US03**：作为 Joe，我可以按 FDE、AI 治理、普通人与应用、WAIC 演进等主题进入当前知识。
- **US04**：作为 Joe，我可以从一条判断回查 Claim、SQS/CCS、证据谱系和原始来源。
- **US05**：作为 Joe，我可以输入一个主题或问题，获得带时间截面和置信边界的滚动简报。
- **US06**：作为 Joe，我可以从已复核简报生成口径一致、署名 Joe 的 PPT。
- **US07**：作为 Joe，我可以让多个 Agent 基于同一冻结证据包进行圆桌讨论，而不会把 Agent 共识误当成独立证据。
- **US08**：作为 Joe，我可以看到哪些新资料加强、削弱、限定或替代了既有 Claim。
- **US09**：作为 Joe，我只需要确认高影响判断、谱系争议和正式发布，不必逐条审核低价值线索。
- **US10**：作为 Joe，即使某天没有新增资料，也能确认同步正常，而不会产生空简报或无意义 Git 提交。
- **US11**：作为 Joe，我在得到大脑订阅博主只用于观察；除非我主动保存为普通笔记，否则其内容不进入仓库。
- **US12**：作为 Joe，我可以回看不同日期的简报，理解自己的判断如何随证据变化。

## Architectural decisions

- **证据后台不重排**：保留 `1-raw -> 2-data -> 3-processing -> 4-outputs`，它继续表示证据生命周期，不承担日常导航。
- **唯一工作入口**：根 README 首屏进入 Wiki Research Desk；`HOME` 是稳定入口，`NOW` 是滚动变化面板。技术 INDEX 只用于维护，不再与工作入口竞争。
- **得到大脑输入白名单**：自动入口仅接受自建知识库 `JVl2k6DY` 中的普通笔记。订阅博主、订阅内容和直播不登记、不抓取、不评分、不进入失败清单。
- **主动选择不等于可信**：Joe 保存一条资料只提高处理优先级，不提高 SQS，也不自动提高相关 Claim 的 CCS。
- **版本与身份**：`note_id` 始终按字符串保存；同一笔记的内容变化由上游版本信息和内容哈希识别。Raw 历史不覆盖，修订版与旧版归入同一 canonical source 和 evidence lineage。
- **关系先于分数变化**：新资料先判定为 `new-source`、`duplicate`、`same-lineage`、`new-version`、`corroboration`、`scope-update`、`conflict` 或 `no-impact`，再决定是否调整 CCS。
- **选择性深加工**：每条正式进入的普通笔记都登记并获得 provisional SQS；只有命中活跃 Topic、Question 或 Claim 的资料才抽取候选 Claim、进行交叉验证和 CCS 影响分析。
- **持久判断独立于派生库存**：来源处理状态、谱系关系、首次发现时间和知识变化使用独立账本；可重建的 source registry 不承载人工判断。
- **Git 是审计记录**：自动任务使用独立干净工作区，只暂存允许路径，只做 fast-forward push，禁止 force push，禁止提交 Joe 的未完成修改。
- **零变化是成功状态**：零新增、零修订且无复审到期时，不改知识文件、不生成简报、不 commit。同步失败必须与零变化明确区分。
- **Markdown 是生成真源**：简报首先生成不可覆盖的 Markdown 快照；PDF、PPT 和 figures 从已复核的 Brief/Synthesis 派生，不能直接从当天原料拼装。
- **简报不是证据**：Brief、PPT、Roundtable 和 Release 不能反向支撑 Claim；它们只能引用已有来源和 Claim。
- **Joe 门禁**：AI 可以自动生成 provisional SQS、候选 Claim、冲突建议、CCS delta 和内部简报；A/B、core、release 级判断、模糊谱系裁决及正式发布必须由 Joe 确认。
- **Agent 不是来源**：多个 Agent 读取同一证据后形成共识，只代表推理收敛，不增加独立证据谱系或 CCS。
- **执行权威唯一**：每日同步只配置一个权威调度器。优先使用能访问本机 getnote 与 Git 凭据的 Codex 定时任务；其他 cron、LaunchAgent 或 GitHub Action 不并行启用。
- **首版不建重型基础设施**：不引入数据库、全量向量库或大规模实体图谱。主题路由、显式链接、JSONL 账本和可重建 Markdown 视图先跑通。
- **公开边界**：完整第三方内容、私人批注和可能受版权限制的材料只在获授权或受控仓库保存；公开输出使用可追溯引用、必要摘录和来源链接。
- **署名**：正式简报、PDF、PPT 和研究报告统一标注“研究与整理：Joe”。

## Key models

- **IntakeRecord**：上游 ID、首次发现时间、版本哈希、捕获方式、处理状态、主题与问题路由。
- **SourceRelation**：canonical source、evidence lineage、重复、派生、翻译、摘要和版本替代关系。
- **Topic**：稳定主题、当前问题、当前判断、关键 Claim、开放冲突、最近 Brief 和观察信号。
- **KnowledgeChange**：新来源影响了哪个 Claim、变化前后状态、原因、受影响的 Synthesis/Release 和审核状态。
- **Briefing (`BRF`)**：问题、时间截面、上一版本、冻结来源集、当前判断、反证、未知项和生成版本。
- **ReviewItem**：需要 Joe 确认的谱系、评分、核心 Claim、发布影响或到期复审。
- **Roundtable (`RT`)**：议题、冻结证据包、角色发言、最强异议、裁决和回流建议。

## Research Desk 信息架构

根 README 首屏只承担项目定位和任务入口，Research Desk 承担日常使用：

```text
README
  -> HOME：系统里有什么、从哪里进入
      -> NOW：最近真正发生了什么变化
      -> TOPICS：按主题理解
      -> QUESTIONS：按问题获得当前答案
      -> SOURCES：查看已接受资料及评分边界
      -> CLAIMS / TENSIONS：查看判断和分歧
      -> REVIEWS：处理需要 Joe 拍板的事项
      -> BRIEFINGS：生成或回看简报
      -> OUTPUTS：查看正式 PDF、PPT 和 figures
```

Research Desk 首屏优先展示：

- 内容截止时间和输入边界。
- 最近有效新增、待处理、判断变化和待 Joe 复核数量。
- “今天值得看”的 3 至 5 项，以及每项为什么值得看。
- 当前四个核心主题的一句判断和最近变化。
- 录入、查看变化、按主题浏览、生成简报、发起圆桌和查看输出的入口。

主要路径的点击预算：

- 今天看什么：README 到 NOW，1 次。
- 理解一个主题：README 到 Topic，最多 2 次。
- 判断凭什么成立：README 到 Topic，再到 Claim/Source，最多 3 次。
- 查看待复核：README 到 Review，最多 2 次。
- 回看某期简报：README 到 Briefing，最多 2 次；回查证据最多 3 次。

## Generation contracts

面向 Agent 的稳定自然语言入口：

```text
同步资讯
看今天
简报：<主题或问题> [时间范围]
更新简报：<BRF-ID>
PPT：<已复核 BRF-ID>
圆桌：<Question-ID 或决策问题> [BRF-ID]
```

Brief 固定回答：

1. 一句话当前判断。
2. 相较上一期真正发生了什么变化。
3. 哪些判断被加强、削弱、限定或替代。
4. 最强反证、开放冲突和未知项。
5. 对 Joe、普通人、企业或治理的实际含义。
6. 下一步需要观察或主动寻找什么证据。
7. 来源、SQS、CCS、谱系和 `as_of`。

PPT 只在以下条件触发：

- Joe 主动要求。
- 核心 Claim 或 Synthesis 发生实质变化。
- 月度或季度积累出足够的已复核变化。
- 存在明确汇报或发布场景。

## Phase 1: 一条普通笔记贯通 Research Desk

**User stories**: US01、US02、US03、US04、US11

### What to build

以 `JVl2k6DY` 中一条 Joe 主动保存的普通笔记作为 tracer bullet：只读获取、登记、保存可追溯来源信息、生成 provisional SQS、关联一个现有主题或问题，并在 Research Desk 的 NOW、Source 和 Topic 路径中展示。订阅博主内容在连接器入口即被排除。

### Acceptance criteria

- [x] 只接受知识库中的普通笔记；订阅博主记录在 raw、registry、日志和临时目录中的数量均为 0。
- [x] `note_id` 以字符串保存，并能从 Source 页面回到得到大脑或原始 URL。
- [x] 一条笔记可以完成 `Getnote -> Source -> Topic/Question -> Research Desk` 的完整路径。
- [x] Research Desk 能显示标题、进入日期、为什么值得看、处理状态、SQS 和关联问题。
- [x] README 第一屏可以一次点击进入 Research Desk。
- [x] 主题页可以在一次点击内到达相关 Claim 和来源。
- [x] 未评分、低评分和 Joe 未复核是三个不同状态。
- [x] 治理 lint 和链接检查通过。

---

## Phase 2: 可靠的每日增量与 Git 闭环

**User stories**: US01、US02、US10、US11

### What to build

把单条样板扩展为可长期运行的每日事务：扫描普通笔记、识别新增与修订、重试并校验、原子落盘、更新确定性索引和 Research Desk、执行治理门禁，再以明确文件白名单 commit/push。建立首次基线，历史笔记不伪装成当日新增。

### Acceptance criteria

- [x] 初次运行可以把当前普通笔记建立为 baseline，并明确区分历史库存与此后新增。
- [x] 零新增且无复审到期时文件逐字节不变，无 Git commit。
- [x] 同一 `note_id` 重跑不会产生重复文件。
- [x] 同一笔记修订时保留旧版，并登记同一 canonical source 的新版本。
- [x] 下载有超时、有限重试、失败清单和非零失败状态；连接失败不能显示为“无新增”。
- [x] 临时内容通过校验后才原子落盘；中断后可恢复，不留下半文件。
- [x] 并发任务只有一个写入者。
- [x] Raw、来源注册表、工作账本、NOW 和治理快照计数一致，并只在同一通过门禁的 Git commit 中对远端可见；本地中断由持久事务 manifest 与 publish journal 恢复。
- [x] 自动提交只包含允许路径，不携带 Joe 的其他工作区改动。
- [x] 远端分叉或非 fast-forward 时停止并告警，不自动 merge、rebase 或 force push。

---

## Phase 3: 蜂巢增量评分与交叉验证

**User stories**: US04、US08、US09、US10

### What to build

对每条新普通笔记先做来源身份、版本和谱系判断，再计算 provisional SQS。命中活跃问题的资料与相关 Claim 进行定向比较，识别独立支持、同源复述、范围变化、版本替代和反证，只对受影响 Claim 提出 CCS delta，并把高影响变化送入 Joe Review。

### Acceptance criteria

- [ ] 同源转载、摘要或同一视频不同转写不会增加独立证据谱系。
- [ ] Joe 主动保存只影响优先级，不直接增加 SQS/CCS。
- [ ] 新资料先区分真实冲突、范围不同和时间更新，不因相反标题自动降分。
- [ ] 每次 Claim 变化能展示变化前后等级、证据谱系变化、原因、范围和受影响对象。
- [ ] 低质量或同源的相反说法只进入 disagreement signal，不自动改变核心 Claim。
- [ ] 独立高质量反证建立或更新 Tension，不静默覆盖旧 Claim。
- [ ] A/B、core、release Claim 的升降级与范围变化必须进入 Joe Review。
- [ ] 来源关系和知识变化保存在独立、可审计账本，重建 registry 不会丢失。
- [ ] 未命中活跃问题的资料保留在观察池，不进行无目的全量 Claim 抽取。

---

## Phase 4: 可浏览的主题与变化工作台

**User stories**: US02、US03、US04、US08、US09、US12

### What to build

把 Phase 1 的最小入口扩展为完整的浏览体验。Joe 可以从最近变化、主题、问题、来源、Claim、冲突和复核任务进入同一知识网络，并在移动端 GitHub 页面中快速扫描，不依赖宽表格或文件树。

### Acceptance criteria

- [ ] NOW 只显示新增来源、判断变化、新冲突、新简报和新发布等有效变化。
- [ ] 首批至少提供 WAIC 演进、普通人与应用、AI 治理、FDE/企业 AI 四个稳定 Topic。
- [ ] 每个 Topic 首屏包含当前判断、最近变化、关键 Claim、开放冲突、精选来源、最新 Brief 和观察信号。
- [ ] Source 总览只显示正式接受的普通笔记和 Joe 手工批准来源，不显示订阅博主。
- [ ] Claim 总览以可读陈述为主，不要求 Joe 先理解内部编号。
- [ ] Review 按“阻塞发布、核心未确认、到期复审、谱系待确认”排序。
- [ ] 零新增时显示健康空状态和基于现有资料可执行的入口，不生成空表。
- [ ] 375px 宽度下核心路径不依赖横向滚动；状态不只用颜色表达。
- [ ] 所有视图均可从账本和 Wiki 对象重建，不成为第二套事实库。

---

## Phase 5: 问题驱动的滚动简报

**User stories**: US03、US04、US05、US08、US09、US10、US12

### What to build

让 Joe 从 Topic、Question 或自然语言问题生成一份版本化 Brief。系统只读取命中的高价值来源和既有 Claim，与上一期 Brief 比较变化，冻结来源集和时间截面，生成可回查、可更新但不覆盖历史的研究快照。

### Acceptance criteria

- [ ] 可以用主题、Question ID 或自然语言问题发起简报。
- [ ] Brief 显示 `as_of`、时间窗口、上一版本和冻结来源集合哈希。
- [ ] Brief 明确区分事实、来源方主张、Wiki 推断和假设。
- [ ] 每个核心判断都能回到 Claim、CCS、来源、SQS 和证据谱系。
- [ ] Brief 明确列出本期变化、延续判断、最强反证、未知项和下一观察信号。
- [ ] 低分或未评分资料只能作为线索，不被包装为确定事实。
- [ ] 无实质变化时可以返回“判断未变”结果，但不创建空洞的新 Brief 版本。
- [ ] 旧 Brief 不覆盖；索引可以按日期和主题比较历次变化。
- [ ] Brief 不能出现在 Claim 的来源字段中。
- [ ] FDE 示例简报无需扫描全部历史正文即可完成，并能在三次点击内回查原始来源。

---

## Phase 6: 从已复核简报生成 PPT 与正式发布

**User stories**: US04、US06、US09、US12

### What to build

从 Joe 已复核的 Brief 和 Synthesis 生成同口径的 PPT、必要的 PDF 和 figures。输出过程冻结内容版本、图表数据和来源映射；正式文件经过视觉检查、治理 lint 和 release 门禁后发布。

### Acceptance criteria

- [ ] PPT 只能选择 `joe-reviewed` Brief/Synthesis 作为主要内容源。
- [ ] PPT 中的核心数字、图表和判断均可追溯到来源与评分理由。
- [ ] PPT 与 Markdown Brief 使用同一时间截面和结论口径。
- [ ] 没有实质知识变化时不自动生成新 PPT。
- [ ] 自动生成版本明确标为 draft，不能自动成为正式 release。
- [ ] 正式 PPT/PDF 统一署名“研究与整理：Joe”。
- [ ] 中文文本、图表、页码和来源完成桌面与移动预览检查，无截断、遮盖或重叠。
- [ ] Release 映射到 Brief/Synthesis、输出文件、figures 和版本信息。
- [ ] 旧版输出保留，可从 Release 看到其对应的知识时间截面。

---

## Phase 7: 证据约束的 Agent 圆桌与评分校准

**User stories**: US04、US07、US08、US09、US12

### What to build

围绕一个 Question 或决策问题，冻结已评分的 Brief/Claim/Source 作为 Evidence Pack，由主持、证据审计、议题席位和反证席进行结构化讨论。圆桌输出最强判断、最强异议、未知项和研究任务；Joe 复核后才提出 Wiki 变更。Joe 对简报、评分和圆桌建议的修改记录进入校准闭环。

### Acceptance criteria

- [ ] 每场圆桌冻结问题、范围、`as_of`、证据清单和来源集合哈希。
- [ ] 各席位独立开场，再交叉质询并明确什么证据会改变立场。
- [ ] 每条事实性发言引用 Claim 或 Source；无引用内容只能标为 hypothesis。
- [ ] 证据审计员检查 SQS/CCS 边界、同源谱系和适用范围。
- [ ] 圆桌裁决使用 supported、conditional、contested、insufficient、rejected，不采用多数票决定事实。
- [ ] Agent 共识不增加 SQS、CCS 或独立谱系数量。
- [ ] 圆桌本身不进入 source registry，也不能成为 Claim 的证据。
- [ ] Joe 复核后，结果才可映射为候选 Claim、Tension、Question、Synthesis 或 Release 动作。
- [ ] 系统记录 Joe 对 AI 评分和建议的接受、修改、驳回及理由，用于后续评分版本校准。
- [ ] 评分规则升级有版本、样本、差异记录和迁移说明，不静默改变历史结果。

## 全局验收场景

1. **零新增**：同步成功、无文件变化、无 commit，Research Desk 保留最近知识变化时间。
2. **一条新增普通笔记**：完成来源登记、SQS、主题路由、NOW 展示、lint 和 Git 推送。
3. **订阅博主新增内容**：仓库中无 raw、source、日志正文、评分或简报记录。
4. **同一笔记修订**：保留旧版，新增版本关系，不增加独立谱系。
5. **同源转载**：登记为同谱系，不提高 CCS。
6. **独立支持**：命中同范围 Claim，形成可解释的 CCS 上调建议。
7. **独立反证**：形成 Tension 和 CCS 复审建议，不覆盖历史判断。
8. **同步失败**：非零状态、无半文件、无错误 push，并给出恢复动作。
9. **生成简报**：从问题到 Brief，再到核心来源不超过三次点击。
10. **生成 PPT**：只使用已复核 Brief，视觉与治理检查通过，署名 Joe。
11. **Agent 圆桌**：共识不提高证据分，最强异议和补证任务被保留。
12. **历史回看**：可以比较两个 Brief 或 Release 的时间截面与 Claim 变化。

## Out of scope for v2

- 自动抓取整个互联网或替 Joe 决定关注什么。
- 自动导入得到大脑订阅博主、直播或所有关注内容。
- 对历史 800 多条材料一次性全量评分和摘要。
- 用文章热度、转载次数或 Agent 数量替代独立证据。
- 未经 Joe 确认自动发布正式 PPT、PDF 或修改核心结论。
- 初期建设数据库、复杂实体知识图谱或不可审计的黑盒向量真源。
- 自动删除上游已移除的笔记或仓库历史文件。

## 建议实施顺序

先完成 Phase 1 的一条普通笔记闭环并让 Joe 实际使用，再进入 Phase 2 定时化。Phase 3 与 Phase 4 共同构成“资料不再只是存储”的关键节点；Phase 5 验证“能生成”；Phase 6、Phase 7 在 Brief 稳定后再启用，避免输出和讨论建立在漂移的知识底座上。
