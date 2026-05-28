# pre-symphony 代码架构(CPLAN)

Last updated: 2026-05-28 · 类型:**具体架构设计**(模块 / 类 / 接口 / 数据模型 / 调用流)
配对:[CCHECKER](20260528-pre-symphony_CCHECKER.md) · [CDECISION_TREE](20260528-pre-symphony_CDECISION_TREE.md)
项目管理见:[PLAN](../PLAN/20260528-pre-symphony_PLAN.md) · 需求见:[PRD](../PRD/20260528-pre-symphony-requirements.md)

> 本文件只管「代码长什么样」。里程碑/排期/风险在 PLAN,不重复。具体技术选型岔路见 CDECISION_TREE。

---

## 1. 模块总览

Python 包 `pre_symphony/`,单向数据流,每个模块一职:

| 模块 | 职责 | 输入 → 输出 | FR |
|---|---|---|---|
| `parse_plan` | 解析 PLAN 输入契约 | `PLAN.md` → `ParsedPlan` | FR1 |
| `build_graph` | 构造 DAG | `ParsedPlan` → `PlanGraph`(`plan_graph.json`) | FR2 |
| `validate` | 图校验 | `PlanGraph` → `ValidationReport`(异常即阻断) | FR3 |
| `plan_stages` | 波次 / 初始状态 / 活跃前沿 | `PlanGraph` → `PlanGraph`(标注 wave/state/frontier) | FR4/FR5 |
| `synth_issues` | 合成 issue 记录 | `PlanGraph` → `list[IssueRecord]`(`issues.json`) | FR6 |
| `visualize` | 可视化 + dry-run | `PlanGraph`+`issues` → Mermaid/Graphviz + 摘要 | FR7 |
| `linear_client` | 封装 linear-cli | 调 `vendor/linear-cli`(CLI + 原始 GraphQL) | FR9 |
| `push_linear` | 幂等 reconcile + 文档上传 | `issues` + `LinearMap` → Linear 写入 | FR8/FR10/FR11 |
| `state_store` | 读写本地状态 | `state/linear_map.json`、`plan_graph.json` | 横切 |
| `cli`(`__main__`) | 子命令入口 | `build / validate / synth / preview / push` | 横切 |

---

## 2. 数据模型(dataclass)

```python
NodeKind   = Literal["work", "decision", "milestone_marker"]
EdgeKind   = Literal["blocks", "related"]          # blocks → Linear blockedBy
IssueState = Literal["Backlog", "Todo"]            # 初始态;其余由 Symphony 推进

@dataclass(frozen=True)
class PlanNode:
    node_id: str            # 自动 hash(稳定子集),G9;不要求 LLM 写
    kind: NodeKind
    title: str
    body: str               # 实现说明
    acceptance: list[str]   # G5 验收标准(work 节点必填)
    validation: list[str]   # G6 验证/测试命令(work 节点必填)
    spec_anchor: str        # G8 provenance,回链 SPEC 章节/claim
    milestone: str | None   # G4 阶段标志(本地全量)
    priority: int | None    # G10
    labels: list[str]       # G11,含 "symphony"
    touch_scope: list[str]  # G12 粗略文件/模块范围,供粒度校验
    # decision 专用:
    options: list[str] = field(default_factory=list)   # 各结果分档 → 下游分支 id

@dataclass(frozen=True)
class PlanEdge:
    src: str; dst: str; kind: EdgeKind   # dst blocked_by src(kind=blocks)

@dataclass
class PlanGraph:
    nodes: dict[str, PlanNode]
    edges: list[PlanEdge]
    # plan_stages 标注:
    waves: dict[str, int]            # node_id → 波次序号
    initial_state: dict[str, IssueState]
    frontier: set[str]               # 当前活跃前沿(可推送)

@dataclass
class IssueRecord:               # synth_issues 输出,对齐 Symphony schema
    node_id: str
    title: str
    description: str             # 含 AC + Validation + provenance + 隐藏标记行
    labels: list[str]
    priority: int | None
    milestone: str | None
    state: IssueState
    blocked_by: list[str]        # 依赖节点的 node_id(推送时解析为 Linear id)

@dataclass
class LinearMap:                 # state/linear_map.json
    by_node: dict[str, str]      # node_id(hash) → Linear issue identifier
    document_id: str | None      # FR11 单文档(更新式)
    milestones: dict[str, str]   # 本地 milestone 名 → Linear milestone id
```

