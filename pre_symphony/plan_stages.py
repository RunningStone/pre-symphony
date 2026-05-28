"""Annotate a PlanGraph with waves, initial state, and the active frontier (FR4/FR5).

Policy (refines PRD; grounded in Symphony SPEC §8.2):
- The *active frontier* is every node NOT transitively behind a decision node.
  Decision-downstream branches are held locally and pushed only after the
  decision is resolved and pre-symphony is re-run (§5.3).
- Frontier nodes get initial state ``Todo``. Symphony will not dispatch a Todo
  issue while any blocker is non-terminal (SPEC §8.2), so ordering is enforced
  by ``blockedBy`` relations rather than by parking dependents in Backlog.
"""

from __future__ import annotations

from collections import deque

from .models import PlanGraph


def annotate_stages(graph: PlanGraph) -> PlanGraph:
    adj, radj = _blocks_adjacency(graph)
    graph.waves = _compute_waves(graph, adj, radj)
    behind = _behind_decision(graph, adj)
    graph.frontier = [nid for nid in graph.nodes if nid not in behind]
    graph.initial_state = {nid: "Todo" for nid in graph.frontier}
    return graph


def _blocks_adjacency(graph: PlanGraph) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    ids = set(graph.nodes)
    adj: dict[str, list[str]] = {nid: [] for nid in ids}
    radj: dict[str, list[str]] = {nid: [] for nid in ids}
    for edge in graph.edges:
        if edge.kind == "blocks" and edge.src in ids and edge.dst in ids:
            adj[edge.src].append(edge.dst)
            radj[edge.dst].append(edge.src)
    return adj, radj


def _compute_waves(
    graph: PlanGraph, adj: dict[str, list[str]], radj: dict[str, list[str]]
) -> dict[str, int]:
    """Longest-path topological level (assumes acyclic; validate enforces that)."""
    indeg = {nid: len(radj[nid]) for nid in graph.nodes}
    wave = {nid: 0 for nid in graph.nodes}
    queue = deque(nid for nid in graph.nodes if indeg[nid] == 0)
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            wave[v] = max(wave[v], wave[u] + 1)
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return wave


def _behind_decision(graph: PlanGraph, adj: dict[str, list[str]]) -> set[str]:
    behind: set[str] = set()
    for nid, node in graph.nodes.items():
        if node.kind != "decision":
            continue
        stack = list(adj[nid])
        while stack:
            v = stack.pop()
            if v in behind:
                continue
            behind.add(v)
            stack.extend(adj[v])
    return behind
