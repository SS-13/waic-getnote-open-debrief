# Joseph's Garden 主知识库接入

## 当前状态

| 层级 | 状态 | 证据 |
|---|---|---|
| WAIC 本地 Wiki 升级 | 已完成 | Schema v0.3、K006、SQS/CCS 账本与 REL003 已加入；既有 Q001-Q003 保持可回查 |
| 交付物映射 | 已完成 | REL001 映射 Markdown、PDF、PPT 与 F01-F08 |
| 主库正式注册 | 已完成 | `waic-research`，Dashboard 顺序 70 |
| Vault 映射入口 | 已完成 | `10_domains/WAIC-AI战略研究/README.md` 与 REL001 指针 |
| 夜间自检 | 已配置 | 自动化 `waic`，每日 23:38 |
| `SYSTEM_STATUS.md` 首次发布 | 已完成 | 2026-07-22 12:21 发布，单系统与全库协议校验均通过 |

## 对接身份

| 字段 | 建议值 |
|---|---|
| `system_id` | `waic-research` |
| `system_name` | `WAIC AI 战略研究` |
| `system_kind` | `research` |
| `system_parent` | `knowledge-core` |
| 主库映射根目录 | `10_domains/WAIC-AI战略研究` |
| 主库人工入口 | `10_domains/WAIC-AI战略研究/README.md` |
| 主库状态路径 | `10_domains/WAIC-AI战略研究/SYSTEM_STATUS.md` |
| 外部真源 | 本仓库 `3-processing/wiki/`、`3-processing/index/`、`4-outputs/2026/` |

## 已执行的主库动作

1. `99_知识库治理/system-registry.json` 已注册 `waic-research`，顺序 70，自检时间 23:38，自动化 ID 为 `waic`。
2. `99_知识库治理/系统注册表.md` 已增加同一系统的人工记录。
3. Vault 已建立 `10_domains/WAIC-AI战略研究/README.md`，并映射 REL001、REL002；REL003 与状态快照随本次评分体系发布更新。
4. 主系统晨检已从写死的“8 份状态”改为读取注册表中的全部状态。
5. 首份 `SYSTEM_STATUS.md` 已由 WAIC 子系统自主发布；夜间任务继续在 23:38 自检，主系统次日 07:10 只读并校验。

## 首次状态的真源

- `3-processing/index/source-registry.snapshot.json`：来源库存与重复谱系。
- `3-processing/index/governance-lint-report.json`：注册表、Wiki 字段和链接健康。
- `3-processing/wiki/HOME.md`：问题、综合、概念与发布入口。
- `3-processing/wiki/releases/REL001-WAIC战略研究报告发布映射.md`：最近正式产出。
- `4-outputs/2026/reports/waic-strategic-research-2018-2026/README.md`：交付文件及研究口径。

## 建议状态指标

主 Dashboard 最多显示四项：

| 指标 | 含义 |
|---|---|
| 已注册来源 | `source-registry.snapshot.json` 中的来源数量 |
| 有 ID 的 Wiki 对象 | lint 报告中的 `wikiIds` |
| 活跃研究问题 | `questions/` 中非 archived 问题数 |
| 正式 release | `releases/` 中 `published` 数量 |

这些指标衡量可调用存量和发布流动，不把文件数量当作人的掌握程度。

## 升级闭环

```text
新增资料
  → source registry
  → 问题驱动摄取
  → claim / tension / synthesis
  → 可复用 concept
  → release 映射交付物
  → publish-system-status
  → Joseph's Garden Dashboard
```

主知识库只订阅状态和入口，不复制或改写 raw。外部仓库仍是 WAIC 证据与分析的真源，Vault 中的入口和状态是派生视图。

## 评分系统的孵化与上提

WAIC 研究子系统是蜂巢式置信度体系的校准场，而非主知识库所有内容的容器。SQS（来源可靠度）与 CCS（Claim 结论置信度）在本仓库通过来源账本、Claim 账本、证据谱系去重、复审条件与治理 lint 持续验证；当前为 `v1.0 / provisional`。

Joseph's Garden 已建立 `10_domains/AI知识中枢/` 与 `98_原料池/AI收件箱/`：前者负责跨主题导航、研究问题、学习和实践连接，后者接收非 WAIC 的新外部输入。主库现在复用来源/结论分离、谱系去重和复审的原则；在跨来源类型校准、Joe 复核、一致性检验、版本迭代和小范围试运行完成前，不把具体阈值或分数宣布为总库强制标准。

评分规则完成上提后，应保留四种对象的边界：SQS 只评来源，CCS 只评 Claim，Mastery L0-L4 评学习掌握，Capability E0-E4 评项目交付证据。任何正式上提都必须登记新版本与迁移说明，不回写或复制 WAIC 的 `1-raw/`。

## 主库映射结果

- Vault 入口：`/Users/macos/Documents/Joseph_garden/Joseph's garden/10_domains/WAIC-AI战略研究/README.md`
- Vault release 指针：`/Users/macos/Documents/Joseph_garden/Joseph's garden/10_domains/WAIC-AI战略研究/REL001-WAIC战略研究报告发布映射.md`
- 状态端点：`/Users/macos/Documents/Joseph_garden/Joseph's garden/10_domains/WAIC-AI战略研究/SYSTEM_STATUS.md`
- 注册记录：`system_id=waic-research`、`dashboardOrder=70`、`checkTime=23:38`、`statusAutomationId=waic`
- 首次状态：`green`，`checked_at=2026-07-22T12:21:26+08:00`，全库 9 个状态端点校验通过
