# WAIC AI 战略研究

> **WAIC 2018–2026 的原始资料、二阶解读与问题驱动 Wiki**
> 整理：Joe · 这是个人 AI 总知识库中的 WAIC 专题研究子系统。

## Research Desk

日常阅读从这里开始：

- [进入研究工作台：当前判断、主题与任务入口](3-processing/wiki/HOME.md)
- [看最近发生了什么](3-processing/wiki/NOW.md)
- [按主题理解](3-processing/wiki/topics/README.md)
- [查看来源与评分边界](3-processing/wiki/sources/README.md)
- [处理待 Joe 复核事项](3-processing/wiki/reviews/README.md)
- [生成或回看简报](3-processing/wiki/briefings/README.md)

> 新的 Get笔记输入只接受 Joe 自建知识库 `JVl2k6DY` 中主动保存的普通笔记。订阅博主、订阅内容和直播不导入、不登记、不评分；Joe 主动保存也只提高处理优先级，不提高 SQS 或 CCS。
>
> Phase 2 已冻结 5 条普通笔记的历史基线，并接入此后 2 条真实新增；当前 7 条普通笔记中 6 条为 `pending`、1 条为 `routed`。每日 09:07 的独立 worktree 事务在零变化时不改知识文件、不创建 commit；评分与 Claim 交叉验证留给 Phase 3。

---

## 📌 这是什么

这是一个持续演进的 **WAIC 专题研究知识库**，不是技术应用仓库，也不是承载全部 AI 课程、资讯和个人想法的通用笔记目录。

项目从 2026 WAIC 下午流水席 37 场嘉宾访谈的二阶解读起步，目前已经扩展为 2018–2026 WAIC 资料池，并增加了以真实问题为入口的 LLM Wiki。原始资料负责保真，Wiki 负责积累可追溯的主张、冲突和跨来源判断。

AI 总知识库的总入口、课程、项目能力和个人决策维护在 Joseph's Garden；本仓库以 WAIC 为核心证据池，只接入被活跃研究问题实际使用的外部佐证。完整边界与接入方法见 [AI 总知识库架构](3-processing/governance/AI_TOTAL_KB_ARCHITECTURE.md)。

---

## 🚀 推荐阅读：WAIC 2018–2026 深度战略研究

这份报告基于除 `4-outputs/` 外的全库样本，重点回答：九年间 AI 如何演进，应用场景如何变化，普通人会从哪里进入，哪些岗位会扩展，以及治理怎样成为可规模化能力。

| 版本 | 用途 | 入口 |
| --- | --- | --- |
| 完整文字稿 | 查结论、证据、附录和来源 | [Markdown 报告](4-outputs/2026/reports/waic-strategic-research-2018-2026/WAIC-2018-2026-战略研究报告.md) |
| 专业图文版 | 连续阅读与正式分发 | [《WAIC 2018–2026 AI 演进、应用、就业与治理战略研究报告》PDF](4-outputs/2026/reports/waic-strategic-research-2018-2026/WAIC-2018-2026-AI演进、应用、就业与治理战略研究报告.pdf) |
| 汇报版 | 会议讲解与投屏展示 | [22 页 PPT](4-outputs/2026/reports/waic-strategic-research-2018-2026/WAIC-2018-2026-AI演进、应用、就业与治理战略研究报告-汇报版.pptx) |
| 独立图表 | 文章、演示与二次分析 | [8 张研究 Figures](4-outputs/2026/figures/waic-strategic-research-2018-2026/README.md) |

### 四个核心判断

1. **九年主线不是模型参数升级，而是 AI 的责任半径扩大**：从识别和推荐，走向生成、工具调用、任务执行和物理行动。
2. **应用价值从“功能可见”转向“任务闭环”**：软件 Agent 会先于通用家用机器人规模化，工业具身智能处于两者之间。
3. **普通人的第一波变化发生在工作流和公共服务**：随后才是眼镜、陪伴设备和家庭机器人等持续终端。
4. **治理不是附加成本，而是进入高价值场景的条件**：身份权限、部署前测试、运行监测、人工接管和责任救济需要成为持续控制环。

### 证据规模与边界

- 扫描 `887` 份 Markdown，年度统计以 `836` 个唯一 `note_id` 为分母。
- 纳入 2026 流水席 `37` 场访谈、`38` 个命名主体，以及治理论坛和完整逐字稿。
- WAIC 是产业供给侧窗口，不代表全国平均采用；厂商销量、客户、参数和效果均保留“自报”属性。

### 知识库升级

这份研究不只存放在输出目录，已经回写为可追踪的 Wiki 升级：新增 [Q002](3-processing/wiki/questions/Q002-AI责任半径扩大后，应用、岗位与治理如何联动.md)、[SYN002](3-processing/wiki/syntheses/SYN002-AI演进、应用、就业与治理战略综合.md)、4 个分析概念和 [REL001 发布映射](3-processing/wiki/releases/REL001-WAIC战略研究报告发布映射.md)。系统已作为 `waic-research` 接入 Joseph's Garden 主知识库，具体映射、状态协议与自检时序见 [主知识库接入说明](3-processing/governance/MAIN_KB_INTEGRATION.md)。

## FDE 专项研究

