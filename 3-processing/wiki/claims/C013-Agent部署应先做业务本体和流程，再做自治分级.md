---
id: C013
type: claim
status: reviewed
question_ids: [Q003]
source_ids: [SRC-Q003-02, SRC-Q003-04, SRC-Q003-10, SRC-Q003-11, SRC-Q003-16]
scope: enterprise-agent-deployment-method
as_of: 2026-07-22
---

# Agent 部署应先做业务本体和流程，再做自治分级

## Claim

企业 Agent 部署的起点应是价值流、业务对象、决策权与责任边界，而不是选择一个通用 Agent 或给组织画“多 Agent 矩阵”。在此基础上，才把数据、权限、工具和任务拆开，并按任务可验证性与风险责任半径分配 AI 自治程度。

## Evidence

- Palantir 将 Ontology 定义为连接数据资产与现实业务对象的 operational layer，并以对象、属性、关系、行动、函数和动态安全将业务操作显式化。[Palantir Ontology](https://www.palantir.com/docs/foundry/ontology/overview/)
- OpenAI FDE 先做 discovery 和 technical scoping；Technical Deployment Lead 明确要求嵌入客户团队，映射工作流与成功标准，再推进交付和采用。[OpenAI FDE](https://openai.com/careers/forward-deployed-engineer-(fde)-sf-san-francisco/) [OpenAI TDL](https://openai.com/careers/technical-deployment-lead-forward-deployed-engineering-(fde)-sf-san-francisco/)
- 阿里云 WAIC 演讲把业务原生、组织原生、工程原生、运营原生、基础设施原生同时作为企业 Agent 的前提，且将权限与过程放在模型能力同等位置。[阿里云](<../../../1-raw/WAIC-2026当届/论坛演讲实录/2026-07-18__周琦_·_阿里云｜Agent_Native_Cloud：让智能体成为企业原生的能力.md>)

## Boundary

这是一套部署方法论，不是任何一家厂商的强制架构。业务本体的粒度、工具协议与模型选择随行业、系统成熟度和监管要求变化。
