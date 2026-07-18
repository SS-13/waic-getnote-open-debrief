# outputs/ · 第三大块：我的产出

> 图表、报告、跨年对比 —— 这是仓库里**真正对外的部分**。
> 前两大块（data / processed）是原料，本块是成品。

---

## 结构

```
outputs/
├── 2024/
│   ├── charts/            ← 图（PNG / SVG / HTML）
│   ├── reports/           ← 报告（MD / PDF / Notebook）
│   └── compare/           ← 跨议题 / 跨年对比
└── 2025/
    ├── charts/
    ├── reports/
    └── compare/
```

| 子目录 | 用途 | 命名示例 |
| --- | --- | --- |
| `charts/` | 单图、单可视化 | `2025-07-31__company_mentions.png` |
| `reports/` | 完整分析报告 | `2025-waic-recap.md` |
| `compare/` | 跨年 / 跨议题对比 | `2024-vs-2025-topics.md` |

---

## 文件命名约定

`<YYYY-MM-DD>__<主题>.<ext>`

- 日期：产出日期（不是数据日期）
- 主题：kebab-case，简要说明这张图/这份报告在讲什么

---

## 入库策略

✅ 入库：图表、报告、对比（体积可控）
❌ 不入库：交互式 notebook 的 `.ipynb` 检查点、临时文件

---

## 引用规范

任何对外发布的产物，致谢处加：

> 数据来源：得到 App「笔记」· WAIC <year> 采访
> 二阶解读：本仓库 owner

这是对源头团队的**最小尊重**。