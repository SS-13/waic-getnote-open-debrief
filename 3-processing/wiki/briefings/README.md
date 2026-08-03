---
id: VIEW-BRIEFINGS
type: navigation-view
status: active
as_of: 2026-08-03
derived: true
---

# 滚动简报

> 当前正式 Brief（`BRF`）数量：`0`。本页提供稳定入口和历史索引位置，不把现有 Synthesis 伪装成已经生成的简报。

## 空状态

现在没有独立、不可覆盖的 BRF 时间快照。可以先读取已有的阶段性综合，也可以基于一个 Topic、Question 或自然语言问题发起首份简报。

- [WAIC 演进阶段答案 SYN001](../syntheses/SYN001-2018至2026-WAIC变化的普通人视角.md)
- [应用、岗位与治理阶段答案 SYN002](../syntheses/SYN002-AI演进、应用、就业与治理战略综合.md)
- [FDE 与企业 AI 阶段答案 SYN003](../syntheses/SYN003-FDE中美企业AI部署与治理产业研判.md)
- [按四个稳定主题选择问题](../topics/README.md)

## 如何发起简报

向 Agent 使用以下自然语言入口：

```text
简报：<主题或问题> [时间范围]
更新简报：<BRF-ID>
```

示例：

```text
简报：FDE 与企业 AI 2026-07-01 至 2026-08-03
简报：AI 治理对普通人的实际影响
简报：Q003
```

Agent 应优先读取 Topic、Question、Claim、Tension、Synthesis、SQS/CCS 账本和被命中的来源索引；不需要为每份简报扫描全部历史正文。

## 每份 Brief 必须回答

1. 一句话当前判断。
2. 相较上一期真正发生了什么变化。
3. 哪些判断被加强、削弱、限定或替代。
4. 最强反证、开放冲突和未知项。
5. 对 Joe、普通人、企业或治理的实际含义。
6. 下一步需要观察或主动寻找什么证据。
7. 来源、SQS、CCS、证据谱系和 `as_of`。

## 版本与证据边界

- Brief 是一个冻结来源集和时间截面的研究快照；旧版本不得覆盖。
- 无实质变化时可以回答“判断未变”，但不创建空洞的新版本。
- 未评分或低分来源只能作为线索，不能包装为确定事实。
- Brief、PPT 和 Agent 圆桌不是来源，不能反向支撑 Claim 或提高 CCS。
- 正式 Brief、PDF、PPT 和报告统一署名“研究与整理：Joe”。

首份 Brief 形成后，应在本页按日期、主题、Question、状态和上一版本建立索引。只有 Joe 已复核的 Brief/Synthesis 才能作为正式 PPT 的主要内容源。

[返回 Research Desk](../HOME.md) · [查看正式输出](../../../4-outputs/README.md)
