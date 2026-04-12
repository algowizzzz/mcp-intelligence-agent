import os
import json
import mimetypes
from datetime import datetime, timezone


def _s3_mode() -> bool:
    return os.environ.get('STORAGE_BACKEND', 'local') == 's3'


def _build_tree_from_keys(keys: list) -> list:
    """Build nested folder/file tree from flat list of relative S3 key suffixes."""
    # Build a nested dict first
    tree_dict: dict = {}
    for rel in keys:
        rel = rel.replace('\\', '/')
        if not rel or rel.startswith('.'):
            continue
        parts = rel.split('/')
        node = tree_dict
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        # leaf = file
        node[parts[-1]] = None  # None marks a file

    def _to_entries(d: dict, parent_path: str) -> list:
        entries = []
        for name, value in sorted(d.items()):
            path = f"{parent_path}/{name}" if parent_path else name
            if value is None:
                # file
                mime, _ = mimetypes.guess_type(name)
                entries.append({
                    "type": "file",
                    "name": name,
                    "path": path,
                    "size_bytes": 0,
                    "modified_at": None,
                    "mime": mime or "application/octet-stream",
                })
            else:
                # folder
                entries.append({
                    "type": "folder",
                    "name": name,
                    "path": path,
                    "children": _to_entries(value, path),
                })
        return entries

    return _to_entries(tree_dict, "")


def build_tree(base, rel=""):
    """Local filesystem tree builder (unchanged)."""
    entries = []
    full = os.path.join(base, rel) if rel else base
    try:
        names = sorted(os.listdir(full))
    except Exception:
        return entries
    for name in names:
        if name.startswith("."):
            continue
        item_rel = os.path.join(rel, name) if rel else name
        item_full = os.path.join(base, item_rel)
        if os.path.isdir(item_full):
            entries.append({
                "type": "folder",
                "name": name,
                "path": item_rel.replace("\\", "/"),
                "children": build_tree(base, item_rel),
            })
        else:
            stat = os.stat(item_full)
            mime, _ = mimetypes.guess_type(item_full)
            entries.append({
                "type": "file",
                "name": name,
                "path": item_rel.replace("\\", "/"),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "mime": mime or "application/octet-stream",
            })
    return entries


def build_index(root_path: str) -> dict:
    """Build and persist .index.json for root_path. Returns the index dict."""
    if _s3_mode():
        from sajha.storage import storage
        keys = storage.list_prefix(root_path)
        tree = _build_tree_from_keys(keys)
        index = {
            "root": root_path,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "tree": tree,
        }
        index_key = root_path.rstrip('/') + '/.index.json'
        storage.write_text(index_key, json.dumps(index, indent=2))
        return index
    else:
        index = {
            "root": root_path,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "tree": build_tree(root_path),
        }
        index_path = os.path.join(root_path, ".index.json")
        os.makedirs(root_path, exist_ok=True)
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)
        return index


def get_index(root_path: str, max_age_seconds: int = 60) -> dict:
    """Return cached index if fresh, else rebuild."""
    if _s3_mode():
        from sajha.storage import storage
        index_key = root_path.rstrip('/') + '/.index.json'
        if storage.exists(index_key):
            try:
                raw = storage.read_text(index_key)
                index = json.loads(raw)
                built_at = index.get('built_at')
                if built_at:
                    age = (datetime.now(timezone.utc).timestamp() -
                           datetime.fromisoformat(built_at).timestamp())
                    if age < max_age_seconds:
                        return index
            except Exception:
                pass
        return build_index(root_path)
    else:
        index_path = os.path.join(root_path, ".index.json")
        if os.path.exists(index_path):
            try:
                mtime = os.path.getmtime(index_path)
                age = datetime.now(timezone.utc).timestamp() - mtime
                if age < max_age_seconds:
                    with open(index_path) as f:
                        return json.load(f)
            except Exception:
                pass
        return build_index(root_path)
