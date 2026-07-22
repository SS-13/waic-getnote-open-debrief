# WAIC LLM Wiki Schema v0.2

## 目标

把历年 WAIC 资料转成可积累、可追溯、可质疑的个人知识库。Wiki 保存已经形成的理解；需要核实时，回查原始来源。

## 知识对象

| 类型 | ID 前缀 | 用途 |
|---|---|---|
| question | `Q` | 用户真实问题及阶段性答案 |
| source | `SRC` | 已摄取来源的身份、质量和版本关系 |
| claim | `C` | 可判断真伪或适用范围的原子主张 |
| tension | `T` | 主张之间的冲突、差异或时间变化 |
| synthesis | `SYN` | 跨来源比较、趋势和当前判断 |
| concept | `K` | 被多个问题或综合反复调用的分析概念 |
| release | `REL` | Wiki 结论与报告、PDF、PPT、图表之间的发布映射 |

`concept` 只在确有复用价值时建立；`entity` 暂不独立建模，不为扩大图谱而建页。

## 对象最小字段

| 类型 | 必填字段 |
|---|---|
| question | `id`、`type`、`status`、`as_of`、`event`、`years` |
| claim | `id`、`type`、`status`、`question_ids`、`source_ids`、`scope`、`as_of` |
| tension | `id`、`type`、`status`、`question_ids`、`claim_ids`、`as_of` |
| synthesis | `id`、`type`、`status`、`question_ids`、`claim_ids`、`as_of` |
| concept | `id`、`type`、`status`、`claim_ids`、`as_of` |
| release | `id`、`type`、`status`、`synthesis_ids`、`output_paths`、`as_of` |

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
7. `release` 只能指向已经存在的 synthesis 与交付文件；输出层不得反向成为 claim 的证据。
8. 报告修订影响核心判断时，先更新 claim/synthesis，再更新 release 映射和交付物。

## 来源保真度

来源保真度描述“离原始表达有多近”，不代表内容一定真实：

| 等级 | 典型来源 |
|---|---|
| `verbatim` | 完整逐字稿、现场录音实录 |
| `structured` | 人工整理稿、官方完整报告 |
| `summary` | AI 摘要、媒体摘要 |
| `pointer` | 只有链接或活动提示的笔记 |

## 摄取流程

1. 登记来源身份、`note_id`、路径、证据谱系和内容保真度。
2. 围绕一个 question 选择少量高相关来源。
3. 抽取候选 claim，并保留来源定位。
4. 优先更新已有页面，再决定是否新建对象。
5. 登记 tension、未知项和反证。
6. 更新 question 与 synthesis，并记录 `as_of`。
7. 执行结构 lint 和语义 lint。

## 回答格式

回答一个 question 时，应至少包含：

- 当前判断
- 分阶段证据
- 反证或替代解释
- 普通人可观察的信号
- 仍然未知的部分
- 来源与 `as_of`
