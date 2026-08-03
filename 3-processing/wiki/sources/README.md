---
id: VIEW-SOURCES
type: navigation-view
status: active
as_of: 2026-08-03
derived: true
---

# 来源视图

> 这里只展示已被正式接受的证据入口与评分边界，不复制来源正文。SQS 评价来源能直接证明什么，不代表其中所有结论都成立。

## 当前库存快照

- 技术来源注册表的实时数量以 [Registry snapshot](../../index/source-registry.snapshot.json) 为准；最近接入、分流和评分计数以 [NOW](../NOW.md) 的机器区块为准，导航性的 `README.md`、`INDEX.md` 不计为证据。
- SQS 账本截至 2026-08-03 有 `28` 条来源评估。
- 问题级来源索引分别覆盖 Q001 `18` 条、Q002 `17` 条、Q003 `18` 条；它们存在交叉引用，不是互斥总数。
- 新输入白名单 `JVl2k6DY` 的 write-once marker 冻结 `5` 条历史基线；基线后的普通笔记按真实 `new-source` 或 `revision` 进入，不回写基线。

[技术注册表](../../index/source-registry.jsonl) · [来源 SQS 账本](../../index/source-assessments.jsonl) · [评分规范](../../governance/CONFIDENCE_SCORING.md)

## 最近接受的来源

### 北京智能体政策解读

`SQS C / 60 · AI summary · AI provisional · 2026-08-03`

能够证明微信公众号作者卡兹克提出了这套政策解读，并可回查得到大脑笔记、微信链接和接入版本。当前保存正文是得到大脑 AI 整理，不是北京市政策原文或作者逐字原文；不能单独证明政策条文、执行效果、行业普及或文中引用数字。

[来源页](SRC-AI-001-北京智能体政策解读.md) · [得到大脑笔记](https://www.biji.com/note/1916397389742706520) · [Q002](../questions/Q002-AI责任半径扩大后，应用、岗位与治理如何联动.md) · [Q003](../questions/Q003-FDE如何将企业转化为可治理的AI运行系统，中美路径有何差异.md)

### 飞书社区《FDE 人才白皮书》

`SQS C / 64 · structured · AI provisional · 2026-08-02`

能够直接证明作者陈宇锋发布了这套 FDE 框架，并保留全文、章节、表格和四张配图。不能单独证明其中的招聘增速、薪资、融资、团队规模、行业普遍性和预测。

[来源卡](../../../2-data/外部研究资料/2026-08-02__飞书社区FDE人才白皮书__来源卡.md) · [完整解读与评分](../_indexes/SRC-Q003-18-飞书社区FDE人才白皮书-解读与蜂巢评分.md) · [关联 Claim C015](../claims/C015-半数字化企业中的业务翻译与最小闭环假设.md)

### 赫拉利达沃斯 AI 治理表达

`SQS B / 76 · structured · AI provisional · 2026-08-02`

能够支持“赫拉利在这份第三方视频记录中公开表达了哪些观点”。上传方不是达沃斯或演讲者官方主体；预测性表达不能当作事实结论，目前也没有形成高影响 Claim。

[来源卡](../../../2-data/外部研究资料/2026-07-27__赫拉利达沃斯AI治理表达__来源卡.md) · [外部来源索引](../_indexes/EXTERNAL-RESEARCH-SOURCES.md)

## 按问题回查

- [Q001：WAIC 演进与普通人视角来源](../_indexes/Q001-SOURCES.md)
- [Q002：应用、岗位与治理来源](../_indexes/Q002-SOURCES.md)
- [Q003：FDE 与企业 AI 部署来源](../_indexes/Q003-SOURCES.md)
- [非 WAIC 外部研究资料](../_indexes/EXTERNAL-RESEARCH-SOURCES.md)

## 如何读来源状态

- `未评分`：尚未进入 SQS 账本，不等于低质量。
- `A–E`：来源对其直接事实的可靠度等级，不是整篇内容的真值。
- `AI provisional`：AI 已初评，尚未由 Joe 确认。
- `Joe reviewed`：Joe 已确认评分及其适用边界。
- `fidelity`：表达离原始材料有多近；它与可靠度是两个维度。
- `canonicalSourceId / evidenceLineageId`：用于识别同源转载、摘要、转写和版本，避免重复计票。

## 新输入白名单

新的自动入口只接受 Joe 自建 Get笔记知识库 `JVl2k6DY` 中的普通笔记。Phase 2 已完成 5 条普通笔记的全量历史基线，并允许此后的真实新增与修订滚动接入；订阅博主、订阅内容和直播在来源登记前排除，不进入 raw、registry、SQS、失败清单或 Brief 候选。

Joe 主动保存一条资料只提高处理优先级。它仍需独立判断来源身份、直接性、可追溯性、完整性、利益关系和时效。

[返回 Research Desk](../HOME.md) · [按主题浏览](../topics/README.md)
