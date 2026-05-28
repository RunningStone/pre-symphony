"""Parse a PLAN markdown file into a ParsedPlan (FR1).

PLAN input contract
-------------------
- Optional YAML front-matter at the top (between ``---`` lines): global metadata
  such as ``spec``, ``project``, ``default_labels``.
- Each node is a level-2 heading of the form::

      ## [<kind>] <title> @<role>

  where ``<kind>`` is ``work`` / ``decision`` / ``milestone_marker`` and
  ``<role>`` is a short, human-writable, unique handle. Dependencies reference
  other nodes by ``role`` (never by id — ids are auto-hashed).
- The heading is immediately followed by a fenced ``yaml`` block holding the
  node's metadata: ``milestone``, ``spec_anchor``, ``priority``, ``depends_on``,
  ``labels``, ``touch``, ``body``, ``acceptance``, ``validation``, ``options``.

Parsing is intentionally lenient about *missing* fields (e.g. acceptance):
those are kept empty and flagged later by ``validate`` — parsing only fails on
structurally broken input.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import ParsedNode, ParsedPlan

_FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_HEADING_RE = re.compile(
    r"^##\s+\[(?P<kind>[\w-]+)\]\s+(?P<title>.+?)\s+@(?P<role>[\w./-]+)\s*$"
)
_YAML_FENCE_RE = re.compile(r"^```ya?ml\s*$")
_FENCE_END_RE = re.compile(r"^```\s*$")


class ParseError(Exception):
    """Structurally broken PLAN input."""


def parse_plan(md_path: Path | str) -> ParsedPlan:
    text = Path(md_path).read_text(encoding="utf-8")
    meta, body = _split_front_matter(text)
    return ParsedPlan(meta=meta, nodes=_parse_nodes(body))


def _split_front_matter(text: str) -> tuple[dict, str]:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ParseError(f"invalid front-matter YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise ParseError("front-matter must be a YAML mapping")
    return meta, text[match.end() :]


def _parse_nodes(body: str) -> list[ParsedNode]:
    lines = body.splitlines()
    nodes: list[ParsedNode] = []
    i, n = 0, len(lines)
    while i < n:
        heading = _HEADING_RE.match(lines[i])
        if not heading:
            i += 1
            continue
        role = heading.group("role")
        j = i + 1
        while j < n and lines[j].strip() == "":
            j += 1
        if j >= n or not _YAML_FENCE_RE.match(lines[j]):
            raise ParseError(
                f"node '@{role}' (line {i + 1}) must be followed by a ```yaml metadata block"
            )
        k, buf = j + 1, []
        while k < n and not _FENCE_END_RE.match(lines[k]):
            buf.append(lines[k])
            k += 1
        if k >= n:
            raise ParseError(f"unterminated yaml block for node '@{role}'")
        try:
            data = yaml.safe_load("\n".join(buf)) or {}
        except yaml.YAMLError as exc:
            raise ParseError(f"invalid YAML for node '@{role}': {exc}") from exc
        if not isinstance(data, dict):
            raise ParseError(f"metadata for node '@{role}' must be a YAML mapping")
        nodes.append(
            _build_parsed_node(heading.group("kind"), heading.group("title").strip(), role, data)
        )
        i = k + 1
    return nodes


def _as_str_tuple(value) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    raise ParseError(f"expected a list or string, got {type(value).__name__}")


def _build_parsed_node(kind: str, title: str, role: str, data: dict) -> ParsedNode:
    priority = data.get("priority")
    if priority is not None and not isinstance(priority, int):
        try:
            priority = int(priority)
        except (TypeError, ValueError) as exc:
            raise ParseError(f"priority for '@{role}' must be an integer") from exc
    milestone = data.get("milestone")
    return ParsedNode(
        kind=kind,
        title=title,
        role=role,
        spec_anchor=str(data.get("spec_anchor", "")).strip(),
        milestone=str(milestone) if milestone is not None else None,
        priority=priority,
        depends_on=_as_str_tuple(data.get("depends_on")),
        labels=_as_str_tuple(data.get("labels")),
        touch=_as_str_tuple(data.get("touch")),
        body=str(data.get("body", "")).strip(),
        acceptance=_as_str_tuple(data.get("acceptance")),
        validation=_as_str_tuple(data.get("validation")),
        options=_as_str_tuple(data.get("options")),
    )
