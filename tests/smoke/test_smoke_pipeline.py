"""Smoke tests: minimal end-to-end through the CLI, no network."""

from pathlib import Path

from pre_symphony.__main__ import main
from pre_symphony.state_store import load_issues

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_plan.md"


def test_smoke_plan_to_issues(tmp_path):
    out = tmp_path / "issues.json"
    graph_out = tmp_path / "plan_graph.json"
    main(["synth", "--plan", str(FIXTURE), "-o", str(out), "--graph-out", str(graph_out)])

    issues = load_issues(out)
    assert len(issues) == 3
    assert all("pre-symphony:node=" in i.description for i in issues)
    assert graph_out.exists()


def test_smoke_preview_is_local(capsys):
    main(["preview", "--plan", str(FIXTURE)])
    out = capsys.readouterr().out
    assert "flowchart TD" in out
    assert "to push (frontier): 3" in out


def test_smoke_push_confirm_gate_writes_nothing(tmp_path, capsys):
    state_dir = tmp_path / "state"
    main(["push", "--plan", str(FIXTURE), "--state-dir", str(state_dir)])
    out = capsys.readouterr().out
    assert "Re-run with --yes" in out
    # confirm gate: no Linear state written, no client constructed
    assert not (state_dir / "linear_map.json").exists()
