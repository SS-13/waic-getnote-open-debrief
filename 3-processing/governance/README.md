# WAIC LLM Wiki Governance v1.1

> 治理的目标不是把资料做成更大的目录，而是让每一条可复用知识都能说明：它来自哪里、适用于何时、证据强度如何、与什么冲突、何时需要重审。

## 治理边界

- `1-raw/`：Get笔记原始记录，保持只读。
- `2-data/`：人工整理与完整逐字稿等补充证据，保持只读。
- `3-processing/index/source-registry.jsonl`：当前来源库存的派生注册表。
- `3-processing/wiki/`：经问题驱动摄取后的 question、claim、tension、synthesis、concept 与 release。
- `4-outputs/`：对外产出，只能引用 Wiki 或证据层，不能反向充当事实来源；由 release 记录映射。

## 四个工作模式

| 模式 | 允许动作 | 不允许动作 |
|---|---|---|
| `register` | 更新来源注册表、识别增量和指纹变化 | 改写来源内容 |
| `explore` | 阅读、比较、提出候选 claim | 把候选当作知识库结论 |
| `integrate` | 写入有来源定位的 claim、tension、synthesis | 静默覆盖相反证据 |
| `release` | 从已审查 Wiki 派生产出 | 从未审查的展示或摘要直接下结论 |

## 发布对象链

`source → claim → tension/synthesis → concept → release → Markdown/PDF/PPT/figures`

其中 `concept` 是跨问题复用的分析框架，`release` 是发布登记而不是新证据。输出层发现错误时，必须沿链回到最早受影响的知识对象修订。

## 权威顺序

1. 具体来源及其定位。
2. 经过引用核验的 claim。
3. synthesis 与输出。

当下层与上层冲突时，回到上层修正，不在输出层补丁式改写。

## 文档

- [来源注册表 schema](SOURCE_REGISTRY_SCHEMA.md)
- [摄取协议](INGESTION_PROTOCOL.md)
- [Lint 与发布门禁](LINT_AND_RELEASE.md)
- [运营节奏](OPERATING_CADENCE.md)
- [主知识库接入](MAIN_KB_INTEGRATION.md)
- [主知识库注册申请](MAIN_KB_REGISTRATION_REQUEST.json)
- [注册表生成器](build-source-registry.mjs)
- [治理 lint](lint-knowledge-base.mjs)
