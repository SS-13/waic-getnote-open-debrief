# Joseph's Garden 主知识库接入

## 当前状态

| 层级 | 状态 | 证据 |
|---|---|---|
| WAIC 本地 Wiki 升级 | 已完成 | Schema v0.2、Q002、C005-C009、T002、SYN002、K001-K004、REL001 |
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
3. Vault 已建立 `10_domains/WAIC-AI战略研究/README.md` 和 `REL001-WAIC战略研究报告发布映射.md`。
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

## 主库映射结果

- Vault 入口：`/Users/macos/Documents/Joseph_garden/Joseph's garden/10_domains/WAIC-AI战略研究/README.md`
- Vault release 指针：`/Users/macos/Documents/Joseph_garden/Joseph's garden/10_domains/WAIC-AI战略研究/REL001-WAIC战略研究报告发布映射.md`
- 状态端点：`/Users/macos/Documents/Joseph_garden/Joseph's garden/10_domains/WAIC-AI战略研究/SYSTEM_STATUS.md`
- 注册记录：`system_id=waic-research`、`dashboardOrder=70`、`checkTime=23:38`、`statusAutomationId=waic`
- 首次状态：`green`，`checked_at=2026-07-22T12:21:26+08:00`，全库 9 个状态端点校验通过
