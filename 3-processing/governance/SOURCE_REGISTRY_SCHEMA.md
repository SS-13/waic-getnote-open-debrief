# Source Registry Schema v1.0

## 目的

`3-processing/index/source-registry.jsonl` 是可重建的来源清单。它只读取证据层元数据和文件内容指纹，不保存正文副本，不修改来源文件。

## 主键与去重

| 字段 | 规则 |
|---|---|
| `sourceId` | 本地文件记录身份：`raw:<noteId>`、`data:<noteId>` 或文件内容 SHA-256 指纹。 |
| `canonicalSourceId` | 底层来源身份：有 `noteId` 时为 `note:<noteId>`；用于发现跨层副本。 |
| `noteId` | Get笔记的唯一键；允许为空。 |
| `contentHash` | 文件全文 SHA-256，用于发现同一路径内容更新。 |
| `duplicateOf` | 仅在人工审核确认同一来源或同一证据谱系后填写。 |

同一 `canonicalSourceId` 表示来自同一 Get笔记来源，但不自动删除副本。`2-data/` 可能提供同一来源的更高保真版本；是否设置 `duplicateOf` 或 `supersedes` 必须经过审查。

## 记录字段

| 字段 | 含义 |
|---|---|
| `schemaVersion` | 当前记录 schema 版本。 |
| `sourceId` / `canonicalSourceId` / `noteId` | 本地文件、底层来源与 Get笔记身份。 |
| `sourceLayer` | `raw` 或 `data`。 |
| `relativePath` | 相对仓库根目录的路径。 |
| `title` / `author` / `source` | frontmatter 可用元数据。 |
| `eventYear` | 从 WAIC 路径或标题推断的事件年份；无法判断时为 `null`。 |
| `publishedAt` / `capturedAt` | 来源发布与本地采集时间；允许为空。 |
| `contentSource` | 如 `manual-transcript` 等上游标注。 |
| `fidelity` | `verbatim`、`structured`、`summary`、`pointer` 或 `unknown`。 |
| `contentHash` | 全文指纹。 |
| `reviewStatus` | `registered`、`triaged`、`integrated`、`superseded`、`excluded`。 |
| `duplicateOf` | 已确认重复时的 `sourceId`；默认 `null`。 |
| `registeredAt` | 本次注册表生成时间。 |

## 时间语义

- `eventYear` 不是文件采集年份。
- `publishedAt` 不是 `capturedAt`。
- Wiki 的 claim 与 synthesis 另有自己的 `asOf`。

任何跨年趋势判断都必须以 `eventYear` 或明确的 `eventDate` 为基准。

## 保真度规则

保真度表示表达离原始材料的距离，不是事实正确性的评级。

| 值 | 条件 |
|---|---|
| `verbatim` | 明确标为完整逐字稿、现场录音实录或 `manual-transcript`。 |
| `structured` | 人工整理稿、官方完整报告。 |
| `summary` | 明确是 AI 摘要或二阶摘要。 |
| `pointer` | 只有链接、预告或极少内容。 |
| `unknown` | 元数据无法可靠判断时的默认值。 |

## 注册表生成与审查

生成器负责机械字段，不负责语义判断。`fidelity`、`reviewStatus`、`duplicateOf` 的非默认升级必须经人工或带证据的 Agent 审查，并留下 Wiki 或治理记录。
