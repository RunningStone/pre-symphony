"""Data models for the PLAN DAG and Linear issue records.

See DOCs/CODE-DESIGN/20260528-pre-symphony_CPLAN.md §2.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Literal

NodeKind = Literal["work", "decision", "milestone_marker"]
EdgeKind = Literal["blocks", "related"]
IssueState = Literal["Backlog", "Todo"]


def compute_node_id(spec_anchor: str, kind: str, role: str) -> str:
    """Stable id over a *stable subset only* (CDECISION_TREE CD-4).

    Title/body are deliberately excluded so that rewording a node does not
    change its id and make it look like a brand-new issue.
    """
    key = f"{spec_anchor}\n{kind}\n{role}"
    return sha256(key.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class ParsedNode:
    """A node as parsed from the PLAN, before ids/edges are resolved.

    ``depends_on`` references other nodes by their human-writable ``role``,
    never by id (ids are auto-hashed, see compute_node_id).
    """

    kind: str
    title: str
    role: str
    spec_anchor: str
    milestone: str | None = None
    priority: int | None = None
    depends_on: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    touch: tuple[str, ...] = ()
    body: str = ""
    acceptance: tuple[str, ...] = ()
    validation: tuple[str, ...] = ()
    options: tuple[str, ...] = ()


@dataclass
class ParsedPlan:
    meta: dict
    nodes: list[ParsedNode]


@dataclass
class PlanNode:
    node_id: str
    kind: str
    title: str
    role: str
    spec_anchor: str
    body: str = ""
    acceptance: list[str] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)
    milestone: str | None = None
    priority: int | None = None
    labels: list[str] = field(default_factory=list)
    touch_scope: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)


@dataclass
class PlanEdge:
    src: str
    dst: str
    kind: str = "blocks"  # dst is blocked_by src when kind == "blocks"


@dataclass
class PlanGraph:
    nodes: dict[str, PlanNode] = field(default_factory=dict)
    edges: list[PlanEdge] = field(default_factory=list)
    # Stage annotations, filled by plan_stages (M2). Empty until then.
    waves: dict[str, int] = field(default_factory=dict)
    initial_state: dict[str, str] = field(default_factory=dict)
    frontier: list[str] = field(default_factory=list)


def graph_to_dict(graph: PlanGraph) -> dict:
    return {
        "nodes": {nid: asdict(node) for nid, node in graph.nodes.items()},
        "edges": [asdict(edge) for edge in graph.edges],
        "waves": graph.waves,
        "initial_state": graph.initial_state,
        "frontier": graph.frontier,
    }


def graph_from_dict(data: dict) -> PlanGraph:
    return PlanGraph(
        nodes={nid: PlanNode(**nd) for nid, nd in data.get("nodes", {}).items()},
        edges=[PlanEdge(**ed) for ed in data.get("edges", [])],
        waves=data.get("waves", {}),
        initial_state=data.get("initial_state", {}),
        frontier=data.get("frontier", []),
    )
