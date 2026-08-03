# Knowledge Workbench Automation

这里是知识工作台的运行连接器，不属于 `scripts/` 中的历史复现工具。

## 当前边界

- 唯一自动来源：得到大脑自建知识库 `ai 资讯`（`JVl2k6DY`）。
- 只调用知识库普通笔记列表和单条笔记详情接口。
- 不调用订阅博主、订阅内容或直播接口。
- 链接笔记只保存得到大脑 AI 整理、来源链接和内容指纹，不复制第三方网页全文。
- Joe 记录为 `curator`，不冒充第三方资料作者；笔记保存时间与来源发布时间分开处理。
- Raw 版本不覆盖；同一笔记修订后形成新版本，并保留相同 canonical source 与 evidence lineage。

## 日常权威流程

每日任务在 Codex 创建的独立 worktree 中运行：

```bash
python3 automation/publish_daily_sync.py
```

当前调度器：Codex Automation `waic-2`，每日 `09:07`（Asia/Shanghai），状态 `ACTIVE`。既有夜间 `waic` 状态自检保留，两者职责不重叠。

新任务要求 worktree 干净；若它只落后 `origin/main`，会在隔离环境中直接切到已验证的远端后继提交，真正分叉或无归属的本地超前则停止。任务启动前先持久化 publish journal，随后执行普通笔记同步、批次账本、Registry、NOW 与治理 lint。只有所有门禁通过且变更路径全部命中白名单时才 commit/push；推送前若远端已经前进，任务立即停止，不 merge、rebase 或 force push。

若上次进程中断，只有 journal 的基础提交、阶段、白名单路径和 SHA-256 均与当前 worktree 一致时才会续跑。它可恢复 pipeline 未完成、已完成未 commit、已 commit 未 push，以及 push 成功但回执丢失；没有有效 journal 的任何脏改动仍会被拒绝。

write-once 完整基线为 `5` 条普通笔记，其中 `1` 条已评分并路由、`4` 条保持 `pending`；此后已有 `2` 条按 `new-source + pending` 接入。全量完成状态由 `3-processing/index/intake-baseline.json` 独立证明，不再用 ledger 是否为空猜测；单条 tracer 或部分同步不会结束 baseline 模式。动态计数以 `3-processing/wiki/NOW.md` 为准。

## 人工诊断

```bash
python3 automation/sync_getnote_intake.py --dry-run
```

该命令只检查 Getnote 差集，不改知识文件。`run_daily_pipeline.py` 和 `publish_daily_sync.py` 属于每日自动事务，不应在 Joe 有其他改动的主工作区手工发布。

## Phase 2 已上线能力

- Getnote 请求有 60 秒超时、最多 3 次有限重试和明确失败清单。
- `.cache/getnote-intake/` 保存被 Git 忽略的运行状态、失败记录、文件事务 manifest 和 publish journal；失败不冒充 `zero-change`。
- 单写入者锁阻止并发摄取；Raw 与 ledger 先完整 staging 和校验，再发布或回滚。
- 同一 `note_id + versionHash` 重跑不重复；修订保留旧 Raw，并沿用 canonical source 和 evidence lineage。
- 全量列表必须明确返回 `has_more=false`；首次全量成功后，排序 note ID、数量和哈希写入 create-only baseline marker，并与 Raw/ledger 在同一文件事务提交。
- `ordinaryNoteIdsHash` 对升序 ID 逐项追加 LF 后计算 SHA-256，供 Python 同步器与 Node 治理 lint 交叉复核。
- baseline 最终判定在单写者锁内、历史事务恢复之后执行；治理派生失败时 marker、ledger 与新增 Raw 一并回滚。
- `intake-batches.jsonl` 区分 baseline、new source 和 revision；NOW 机器区块只展示实质批次。
- Registry、snapshot、batch、NOW 与 lint 连续双跑字节稳定。
- Git 发布只允许预定路径；journal 对路径和内容哈希进行归属校验，中断后只续跑本任务拥有的状态。
- Git commit 是对远端可见的原子边界；远端分叉时停止，不自动处理历史。

Phase 2 不自动完成 SQS、谱系裁决、Claim/CCS 变化、正式 Brief 或 PPT。新资料可以获得 Topic/Question 候选，但初始状态保持 `pending`；这些语义判断属于 Phase 3。

## 状态含义

- `changed`：发现新来源、修订，或修复了陈旧派生视图；完整门禁通过后才发布。
- `zero-change`：连接成功、内容无变化、派生视图一致；知识文件逐字节不变，不创建 commit。
- `dry-run`：只报告 Getnote 差集。
- `failed`：认证、网络、结构、下载、lint 或 Git 边界失败；不得解释为“没有新增”。

## 验证

测试命令：

```bash
python3 -m unittest discover -s automation/tests -p 'test_*.py' -v
node 3-processing/governance/lint-knowledge-base.mjs
```
