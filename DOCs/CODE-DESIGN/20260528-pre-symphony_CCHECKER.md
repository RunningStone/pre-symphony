# pre-symphony 测试设计(CCHECKER)

Last updated: 2026-05-28 · 配对:[CPLAN](20260528-pre-symphony_CPLAN.md)

> 三层测试(对齐组织规则):UnitTest 秒级、SmokingTest 分钟级不触网、IntegrationTest 打真实 Linear 测试 project。每项标 测试名 / 输入 / 预期 / 边界。

---

## 1. UnitTest(单个类/方法边界)

### parse_plan
- [ ] `test_parse_minimal`:输入最小合法 PLAN → `ParsedPlan` 节点数正确
- [ ] `test_parse_missing_acceptance`:work 节点缺验收 → 解析保留缺失标记(由 validate 报错,不在此抛)
- [ ] 边界:空文件 / 只有标题无内容 / 非法 front-matter

### build_graph
- [ ] `test_node_id_stable`:同 `spec_anchor+kind+role` → **同 hash**;正文改动 → hash 不变(CD-4)
- [ ] `test_edges_blocked_by`:`blocks` 边正确映射 dst.blocked_by=src
- [ ] 边界:重复 node_id 冲突检测;decision 节点 options 解析

### validate
- [ ] `test_detect_cycle`:有环图 → `ValidationError`,报出环路径
- [ ] `test_dangling_edge`:边指向不存在节点 → 报错
- [ ] `test_missing_required`:work 节点缺 acceptance/validation → 报错
- [ ] `test_granularity_warn`:touch_scope 过宽 → 标记建议拆分
- [ ] 边界:单节点图、纯 decision 图

### plan_stages
- [ ] `test_topo_waves`:已知 DAG → 波次序号符合拓扑
- [ ] `test_roots_todo`:无未满足依赖的节点 → `Todo`,其余 `Backlog`
- [ ] `test_frontier`:决策节点**之后**的分支不进 frontier
- [ ] 边界:多根、决策节点为根

### synth_issues
- [ ] `test_schema_fields`:输出含 title/description/labels/priority/milestone/state/blocked_by
- [ ] `test_description_markers`:描述含 AC + Validation + provenance + `<!-- pre-symphony:node=<hash> -->`
- [ ] `test_frontier_only`:只合成 frontier∪其依赖,未选分支不出现
- [ ] 边界:无 milestone 节点、无依赖节点

### push_linear / reconcile(mock LinearClient)
- [ ] `test_create_when_absent`:map 空 → 全部 create
- [ ] `test_skip_when_unchanged`:map 命中且无 diff → skip,**不重复建**
- [ ] `test_update_when_changed`:命中且有 diff → update
- [ ] `test_document_update_not_append`:FR11 文档为替换而非追加,闭合段落消失
- [ ] 边界:Linear 现存有标记但 map 丢失 → 靠标记回收(不误建)

---

## 2. SmokingTest(模块级最小端到端,不触网)
- [ ] `smoke_plan_to_issues`:tiny PLAN(3 work + 1 decision)→ build→validate→stages→synth → `issues.json` 正确;全程 mock/无网络
- [ ] `smoke_preview`:同上再 visualize → 产出 Mermaid + dry-run 摘要,人工确认门拦住未确认的 push

## 3. IntegrationTest(完整 pipeline,真实 Linear 测试 project)
- [ ] `integ_push_idempotent`:对真实测试 project 推送 → 建 issue+milestone+关系;**再跑一次全 skip**,project 内无重复
- [ ] `integ_decision_rerun`:完成决策人工门 → 重跑 → 被选分支前沿出现、未选分支不创建
- [ ] `integ_symphony_pickup`(可选/手动):确认 Symphony 能 poll 到产出的 `Todo` issue 并起 workspace

## 运行约定
- [ ] UnitTest 每次 commit 前全绿
- [ ] SmokingTest 合并新 feature 前通过
- [ ] IntegrationTest 按需手动(需 `LINEAR_API_KEY` + 测试 project)
