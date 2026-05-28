from pathlib import Path

from pre_symphony.build_graph import build_graph
from pre_symphony.models import ParsedNode, ParsedPlan
from pre_symphony.parse_plan import parse_plan
from pre_symphony.plan_stages import annotate_stages

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_plan.md"


def _annotated():
    return annotate_stages(build_graph(parse_plan(FIXTURE)))


def _id(graph, role):
    return next(nid for nid, n in graph.nodes.items() if n.role == role)


def test_waves_follow_topo_order():
    g = _annotated()
    assert g.waves[_id(g, "parser")] == 0
    assert g.waves[_id(g, "builder")] == 1
    assert g.waves[_id(g, "storage-choice")] == 2


def test_frontier_is_all_when_nothing_after_decision():
    g = _annotated()
    assert set(g.frontier) == set(g.nodes)
    assert all(state == "Todo" for state in g.initial_state.values())


def test_node_behind_decision_excluded_but_decision_kept():
    plan = ParsedPlan(
        meta={},
        nodes=[
            ParsedNode("decision", "D", "dec", "S#1", options=("a", "b")),
            ParsedNode(
                "work", "Impl", "impl", "S#2",
                depends_on=("dec",), acceptance=("x",), validation=("y",),
            ),
        ],
    )
    g = annotate_stages(build_graph(plan))
    assert _id(g, "impl") not in g.frontier
    assert _id(g, "dec") in g.frontier