FDE（Forward Deployed Engineer）研究把企业 AI 的问题从“如何做一个 Agent”转成“如何把业务、数据、权限、模型、组织和持续治理组成生产系统”。报告基于 WAIC 历届企业部署材料、OpenAI/Palantir/Anthropic 官方岗位页及中美治理资料，采用能力形态而非单一职位名比较中美路径。

- [完整行业报告](4-outputs/2026/reports/fde-industry-report-2026/FDE-2026-中美企业AI部署与治理行业报告.md)
- [Wiki 综合 SYN003](3-processing/wiki/syntheses/SYN003-FDE中美企业AI部署与治理产业研判.md)
- [Agent 自治与责任矩阵 K005](3-processing/wiki/concepts/K005-Agent自治与责任矩阵.md)

## 蜂巢式知识置信度评分

资料会持续进入这个知识库：新的 WAIC、政府文件、研究报告、厂商公告、新闻与日常线索。它们不应因热度或转载量获得相同权重。系统现已建立两层评分：来源可靠度 `SQS` 评价一份资料对其直接事实的可靠度；Claim 结论置信度 `CCS` 评价一个判断是否获得独立证据谱系的支撑。

- [评分体系说明与专业 PDF](4-outputs/2026/reports/beehive-confidence-scoring/README.md)
- [蜂巢式置信度与证据收敛 K006](3-processing/wiki/concepts/K006-蜂巢式置信度与证据收敛.md)
- [蜜蜂选巢读书笔记](3-processing/wiki/_indexes/BOOK-001-达尔文投资知识-蜜蜂选巢笔记.md)
- [评分规范](3-processing/governance/CONFIDENCE_SCORING.md)

当前已纳入 28 条跨类型来源与 5 条 Claim：C008、C009、C010、C014 四条核心 B 级 Claim 已于 2026-08-03 由 Joe 确认，C015 仍为 C 级支持性假设。确认不改变原始分数；同源转载、摘要和改写仍只计算为一个证据谱系。

---

## 🎯 这不是什么

- ❌ 这不是一段可以 `git clone && npm install && npm run dev` 跑起来的应用
- ❌ 这不是某家公司的产品代码
- ❌ 这不是 WAIC 官方内容——所有访谈内容版权归得到 App 所有

---

## 🧠 怎么用（最重要）

**你拿去和 AI 一起读。**

每个人有自己分析问题的角度。你可以：

1. **从 [`3-processing/wiki/HOME.md`](3-processing/wiki/HOME.md) 进入问题**
2. **读 synthesis、claim 和 tension**，了解当前结论与分歧
3. **沿引用回查 `1-raw/` 或 `2-data/`**，核验具体来源
4. **继续追问、修正或写自己的解读**——笔记、文章、二创、PPT
5. **看 `4-outputs/`** 里的卡片图、看板、问题清单当快速浏览入口

> **我的解读不是标准答案。** 仓库提供的是**结构化的原料**，你做出来的东西才是成品。

---

## 🪴 欢迎你扩展

如果你基于这份资料写了**有意思的扩展**（新分类、新分析、新卡片、新工具），**欢迎提 PR**。

- 任何形式的二创都接受：评论、批注、对比分析、可视化、跨场关联……
- 我能获得新的认知，是这份资料**最大的价值**

---

## ⭐ 如果觉得有用，请 Star

**这个 Star 不是给我的，是给这个主题的。**

WAIC 是中国 AI 行业一年一度的风向标——这种规模的现场访谈不多，**把内容结构化沉淀下来让更多人能用**，是这件事本身的价值。

---

## 🙏 内容来源

本仓库所有访谈内容，均来自：

- **得到 App「得到大脑」**独家整理的 WAIC 2026 流水席访谈记录
- 原访谈由**罗振宇 & 快刀青衣**主理

没有得到团队的现场采访和深度整理，这份档案不存在。

---

## 🔗 相关链接

- **GitHub 仓库**：`https://github.com/SS-13/waic-getnote-open-debrief`
- **得到 App**：「WAIC 流水席」专题

---

## 📁 目录速览

```
仓库/
├── 1-raw/         # 原始数据（getnote CLI 拉的逐字稿 + 智能总结）
├── 2-data/        # 手工整理信息（完整逐字稿 / 人工分组）
├── 3-processing/    # 索引、MECE 文档与问题驱动 LLM Wiki
├── 4-outputs/       # 产出（卡片图、看板、PDF 合集）
├── agents.md        # 给 AI agent 看的结构说明
├── LICENSE          # MIT
└── README.md        # 本文件
```

> 📦 `scripts/`（复现工具）和 `templates/`（HTML 模板）在仓库里但**不主动展示**——它们是 Joe 自己复现用的，不是给你用的。

## 新资料接入边界

- 既有 `1-raw/` 保留为 WAIC 历史证据，不因新入口切换而覆盖或重排。
- 新的自动入口白名单是 Get笔记自建知识库 `JVl2k6DY`，只接受普通笔记。
- 订阅博主、订阅内容和直播在登记前排除，不进入 raw、来源库存、评分账本或简报候选。
- 零新增是正常状态：不生成空简报，也不应制造无意义的 Git 提交。
- 最近有效变化、来源状态和待复核项统一从 [Research Desk](3-processing/wiki/HOME.md) 查看。

V2 的完整输入、浏览、简报与 Agent 圆桌约束见 [Research Workbench v2 计划](plans/knowledge-workbench-v2.md)。仓库维护边界见 [`agents.md`](./agents.md)。
