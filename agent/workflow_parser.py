"""workflow_parser.py — YAML frontmatter parser for multi-agent workflow .md files (REQ-13).

Workflow markdown files may include a YAML frontmatter block between ``---``
delimiters that describes a multi-agent orchestration plan.  This module
extracts and validates that frontmatter and provides utilities for building
execution groups and resolving inter-agent dependencies.

Expected frontmatter schema
---------------------------
---
agent_mode: multi
agents:
  - id: risk_summary
    description: Summarise market risk exposure
    task: Pull VaR and sensitivity data for all desks
    order: 1
  - id: reg_check
    description: Check regulatory limits
    task: Compare {risk_summary.result_summary} against FRTB thresholds
    order: 2
---

agent_mode must be 'multi' for parse_workflow_frontmatter() to return a dict
(returns None for single-agent or absent frontmatter so callers can gate
multi-agent logic cleanly).

Agents with the same ``order`` value are scheduled in parallel; lower order
values run first.  The ``order`` field defaults to 1 if omitted.
"""

from __future__ import annotations

import re
from typing import Optional

try:
    import yaml
except ImportError as _yaml_import_err:  # pragma: no cover
    raise ImportError(
        "PyYAML is required for workflow_parser.  "
        "Install it with: pip install pyyaml"
    ) from _yaml_import_err

# ── Constants ──────────────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)

_REQUIRED_TOP_LEVEL = {"agent_mode", "agents"}
_REQUIRED_AGENT_FIELDS = {"id", "description", "task"}

# Maximum number of characters to return when resolving a dependency placeholder.
_DEPENDENCY_SUMMARY_CHARS = 500


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_workflow_frontmatter(content: str) -> Optional[dict]:
    """Extract and validate YAML frontmatter from a workflow markdown file.

    Parameters
    ----------
    content : str
        Full text of the workflow markdown file.

    Returns
    -------
    dict
        Parsed and validated frontmatter with at minimum keys:
        ``agent_mode``, ``agents`` (list of agent dicts).
    None
        If no ``---`` frontmatter block is found, if the YAML is malformed,
        if ``agent_mode`` is not ``'multi'``, or if required fields are missing.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None

    raw_yaml = match.group(1)
    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError:
        return None

    if not isinstance(data, dict):
        return None

    # Must declare agent_mode: multi
    if data.get("agent_mode") != "multi":
        return None

    # Must have top-level required keys
    missing_top = _REQUIRED_TOP_LEVEL - set(data.keys())
    if missing_top:
        return None

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        return None

    # Validate every agent entry
    for agent in agents:
        if not isinstance(agent, dict):
            return None
        missing_agent = _REQUIRED_AGENT_FIELDS - set(agent.keys())
        if missing_agent:
            return None
        # Coerce id and description to str in case YAML parsed them as other types
        agent["id"] = str(agent["id"])
        agent["description"] = str(agent["description"])
        agent["task"] = str(agent["task"])
        # Default order to 1 if not supplied
        if "order" not in agent:
            agent["order"] = 1
        else:
            try:
                agent["order"] = int(agent["order"])
            except (TypeError, ValueError):
                agent["order"] = 1

    return data


def get_execution_groups(agents: list[dict]) -> list[list[dict]]:
    """Group agents by their ``order`` field for parallel scheduling.

    Agents with the same order value form a parallel group.  Groups are
    returned in ascending order so callers can iterate and await each group
    before starting the next.

    Parameters
    ----------
    agents : list[dict]
        Agent definitions from parse_workflow_frontmatter()["agents"].
        Each dict must have an ``order`` key (int).

    Returns
    -------
    list[list[dict]]
        Outer list is ordered by ascending ``order`` value.
        Each inner list contains agents that should run in parallel.

    Examples
    --------
    >>> agents = [
    ...     {"id": "a", "order": 1},
    ...     {"id": "b", "order": 1},
    ...     {"id": "c", "order": 2},
    ... ]
    >>> get_execution_groups(agents)
    [[{"id": "a", "order": 1}, {"id": "b", "order": 1}], [{"id": "c", "order": 2}]]
    """
    if not agents:
        return []

    # Collect all unique order values, sorted ascending.
    order_values = sorted({a.get("order", 1) for a in agents})

    groups: list[list[dict]] = []
    for order in order_values:
        group = [a for a in agents if a.get("order", 1) == order]
        if group:
            groups.append(group)

    return groups


def resolve_dependencies(agent_def: dict, completed_results: dict[str, str]) -> str:
    """Replace ``{id.result_summary}`` placeholders with completed result excerpts.

    Scans the ``task`` field of an agent definition and substitutes every
    ``{<agent_id>.result_summary}`` placeholder with the first
    ``_DEPENDENCY_SUMMARY_CHARS`` characters of the referenced agent's result.

    Parameters
    ----------
    agent_def : dict
        Single agent definition dict.  The ``task`` key is read and its
        resolved version is returned.
    completed_results : dict[str, str]
        Mapping of agent_id → full result string for already-completed agents.

    Returns
    -------
    str
        The ``task`` string with all resolvable placeholders substituted.
        Unresolvable placeholders (referencing agents that haven't completed
        yet or don't exist) are left as-is so the caller can detect them.
    """
    task_text: str = agent_def.get("task", "")
    if not task_text:
        return task_text

    # Find all {<id>.result_summary} patterns.
    placeholder_re = re.compile(r"\{([^}]+)\.result_summary\}")

    def _replacer(match: re.Match) -> str:
        ref_id = match.group(1).strip()
        result = completed_results.get(ref_id)
        if result is None:
            # Leave placeholder intact — caller can detect missing dependency.
            return match.group(0)
        summary = result[:_DEPENDENCY_SUMMARY_CHARS]
        if len(result) > _DEPENDENCY_SUMMARY_CHARS:
            summary += "..."
        return summary

    return placeholder_re.sub(_replacer, task_text)
