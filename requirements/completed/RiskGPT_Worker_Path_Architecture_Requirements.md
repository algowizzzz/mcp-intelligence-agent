# RiskGPT — Worker Path Architecture Requirements
**Status:** Pending
**Date:** 2026-04-03
**Author:** Saad Ahmed
**Scope:** Path architecture consolidation — three-category data model, workflow retirement, section key unification, domain_data migration to MR worker, my_data per-user scoping, common_data as shared platform layer

---

## 1. Background and Motivation

RiskGPT was originally built with a single-tenant data layout where all workers shared global directories under `sajhamcpserver/data/`. As the platform evolved to support multiple independent Digital Workers, per-worker path overrides were added to `workers.json`. However, the global paths were never retired, resulting in a split-brain state where:

- The **chat UI** (mcp-agent.html → agent_server.py) reads worker-scoped paths correctly via the `_resolve_worker_path()` function.
- The **admin panel** (admin.html → super admin file tree endpoints) uses a different resolver (`_admin_section_roots_for_worker()`) with a different section key schema.
- The **SAJHA tool layer** (`operational_tools.py`) still reads some global paths as hard fallbacks, bypassing worker context headers in certain code paths.
- The global `data/workflows/verified/` directory still holds 12 live workflow files that should have been fully migrated to the Market Risk worker path.

This document defines requirements for closing all identified gaps and establishing the target three-category data model. **No code changes are authorised until this document is reviewed and approved.**

---

## 2. Target Data Architecture

The platform will organise all data under three and only three categories. Each category has a distinct owner, scope, and access pattern.

```
sajhamcpserver/data/
  workers/
    {worker_id}/
      domain_data/        ← CATEGORY 1: worker-scoped analytical reference data
      my_data/
        {user_id}/        ← CATEGORY 2: user-scoped working files (per user within worker)
      workflows/
        verified/         ← worker-scoped verified workflows
        my/               ← worker-scoped user-created workflows
  common/                 ← CATEGORY 3: platform-wide shared read-only reference data
    regulatory/
```

| Category | Scope | Written by | Read by | Admin-editable? |
|---|---|---|---|---|
| `domain_data` | Per worker | Platform admin | Worker tools + agent | Yes, per worker |
| `my_data/{user_id}` | Per user within worker | Agent on behalf of user | User only | No (user-owned) |
| `common_data` | All workers | Platform team only | All workers | No (platform-managed) |

The old global directories (`data/domain_data/`, `data/uploads/`, `data/workflows/`) do not exist in the target architecture. All content must be migrated and those directories retired.

---

## 3. Current State Inventory

### 3.1 Filesystem — Workflows

| Path | File Count | Status |
|---|---|---|
| `data/workflows/verified/` | **12 files** | Legacy global — retire after migration |
| `data/workflows/my/` | 2 files | Legacy global — move to MR worker |
| `data/workers/w-market-risk/workflows/verified/` | **12 files** | Correct destination, already populated |
| `data/workers/w-market-risk/workflows/my/` | 0 files | Target destination for the 2 legacy files |
| `data/workers/w-e74b5836/workflows/verified/` | **0 files** | Intentionally empty (decided) |

### 3.2 Filesystem — Domain Data

| Path | Contents | Status |
|---|---|---|
| `data/domain_data/` | `osfi/`, `duckdb/`, `msdocs/`, `test_ccr/` | Legacy global — migrate to MR worker, then retire |
| `data/workers/w-market-risk/domain_data/` | `counterparties/`, `iris/`, `market_data/`, `analytics/` | Active — keep, merge legacy content in |
| `data/workers/w-e74b5836/domain_data/` | sparse | Active — TBD content |

### 3.3 Filesystem — My Data (Uploads)

| Path | Contents | Status |
|---|---|---|
| `data/uploads/` | `company_briefs/`, `charts/`, `exports/`, `reports/` | Legacy global — migrate to `w-market-risk/my_data/saad/`, then retire |
| `data/workers/w-market-risk/my_data/` | Empty | Target root — will contain `saad/` sub-directory |
| `data/workers/w-e74b5836/my_data/` | Empty | Active, empty |

### 3.4 Filesystem — Common Data

| Path | Contents | Status |
|---|---|---|
| `data/common/regulatory/` | OSFI, BCBS, Fed docs | Active — formal third category, read-only, shared across all workers |

### 3.5 Section Key Mismatch (Critical Bug)

`agent_server.py` defines three path resolver functions with **inconsistent section key schemas**:

