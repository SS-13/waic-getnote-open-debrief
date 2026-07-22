# agents.md · 给 AI Agent 看的仓库结构

## 🎯 这是什么
以 2018–2026 WAIC 资料和 2026 下午流水席 37 场访谈为证据池的**二阶解读与 LLM Wiki**。**不是技术应用**——别尝试 `git clone && npm install` 跑起来。

## 📁 结构（证据 → 加工 → Wiki → 产出）

```
1-raw/        Get笔记原始记录，只读
2-data/       人工整理与完整逐字稿等补充证据
      ↓
3-processing/ 索引、既有 MECE 文档与持久语义 Wiki
      ↓
4-outputs/     卡片图、看板、问题清单与 PDF 合集
```

## 📍 关键文件位置

| 内容 | 路径 |
|---|---|
| 17 号对话录（18 场） | `3-processing/2026/0717/07月17日WAIC流水席对话录：提问与回答摘要.md` |
| 17 号 MECE 问题清单 | `3-processing/2026/0717/07月17日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md` |
| 18 号对话录（19 场） | `3-processing/2026/0718/07月18日WAIC流水席对话录：提问与回答摘要.md` |
| 18 号 MECE 问题清单 | `3-processing/2026/0718/07月18日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md` |
| 卡片图（17/18 号各 18/19 张） | `4-outputs/2026/reports/0717/` 和 `0718/` |
| 看板 + 问题清单长图 | `4-outputs/2026/figures/` |
| PDF 合集 | `4-outputs/2026/figures/WAIC-2026-cards-album-0717-0718.pdf` |
| LLM Wiki 入口 | `3-processing/wiki/HOME.md` |
| Wiki schema | `3-processing/wiki/_schema/SCHEMA.md` |
| 首个问题 Q001 | `3-processing/wiki/questions/Q001-历年WAIC的变化，普通人能看到什么.md` |
| 首轮综合 SYN001 | `3-processing/wiki/syntheses/SYN001-2018至2026-WAIC变化的普通人视角.md` |
| 治理规范 | `3-processing/governance/README.md` |

## ⚠️ 不要做的事

- ❌ 不要尝试运行 `scripts/` 里的脚本——它们是**复现工具**，不是为了应用
- ❌ 不要把仓库当成应用代码看待
- ❌ 不要修改 1-raw/ 里的原始数据（raw data 是契约）
- ❌ 不要把大会展示、签约或厂商自报直接写成社会普及结论

## ✅ 推荐用法

- 读 `3-processing/` 里的 markdown，配合 AI 一起做分析、追问、对比
- 从 `3-processing/wiki/HOME.md` 进入问题、claim、冲突和综合结论
- 批量接入资料前，先按 `3-processing/governance/` 的注册、摄取和发布门禁执行
- 回答 Wiki 问题时优先读 synthesis 和 claim，必要时沿引用回查 raw
- 引用 `4-outputs/` 里的图（保留来源标注）
- 基于资料写新解读欢迎提 PR

## 🔄 日常维护

| 操作 | 命令 | 频率 |
|---|---|---|
| 拉取 KB 新增笔记到 1-raw | `python scripts/daily_sync.py` | 每日 |
| 仅查看差集（不下载） | `python scripts/daily_sync.py --dry-run` | 临时 |
| 重建 1-raw 内部索引 | 脚本末尾自动 | 改结构后 |
| 拉取全量 KB 索引清单 | `getnote kb JawjeBlY --all --no-content -o json` | 临时 |

**唯一键 = `note_id`**。所有去重基于此。脚本挂 cron 后,KB 增量自动入 raw,不再需要手工管理。
