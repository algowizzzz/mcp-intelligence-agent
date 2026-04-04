import os, json
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.storage import storage
from sajha.path_resolver import resolve as path_resolve


def _get_worker_ctx():
    try:
        from flask import g as _g
        return getattr(_g, 'worker_ctx', {}) or {}
    except RuntimeError:
        return {}


def _workflows_dir():
    """Return workflows dir. Checks per-request worker context first (G-04), then properties file."""
    try:
        from flask import g as _g
        worker_root = getattr(_g, 'worker_data_root', None)
        if worker_root:
            # worker_data_root = domain_data path; workflows live one level up at worker root
            worker_base = os.path.dirname(worker_root.rstrip('/'))
            return worker_base + '/workflows'
    except RuntimeError:
        pass
    props_path = os.path.join(os.path.dirname(__file__), "../../..", "config", "application.properties")
    try:
        with open(os.path.abspath(props_path)) as f:
            for line in f:
                if line.strip().startswith("data.workflows_dir"):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return "./data/workflows"


def _workflows_base():
    """Return the base workflows directory (parent of verified/ and my/)."""
    return _workflows_dir()


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
        base = _workflows_base()
        roots = {
            "verified": os.path.join(base, "verified"),
            "my": os.path.join(base, "my"),
        }
        workflows = []
        for source, root in roots.items():
            if not os.path.exists(root):
                continue
            for dirpath, _, files in os.walk(root):
                for fname in sorted(files):
                    if not fname.endswith(".md") or fname.startswith("."):
                        continue
                    full_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(full_path, base).replace("\\", "/")
                    try:
                        content = storage.read_text(full_path)
                        name, description, inputs = _parse_workflow_meta(fname, content)
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
        base = _workflows_base()
        # Normalise
        filename = filename.lstrip("/").lstrip("./")
        if not filename.endswith(".md"):
            filename += ".md"
        # Safety: resolve and confirm inside base
        full_path = os.path.realpath(os.path.join(base, filename))
        if not full_path.startswith(os.path.realpath(base)):
            return {"error": "Access denied"}
        if not os.path.exists(full_path):
            # Fallback: try searching verified/ and my/ by basename
            basename = os.path.basename(filename)
            for sub in ["verified", "my"]:
                candidate = os.path.join(base, sub, basename)
                if os.path.exists(candidate):
                    full_path = candidate
                    filename = os.path.join(sub, basename).replace("\\", "/")
                    break
            else:
                return {"error": f"Workflow not found: {filename}"}
        content = storage.read_text(full_path)
        fname = os.path.basename(full_path)
        name, description, inputs = _parse_workflow_meta(fname, content)
        return {
            "filename": filename,
            "name": name,
            "description": description,
            "inputs": inputs,
            "content": content,
        }