| Resolver | Used By | Verified workflows key |
|---|---|---|
| `_resolve_worker_path(worker, section)` | Chat UI file endpoints, tool context injection | `'verified'` ❌ |
| `_admin_section_roots_for_worker(worker)` | Admin panel worker file tree | `'verified_workflows'` ✓ |
| `_resolve_admin_path(section, rel)` | Super admin global file tree | `'verified_workflows'` ✓ |

When the admin panel requests `/api/super/workers/{id}/files/verified_workflows`, the endpoint calls `_resolve_worker_path(w, 'verified_workflows')`, which does not have `'verified_workflows'` in its mapping. The fallback auto-creates an empty directory at an unintended path, causing the admin file tree to show 0 workflows while the chat UI correctly displays 12 (read from the legacy global fallback path).

---

## 4. Requirements

### REQ-WF-01 — Retire Global Verified Workflows Directory

**Priority:** High
**Affects:** `agent_server.py`, `data/workflows/verified/`
**Decision:** The 12 files in the global directory are already duplicated at `data/workers/w-market-risk/workflows/verified/`. The global directory is redundant and must be retired.

The global constant `_VERIFIED_WF` and any default fallback to `data/workflows/verified/` must be removed from `agent_server.py`. Retirement of the directory on disk must only proceed after REQ-WF-02 and REQ-WF-03 are deployed and verified end-to-end.

**Acceptance criteria:**
- No code path in `agent_server.py` references `data/workflows/verified/` as a default or fallback for any worker.
- The global constant `_VERIFIED_WF` is removed or marked deprecated-migration-only.
- MR worker continues to serve all 12 verified workflows from its worker-scoped path.
- Admin panel and chat UI both show 12 verified workflows for the MR worker before the global dir is deleted.

---

### REQ-WF-02 — Unify Section Key Schema in `_resolve_worker_path()`

**Priority:** High (blocks REQ-WF-01 and REQ-WF-03)
**Affects:** `agent_server.py` — `_resolve_worker_path()` function

The canonical section key for verified workflows across all resolvers and all API endpoints must be **`'verified_workflows'`**. The `_resolve_worker_path()` mapping must be updated to recognise this key, aliasing it to the same worker config field (`workflows_path`) as the existing `'verified'` key.

Both `'verified'` and `'verified_workflows'` must resolve correctly during the transition period. Once all callers are confirmed to use `'verified_workflows'`, the `'verified'` alias can be removed.

Additionally, `_resolve_worker_path()` must be hardened against unknown section keys: it must raise an explicit error rather than silently auto-creating directories.

**Acceptance criteria:**
- `_resolve_worker_path(worker, 'verified_workflows')` returns the correct worker-scoped path.
- `_resolve_worker_path(worker, 'verified')` continues to work during transition.
- Passing an unrecognised section key raises a `ValueError` (no silent directory creation).
- All new code uses `'verified_workflows'` exclusively.

---

### REQ-WF-03 — Fix Super Admin Worker File Tree Endpoint

**Priority:** High
**Affects:** `agent_server.py` — `GET /api/super/workers/{worker_id}/files/{section}` and all associated mutation endpoints

The super admin file tree endpoint currently calls `_resolve_worker_path()` for all sections. Once REQ-WF-02 is complete this will work for `verified_workflows`, but the broader issue is that super admin file endpoints should use `_admin_section_roots_for_worker()` consistently (the same resolver used by admin panel endpoints), not the user-facing resolver.

**Acceptance criteria:**
- Admin panel → MR worker file tree shows 12 verified workflow files.
- Admin panel → CCR worker file tree shows 0 verified workflow files.
- No phantom empty directories are auto-created when navigating the admin panel.
- All super admin file mutation endpoints (upload, move, delete, mkdir) use the same resolver as the GET endpoint.

---

### REQ-WF-04 — Migrate Global My-Workflows to MR Worker

**Priority:** Medium
**Affects:** `agent_server.py`, `data/workflows/my/`
**Decision:** Both files in `data/workflows/my/` are attributed to the Market Risk worker and must be moved to `data/workers/w-market-risk/workflows/my/`.

Once migrated and verified, the global `data/workflows/my/` directory must be removed from all code defaults and deleted from disk.

**Acceptance criteria:**
- Both files from `data/workflows/my/` are present in `data/workers/w-market-risk/workflows/my/`.
- No code path references `data/workflows/my/` as a default or fallback.
- The global constant `_MY_WF` is removed or marked deprecated-migration-only.

---

### REQ-WF-05 — CCR Worker Verified Workflows: Intentionally Empty

