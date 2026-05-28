from pathlib import Path

from pre_symphony.build_graph import build_graph
from pre_symphony.models import ParsedNode, ParsedPlan
from pre_symphony.parse_plan import parse_plan
from pre_symphony.plan_stages import annotate_stages
from pre_symphony.synth_issues import synth_issues

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_plan.md"


def _annotated():
    return annotate_stages(build_graph(parse_plan(FIXTURE)))


def _id(graph, role):
    return next(nid for nid, n in graph.nodes.items() if n.role == role)


def test_issue_schema_and_markers():
    g = _annotated()
    issues = synth_issues(g)
    rec = next(r for r in issues if r.node_id == _id(g, "parser"))
    assert "<!-- pre-symphony:node=" in rec.description
    assert "## Acceptance Criteria" in rec.description
    assert "## Validation" in rec.description
    assert "Provenance: SPEC#3.2" in rec.description
    assert "symphony" in rec.labels
    assert rec.state == "Todo"
    assert rec.priority == 2


def test_blocked_by_resolved_to_node_ids():
    g = _annotated()
    issues = synth_issues(g)
    builder = next(r for r in issues if r.node_id == _id(g, "builder"))
    assert _id(g, "parser") in builder.blocked_by


def test_decision_lists_options():
    g = _annotated()
    issues = synth_issues(g)
    decision = next(r for r in issues if r.node_id == _id(g, "storage-choice"))
    assert "## Options" in decision.description
    assert "json-files" in decision.description


def test_frontier_only_excludes_post_decision_nodes():
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
    roles = {g.nodes[r.node_id].role for r in synth_issues(g)}
    assert "dec" in roles and "impl" not in roles