`node_id` 算法(见 CDECISION_TREE CD-4):`sha256(spec_anchor + "\n" + kind + "\n" + role_key)[:12]`,**正文不进 hash**。

---

## 3. 关键接口(方法签名)

```python
# parse_plan.py
def parse_plan(md_path: Path) -> ParsedPlan: ...

# build_graph.py
def build_graph(plan: ParsedPlan) -> PlanGraph: ...           # 含 node_id hash 赋值

# validate.py
class ValidationError(Exception): ...                          # 阻断式
def validate(graph: PlanGraph) -> ValidationReport: ...        # 无环/完整/粒度/必填

# plan_stages.py
def annotate_stages(graph: PlanGraph) -> PlanGraph: ...        # 拓扑→waves, 根→Todo, 计算 frontier

# synth_issues.py
def synth_issues(graph: PlanGraph) -> list[IssueRecord]: ...   # 仅 frontier∪其依赖

# visualize.py
def to_mermaid(graph: PlanGraph) -> str: ...
def dry_run_summary(graph: PlanGraph, issues: list[IssueRecord]) -> str: ...

# linear_client.py  (薄封装 vendor/linear-cli;实现方式由 DP1 决定)
class LinearClient:
    def create_issue(self, rec: IssueRecord, project: str) -> str: ...   # 返回 identifier
    def ensure_milestone(self, name: str, project: str) -> str: ...
    def create_relation(self, blocker_id: str, blocked_id: str) -> None: ...
    def query_issues(self, project: str) -> list[dict]: ...              # query --json
    def upsert_document(self, title: str, content: str, doc_id: str|None) -> str: ...

# push_linear.py
def reconcile(issues: list[IssueRecord], lmap: LinearMap, client: LinearClient,
              project: str, dry_run: bool) -> LinearMap: ...   # create/update/skip
```

---

## 4. 调用流(入口 → 出口)

```
SKILL.md ──▶ python -m pre_symphony <subcommand>

build:    parse_plan ─▶ build_graph ─▶ (写 plan_graph.json)
validate: 读 plan_graph.json ─▶ validate ─▶ 报告/抛 ValidationError
synth:    读 graph ─▶ annotate_stages ─▶ synth_issues ─▶ (写 issues.json)
preview:  读 graph+issues ─▶ to_mermaid + dry_run_summary ─▶ 终端/文件(人工确认门)
push:     读 issues + LinearMap ─▶ reconcile(LinearClient) ─▶ 写 Linear + 更新 linear_map.json
                                   └─▶ upsert_document(更新式, 仅活跃前沿)  [FR11]
```

**幂等核心(reconcile)**:对每个 IssueRecord,以 `node_id` 查 `LinearMap.by_node` 与 Linear 现存(描述里的 `<!-- pre-symphony:node=<hash> -->` 标记)→ 命中则 diff→update,未命中则 create;**绝不重复建**。

---

## 5. 与现有代码 / 外部的集成点

- **`vendor/linear-cli`(submodule)**:`linear_client` 通过 subprocess 调用其二进制;关系/state/label 走 `linear api` 原始 GraphQL(待 DP1 定;若不足则内置 `httpx` GraphQL,见 CDECISION_TREE CD-3)。
- **Symphony**:`synth_issues` 的输出 schema 必须与 `REPOs/symphony/SPEC.md §4.1.1` 对齐;`initial_state` 只用 `Backlog`/`Todo`。
- **SKILL.md**:不含业务逻辑,只按 §4 顺序调子命令并在 preview 后插入人工确认。
- **state/**:`plan_graph.json`、`issues.json`、`linear_map.json` 为可提交的可观测产物(NFR5)。
