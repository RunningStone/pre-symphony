from pathlib import Path

import pytest

from pre_symphony.parse_plan import ParseError, parse_plan

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_plan.md"


def test_parse_minimal():
    plan = parse_plan(FIXTURE)
    assert plan.meta["project"] == "pre-symphony-dev"
    assert plan.meta["default_labels"] == ["symphony"]
    assert [n.role for n in plan.nodes] == ["parser", "builder", "storage-choice"]

    parser = plan.nodes[0]
    assert parser.kind == "work"
    assert parser.title == "Implement PLAN parser"
    assert parser.spec_anchor == "SPEC#3.2"
    assert parser.priority == 2
    assert parser.acceptance and parser.validation

    assert plan.nodes[1].depends_on == ("parser",)

    decision = plan.nodes[2]
    assert decision.kind == "decision"
    assert decision.options == ("json-files", "sqlite")


def test_missing_yaml_block_raises(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("## [work] No meta @x\n\njust prose, no yaml\n", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_plan(bad)


def test_missing_acceptance_kept_not_raised(tmp_path):
    p = tmp_path / "p.md"
    p.write_text(
        "## [work] No AC @x\n```yaml\nspec_anchor: S#1\nbody: hi\n```\n",
        encoding="utf-8",
    )
    plan = parse_plan(p)
    # Parsing keeps it empty; validate is what flags missing acceptance.
    assert plan.nodes[0].acceptance == ()
    assert plan.nodes[0].validation == ()


def test_bad_front_matter_raises(tmp_path):
    p = tmp_path / "p.md"
    p.write_text("---\nfoo: [1, 2\n---\n", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_plan(p)


def test_no_front_matter_is_ok(tmp_path):
    p = tmp_path / "p.md"
    p.write_text(
        "# Title\n## [work] A @a\n```yaml\nspec_anchor: S#1\nacceptance: [x]\nvalidation: [y]\n```\n",
        encoding="utf-8",
    )
    plan = parse_plan(p)
    assert plan.meta == {}
    assert len(plan.nodes) == 1
