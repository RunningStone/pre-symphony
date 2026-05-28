# pre-symphony 项目计划(PLAN)

Last updated: 2026-05-28 · 类型:**项目管理**(里程碑 / 交付 / 排期 / 依赖 / 风险)
配对文件:[CHECKER](20260528-pre-symphony_CHECKER.md) · [DECISION_TREE](20260528-pre-symphony_DECISION_TREE.md)
架构细节见:[CODE-DESIGN/_CPLAN](../CODE-DESIGN/20260528-pre-symphony_CPLAN.md) · 需求见:[PRD](../PRD/20260528-pre-symphony-requirements.md)

> 本文件只管「做什么、按什么顺序、谁依赖谁、风险在哪」。**类/接口/调用流等架构细节不在此**,见 CPLAN。

---

## 1. 目标

按 [PRD](../PRD/20260528-pre-symphony-requirements.md) 交付 pre-symphony:把 coding agent 基于 SPEC 写的 PLAN,转成对 Symphony 友好、可追踪可回滚的 Linear issue 列表。**完整 DAG 本地建模,只推送活跃前沿**。

**完成定义(DoD)**:能跑通 `SPEC → PLAN.md → plan_graph.json →(校验)→ issues.json →(人工确认)→ Linear`,且重跑幂等、Symphony 能据此接力。

---

## 2. 里程碑与排期

| 里程碑 | 目标 | 交付物 | 出口判据 | 预估 | 依赖 |
|---|---|---|---|---|---|
| **M0** 需求冻结 | PRD + 核心决策定稿 | PRD / PLAN / CPLAN 三件套 | 本批文档评审通过 | 0.5d | — |
| **M1** 建图与校验 | PLAN→DAG→校验,纯本地无 Linear | `parse_plan` / `build_graph` / `validate` + `plan_graph.json` | 给定样例 PLAN 能产出通过校验的 DAG;坏样例报出可行动错误 | 1.5d | M0 |
| **M2** 合成与预览 | DAG→issue 记录 + 可视化 + dry-run | `plan_stages` / `synth_issues` / `visualize` + `issues.json` + Mermaid | 活跃前沿被正确切出;dry-run 产物可读、人工可确认;**不触网** | 1.5d | M1 |
| **M3** 推送与 Linear | 幂等 reconcile 到 Linear | `linear_client` / `push_linear` + `state/linear_map.json` | 首次推送建 issue + milestone + 关系;重跑 skip 不重复;闭合 PLAN document 更新式替换 | 2d | M2、Linear API key/project、DP1 |
| **M4** 编排与端到端 | SKILL 串起全流程 + 真跑一遍 | `SKILL.md` + 端到端记录 | 一条 SPEC 走到 Linear,Symphony 能 poll 到并起 workspace | 1d | M3 |

> 预估为粗估(理想人日),不含评审等待。M3 受 DP1(linear-cli 能力)影响,可能上浮。

---

## 3. 代码修改清单(高层,文件级;细节见 CPLAN)

| 文件 / 模块 | 操作 | 说明 | 里程碑 |
|---|---|---|---|
| `pre_symphony/parse_plan.py` | 新增 | 解析 PLAN 输入契约 → 结构化中间表示 | M1 |
| `pre_symphony/build_graph.py` | 新增 | 构造 PLAN DAG(节点/边/决策/milestone)→ `plan_graph.json` | M1 |
| `pre_symphony/validate.py` | 新增 | DAG 校验(无环/完整/粒度/必填) | M1 |
| `pre_symphony/plan_stages.py` | 新增 | 波次 + 初始状态 + 活跃前沿计算 | M2 |
| `pre_symphony/synth_issues.py` | 新增 | 合成 Symphony 友好 issue → `issues.json` | M2 |
| `pre_symphony/visualize.py` | 新增 | Mermaid/Graphviz + dry-run 预览 | M2 |
| `pre_symphony/linear_client.py` | 新增 | 封装 `vendor/linear-cli`(CLI + 原始 GraphQL) | M3 |
| `pre_symphony/push_linear.py` | 新增 | 幂等 reconcile + document 更新式上传 | M3 |
| `SKILL.md` | 新增 | agent 入口,编排以上步骤 | M4 |
| `pyproject.toml` | 新增 | Python 依赖与打包 | M1 |

---

## 4. 依赖关系

- **外部**:
  - `vendor/linear-cli` submodule —— 已就位(pin `v2.0.0-7-gfc85b91`)。
  - Linear API key + 目标 project slug —— **M3 前必须就绪**(用户提供)。
  - 上游 PLAN 输入契约 —— 由本项目定义(FR1),需与 claude-code 侧约定。
- **内部**:M0 → M1 → M2 → M3 → M4 线性推进;M1 的 DAG 模型是后续一切的根。
- **决策依赖**:M3 依赖 DP1 的结论(linear-cli 能否覆盖关系/state/label);见 DECISION_TREE。

---

## 5. 集成影响(对下游 / 接力)

- **对 Symphony**:产出物必须满足 Symphony issue schema(`SPEC.md §4.1.1`)与状态约定(根节点 `Todo`、其余 `Backlog`),否则 Symphony 选不中或误启。
- **对上游 claude-code**:PLAN 输入契约一旦定稿即成为对上游的接口;变更需同步上游产 PLAN 的方式。
- **对工作区**:本项目是 `pavo_auto_tools` 自动化流里「计划 → 可执行 issue」的桥;不改 Symphony、不改 ARIS。

---

## 6. 风险(详见 DECISION_TREE)

- **R1**:linear-cli 的 `api` 子命令不足以建关系/设 state/label → 退到自带 GraphQL HTTP 客户端(DP1)。
- **R2**:hash 幂等键在节点正文变动时误判为新 issue → 收紧 hash 输入子集或加模糊匹配(DP2)。
- **R3**:上游 PLAN 契约太松导致建图歧义 → 收紧契约 / 增加校验(DP3)。
