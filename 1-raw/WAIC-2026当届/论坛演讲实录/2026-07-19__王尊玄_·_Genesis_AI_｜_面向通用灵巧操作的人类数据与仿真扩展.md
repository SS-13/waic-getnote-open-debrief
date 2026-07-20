---
title: "王尊玄 · Genesis AI ｜ 面向通用灵巧操作的人类数据与仿真扩展"
author: Joe
date: 2026-07-19
source: getnote
note_id: 1916059717265454968
captured_at: 2026-07-19 22:01:09
original_url: https://www.biji.com/note/1916059717265454968
---

- **论坛**：WAIC 2026「智启具身·迎接物理 AI 智能涌现论坛」（智源、蜜蜂科技联合主办）
- **时间**：2026-07-19 · 上海 · 金厅 A+B · 主旨演讲
- **嘉宾**：王尊玄（Genesis AI，联合创始人）

## 一句话概要
主张用"系统化"的方式解 robotics：从硬件/数据设备而非只靠算法去解决人机对齐，用一比一手套采集非侵入式被动数据，并把仿真推到高保真极致，让物理 AI agent 在仿真里做自我进化（self-evolution），把"受实时限制"的问题转化为"可 scale compute"的问题。

## 核心观点
- Robotics 是一个**系统性问题**：应先看 end-to-end pipeline（数据收集→硬件→中间件/控制栈→数据采集系统→模型训练→数据管线→评测→数据飞轮），找出最关键的 pain point 再做优化。
- 数据采集主张做**一比一手数据**：让手套、机器手、人手都长得一模一样，从**硬件设计与数据设备**去解决对齐，而不是只从模型/算法去弥合 embodiment gap。
- 好的数据系统应是**非侵入式、被动式**：工人戴上手套就能照常做原本的工作——这在商业部署上很关键，避免让商业伙伴额外培训员工。
- 三类数据各有取舍：**第一人称（egocentric）数据**采集成本最低（戴个头套即可）但缺物理选项、离部署远；**机器人数据**含最多物理资讯、与部署最直接相关，但采集成本高、量受限；理想是兼顾"物理信息"与"离部署近"两个维度。
- 仿真要推到 fidelity 极致（rendering + physics），fidelity 的最终定义是"能否用于 robot learning / robot evaluation"；算法开发由评测需求驱动（哪块 contact dynamics 不好就往哪推进），并高度重视并行化 efficiency。
- North Star 是 inner loop（physical AI agent 在海量仿真环境交互、拿分数做类 RL 更新）+ outer loop，让基础模型在仿真里做 self-evolution——把"一直要实时采集经验"的现实问题，转化为"scale compute 就能解决"的问题。
- 资源投入约 **80% 用于 scale data**（手套数据、第一人称预训练数据、data contextualization/标注、大规模仿真环境），**20% 用于算法**（模型架构、离线/人在环数据采集等）。

## 内容整理

### 把 robotics 当系统性问题
王尊玄开场即点明 Genesis AI 的第一个 high-level 观点：robotics 是系统性问题。构建机器人系统时要看完整的 end-to-end pipeline——从数据收集、硬件、中间件与控制栈、数据采集系统，到模型训练、数据管线处理、评测，再回到数据飞轮——先找出最关键的 pain point，再针对性优化。今天大家都在讲 scaling，可 anchor 到大模型的几个 stage：预训练用人类数据（手套数据 + 第一人称视角数据），再做对齐（告诉模型该做什么 task），最后用大量仿真环境做 RL training。

### 从硬件与数据设备解决对齐
关于数据，团队的 belief 是做"一比一"的手数据：想办法让手套、机器手、人手长得一模一样。现有采集方案里，遥操很难 scale（硬件问题多、环境不同）；很多人选择从模型训练或 representation learning 去把 UMI 训练数据 transfer 到工厂。而 Genesis 从系统性角度反问：为什么不从**硬件设计和数据设备**去解决？其重点是设计一套非侵入式、被动式的数据系统——工人戴上手套就能照常做原本的工作，这在商业部署上很关键，避免要求商业伙伴额外培训员工；同时手套要能让采集端与最终部署硬件做很大程度的对齐。他进一步用两个维度评估各类数据：第一人称数据优势是采集极便宜（戴个头套即可），但缺物理选项、离部署远；机器人数据含最多物理资讯、与部署最直接相关，但成本高、量受限。

### 高保真仿真与自我进化
考虑到真机采集"慢、有安全性与硬件可靠性考量"，团队发展 Generative Flow，把仿真推向 rendering 与 physics 的高保真极致。fidelity 的定义最终落在"能否用于 robot learning / robot evaluation"；训练栈开发高度重视并行化 efficiency（做规模实验时很重要），物理算法开发由评测需求驱动——觉得 contact dynamics 不够好，就往那个方向继续推进 fidelity。整个发展的 North Star，是构建 inner loop 与 outer loop：inner loop 里 physical AI agent 在海量（如十万个）仿真环境中大量交互、拿到分数后做类 RL 层面的更新，从而让物理 AI agent 或任意基础模型在仿真里做 self-evolution。这样就把"一直要实时 actively collect experience"的现实约束，转化为"你可以 scale compute、compute 越大 performance 越好"的问题。

### 资源分配与部署目标
在数据与模型的取舍上，Genesis 把约 80% 的 effort 放在 scale data（手套数据、第一人称预训练数据、data contextualization/标注、大规模仿真环境），约 20% 放在算法（模型架构、离线或人在环的数据采集等）。模型方向的 scaling 目标是 **instant deployment**，并抛出一个关键判断：robotics 是不是一个"局部问题"（local problem）——若是局部问题，就能把它拆成金字塔式的多层、复用已知 pretrained model；这直接影响资源如何分配。团队目前正把原本 lab 级场景往真实世界部署推进，做到完整闭环。

## 金句
> "与其从模型和算法去弥合人机差距，不如从硬件设计和数据设备去解决——让手套、机器手和人手长得一模一样。"
> "一旦能让 agent 在仿真里自我进化，我们就把一个被实时限制的现实问题，变成了一个'scale compute 就能解决'的问题。"
