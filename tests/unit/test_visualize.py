from pathlib import Path

from pre_symphony.build_graph import build_graph
from pre_symphony.parse_plan import parse_plan
from pre_symphony.plan_stages import annotate_stages
from pre_symphony.synth_issues import synth_issues
from pre_symphony.visualize import dry_run_summary, to_mermaid

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_plan.md"


def _annotated():
    return annotate_stages(build_graph(parse_plan(FIXTURE)))


def test_mermaid_has_nodes_and_edges():
    g = _annotated()
    mermaid = to_mermaid(g)
    assert mermaid.startswith("flowchart TD")
    assert "-->" in mermaid
    assert "decision" in mermaid  # decision classDef applied to storage-choice


def test_dry_run_summary_reports_counts_and_titles():
    g = _annotated()
    summary = dry_run_summary(g, synth_issues(g))
    assert "to push (frontier): 3" in summary
    assert "Implement PLAN parser" in summary
