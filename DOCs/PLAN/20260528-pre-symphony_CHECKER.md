# pre-symphony 项目验证(CHECKER)

Last updated: 2026-05-28 · 配对:[PLAN](20260528-pre-symphony_PLAN.md) · 引用:[DECISION_TREE](20260528-pre-symphony_DECISION_TREE.md)

> 完成一项勾一项,不删除已完成项。分组对应 PLAN 的里程碑。

## M0 需求与设计冻结
- [x] PRD 定稿(含 §9.A 全部决策)
- [x] PLAN 三件套就位(PLAN / CHECKER / DECISION_TREE)
- [x] CPLAN 三件套就位(CPLAN / CCHECKER / CDECISION_TREE)
- [x] PLAN 输入契约草案(FR1)—— 实现在 `pre_symphony/parse_plan.py` docstring + `tests/fixtures/sample_plan.md`;与上游正式约定待 M4

## M1 建图与校验(纯本地)
- [x] `parse_plan` 能解析样例 PLAN → 中间表示(`ParsedPlan`)
- [x] `build_graph` 产出 `plan_graph.json`(节点/边/决策节点/milestone 字段齐全,稳定 hash id)
- [x] `validate` 检出:有环 / 悬空依赖 / 缺验收标准 / 缺验证 / 粒度过大(warning)/ 决策缺 options
- [x] 坏样例每类各有一个报错用例,报错信息可行动(见 `tests/unit/test_validate.py`)
- [x] 单元测试覆盖以上(16 passed)

## M2 合成与预览(不触网)
- [x] `plan_stages` 正确算出波次、初始状态(前沿→Todo)、**活跃前沿**(决策下游排除)
- [x] `synth_issues` 产出 `issues.json`,字段对齐 Symphony schema(title/desc 含 AC+Validation+provenance/marker、labels/priority/milestone/blockedBy/state)
- [x] `visualize` 产出 Mermaid 图 + dry-run 摘要(Graphviz 为可选,暂未做)
- [x] 人工确认门生效:`push` 无 `--yes` 仅本地预览、不写 Linear
- [x] 冒烟测试:tiny PLAN 全流程到 `issues.json`(`tests/smoke/`)

## M3 推送与 Linear
- [x] `linear_client` 实现:`linear api` 原始 GraphQL(create/update/relation/milestone/document/query)—— **代码完成,实跑待 Linear creds**
- [x] DP1 结论:统一用 `linear api` 原始 GraphQL(机制已确认;字段名待实跑校验)—— 见 DECISION_TREE
- [x] `reconcile` 幂等逻辑:create/update/skip + marker 回收 + `linear_map.json`(单测覆盖,fake client)
- [x] document **更新式**上传逻辑:`render_document` + upsert(单测覆盖「替换非追加」)
- [ ] 首次推送 + `blockedBy` + 初始 state 真跑(**待 LINEAR_API_KEY/team/project**)
- [ ] 集成测试跑到真实 Linear project(**gated;无 creds 时自动 skip**)

## M4 编排与端到端
- [x] `SKILL.md` 编排全流程,引擎无关(claude-code / codex)
- [x] CLI 全流程 build/validate/synth/preview/push(确认门)—— 本地端到端跑通
- [ ] 端到端真跑:SPEC → PLAN → Linear,Symphony poll 到并起 workspace(**待 creds**)
- [ ] 决策节点流程:完成人工门 → 重跑 → 被选分支推送、未选不创建(**待真实 Linear 验证**)
- [ ] 端到端记录归档(PROGRESS)—— 待真跑后
