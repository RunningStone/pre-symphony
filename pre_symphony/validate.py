"""Validate a PlanGraph (FR3): acyclicity, edge completeness, required fields,
granularity. Errors block a push; warnings are advisory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import PlanGraph

GRANULARITY_TOUCH_LIMIT = 5


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_errors(self) -> "ValidationReport":
        if self.errors:
            raise ValidationError(self)
        return self

    def __str__(self) -> str:
        lines = [f"ERROR: {e}" for e in self.errors]
        lines += [f"WARN:  {w}" for w in self.warnings]
        return "\n".join(lines) if lines else "OK: graph is valid"


class ValidationError(Exception):
    def __init__(self, report: ValidationReport):
        self.report = report
        super().__init__(str(report))


def validate(graph: PlanGraph) -> ValidationReport:
    report = ValidationReport()
    node_ids = set(graph.nodes)

    for edge in graph.edges:
        if edge.src not in node_ids:
            report.errors.append(f"edge {edge.src} -> {edge.dst}: source node not found ({edge.src})")
        if edge.dst not in node_ids:
            report.errors.append(f"edge {edge.src} -> {edge.dst}: target node not found ({edge.dst})")

    cycle = _find_cycle(graph, node_ids)
    if cycle:
        report.errors.append("cycle detected: " + " -> ".join(cycle))

    for node_id, node in graph.nodes.items():
        label = f"@{node.role} ({node_id})"
        if node.kind == "work":
            if not node.acceptance:
                report.errors.append(f"{label}: work node missing acceptance criteria")
            if not node.validation:
                report.errors.append(f"{label}: work node missing validation")
        if node.kind == "decision" and len(node.options) < 2:
            report.errors.append(f"{label}: decision node must have >= 2 options")
        if not node.spec_anchor:
            report.warnings.append(f"{label}: missing spec_anchor (provenance)")
        if len(node.touch_scope) > GRANULARITY_TOUCH_LIMIT:
            report.warnings.append(
                f"{label}: touches {len(node.touch_scope)} paths "
                f"(> {GRANULARITY_TOUCH_LIMIT}); consider splitting"
            )

    return report


def _find_cycle(graph: PlanGraph, node_ids: set[str]) -> list[str] | None:
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in graph.edges:
        if edge.src in node_ids and edge.dst in node_ids:
            adj[edge.src].append(edge.dst)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in node_ids}
    stack: list[str] = []

    def dfs(u: str) -> list[str] | None:
        color[u] = GRAY
        stack.append(u)
        for v in adj[u]:
            if color[v] == GRAY:
                return stack[stack.index(v) :] + [v]
            if color[v] == WHITE:
                found = dfs(v)
                if found:
                    return found
        stack.pop()
        color[u] = BLACK
        return None

    for nid in node_ids:
        if color[nid] == WHITE:
            found = dfs(nid)
            if found:
                return found
    return None
