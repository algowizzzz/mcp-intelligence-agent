import os, json
from sajha.tools.base_mcp_tool import BaseMCPTool


def _workflows_dir():
    """Read workflows dir from application.properties, fallback to ./data/workflows."""
    props_path = os.path.join(os.path.dirname(__file__), "../../..", "config", "application.properties")
    try:
        with open(os.path.abspath(props_path)) as f:
            for line in f:
                if line.strip().startswith("data.workflows_dir"):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return "./data/workflows"


def _metadata():
    """Load .metadata.json sidecar if present."""
    d = _workflows_dir()
    meta_path = os.path.join(d, ".metadata.json")
    try:
        with open(meta_path) as f:
            return json.load(f)
    except Exception:
        return {}


def _parse_workflow_meta(filename, content):
    """Extract display name, description, and inputs from MD content."""
    lines = content.splitlines()
    name = filename.replace(".md", "").replace("_", " ").title()
    description = ""
    inputs = ""
    in_inputs = False
    for line in lines:
        stripped = line.strip()
        # First non-heading, non-empty line after title = description
        if not description and stripped and not stripped.startswith("#"):
            description = stripped[:120]
        # Title from first H1
        if stripped.startswith("# ") and name == filename.replace(".md", "").replace("_", " ").title():
            name = stripped[2:].strip()
        # Inputs section
        if stripped.lower() == "## inputs:":
            in_inputs = True
            continue
        if in_inputs:
            if stripped.startswith("##"):
                break
            if stripped.startswith("-"):
                inputs += stripped[1:].strip() + "; "
    return name, description, inputs.rstrip("; ")


class WorkflowListTool(BaseMCPTool):
    """List all available MD workflows with name, description, and input hints.
    Call this when the user asks what workflows are available, or when a query may
    be served by a known workflow. Returns names and descriptions only — use
    workflow_get to fetch full content before executing.
    """

    def __init__(self, config=None):
        default_config = {
            "name": "workflow_list",
            "description": (
                "List all available agent workflows with their names, descriptions, "
                "and required inputs. Call this to discover what workflows exist "
                "before deciding which one to use. Returns metadata only — use "
                "workflow_get to retrieve full workflow instructions."
            ),
            "version": "1.0.0",
            "enabled": True,
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self):
        return {"type": "object", "properties": {}}

    def get_output_schema(self):
        return {"type": "object"}

    def execute(self, arguments):
        d = _workflows_dir()
        meta = _metadata()
        workflows = []
        try:
            files = sorted(f for f in os.listdir(d) if f.endswith(".md") and not f.startswith("."))
        except Exception as e:
            return {"error": str(e), "workflows": []}
        for filename in files:
            try:
                with open(os.path.join(d, filename)) as f:
                    content = f.read()
                name, description, inputs = _parse_workflow_meta(filename, content)
                file_meta = meta.get(filename, {})
                last_used = file_meta.get("last_used") if isinstance(file_meta, dict) else file_meta
                workflows.append({
                    "filename": filename,
                    "name": name,
                    "description": description,
                    "inputs": inputs,
                    "last_used": last_used,
                })
            except Exception as e:
                workflows.append({"filename": filename, "error": str(e)})
        return {"workflows": workflows, "count": len(workflows)}


class WorkflowGetTool(BaseMCPTool):
    """Fetch the full markdown content of a specific workflow by filename.
    Call this after workflow_list to retrieve the complete step-by-step instructions
    for a chosen workflow. Read the returned content and follow the steps as written.
    """

    def __init__(self, config=None):
        default_config = {
            "name": "workflow_get",
            "description": (
                "Retrieve the full markdown instructions for a specific workflow. "
                "Pass the filename from workflow_list. Read the returned content "
                "and execute the steps in order as your instructions."
            ),
            "version": "1.0.0",
            "enabled": True,
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Exact MD filename from workflow_list e.g. counterparty_intelligence.md"
                }
            },
            "required": ["filename"]
        }

    def get_output_schema(self):
        return {"type": "object"}

    def execute(self, arguments):
        filename = arguments.get("filename", "")
        if not filename.endswith(".md"):
            filename += ".md"
        # Safety: no path traversal
        filename = os.path.basename(filename)
        filepath = os.path.join(_workflows_dir(), filename)
        if not os.path.exists(filepath):
            return {"error": f"Workflow not found: {filename}"}
        with open(filepath) as f:
            content = f.read()
        name, description, inputs = _parse_workflow_meta(filename, content)
        return {
            "filename": filename,
            "name": name,
            "description": description,
            "inputs": inputs,
            "content": content,
        }
