"""Build a PlanGraph from a ParsedPlan (FR2).

Assigns stable node ids (auto-hash), resolves ``depends_on`` roles into edges,
and merges global ``default_labels``. Unknown dependency roles are passed
through as ``<unresolved:role>`` so that ``validate`` can report them rather
than failing here.
"""

from __future__ import annotations

from .models import ParsedPlan, PlanEdge, PlanGraph, PlanNode, compute_node_id


class BuildError(Exception):
    """The plan cannot be turned into a graph (e.g. duplicate role)."""


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def build_graph(plan: ParsedPlan) -> PlanGraph:
    default_labels = _as_list(plan.meta.get("default_labels"))
    role_to_id: dict[str, str] = {}
    nodes: dict[str, PlanNode] = {}

    for pn in plan.nodes:
        if pn.role in role_to_id:
            raise BuildError(f"duplicate role '@{pn.role}'")
        node_id = compute_node_id(pn.spec_anchor, pn.kind, pn.role)
        if node_id in nodes:
            raise BuildError(
                f"node id collision for '@{pn.role}' -> {node_id} "
                "(same spec_anchor+kind+role as another node)"
            )
        role_to_id[pn.role] = node_id
        labels = list(dict.fromkeys([*default_labels, *pn.labels]))  # dedupe, keep order
        nodes[node_id] = PlanNode(
            node_id=node_id,
            kind=pn.kind,
            title=pn.title,
            role=pn.role,
            spec_anchor=pn.spec_anchor,
            body=pn.body,
            acceptance=list(pn.acceptance),
            validation=list(pn.validation),
            milestone=pn.milestone,
            priority=pn.priority,
            labels=labels,
            touch_scope=list(pn.touch),
            options=list(pn.options),
        )

    edges: list[PlanEdge] = []
    for pn in plan.nodes:
        dst = role_to_id[pn.role]
        for dep_role in pn.depends_on:
            src = role_to_id.get(dep_role, f"<unresolved:{dep_role}>")
            edges.append(PlanEdge(src=src, dst=dst, kind="blocks"))

    return PlanGraph(nodes=nodes, edges=edges)
