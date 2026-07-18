# processed/ · 第二大块：整理后数据

> 把 `data/<year>/` 里的原始笔记归一化成稳定的 schema，让下游分析脚本不用关心原始格式差异。

---

## 结构

```
processed/
├── 2024/
│   ├── notes.csv          ← 全部 note 一行一条
│   ├── companies.csv      ← 公司维度聚合
│   ├── topics.json        ← 议题聚类结果
│   └── ...
└── 2025/
    └── ...
```

## 当前 schema

### `notes.csv`

| 列 | 类型 | 说明 |
| --- | --- | --- |
| `note_id` | str | 唯一 ID |
| `date` | str | 采访日期（YYYY-MM-DD） |
| `interviewee` | str | 被访者 |
| `company` | str | 被访者公司 |
| `title` | str | 笔记标题 |
| `duration_sec` | int | 音频时长 |
| `transcript_len` | int | 文字稿字数 |
| `tags` | str | 用 `|` 分隔 |
| `source_path` | str | 对应 `data/<year>/` 下的源文件路径 |

### `companies.csv`

| 列 | 类型 | 说明 |
| --- | --- | --- |
| `company` | str | 公司名 |
| `mentions` | int | 在该年所有 note 中被提及的次数 |
| `note_count` | int | 该公司被访次数 |

### `topics.json`

```json
{
  "year": 2025,
  "topics": [
    {
      "topic_id": "t01",
      "label": "大模型应用",
      "note_ids": ["2025-07-XX__...", "..."],
      "keywords": ["应用", "落地", "场景"]
    }
  ]
}
```

## 如何生成

```bash
# 归一化所有 note 到 CSV
python scripts/normalize.py --year 2025

# 生成 companies.csv（频次统计）
python scripts/analyze.py --year 2025 --kind companies
```

## 入库策略

| 文件 | 入库？ | 原因 |
| --- | --- | --- |
| `notes.csv` | ✅ | 体积小，可被 git diff |
| `companies.csv` | ✅ | 同上 |
| `topics.json` | ✅ | 同上 |
| 任何 > 1MB | ❌ | 拆出去或 gitignore |