from pathlib import Path

import pytest

from pre_symphony.build_graph import BuildError, build_graph
from pre_symphony.models import ParsedNode, ParsedPlan, compute_node_id
from pre_symphony.parse_plan import parse_plan

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_plan.md"


def test_node_id_stable_and_role_sensitive():
    a = compute_node_id("SPEC#1", "work", "x")
    assert a == compute_node_id("SPEC#1", "work", "x")
    assert compute_node_id("SPEC#1", "work", "y") != a
    assert compute_node_id("SPEC#2", "work", "x") != a


def test_build_edges_blocked_by():
    graph = build_graph(parse_plan(FIXTURE))
    assert len(graph.nodes) == 3
    parser_id = compute_node_id("SPEC#3.2", "work", "parser")
    builder_id = compute_node_id("SPEC#3.3", "work", "builder")
    assert any(
        e.src == parser_id and e.dst == builder_id and e.kind == "blocks"
        for e in graph.edges
    )


def test_default_labels_merged_and_deduped():
    graph = build_graph(parse_plan(FIXTURE))
    parser_id = compute_node_id("SPEC#3.2", "work", "parser")
    labels = graph.nodes[parser_id].labels
    assert "symphony" in labels and "backend" in labels
    assert labels.count("symphony") == 1


def test_duplicate_role_raises():
    plan = ParsedPlan(
        meta={},
        nodes=[
            ParsedNode("work", "a", "dup", "S#1", acceptance=("x",), validation=("y",)),
            ParsedNode("work", "b", "dup", "S#2", acceptance=("x",), validation=("y",)),
        ],
    )
    with pytest.raises(BuildError):
        build_graph(plan)


def test_unresolved_dependency_passes_through():
    plan = ParsedPlan(
        meta={},
        nodes=[
            ParsedNode(
                "work", "a", "a", "S#1",
                depends_on=("ghost",), acceptance=("x",), validation=("y",),
            )
        ],
    )
    graph = build_graph(plan)
    assert any(e.src.startswith("<unresolved:") for e in graph.edges)
