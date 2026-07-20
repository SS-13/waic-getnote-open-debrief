# agents.md · 给 AI Agent 看的仓库结构

## 🎯 这是什么
WAIC 2026 下午流水席 37 场访谈的**二阶解读知识库**。**不是技术应用**——别尝试 `git clone && npm install` 跑起来。

## 📁 结构（数据流向：1 → 2 → 3）

```
1-raw/       原始数据（getnote CLI 拉的逐字稿 + 智能总结）
   ↓
3-processing/ 加工数据（按 MECE 分类的对话录：提问清单 + 回答摘要）
   ↓
4-outputs/    产出（卡片图 PNG + 看板 + 问题清单 + PDF 合集）
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

## ⚠️ 不要做的事

- ❌ 不要尝试运行 `scripts/` 里的脚本——它们是**复现工具**，不是为了应用
- ❌ 不要把仓库当成应用代码看待
- ❌ 不要修改 1-raw/ 里的原始数据（raw data 是契约）

## ✅ 推荐用法

- 读 `3-processing/` 里的 markdown，配合 AI 一起做分析、追问、对比
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
