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
- [ ] `plan_stages` 正确算出波次、初始状态(根→Todo)、**活跃前沿**
- [ ] `synth_issues` 产出 `issues.json`,字段对齐 Symphony schema(title/desc 含 AC+Validation+provenance/labels/priority/milestone/关系/state)
- [ ] `visualize` 产出 Mermaid/Graphviz 图 + dry-run 摘要
- [ ] 人工确认门生效:未确认不进入推送
- [ ] 冒烟测试:tiny PLAN 全流程到 `issues.json`(见 CCHECKER)

## M3 推送与 Linear
- [ ] `linear_client` 跑通:`issue create` / `milestone create` / `issue query --json`
- [ ] DP1 结论落定:关系/state/label 用 `linear api` 还是自带 GraphQL(更新 DECISION_TREE)
- [ ] 首次推送:建 issue + milestone + `blockedBy` 关系 + 初始 state
- [ ] 重跑幂等:已存在节点 skip / 变更节点 update,**无重复 issue**
- [ ] `state/linear_map.json` 正确维护(node hash → Linear identifier)
- [ ] PLAN/SPEC document **更新式**上传:闭合段落删除,只留活跃前沿
- [ ] 集成测试:跑到真实 Linear 测试 project(见 CCHECKER)

## M4 编排与端到端
- [ ] `SKILL.md` 编排全流程,引擎无关(claude-code / codex)
- [ ] 端到端:一条 SPEC → PLAN → Linear,Symphony 能 poll 到并起 workspace
- [ ] 决策节点流程验证:完成人工门 → 重跑 → 被选分支前沿推送、未选不创建
- [ ] 端到端记录归档(PROGRESS)
