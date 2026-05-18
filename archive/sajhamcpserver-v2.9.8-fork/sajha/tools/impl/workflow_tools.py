import os, json, logging
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.storage import storage

_logger = logging.getLogger(__name__)


def _workflow_paths() -> tuple:
    """Return (verified_dir, my_dir) for the current worker request.

    Resolution order (per path):
      1. Dedicated headers X-Worker-Verified-Workflows / X-Worker-My-Workflows
         (set by agent/tools.py from worker record's workflows_path field)
      2. Derive from X-Worker-Data-Root: parent(domain_data) + /workflows/{verified|my}
      3. PropertiesConfigurator fallback (outside Flask context)
      4. Hardcoded default ./data/workflows/{verified|my}
    """
    try:
        from flask import g as _g

        verified = getattr(_g, 'worker_verified_workflows', '') or ''
        my       = getattr(_g, 'worker_my_workflows',       '') or ''

        if verified and my:
            return verified.rstrip('/'), my.rstrip('/')

        # Fallback: derive from domain_data path (same worker directory structure)
        domain_root = getattr(_g, 'worker_data_root', '') or ''
        if domain_root:
            wf_base = os.path.dirname(domain_root.rstrip('/')) + '/workflows'
            return wf_base + '/verified', wf_base + '/my'

        _logger.warning(
            "workflow_tools: X-Worker-Verified-Workflows and X-Worker-Data-Root headers "
            "both missing — falling back to properties/default paths"
        )

    except RuntimeError:
        pass  # outside Flask context

    # Outside Flask context or no headers: use PropertiesConfigurator
    try:
        from sajha.core.properties_configurator import PropertiesConfigurator
        _props = PropertiesConfigurator()
        wf_dir = _props.get('data.workflows_dir', './data/workflows')
        return wf_dir.rstrip('/') + '/verified', wf_dir.rstrip('/') + '/my'
    except Exception:
        pass

    return './data/workflows/verified', './data/workflows/my'


def _metadata():
    """Load .metadata.json sidecar from the verified workflows dir if present."""
    verified_dir, _ = _workflow_paths()
    meta_path = verified_dir.rstrip('/') + '/.metadata.json'
    try:
        return json.loads(storage.read_text(meta_path))
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
        verified_dir, my_dir = _workflow_paths()
        roots = {
            "verified": verified_dir,
            "my":       my_dir,
        }
        workflows = []
        for source, root in roots.items():
            for rel_key in storage.list_prefix(root):
                fname = os.path.basename(rel_key)
                if not fname.endswith(".md") or fname.startswith("."):
                    continue
                full_path = root.rstrip('/') + '/' + rel_key
                rel_path  = source + '/' + rel_key.replace("\\", "/")
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
        verified_dir, my_dir = _workflow_paths()
        # Normalise input
        filename = filename.lstrip("/").lstrip("./")
        if not filename.endswith(".md"):
            filename += ".md"

        # Try verified/ then my/ in resolution order
        full_path = None
        for candidate_dir, source in ((verified_dir, "verified"), (my_dir, "my")):
            # Build candidate: handles bare name, "verified/name.md", or full path
            bare = os.path.basename(filename)
            candidates = [
                candidate_dir.rstrip('/') + '/' + filename,
                candidate_dir.rstrip('/') + '/' + bare,
            ]
            for cp in candidates:
                # Path-traversal guard: must stay within the candidate dir
                if not cp.startswith(candidate_dir.rstrip('/')):
                    continue
                if storage.exists(cp):
                    full_path = cp
                    filename  = source + '/' + bare
                    break
            if full_path:
                break

        if not full_path:
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
