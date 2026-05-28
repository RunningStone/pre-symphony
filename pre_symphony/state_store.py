"""Read/write the local JSON artifacts (NFR5): plan_graph.json, issues.json,
linear_map.json. These are human-readable and git-diffable.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import (
    IssueRecord,
    LinearMap,
    PlanGraph,
    graph_from_dict,
    graph_to_dict,
    linear_map_from_dict,
    linear_map_to_dict,
)


def _write(path: Path | str, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_graph(graph: PlanGraph, path: Path | str) -> None:
    _write(path, graph_to_dict(graph))


def load_graph(path: Path | str) -> PlanGraph:
    return graph_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def save_issues(issues: list[IssueRecord], path: Path | str) -> None:
    _write(path, [asdict(issue) for issue in issues])


def load_issues(path: Path | str) -> list[IssueRecord]:
    return [IssueRecord(**d) for d in json.loads(Path(path).read_text(encoding="utf-8"))]


def save_linear_map(lmap: LinearMap, path: Path | str) -> None:
    _write(path, linear_map_to_dict(lmap))


def load_linear_map(path: Path | str) -> LinearMap:
    p = Path(path)
    if not p.exists():
        return LinearMap()
    return linear_map_from_dict(json.loads(p.read_text(encoding="utf-8")))
