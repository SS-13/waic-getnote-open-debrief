# Lint And Release Gates v1.0

## Lint 分层

| 检查 | 类型 | 失败后的动作 |
|---|---|---|
| 重复 `sourceId`、缺字段、路径失效、指纹变化 | 结构 lint | 阻止摄取或发布。 |
| claim 无来源定位、日期偷换、引用不存在 | 结构 lint | 阻止发布。 |
| 把摘要写成逐字引文、同源证据重复计数 | 语义 lint | 退回修订。 |
| 相反主张未登记 tension、synthesis 过期 | 语义 lint | 标记待审，不自动改写。 |
| 输出结论无 claim 或 source 支撑 | 发布 lint | 阻止进入 `4-outputs/`。 |
| release 缺 synthesis 或交付路径 | 发布 lint | 阻止登记为正式发布。 |

当前可执行的基础检查由 `lint-knowledge-base.mjs` 生成 `3-processing/index/governance-lint-report.json`：注册表字段、来源路径、注册表快照、Wiki ID、必填 frontmatter、对象引用、内部链接与 release 输出路径。语义 lint 仍要求结合问题语境进行审查。

## 发布门禁

一个 synthesis 或对外产出发布前必须满足：

1. 所有核心结论链接到 claim。
2. 每条核心 claim 至少一个可定位来源。
3. 已标注来源保真度和 `asOf`。
4. 显示关键限制、反证或未知项。
5. 不把签约、演示、观看量和厂商参数直接等同于社会普及。
6. 建立 release 页面，列出 synthesis、正式交付路径和图表映射。
7. 主知识库只读取已注册的状态接口；未注册时保留接入申请，不伪造已接入状态。
8. 新建正式报告必须署名 `Joe`：Markdown frontmatter 使用 `author: Joe`，PDF/PPT 的封面或首屏显示“研究与整理：Joe”。

## 审查等级

| 等级 | 用途 | 证据要求 |
|---|---|---|
| `provisional` | 探索性回答、内部讨论 | 可用摘要，但必须标注限制。 |
| `reviewed` | 可复用内部结论 | 关键判断回查高保真来源或独立来源。 |
| `publishable` | 对外图文、PPT、报告 | 通过发布门禁并保留引用链。 |