**Priority:** Low
**Affects:** `data/workers/w-e74b5836/workflows/verified/`, chat UI, admin panel
**Decision:** Option B — the CCR worker (`w-e74b5836`) has no verified workflows and this is intentional for now. No content will be authored for this worker at this time.

The system must handle an empty verified workflows directory gracefully rather than falling back to the MR worker or the legacy global path.

**Acceptance criteria:**
- Chat UI shows "No verified workflows available" (or equivalent) when the CCR worker context is active and the verified workflows directory is empty.
- Admin panel shows an empty file tree for the CCR worker's verified workflows — not an error, not a fallback to MR content.
- No cross-worker path sharing occurs.

---

### REQ-DD-01 — Migrate Global Domain Data to MR Worker and Retire Global Folder

**Priority:** Medium
**Affects:** `agent_server.py`, `operational_tools.py`, `data/domain_data/`
**Decision:** All contents of the global `data/domain_data/` directory are attributed to the Market Risk worker. They must be moved into `data/workers/w-market-risk/domain_data/` alongside the existing MR domain data (counterparties, iris, market_data, analytics). The global `data/domain_data/` directory must then be retired.

**Migration mapping:**

| Source (global) | Destination (MR worker) | Notes |
|---|---|---|
| `data/domain_data/osfi/` | `data/workers/w-market-risk/domain_data/osfi/` | OSFI regulatory docs — see note below |
| `data/domain_data/duckdb/` | `data/workers/w-market-risk/domain_data/duckdb/` | DuckDB files for MR queries |
| `data/domain_data/msdocs/` | `data/workers/w-market-risk/domain_data/msdocs/` | MS documentation |
| `data/domain_data/test_ccr/` | `data/workers/w-market-risk/domain_data/test_ccr/` | Test CCR data (not CCR worker — confirm attribution) |

> **Note on OSFI data:** OSFI regulatory docs are read by `osfi_tools.py` which is used across worker types. If the CCR worker also needs OSFI access in future, the OSFI sub-directory should be moved from MR's domain_data into `data/common/regulatory/` instead. This is flagged as a future decision — for now it moves with the rest of the global domain_data into MR's scoped path.

**Code change required:** `operational_tools.py`'s `_domain_root()` currently returns the global path unconditionally. It must be updated to check `getattr(_g, 'worker_data_root', None)` first, matching the pattern already used in `workflow_tools.py`.

**Acceptance criteria:**
- All sub-directories from `data/domain_data/` are present under `data/workers/w-market-risk/domain_data/`.
- `data/domain_data/` is empty and removed from all code defaults.
- `_domain_root()` in `operational_tools.py` is worker-context-aware.
- No tool reads from the global `data/domain_data/` path when a worker context is active.

---

### REQ-DD-02 — Migrate Global Uploads to User-Scoped My-Data and Retire Global Folder

**Priority:** Medium
**Affects:** `agent_server.py`, `operational_tools.py`, `data/uploads/`
**Decision:** All content in `data/uploads/` is attributed to user `saad` working within the MR worker. My-data is now scoped **per user** (not per worker). The migration destination is `data/workers/w-market-risk/my_data/saad/`.

**Migration mapping:**

| Source (global) | Destination (user-scoped) |
|---|---|
| `data/uploads/company_briefs/` | `data/workers/w-market-risk/my_data/saad/company_briefs/` |
| `data/uploads/charts/` | `data/workers/w-market-risk/my_data/saad/charts/` |
| `data/uploads/exports/` | `data/workers/w-market-risk/my_data/saad/exports/` |
| `data/uploads/reports/` | `data/workers/w-market-risk/my_data/saad/reports/` |

**Code change required:** `operational_tools.py`'s `_my_data_root()` currently returns the global `data/uploads/` path unconditionally. It must be updated to check `getattr(_g, 'worker_my_data_root', None)` and resolve to the `{user_id}/` sub-directory within that path.

**Acceptance criteria:**
- All content from `data/uploads/` is present under `data/workers/w-market-risk/my_data/saad/`.
- `data/uploads/` is empty and removed from all code defaults.
- `_my_data_root()` in `operational_tools.py` is worker-context-aware and user-scoped.
- The global constant `_MY_DATA` is removed or marked deprecated-migration-only.

---

### REQ-MD-01 — My-Data Is Per-User (Not Per-Worker)

**Priority:** Medium
**Affects:** `agent_server.py`, `workers.json`, `operational_tools.py`, admin panel UX
**Decision:** My-data is scoped at the **user level**, not the worker level. The path convention is `{worker_id}/my_data/{user_id}/`. Each user authenticated to a worker gets their own isolated sub-directory under that worker's `my_data/` root.

**Requirements:**

