"""Shared helpers for workflow tools — upstream-compliant.

Resolves the verified + my workflow directories from worker context headers
(no Flask `g`, no properties configurator).
"""
import os
from typing import Dict, Tuple


def workflow_paths(ctx: Dict[str, str]) -> Tuple[str, str]:
    """Return (verified_dir, my_dir).

    Resolution order:
      1. Explicit ctx keys workflows_path / my_workflows_path (verified).
      2. Derive from domain_data_path: parent(domain_data) + /workflows/{verified|my}.
      3. Fallback empty strings — tools should handle this gracefully.
    """
    verified = (ctx.get('workflows_path') or '').strip().rstrip('/')
    my       = (ctx.get('my_workflows_path') or '').strip().rstrip('/')

    if verified and my:
        return verified, my

    # Derive from domain_data_path
    dd = (ctx.get('domain_data_path') or '').strip().rstrip('/')
    if dd:
        wf_base = os.path.dirname(dd) + '/workflows'
        return wf_base + '/verified', wf_base + '/my'

    return verified, my


def parse_workflow_meta(filename: str, content: str):
    """Extract display name, description, and inputs from MD content."""
    lines = content.splitlines()
    name = filename.replace(".md", "").replace("_", " ").title()
    description = ""
    inputs = ""
    in_inputs = False
    first_h1 = True
    for line in lines:
        stripped = line.strip()
        if not description and stripped and not stripped.startswith("#"):
            description = stripped[:120]
        if stripped.startswith("# ") and first_h1:
            name = stripped[2:].strip()
            first_h1 = False
        if stripped.lower() == "## inputs:":
            in_inputs = True
            continue
        if in_inputs:
            if stripped.startswith("##"):
                break
            if stripped.startswith("-"):
                inputs += stripped[1:].strip() + "; "
    return name, description, inputs.rstrip("; ")
