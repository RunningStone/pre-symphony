import pytest

from pre_symphony.models import PlanEdge, PlanGraph, PlanNode
from pre_symphony.validate import ValidationError, validate


def _work(node_id: str, role: str, **kw) -> PlanNode:
    return PlanNode(
        node_id=node_id,
        kind="work",
        title=role,
        role=role,
        spec_anchor=f"S#{node_id}",
        acceptance=kw.get("acceptance", ["ac"]),
        validation=kw.get("validation", ["v"]),
        touch_scope=kw.get("touch_scope", []),
    )


def test_clean_graph_ok():
    g = PlanGraph(
        nodes={"a": _work("a", "a"), "b": _work("b", "b")},
        edges=[PlanEdge(src="a", dst="b")],
    )
    assert validate(g).ok


def test_detect_cycle():
    g = PlanGraph(
        nodes={"a": _work("a", "a"), "b": _work("b", "b")},
        edges=[PlanEdge("a", "b"), PlanEdge("b", "a")],
    )
    report = validate(g)
    assert not report.ok
    assert any("cycle" in e for e in report.errors)
    with pytest.raises(ValidationError):
        report.raise_if_errors()


def test_dangling_edge():
    g = PlanGraph(nodes={"a": _work("a", "a")}, edges=[PlanEdge("ghost", "a")])
    report = validate(g)
    assert any("not found" in e for e in report.errors)


def test_missing_required_fields():
    g = PlanGraph(nodes={"a": _work("a", "a", acceptance=[], validation=[])})
    report = validate(g)
    assert any("acceptance" in e for e in report.errors)
    assert any("validation" in e for e in report.errors)


def test_granularity_is_warning_not_error():
    g = PlanGraph(
        nodes={"a": _work("a", "a", touch_scope=[f"f{i}.py" for i in range(7)])}
    )
    report = validate(g)
    assert report.ok
    assert any("splitting" in w for w in report.warnings)


def test_decision_needs_two_options():
    decision = PlanNode(
        node_id="d", kind="decision", title="d", role="d",
        spec_anchor="S#d", options=["only-one"],
    )
    report = validate(PlanGraph(nodes={"d": decision}))
    assert any("options" in e for e in report.errors)
