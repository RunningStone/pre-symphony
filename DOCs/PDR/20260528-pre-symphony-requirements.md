# pre-symphony 需求总纲

Last updated: 2026-05-28 · Status: DRAFT(待评审)

---

## 1. 背景

[Symphony](https://github.com/openai/symphony) 是一个**只读 tracker** 的 Codex 编排服务:它轮询 Linear 上处于 active 状态的 issue,为每个 issue 起隔离 workspace 跑 Codex,并按 issue 状态机推进(`Backlog → Todo → In Progress → Human Review → Merging → Rework → Done`)。它**不负责创建 issue**——issue 从哪来、怎么拆,完全在它职责之外(`SPEC.md §11.5`)。

上游的 coding agent(claude-code / codex)擅长基于某个 SPEC 产出**自由形式的计划(PLAN)**,但这种 PLAN 不是 Symphony 能直接消费的、可追踪可回滚的 issue 列表。

**`pre-symphony` 填的就是这一段空白**:把「基于 SPEC 的 PLAN」转成「对 Symphony 友好的 Linear issue 列表」。

---

## 2. 一句话目标

> 输入:一个 coding agent 基于某 SPEC 写出的 PLAN。
> 处理:把 PLAN 构造成一张**带约束、带阶段标志的有向图(DAG)**,校验、切分到合适粒度。
> 输出:一组**对 Symphony 友好**的 Linear issue(原子、带依赖关系、带验收/验证门、带初始状态),交给 Symphony 追踪与执行。

---

## 3. 范围

### 3.1 In Scope
- 解析 PLAN → 构造 PLAN DAG(节点/边/决策节点/阶段标志)。
- 校验 DAG(无环、粒度、必填字段)。
- 把节点合成为 Symphony 友好的 issue 记录。
- **幂等地**把 issue 推到 Linear(创建/更新/跳过,不产生重复)。
- 推送前的**可视化 + dry-run 预览**(供人工确认)。
- 通过 `schpet/linear-cli`(submodule)访问 Linear。

### 3.2 Out of Scope(明确不做)
- **执行 issue**:由 Symphony + Codex 负责,不在本项目。
- **写 SPEC / 写 PLAN**:由上游 claude-code 负责。
- **做一个 tracker**:Linear 才是 tracker,本项目只往里写。
- **跑 Symphony / 改 Symphony**:本项目只产出它的输入。

---

## 4. 角色与数据流

```
┌─────────────┐   PLAN(md)   ┌──────────────┐  Linear issues  ┌──────────┐  poll  ┌────────┐
│ claude-code │ ───────────▶ │ pre-symphony │ ──────────────▶ │  Linear  │ ◀───── │Symphony│
│ (写 SPEC+PLAN)│             │  (本项目)     │   (经 linear-cli)│ (tracker)│        │+ Codex │
└─────────────┘              └──────────────┘                 └──────────┘        └────────┘
        ▲                            │                                                  │
        │                            └── plan_graph.json / issues.json / 可视化 (人工确认)  │
        └──────────────────────── SPEC 作为可追溯锚点 ◀───── issue 描述里回链 SPEC ──────────┘
```

---

## 5. 核心概念:PLAN DAG 模型

PLAN 被建模为一张有向无环图。**节点 = 一个原子工作项 = 一个 Symphony issue = 一个 PR(回滚单元)**。

「可回滚」不是一个功能,而是**节点粒度**的属性:Symphony 给每个 issue 一个隔离 workspace + 一条从 `origin/main` 切的新分支 + 一个 PR,`Rework` 是整体重置。所以节点必须切到「一个 PR 装得下、能独立 revert」的粒度。

### 5.1 图要捕获的东西(含补充)

用户已点名:**建图 / 上下依赖关系 / 决策节点 / 阶段标志**。在此基础上补充,使其足以生成 Symphony 友好的 issue:

| # | 要素 | 说明 | 映射到 Symphony / Linear |
|---|---|---|---|
| G1 | **节点(原子工作项)** | 一个 PR 能装下的最小独立改动 | 一个 Linear issue |
| G2 | **依赖边** | 区分硬依赖 vs 软关联 | `blocks`/`blockedBy`(硬)、`related`(软) |
| G3 | **决策节点** | 其产出(结果分档)决定下游走哪条分支 | 见 §9 开放问题(Symphony 无条件分支,需特殊处理) |
| G4 | **阶段标志 / 里程碑** | 把节点分成波次(M0 sanity → M1 → M2 …) | Linear **milestone**(`linear milestone create`) |
| G5 | **验收标准(Acceptance Criteria)** | 每节点「做完」的客观判据 | 写进 issue 描述;Symphony 镜像进 workpad 作硬性门 |
| G6 | **验证 / 测试计划(Validation/Test Plan)** | 可执行的验证命令/步骤 | 写进 issue 描述;Symphony 视为不可降级的验收输入 |
| G7 | **初始状态** | DAG 根(无未满足依赖)→ `Todo`;其余 → `Backlog` | issue 初始 state(Symphony 只自动启 active 状态) |
| G8 | **来源可追溯(provenance)** | 节点回链它实现的 SPEC 章节/claim | issue 描述里的 SPEC 锚点 + 隐藏标记行 |
| G9 | **幂等键(stable id)** | 节点稳定 id,保证重跑不产生重复 issue | 描述里 `<!-- pre-symphony:node=<id> -->` + 本地映射文件 |
| G10 | **优先级 / 预估成本** | 排序与并发预算(Symphony 有 `max_concurrent_agents`) | Linear `priority`;成本用于波次规划 |
| G11 | **标签** | 让 Symphony 选中并归类 | label `symphony` + 自定义标签 |
| G12 | **范围契约(touch scope)** | 节点声明它大致动哪些文件/模块,用于校验「一个 PR」假设并提示拆分 | 用于 G1 粒度校验,不一定进 issue |

### 5.2 图约束(校验器必须 enforce)
- **无环**:DAG,拓扑可排序(否则报错并指出环)。
- **依赖完整**:每条边两端节点都存在,无悬空引用。
- **粒度**:超大节点(touch scope 过宽 / 子任务过多)被标记,建议拆分。
- **必填字段**:每个非决策节点必须有 验收标准(G5)+ 验证(G6),否则不允许推送。
- **回滚一致性**:每个节点应对应一个连贯可独立 revert 的改动。

---

## 6. 功能需求(FR)

| ID | 需求 | 理由 / 备注 |
|---|---|---|
| **FR1** | 定义并解析 **PLAN 输入契约**(markdown + 可选 front-matter / 结构化块) | 上游 agent 按此格式产出 PLAN;契约要稳定、对 LLM 友好 |
| **FR2** | 由 PLAN 构造 **PLAN DAG**(§5),落成 `plan_graph.json` | 图是中心产物,后续步骤都基于它 |
| **FR3** | **校验 DAG**(§5.2:无环、完整、粒度、必填字段) | 不合规则阻断推送并给出可行动报错 |
| **FR4** | **决策节点建模**(见 §9 推荐方案) | Symphony 无条件分支,需显式策略 |
| **FR5** | **阶段/里程碑 + 初始状态计算**(波次、Todo vs Backlog) | 拓扑排序得波次;DAG 根 → Todo |
| **FR6** | **合成 Symphony 友好 issue**(title / 描述含 AC+Validation+provenance / labels / priority / milestone / 关系 / 初始 state) | 严格对齐 Symphony issue schema(`SPEC.md §4.1.1`) |
| **FR7** | **dry-run 预览 + 可视化**(导出 `issues.json` + Mermaid/Graphviz 图),**人工确认门** | 对外写之前必须有人看一眼;呼应「降低认知负担 + GUI 辅助」 |
| **FR8** | **幂等推送 / reconcile** 到 Linear(create/update/skip,稳定 id 防重复),维护 `state/linear_map.json` | 这是纯 markdown 规范做不到、必须用代码的核心价值 |
| **FR9** | **Linear 访问层** 经 `schpet/linear-cli`(submodule);CLI 不覆盖的(关系/state/label)走 `linear api` 原始 GraphQL | 见 §8 能力映射;全程不用 MCP |
| **FR10** | **可追溯**:每个 issue 能回链到 SPEC 的章节/claim | 审计 + rebuttal + 复盘 |

---

## 7. 非功能需求(NFR)

- **NFR1 引擎无关**:claude-code 或 codex 都能驱动(核心逻辑在 Python + SKILL,不绑定具体 agent)。
- **NFR2 低上下文 / 不用 MCP**:Linear 访问走 CLI/脚本,避免 MCP 的每请求固定 token 开销。
- **NFR3 确定性 + 幂等**:同一 PLAN 多次跑,结果稳定、不产生重复 issue。
- **NFR4 人在环**:对外写 Linear 之前强制 dry-run + 人工确认。
- **NFR5 可观测**:每次运行产出日志与 `issues.json` 快照,便于复查/回滚决策。
- **NFR6 可移植**:依赖最小化;linear-cli 以 submodule 锁版本。

---

## 8. linear-cli(submodule)能力映射

`vendor/linear-cli`(`schpet/linear-cli`, Deno/TS, pin `v2.0.0-7-gfc85b91`)。

| 需要的操作 | CLI 是否直接支持 | 用法 |
|---|---|---|
| 非交互建 issue | ✅ | `linear issue create -t "<title>" -d "<desc>" [--project <id>] [--milestone <name>]` |
| 建里程碑(阶段标志) | ✅ | `linear milestone create --project <id> --name "<stage>" [--target-date <d>]` |
| 查询/导出现有 issue(reconcile 用) | ✅ | `linear issue query --json [--all-teams --limit 0]` |
| 设依赖关系 `blockedBy`/`related` | ❌(CLI 无关系命令) | 走 `linear api`(原始 GraphQL,`issueRelationCreate`) |
| 设 label / 初始 state(Backlog/Todo)/ priority | ⚠️ 部分/不确定 | 优先 `linear api` GraphQL;先 `linear schema` 自查字段 |
| 附 SPEC/PLAN 为文档 | ✅(可选) | `linear document create --title ... --content-file plan.md` |

**结论**:建 issue / 里程碑 / 查询用 CLI;**关系、state、label 用 `linear api` 原始 GraphQL 兜底**。先用 `linear schema` introspection 确认字段再固化查询。

---

## 9. 开放问题 / 待决策

1. **决策节点怎么落地(最关键)**。Symphony 无条件分支能力。推荐方案(待确认):
   - **只推送活跃前沿**:DAG 完整建模整棵树(用于规划+可视化),但**只把当前可执行的前沿节点推到 Linear**。决策节点本身作为**人工门** issue;它完成后,**重跑 pre-symphony** 展开被选中的分支,未选分支永不创建。
   - 好处:Symphony 模型干净、不创建会被取消的投机 issue、契合「可回滚/不浪费」精神。
   - 备选:一次性把所有分支建成 `Backlog` 且 `blockedBy` 决策节点,事后人工把选中分支移到 `Todo`、取消其余(会产生需清理的 issue)。
2. **阶段标志映射**:Linear **milestone**(推荐)还是 label?milestone 更语义化但需 project 维度。
3. **幂等键策略**:节点 id 用「SPEC 锚点 + 标题 hash」自动生成,还是要求 PLAN 显式写 `id:`?推荐:显式优先、缺省回退到 hash。
4. **是否把 SPEC/PLAN 作为 Linear document 一并上传**(增强可追溯,但增加写操作)。
5. **多 Agent 并行(后续)**:当前先单 Agent 串行产出;未来波次内的独立节点可并行执行(由 Symphony 的 `max_concurrent_agents` 承接),pre-symphony 侧需保证波次/依赖正确。
6. **是否绑定 Linear**:已默认绑定(submodule 即为证)。若未来要脱离 Linear,需为 Symphony 写非 Linear tracker adapter——不在本项目范围。

---

## 10. 架构概览(初步)

```
pre-symphony/
├── SKILL.md                 # 给 coding agent 的技能:编排下面的 Python,串起 PLAN→issues 全流程
├── <python package>/        # 核心逻辑(待实现)
│   ├── parse_plan.py        # FR1: PLAN → 结构化
│   ├── build_graph.py       # FR2: 构造 PLAN DAG → plan_graph.json
│   ├── validate.py          # FR3: DAG 校验
│   ├── plan_stages.py       # FR5: 波次 + 初始状态
│   ├── synth_issues.py      # FR6: 合成 issue → issues.json
│   ├── visualize.py         # FR7: Mermaid/Graphviz + dry-run 预览
│   └── push_linear.py       # FR8/FR9: 经 linear-cli 幂等 reconcile
├── vendor/linear-cli/       # submodule: Linear 访问(CLI + 原始 GraphQL)
├── state/linear_map.json    # 幂等映射:node id → Linear issue identifier
└── DOCs/PDR/                # 本需求文档
```

**核心产物链**:`PLAN.md → plan_graph.json →(校验)→ issues.json →(人工确认)→ Linear`。

---

## 11. 构建里程碑(pre-symphony 自身)

- **M0**:需求评审(本文档)+ 决策 §9.1。
- **M1**:PLAN 输入契约 + 建图 + 校验(FR1–FR3),纯本地、无 Linear。
- **M2**:issue 合成 + 可视化 + dry-run(FR5–FR7),产出 `issues.json` 但不推送。
- **M3**:幂等推送 + linear-cli 接入(FR8–FR9),打通到 Linear。
- **M4**:SKILL 编排 + 端到端跑通(SPEC→PLAN→Linear→Symphony 接力)。
