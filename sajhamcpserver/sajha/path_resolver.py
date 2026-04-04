"""
Unified path resolver for RiskGPT.
All tools and agent_server.py import this to resolve storage paths.

On local filesystem: returns absolute filesystem paths.
On S3: returns s3://bucket/prefix strings (future — not activated locally).

Usage:
    from sajha.path_resolver import resolve
    data_root = resolve('domain_data', worker_ctx)
    my_files  = resolve('my_data', worker_ctx, user_id='risk_agent')
"""
import os


_STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')
_AWS_BUCKET = os.environ.get('AWS_BUCKET', '')


def resolve(category: str, worker_ctx: dict, user_id: str = None) -> str:
    """
    Returns the root path/prefix for the given category and worker context.

    Categories:
      'domain_data'    -> worker-scoped analytical data root
      'my_data'        -> user-scoped working files root (requires user_id)
      'common_data'    -> platform-wide shared reference data root
      'workflows'      -> worker-scoped verified workflows root
      'my_workflows'   -> worker-scoped user-created workflows root
      'templates'      -> worker-scoped templates root

    worker_ctx is the worker dict from workers.json.
    Raises ValueError for unknown categories or missing user_id for my_data.
    """
    if _STORAGE_BACKEND == 's3' and _AWS_BUCKET:
        return _resolve_s3(category, worker_ctx, user_id)
    return _resolve_local(category, worker_ctx, user_id)


def _resolve_local(category: str, worker_ctx: dict, user_id: str = None) -> str:
    """Resolve to local filesystem path."""
    if category == 'domain_data':
        return worker_ctx.get('domain_data_path', './data/domain_data')

    elif category == 'my_data':
        if not user_id:
            raise ValueError("resolve('my_data', ...) requires user_id")
        base = worker_ctx.get('my_data_path', './data/uploads')
        return os.path.join(base, user_id)

    elif category == 'common_data':
        return worker_ctx.get('common_data_path', './data/common')

    elif category == 'workflows':
        # Worker-scoped verified workflows
        p = worker_ctx.get('workflows_path', '')
        if p:
            return p
        # Derive from domain_data parent: worker_root/workflows/verified
        domain = worker_ctx.get('domain_data_path', '')
        if domain:
            import pathlib
            worker_root = str(pathlib.Path(domain).parent)
            return os.path.join(worker_root, 'workflows', 'verified')
        return './data/workflows/verified'

    elif category == 'my_workflows':
        p = worker_ctx.get('my_workflows_path', '')
        if p:
            return p
        domain = worker_ctx.get('domain_data_path', '')
        if domain:
            import pathlib
            worker_root = str(pathlib.Path(domain).parent)
            return os.path.join(worker_root, 'workflows', 'my')
        return './data/workflows/my'

    elif category == 'templates':
        p = worker_ctx.get('templates_path', '')
        if p:
            return p
        domain = worker_ctx.get('domain_data_path', './data/domain_data')
        return os.path.join(domain, 'templates')

    else:
        raise ValueError(f"Unknown path category: '{category}'. "
                         f"Valid: domain_data, my_data, common_data, workflows, my_workflows, templates")


def _resolve_s3(category: str, worker_ctx: dict, user_id: str = None) -> str:
    """Resolve to S3 prefix. Future use — not activated locally."""
    local_path = _resolve_local(category, worker_ctx, user_id)
    # Strip leading ./ or / and prefix with s3://bucket/
    rel = local_path.lstrip('./').lstrip('/')
    return f"s3://{_AWS_BUCKET}/{rel}"
