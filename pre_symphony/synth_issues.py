"""Synthesize Symphony-friendly issue records from an annotated PlanGraph (FR6).

Only the active frontier is emitted (decision-downstream branches are held).
Each issue description carries acceptance criteria, validation, provenance, and
a hidden idempotency marker so reconcile can recover the node->issue mapping
even if the local state file is lost (CD-5).
"""

from __future__ import annotations

from .models import IssueRecord, PlanGraph, PlanNode

MARKER_TEMPLATE = "<!-- pre-symphony:node={node_id} -->"


def marker_for(node_id: str) -> str:
    return MARKER_TEMPLATE.format(node_id=node_id)


def _description(node: PlanNode) -> str:
    parts: list[str] = []
    if node.body:
        parts.append(node.body)
    if node.kind == "decision" and node.options:
        parts.append("## Options\n" + "\n".join(f"- {opt}" for opt in node.options))
    if node.acceptance:
        parts.append("## Acceptance Criteria\n" + "\n".join(f"- [ ] {a}" for a in node.acceptance))
    if node.validation:
        parts.append("## Validation\n" + "\n".join(f"- [ ] {v}" for v in node.validation))
    parts.append(f"---\nProvenance: {node.spec_anchor or '(none)'}\n\n{marker_for(node.node_id)}")
    return "\n\n".join(parts)


def synth_issues(graph: PlanGraph) -> list[IssueRecord]:
    pushed = set(graph.frontier) if graph.frontier else set(graph.nodes)

    blockers: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
    for edge in graph.edges:
        if edge.kind == "blocks" and edge.src in pushed and edge.dst in pushed:
            blockers[edge.dst].append(edge.src)

    records = [
        IssueRecord(
            node_id=nid,
            title=node.title,
            description=_description(node),
            state=graph.initial_state.get(nid, "Todo"),
            labels=list(node.labels),
            priority=node.priority,
            milestone=node.milestone,
            blocked_by=sorted(blockers[nid]),
        )
        for nid, node in graph.nodes.items()
        if nid in pushed
    ]
    records.sort(key=lambda r: (graph.waves.get(r.node_id, 0), r.title))
    return records
