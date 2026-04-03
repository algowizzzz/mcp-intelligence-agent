import os, json, mimetypes
from datetime import datetime, timezone


def build_tree(base, rel=""):
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
    """Build and write .index.json for root_path. Returns the index dict."""
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
    index_path = os.path.join(root_path, ".index.json")
    if os.path.exists(index_path):
        try:
            mtime = os.path.getmtime(index_path)
            age = (datetime.now(timezone.utc).timestamp()) - mtime
            if age < max_age_seconds:
                with open(index_path) as f:
                    return json.load(f)
        except Exception:
            pass
    return build_index(root_path)
