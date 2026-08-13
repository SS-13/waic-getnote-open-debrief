---
id: SRC-EXT-002
type: source
status: provisional
title: Your Brain on ChatGPT 实验报告
registry_source_id: data:doi:10.48550/arxiv.2506.08872:v2
canonical_source_id: doi:10.48550/arXiv.2506.08872
evidence_lineage_id: L-EXT-002
source_class: academic-preprint
fidelity: structured
assessment_id: SA-029
sqs: 84
confidence_band: B
assessment_status: provisional
topic_ids: [TP002]
question_ids: [Q002]
published_at: 2025-06-10
captured_at: 2026-08-12
ingested_at: 2026-08-12
as_of: 2026-08-12
---

# Your Brain on ChatGPT 实验报告

> `SQS B / 84 · AI provisional · Joe 未确认`

## 来源身份

- 论文：<https://arxiv.org/abs/2506.08872>，`v2` 于 2025-12-31 修订；研究主页：<https://www.brainonllm.com/>。
- 作者为 Nataliya Kosmyna 等 8 人，论文标示为 `Preprint, under review`，不等同于同行评审结论。
- 已核对用户提供的 `2506.08872v2.pdf`：216 页，SHA-256 `9b84e8dff3e5a9eaca8d5cdcbdeef3dfb1ef32c2455eda2ed56d0079c9b45790`。
- 本地可读入口：[中文结构化译述与数据核读](../../../2-data/外部研究资料/2026-08-12__MIT__Your_Brain_on_ChatGPT__实验报告中文版.md)。

## 能证明什么

- 能直接证明：作者在 54 名受试者的前三次限时英文议论文会话中设置 LLM、搜索和纯脑力三个平行条件（各 `n=18`），并对 18 名回访者设置两条换工具路径（各 `n=9`）。
- 能直接证明：论文在该协议和样本中报告的 EEG dDTF、即时引用、文章归属感和满意度数据，以及作者对这些数据的解释；其中会话 4 的两段引用结果方向互相矛盾。
- 不能直接证明：LLM 让人“变笨”、造成脑损伤、对任意模型/任务/人群必然有害，或“先不用 AI 再用 AI”已被独立随机试验证明为最优教学顺序。

## 核心边界

第 4 次会话不是一个独立第四组：只有原 LLM 到无工具、原纯脑力到 LLM 两条各 `n=9` 的路径，搜索组没有换工具；题目也从受试者旧题中选择。任何将其写为“四个互不重叠随机对照组”的表述都是错误的。

本来源当前仅作为 Q002 中“工具使用、学习与可观察认知结果”的研究线索，不改变现有核心 Claim 或正式 Release。

## 文内数据冲突

v2 第 45-50 页按会话 4 当前工具分组，报告 `Brain-to-LLM` 仅 `1/9` 正确引用、`LLM-to-Brain` 为 `7/9`；第 149 页却写成撤去 AI 的原 LLM 组有 `78%` 无法引用、`11%` 正确引用，正好反转前述路径。原文未解释该差异。本 Wiki 保留两处定位，不选择任一方向，并将此问题纳入复审条件。

## 蜂巢评分

| 维度 | 分数 | 依据 |
|---|---:|---|
| 身份与原始性 | 18/20 | 作者、机构关联、论文与 DOI 均可回查；当前仍为预印本。 |
| 对所述事实的直接性 | 17/20 | 直接报告研究设计、样本、指标与作者观测；会话 4 的标签矛盾限制其数值方向的可用性。 |
| 可追溯性 | 20/20 | 有完整 216 页 v2、公开图表页、方法、表格与版本历史。 |
| 保真度与完整性 | 15/15 | 已按完整论文与图表页核读中文结构化译述。 |
| 利益关系与纠错透明度 | 6/15 | 作者披露无经费，方法与限制公开；但文内数据冲突未见勘误，且尚未完成同行评审或独立复现。 |
| 时效与版本清晰度 | 8/10 | v1/v2 日期可见，教育技术与模型生态仍快速变化。 |
| **合计** | **84/100，B 级** | 高可追溯的一手研究报告，但会话 4 内部矛盾、预印本状态和小样本限制其可用结论。 |

## 关联

- [Q002：应用、岗位与治理如何联动](../questions/Q002-AI责任半径扩大后，应用、岗位与治理如何联动.md)
- [TP002：普通人与应用](../topics/TP002-普通人与应用.md)
- [外部研究资料索引](../_indexes/EXTERNAL-RESEARCH-SOURCES.md)
- [蜂巢式知识置信度评分规范](../../governance/CONFIDENCE_SCORING.md)
