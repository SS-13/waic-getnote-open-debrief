# 3-processing/ · 加工与语义知识层

> 这里保存从原始来源中形成的结构化索引、既有二阶解读和可持续更新的 LLM Wiki。

## 当前结构

```text
3-processing/
├── index/             # 拉取清单与待处理索引
├── governance/        # 来源注册、摄取、lint 与发布规范
├── 2026/              # 已有 MECE 对话录和问题清单
└── wiki/              # 以问题为入口的持久语义知识层
    ├── HOME.md
    ├── _indexes/
    ├── _schema/
    ├── claims/
    ├── concepts/
    ├── questions/
    ├── releases/
    ├── syntheses/
    └── tensions/
```

## 语义边界

- `1-raw/` 和 `2-data/` 是证据来源，本目录不覆盖它们。
- `index/` 回答“有哪些资料”。
- `governance/` 定义来源注册、问题摄取、lint 与发布门禁。
- `2026/` 保留已有的二阶加工结果。
- `wiki/` 回答“这些资料共同说明了什么”，并用 `release` 记录知识对象与交付物的映射。
- `4-outputs/` 是发布层，不作为 Wiki 的一手证据；输出变更必须回到 claim/synthesis 更新。
- `../2-data/外部研究资料/` 保存非 WAIC 的外部输入来源卡；它们按独立谱系评分，不能混写为 WAIC 原始证据。

## 置信度治理

来源库存与人工评分分离：`index/source-registry.jsonl` 是可重建清单，`index/source-assessments.jsonl` 和 `index/claim-confidence.jsonl` 保存 SQS、CCS、证据谱系、复审与 Joe 复核状态。详见 [蜂巢式置信度评分](governance/CONFIDENCE_SCORING.md)。

## 当前入口

- [WAIC LLM Wiki](wiki/HOME.md)
- [Governance v1.2](governance/README.md)
- [Wiki schema v0.3](wiki/_schema/SCHEMA.md)
- [K006：蜂巢式置信度与证据收敛](wiki/concepts/K006-蜂巢式置信度与证据收敛.md)
- [REL003：蜂巢式知识置信度评分系统发布映射](wiki/releases/REL003-蜂巢式知识置信度评分系统发布映射.md)
- [Q001：历年 WAIC 的变化，普通人能看到什么？](wiki/questions/Q001-历年WAIC的变化，普通人能看到什么.md)
- [SYN001：2018–2026 WAIC 变化的普通人视角](wiki/syntheses/SYN001-2018至2026-WAIC变化的普通人视角.md)
- [Q002：AI 责任半径扩大后，应用、岗位与治理如何联动？](wiki/questions/Q002-AI责任半径扩大后，应用、岗位与治理如何联动.md)
- [SYN002：AI 演进、应用、就业与治理战略综合](wiki/syntheses/SYN002-AI演进、应用、就业与治理战略综合.md)
- [REL001：WAIC 战略研究报告发布映射](wiki/releases/REL001-WAIC战略研究报告发布映射.md)
- [Q003：FDE 如何将企业转化为可治理的 AI 运行系统，中美路径有何差异？](wiki/questions/Q003-FDE如何将企业转化为可治理的AI运行系统，中美路径有何差异.md)
- [SYN003：FDE 中美企业 AI 部署与治理产业研判](wiki/syntheses/SYN003-FDE中美企业AI部署与治理产业研判.md)
- [K005：Agent 自治与责任矩阵](wiki/concepts/K005-Agent自治与责任矩阵.md)
- [REL002：FDE 行业报告发布映射](wiki/releases/REL002-FDE行业报告发布映射.md)
- [外部研究资料索引](wiki/_indexes/EXTERNAL-RESEARCH-SOURCES.md)
- [主知识库接入说明](governance/MAIN_KB_INTEGRATION.md)
