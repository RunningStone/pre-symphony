"""Visualization + dry-run preview (FR7).

``to_mermaid`` renders the full DAG (frontier vs. held-behind-decision), and
``dry_run_summary`` produces a human-readable summary of what would be pushed.
The CLI uses these behind a human-confirm gate before any Linear write.
"""

from __future__ import annotations

from .models import IssueRecord, PlanGraph

_SHORT = 6  # short id length for labels


def _short(node_id: str) -> str:
    return node_id[:_SHORT]


def to_mermaid(graph: PlanGraph) -> str:
    frontier = set(graph.frontier) if graph.frontier else set(graph.nodes)
    lines = ["flowchart TD"]
    for nid, node in graph.nodes.items():
        label = f"{node.role}: {node.title}".replace('"', "'")
        nodeid = f"n_{nid}"
        if node.kind == "decision":
            lines.append(f'  {nodeid}{{"{label}"}}')
        else:
            lines.append(f'  {nodeid}["{label}"]')
    for edge in graph.edges:
        if edge.src in graph.nodes and edge.dst in graph.nodes:
            arrow = "-->" if edge.kind == "blocks" else "-.->"
            lines.append(f"  n_{edge.src} {arrow} n_{edge.dst}")
    # styling
    lines.append("  classDef decision fill:#fde68a,stroke:#b45309;")
    lines.append("  classDef held fill:#e5e7eb,stroke:#9ca3af,stroke-dasharray:4;")
    decisions = [f"n_{nid}" for nid, n in graph.nodes.items() if n.kind == "decision"]
    held = [f"n_{nid}" for nid in graph.nodes if nid not in frontier]
    if decisions:
        lines.append(f"  class {','.join(decisions)} decision;")
    if held:
        lines.append(f"  class {','.join(held)} held;")
    return "\n".join(lines)


def dry_run_summary(graph: PlanGraph, issues: list[IssueRecord]) -> str:
    total = len(graph.nodes)
    pushed = len(issues)
    held = total - len(set(graph.frontier or graph.nodes))
    by_state: dict[str, int] = {}
    by_milestone: dict[str, int] = {}
    for rec in issues:
        by_state[rec.state] = by_state.get(rec.state, 0) + 1
        key = rec.milestone or "(none)"
        by_milestone[key] = by_milestone.get(key, 0) + 1

    lines = [
        "pre-symphony dry-run",
        f"  nodes total      : {total}",
        f"  to push (frontier): {pushed}",
        f"  held behind decision: {held}",
        f"  by state         : {by_state}",
        f"  by milestone     : {by_milestone}",
        "",
        "issues to create/update:",
    ]
    for rec in issues:
        blk = f" [blockedBy {len(rec.blocked_by)}]" if rec.blocked_by else ""
        ms = f" ({rec.milestone})" if rec.milestone else ""
        lines.append(f"  - [{rec.state}] {rec.title}{ms}{blk}")
    return "\n".join(lines)
