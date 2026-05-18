"""workflow_get — retrieve full markdown for a specific workflow."""
import os
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._workflow_common import workflow_paths, parse_workflow_meta


class WorkflowGet(BaseMCPTool):
    """Fetch the full markdown content of a specific workflow by filename."""

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Exact MD filename from workflow_list e.g. counterparty_intelligence.md",
                }
            },
            "required": ["filename"],
        }

    def get_output_schema(self) -> Dict:
        return {"type": "object"}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ctx = arguments.get('_worker_context') or {}
        filename = arguments.get("filename", "")
        verified_dir, my_dir = workflow_paths(ctx)

        filename = filename.lstrip("/").lstrip("./")
        if not filename.endswith(".md"):
            filename += ".md"

        full_path = None
        matched_source = None
        for candidate_dir, source in ((verified_dir, "verified"), (my_dir, "my")):
            if not candidate_dir:
                continue
            bare = os.path.basename(filename)
            candidates = [
                os.path.join(candidate_dir, filename),
                os.path.join(candidate_dir, bare),
            ]
            for cp in candidates:
                cp_norm = os.path.normpath(cp)
                # Path-traversal guard
                if not cp_norm.startswith(os.path.normpath(candidate_dir)):
                    continue
                if os.path.exists(cp_norm):
                    full_path = cp_norm
                    filename = source + '/' + bare
                    matched_source = source
                    break
            if full_path:
                break

        if not full_path:
            return {"error": f"Workflow not found: {filename}"}

        with open(full_path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        fname = os.path.basename(full_path)
        name, description, inputs = parse_workflow_meta(fname, content)
        return {
            "filename": filename,
            "name": name,
            "description": description,
            "inputs": inputs,
            "content": content,
        }
