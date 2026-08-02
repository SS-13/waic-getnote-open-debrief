# WAIC LLM Wiki

> 这是从原始资料持续长出的语义知识层，不是另一份文章目录。

## 当前问题

| ID | 问题 | 状态 |
|---|---|---|
| [Q001](questions/Q001-历年WAIC的变化，普通人能看到什么.md) | 历年 WAIC 的变化，普通人能看到什么？ | 首轮答案已形成 |
| [Q002](questions/Q002-AI责任半径扩大后，应用、岗位与治理如何联动.md) | AI 责任半径扩大后，应用、岗位与治理如何联动？ | 可发布综合已形成 |
| [Q003](questions/Q003-FDE如何将企业转化为可治理的AI运行系统，中美路径有何差异.md) | FDE 如何将企业转化为可治理的 AI 运行系统，中美路径有何差异？ | 可发布综合已形成 |

## 当前综合

- [SYN001：2018–2026 WAIC 变化的普通人视角](syntheses/SYN001-2018至2026-WAIC变化的普通人视角.md)
- [SYN002：AI 演进、应用、就业与治理战略综合](syntheses/SYN002-AI演进、应用、就业与治理战略综合.md)
- [SYN003：FDE 中美企业 AI 部署与治理产业研判](syntheses/SYN003-FDE中美企业AI部署与治理产业研判.md)
- [T001：大会可见性与社会采用之间的距离](tensions/T001-大会可见性与社会采用之间的距离.md)
- [T002：任务闭环价值与责任半径同步扩大](tensions/T002-任务闭环价值与责任半径同步扩大.md)
- [Q001 首轮 18 份来源](./_indexes/Q001-SOURCES.md)
- [Q002 应用、岗位与治理来源](./_indexes/Q002-SOURCES.md)
- [Q003 FDE 与企业 AI 部署来源](./_indexes/Q003-SOURCES.md)

## 可复用框架

- [K001：AI 责任半径](concepts/K001-AI责任半径.md)
- [K002：七级证据成熟度阶梯](concepts/K002-七级证据成熟度阶梯.md)
- [K003：应用成熟度 L0-L4](concepts/K003-应用成熟度L0-L4.md)
- [K004：AI 治理控制环](concepts/K004-AI治理控制环.md)
- [K005：Agent 自治与责任矩阵](concepts/K005-Agent自治与责任矩阵.md)
- [K006：蜂巢式置信度与证据收敛](concepts/K006-蜂巢式置信度与证据收敛.md)

## 外部研究资料

- [外部研究资料索引](_indexes/EXTERNAL-RESEARCH-SOURCES.md)：FDE 白皮书、赫拉利达沃斯治理表达等非 WAIC 输入的来源卡、评分与使用边界
- [SRC-Q003-18：飞书社区 FDE 人才白皮书](_indexes/SRC-Q003-18-飞书社区FDE人才白皮书-解读与蜂巢评分.md)：已完成全文、表格和图片核读；SQS C / 64

## 发布与主库接入

- [REL001：WAIC 战略研究报告发布映射](releases/REL001-WAIC战略研究报告发布映射.md)
- [REL002：FDE 行业报告发布映射](releases/REL002-FDE行业报告发布映射.md)
- [REL003：蜂巢式知识置信度评分系统发布映射](releases/REL003-蜂巢式知识置信度评分系统发布映射.md)
- [主知识库接入说明](../governance/MAIN_KB_INTEGRATION.md)：已注册为 `waic-research`，每日 23:38 自检

## 工作入口

- [Wiki schema v0.2](_schema/SCHEMA.md)：对象、证据和 release 映射规则
- [Governance v1.1](../governance/README.md)：规模化注册、摄取、lint 与发布规范
- [蜂巢式置信度评分](../governance/CONFIDENCE_SCORING.md)：来源 SQS、Claim CCS、谱系去重与复审规则
- [蜜蜂选巢读书笔记](_indexes/BOOK-001-达尔文投资知识-蜜蜂选巢笔记.md)：评分体系的机制来源与边界
- `../index/waic-kb-pull-index.md`：现有来源明细
- `../../1-raw/`：Get笔记原始来源，只读
- `../../2-data/`：人工整理与完整逐字稿等补充来源
- `../../2-data/外部研究资料/`：非 WAIC 的外部研究输入、来源卡与评分边界

## 当前边界

- Wiki 优先回答真实问题，不追求把全部来源加工一遍。
- Wiki 中的结论必须能回到 `1-raw/` 或 `2-data/` 的具体证据。
- `3-processing/2026/` 中的既有 MECE 文档暂视为 legacy synthesis，不在本阶段迁移。
- `4-outputs/` 是发布层，不反向充当事实来源。
