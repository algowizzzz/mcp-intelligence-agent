"""workflow_list — list available agent workflows."""
import os
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._workflow_common import workflow_paths, parse_workflow_meta


class WorkflowList(BaseMCPTool):
    """List all available MD workflows with name, description, and required inputs."""

    def get_input_schema(self) -> Dict:
        return {"type": "object", "properties": {}}

    def get_output_schema(self) -> Dict:
        return {"type": "object"}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ctx = arguments.get('_worker_context') or {}
        verified_dir, my_dir = workflow_paths(ctx)
        roots = {
            "verified": verified_dir,
            "my":       my_dir,
        }
        workflows = []
        for source, root in roots.items():
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _, files in os.walk(root):
                for fname in files:
                    if not fname.endswith(".md") or fname.startswith("."):
                        continue
                    full_path = os.path.join(dirpath, fname)
                    rel_key = os.path.relpath(full_path, root).replace("\\", "/")
                    rel_path = source + '/' + rel_key
                    try:
                        with open(full_path, 'r', encoding='utf-8') as fh:
                            content = fh.read()
                        name, description, inputs = parse_workflow_meta(fname, content)
                        workflows.append({
                            "filename": rel_path,
                            "name": name,
                            "description": description,
                            "inputs": inputs,
                            "source": source,
                        })
                    except Exception as e:
                        workflows.append({"filename": rel_path, "error": str(e)})
        return {"workflows": workflows, "count": len(workflows)}
