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

automation/    当前知识工作台连接器（与 scripts/ 历史复现工具分离）
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
| 当前变化面板 | `3-processing/wiki/NOW.md` |
| 普通笔记接入说明 | `automation/README.md` |

## ⚠️ 不要做的事

- ❌ 不要运行 `scripts/` 里的旧同步或生成脚本——它们只作为**历史复现工具**保留
- ❌ 不要把仓库当成应用代码看待
- ❌ 不要修改 1-raw/ 里的原始数据（raw data 是契约）
- ❌ 不要把大会展示、签约或厂商自报直接写成社会普及结论
- ❌ 不要接入订阅博主、订阅内容或直播；只有 Joe 主动保存到白名单知识库的普通笔记可以自动进入

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
| 自动同步并发布白名单 KB | `python3 automation/publish_daily_sync.py` | Codex 独立 worktree，每日 09:07 |
| 仅查看差集（不写入） | `python3 automation/sync_getnote_intake.py --dry-run` | 临时 |
| 查看最近有效变化 | 打开 `3-processing/wiki/NOW.md` | 每次同步后 |

当前自动入口的唯一白名单是得到大脑自建知识库 `ai 资讯`（`JVl2k6DY`）中的**普通笔记**。`note_id` 必须按字符串保存，用于 canonical identity；同一笔记的版本由 `note_id + versionHash` 区分，旧 Raw 不覆盖。Joe 主动保存只提高处理优先级，不提高 SQS/CCS。

每日任务只能在 Codex 的独立 worktree 中执行。新任务要求 worktree 干净；仅当存在有效 publish journal，且基础提交、白名单路径和内容哈希一致时，才可恢复上一次中断留下的受管改动或自有未推送提交。只落后远端时可切到 `origin/main` 的已验证后继，真正分叉或无归属的本地超前时停止。自动提交仅包含 Raw 新版本、baseline/intake/batch/registry/lint 账本和 NOW 机器区块，禁止 merge、rebase 或 force push。SQS、谱系裁决、Claim/CCS、正式 Brief 和 PPT 仍需后续治理，不属于 Phase 2 自动入口。旧 `scripts/daily_sync.py` 与 `JawjeBlY` 拉取命令仅供历史复现，禁止作为当前日常入口执行。
