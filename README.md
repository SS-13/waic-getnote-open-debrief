# waic-getnote-open-debrief

> **个人项目**：把得到笔记里 WAIC 大会的采访内容，做成自己的年度二阶解读档案。

> 当前年度：**2026**（WAIC 2026 · 2026-07-19 进行中）

---

## 🎯 这是什么

- **不是开源协作大工程**。Owner = 我自己，PR 是补充，不卡流程。
- **不是采访生产方**。采访由得到团队（罗振宇 / 快刀青衣）做，我只做**二阶解读**。
- **是个人年度归档**。WAIC 每年都有，每年我都会拉数据、做整理、出产物。
- **目前活跃年度只有 2026**。历史归档等以后需要对比时再启用。

---

## 📦 三大块

> 这是仓库的核心结构 —— 一切围绕这三块展开。

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   1-data/            2-processing/          3-outputs/            │
│   (原始数据)         (整理后数据)           (我的产出)            │
│                                                                │
│   得到笔记原文       归一化后的稳定 schema    图表 / 报告 / 对比   │
│   入库、可复现        可被分析脚本消费        对外发布 / 自留档     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

| 块 | 路径 | 性质 |
| --- | --- | --- |
| **原始数据** | `1-data/<year>/` | 得到笔记原文（按年归档） |
| **整理后数据** | `2-processing/<year>/` | 归一化、清洗后的稳定 schema |
| **我的产出** | `3-outputs/<year>/` | 图表、报告、跨年对比 |

**按年分目录** —— 今年活跃的是 `2026/`，以后想做对比再开 `2025/`、`2024/` 等历史归档。

---

## 🚀 快速开始

```bash
# 1. 装依赖
pip install -r requirements.txt

# 2. 配凭证（首次）
cp .env.example .env
# 编辑 .env，填入 getnote API 凭证

# 3. 拉原始数据（受 API 限流，慢慢跑）
python scripts/fetch.py --year 2026

# 4. 归一化（一次性）
python scripts/normalize.py --year 2026

# 5. 跑分析（按需）
python scripts/analyze.py --year 2026
```

---

## 📁 目录约定

```
waic-getnote-open-debrief/
├── 1-data/                ← 第一大块：原始数据
│   ├── README.md
│   └── 2026/
│       └── 2026-07-XX__<被访者>.md
├── 2-processing/          ← 第二大块：整理后数据
│   ├── README.md
│   └── 2026/
│       ├── notes.csv
│       ├── companies.csv
│       └── topics.json
├── 3-outputs/             ← 第三大块：我的产出
│   ├── README.md
│   └── 2026/
│       ├── charts/
│       ├── reports/
│       └── compare/       # 跨年对比（等需要时再启用）
├── scripts/
│   ├── fetch.py           ← 拉数据（含限流 + 断点）
│   ├── normalize.py       ← 归一化
│   └── analyze.py         ← 示例分析
├── .env.example
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 🔁 每年怎么用

```
1. 新建 1-data/<year>/ 目录
2. 跑 scripts/fetch.py 慢慢拉数据
3. 跑 scripts/normalize.py 归一化
4. 在 scripts/analyze.py 里加新分析方法
5. 产物输出到 3-outputs/<year>/
6. 想做跨年对比 → 3-outputs/<year>/compare/
```

---

## 🤝 PR / 协作（轻量级）

如果你愿意让人提 PR：

- **不强求流程**，但建议 fork → 分支 → PR
- **不必填 PR 模板**，但 PR 描述里说清楚三件事：
  1. 你分析的是什么数据
  2. 你用了什么方法
  3. 产物放在 3-outputs/ 哪里
- **保留原始数据契约**：所有分析都从 `2-processing/<year>/` 读，不直接读 `1-data/`

---

## 📌 当前状态

- [x] 仓库骨架（个人 + 年度 + 三大块）
- [ ] `1-data/2025/` 数据接入（慢慢拉）
- [ ] `2-processing/2025/` 归一化
- [ ] `3-outputs/2025/` 首份产物
- [ ] `3-outputs/2025/compare/` 跨年对比（需要 `1-data/2024/` 先有）

---

## ⚖️ License

MIT