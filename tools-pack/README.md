# tools-pack

This directory contains B-Pulse's custom MCP tools — the ones formerly bundled
inside our fork of SAJHA. It's loaded by **upstream** SAJHA (pinned as a
submodule at `../sajhamcpserver-upstream/`) at startup via the
`SAJHA_CONFIG_TOOLS_DIR` env var, with `PYTHONPATH` extended to include this
directory so implementation modules resolve as `tools_pack_impl.*`.

## Layout

```
tools-pack/
  configs/           Tool JSON configs (one per tool — upstream scans these)
  impl/              Python implementation modules — exposed as `tools_pack_impl`
  lib/               Shared helpers (worker context, path resolver) used by impl
  tests/             Per-tool smoke tests
```

## How upstream loads us

```bash
cd sajhamcpserver-upstream
export SAJHA_CONFIG_TOOLS_DIR=$(pwd)/../tools-pack/configs
export PYTHONPATH=$(pwd)/../tools-pack
python run_server.py
```

Upstream's `tools_registry` scans `configs/*.json`, reads each
`implementation` field (e.g. `tools_pack_impl.bm25.BM25SearchTool`), imports
the class, and registers it. Upstream's working tree is never modified.

## Worker context

Each tool reads worker scope (worker_id, user_id, data paths) from HTTP
request headers via `tools_pack.lib.worker_ctx.get_worker_ctx(request)`. This
mirrors the headers our agent (`agent/tools.py:_service_headers`) already
sends to SAJHA.

## Adding a new tool

1. Create `configs/<name>.json` with `name`, `description`, `inputSchema`, and
   `implementation: "tools_pack_impl.<module>.<Class>"`.
2. Create `impl/<module>.py` with a class extending
   `sajha.tools.base_mcp_tool.BaseMCPTool` (provides `execute_with_tracking`).
3. Add a smoke test under `tests/test_<name>.py`.

See `REQ-17_*` docs in `requirements/pending/` for full migration context.