1. `my_data_path` in `workers.json` defines the root for that worker (`data/workers/{id}/my_data/`). The `user_id` sub-directory is appended at runtime, not stored in config.
2. `agent_server.py` must inject `X-Worker-My-Data-Root` as `{my_data_path}/{user_id}/` when calling SAJHA tools — not the bare worker root.
3. Tools must never write to the bare `my_data/` root; they must always write to the `{user_id}/` sub-directory.
4. The admin panel must not expose individual user my_data directories as editable file trees — my_data is user-owned.

**Acceptance criteria:**
- All runtime my_data reads and writes target `{my_data_path}/{user_id}/`.
- The `X-Worker-My-Data-Root` header passed to SAJHA tools includes the user_id sub-path.
- The admin panel has no upload/delete access to any `my_data/` path.

---

### REQ-CD-01 — Common Data as Formal Third Category

**Priority:** Medium
**Affects:** `workers.json`, `agent_server.py`, `data/common/`, admin panel
**Decision:** `common_data` is established as a formal, named third data category alongside `domain_data` and `my_data`. It is platform-managed, read-only at runtime, and shared identically across all workers.

All four workers already have `common_data_path: ./data/common` in `workers.json`. This configuration is correct and does not change.

**Requirements:**

1. Document `common_data_path` as the **third canonical data category** — not a worker-specific setting but a platform-wide pointer.
2. No worker may write to `data/common/` via any tool or API endpoint at runtime. Tools that read from common_data must use `worker_common_root` header in read-only mode.
3. The admin panel must not expose `common_data_path` as a per-worker editable file tree. It should either be absent from per-worker views or shown as read-only.
4. If a worker needs supplementary reference data that is not platform-wide, it must go in `domain_data_path`, not `common_data_path`.
5. Future additions to `data/common/` (e.g., new regulatory frameworks) are a platform admin operation, not a worker admin operation.

**Acceptance criteria:**
- No SAJHA tool writes to `data/common/` during agent task execution.
- Admin panel does not offer upload, delete, or move actions on the common data path for any worker.
- `data/common/regulatory/` remains the authoritative location for OSFI, BCBS, Fed, and other platform-level regulatory reference data.

---

### REQ-API-01 — Audit All File Endpoints for Worker Scope Consistency

**Priority:** High
**Affects:** `agent_server.py` — all `/api/files/`, `/api/admin/`, `/api/super/` file endpoints

All file-serving and file-mutation endpoints must use the correct resolver for their caller tier. The following table reflects confirmed and unconfirmed resolver assignments:

| Endpoint Pattern | Resolver Currently Used | Expected Resolver | Status |
|---|---|---|---|
| `GET /api/files/{section}` (user) | `_resolve_worker_path()` | `_resolve_worker_path()` | ✓ confirmed |
| `POST /api/files/{section}/upload` | `_resolve_worker_path()` | `_resolve_worker_path()` | ✓ confirmed |
| `POST /api/files/{section}/move` | `_resolve_worker_path()` | `_resolve_worker_path()` | ✓ confirmed |
| `DELETE /api/files/{section}/file` | `_resolve_worker_path()` | `_resolve_worker_path()` | ✓ confirmed |
| `GET /api/admin/files/{section}` | `_admin_section_roots_for_worker()` | `_admin_section_roots_for_worker()` | ✓ confirmed |
| `POST /api/admin/files/{section}/upload` | `_admin_section_roots_for_worker()` | `_admin_section_roots_for_worker()` | ✓ confirmed |
| `GET /api/super/workers/{id}/files/{section}` | `_resolve_worker_path()` | `_admin_section_roots_for_worker()` | ❌ broken |
| `POST /api/super/workers/{id}/files/{section}/upload` | TBD | `_admin_section_roots_for_worker()` | ⚠ must audit |
| `DELETE /api/super/workers/{id}/files/{section}/file` | TBD | `_admin_section_roots_for_worker()` | ⚠ must audit |
| `POST /api/super/workers/{id}/files/{section}/move` | TBD | `_admin_section_roots_for_worker()` | ⚠ must audit |
| `POST /api/super/workers/{id}/files/{section}/mkdir` | TBD | `_admin_section_roots_for_worker()` | ⚠ must audit |

In addition, once REQ-DD-01 and REQ-DD-02 are implemented, all three data categories (`domain_data`, `my_data`, `common_data`) must be represented as valid section keys in both resolver functions, with `common_data` sections enforced as read-only at the API layer.

**Acceptance criteria:**
- All super admin file endpoints use `_admin_section_roots_for_worker()`.
- All section keys are consistent across user, admin, and super admin tiers.
- No endpoint allows write operations against `common_data`.
- No endpoint silently falls back to a global path when a worker-scoped path is expected.

---

### REQ-API-02 — Audit Tool Context Headers for All Worker-Aware Tools

**Priority:** Medium
**Affects:** `agent_server.py` tool call dispatch, `sajhamcpserver/sajha/tools/impl/`

The agent server injects worker context via HTTP headers when calling SAJHA tools. All tools that read or write data must respect these headers and must not fall back to global paths when a worker context is active.

| Tool Module | Functions to Audit | Risk | Header to check |
|---|---|---|---|
| `workflow_tools.py` | `_workflows_dir()` | Low — already compliant | `X-Worker-Data-Root` |
| `operational_tools.py` | `_domain_root()`, `_my_data_root()`, `_templates_dir()` | **High** — returns global paths unconditionally | `X-Worker-Data-Root`, `X-Worker-My-Data-Root` |
| `iris_ccr_tools.py` | data path resolution | Medium | `X-Worker-Data-Root` |
| `osfi_tools.py` | data path resolution | Medium — OSFI moving to MR domain_data (see REQ-DD-01) | `X-Worker-Data-Root` or `X-Worker-Common-Root` |
| Any tool writing outputs | write path resolution | High — must write to `{user_id}/` sub-path | `X-Worker-My-Data-Root` |

**Acceptance criteria:**
- All tools that read domain data check `worker_data_root` before any fallback.
- All tools that read/write my_data check `worker_my_data_root` (with user_id sub-path) before any fallback.
- All tools that read regulatory/common data use `worker_common_root`.
- No tool writes to a global path when a worker context is active.

---

## 5. Summary Table

| REQ ID | Description | Priority | Type | Decision |
|---|---|---|---|---|
| REQ-WF-01 | Retire global `data/workflows/verified/` | High | Migration + Code | Files already in MR worker — retire global |
| REQ-WF-02 | Unify section key to `'verified_workflows'` in all resolvers | High | Code | Canonical key = `verified_workflows` |
| REQ-WF-03 | Fix super admin file tree endpoint resolver | High | Code | Use `_admin_section_roots_for_worker()` |
| REQ-WF-04 | Migrate 2 global my-workflows to MR worker | Medium | Migration + Code | Move to `w-market-risk/workflows/my/` |
| REQ-WF-05 | CCR worker verified workflows | Low | Documentation | Intentionally empty for now |
| REQ-DD-01 | Migrate global `data/domain_data/` to MR worker | Medium | Migration + Code | All content moves to MR `domain_data/` |
| REQ-DD-02 | Migrate `data/uploads/` to user-scoped my_data | Medium | Migration + Code | Move to `w-market-risk/my_data/saad/` |
| REQ-MD-01 | my_data is per-user, not per-worker | Medium | Code + Config | Path = `{worker}/my_data/{user_id}/` |
| REQ-CD-01 | common_data as formal third category | Medium | Code + Documentation | Read-only, platform-managed, all workers |
| REQ-API-01 | Audit all file endpoints for resolver consistency | High | Audit + Code | 5 super admin endpoints unaudited |
| REQ-API-02 | Audit all SAJHA tools for worker context header compliance | Medium | Audit + Code | `operational_tools.py` known non-compliant |

---

## 6. Implementation Sequence

1. **REQ-WF-02** — Section key unification. No data movement. Unblocks everything else.
2. **REQ-WF-03 + REQ-API-01** — Fix super admin endpoint; complete full endpoint audit. Run concurrently with REQ-WF-02.
3. **REQ-WF-01 + REQ-WF-04** — Retire global workflow directories. Depends on REQ-WF-02/03 being verified in production.
4. **REQ-API-02** — Tool context header audit. Prerequisite for data migration steps.
5. **REQ-DD-01 + REQ-DD-02 + REQ-MD-01** — Domain data migration, uploads migration, and per-user my_data path injection. Run concurrently once REQ-API-02 is done.
6. **REQ-CD-01** — Formalise common_data category in code and documentation. Can run at any point.
7. **REQ-WF-05** — No action required; verify graceful empty-state handling during REQ-WF-03 testing.

---

## 7. Out of Scope

- Changes to `workers.json` path configuration values (already correct)
- Changes to the SAJHA MCP server Flask routing layer
- New tool development
- Authentication, JWT, or role management changes
- Per-user access control beyond the `my_data/{user_id}/` path convention

---

*This document covers diagnosis and requirements only. No code changes are to be made until this document is reviewed and individual REQ items are approved for implementation.*
