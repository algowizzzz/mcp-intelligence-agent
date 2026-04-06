# REQ-10 — Common Data Path (Shared Cross-Worker Data Layer)

**Status:** Pending Implementation
**Version:** 2.0 (2026-04-05)
**Scope:** Activate the `common_data_path` as a fully functional shared data layer visible to all workers, manageable by super_admin/admin, browsable (read-only) by users in the chat sidebar, and searchable by the `document_search` BM25 tool.

---

## 1. Background

### 1.1 Current State

The platform has a three-tier data architecture already wired at the plumbing level:

| Layer | Path | Scope | Status |
|-------|------|-------|--------|
| **domain_data** | `./data/workers/{id}/domain_data/` | Per-worker analytical data | ✅ Fully functional |
| **my_data** | `./data/workers/{id}/my_data/{user_id}/` | Per-user working files | ✅ Fully functional |
| **common_data** | `./data/common/` | Platform-wide shared reference | ❌ Wired but empty, no UI |

The common_data plumbing already exists in the codebase:
- Every worker in `workers.json` has `"common_data_path": "./data/common"`
- `path_resolver.py` supports `resolve('common_data', worker_ctx)` as a valid category
- `agent/tools.py` sends `X-Worker-Common-Root` header to SAJHA on every tool call
- `agent_server.py` line 191: `_COMMON_DATA = _DATA_ROOT / 'common'` and line 340: `_COMMON_DATA.mkdir(parents=True, exist_ok=True)` — folder created at startup
- `_resolve_worker_path()` line 247: already maps `'common'` section to `worker.get('common_data_path', './data/common')`
- `_admin_section_roots_for_worker()` line 315: explicitly excludes common with comment `"platform read-only, REQ-CD-01"`

But nothing populates it, no UI browses it, no tools search it, and admins cannot upload to it.

### 1.2 Use Cases

- **Regulatory library:** OSFI guidelines, Basel frameworks, FRTB docs shared across all workers
- **Corporate policies:** Model validation SOPs, risk appetite statements, compliance checklists
- **Reference data:** Industry classification codes, country risk ratings, CDS convention tables
- **Templates:** Shared report templates, brief templates available to all workers

### 1.3 What Common Data Is NOT

Common data is a **new shared layer** alongside domain_data and my_data. It does not replace or relocate anything. OSFI docs currently in `domain_data/osfi/` stay there. If an admin wants to share them across workers, they upload copies to `data/common/regulatory/osfi/` through the admin panel. Workers can have their own domain-specific copies that take precedence.

### 1.4 Access Model

| Role | Browse | Read | Upload | Delete | Create Folder |
|------|--------|------|--------|--------|---------------|
| super_admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| admin | ✅ | ✅ | ✅ | ❌ | ✅ |
| user | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 2. Architecture

```
sajhamcpserver/data/
├── common/                          ← shared across all workers
│   ├── regulatory/
│   │   ├── osfi/
│   │   ├── basel/
│   │   └── frtb/
│   ├── policies/
│   ├── reference/
│   └── templates/
├── workers/
│   ├── w-market-risk/
│   │   ├── domain_data/             ← worker-specific (IRIS, DuckDB, worker OSFI copies)
│   │   ├── my_data/{user_id}/       ← per-user
│   │   └── ...
│   └── w-credit-risk/
│       └── ...
```

### 2.1 Resolution Priority

When a tool resolves a file path, the priority order is:
1. `my_data` (per-user, most specific)
2. `domain_data` (per-worker)
3. `common_data` (shared, least specific)

---

## 3. Prerequisite Cleanup

Remove stale artifacts from the earlier design session that conflict with the live `document_search` tool:

```
□ Delete config/tools/doc_list_corpus.json       (points to nonexistent DocListCorpusTool)
□ Delete config/tools/doc_search.json            (conflicts with live document_search.json)
□ Delete config/tools/doc_read_passage.json      (points to nonexistent DocReadPassageTool)
□ Delete config/tools/doc_index_build.json       (points to nonexistent DocIndexBuildTool)
□ Delete sajha/tools/impl/doc_retrieval_tools.py (superseded by bm25_search_tool.py)
```

The live tool is **`document_search`** backed by `sajha/tools/impl/bm25_search_tool.py` using the `rank_bm25` library with fingerprint-based cache invalidation. All REQ-10 changes build on this tool.

---

## 4. Backend Changes

### 4.1 Agent Server (`agent_server.py`)

#### 4.1.1 Add `common` to admin file browser

**Current:** `_admin_section_roots_for_worker()` (line ~310) excludes common.

**Change:** Add `common` to the returned dict:

```python
def _admin_section_roots_for_worker(worker: dict) -> dict:
    base = pathlib.Path('sajhamcpserver')
    dd   = base / worker.get('domain_data_path',    './data/domain_data').lstrip('./')
    wf   = base / worker.get('workflows_path',       './data/workflows/verified').lstrip('./')
    mywf = base / worker.get('my_workflows_path',    './data/workflows/my').lstrip('./')
    common = base / worker.get('common_data_path',   './data/common').lstrip('./')
    return {
        'domain_data': dd,
        'verified_workflows': wf,
        'my_workflows': mywf,
        'common': common,
    }
```

#### 4.1.2 User read access — already works

`_resolve_worker_path()` already maps `'common'` (line 247). The existing `GET /api/fs/{section}/tree` and `GET /api/fs/{section}/file` endpoints will work with `section=common` with no code change. Verify in QA.

#### 4.1.3 User upload blocked — already works

`_WRITABLE_SECTIONS = {'uploads', 'my_workflows'}` (line 195). `common` is absent, so `POST /api/fs/common/upload` returns 403 automatically. No code change.

#### 4.1.4 Admin delete protection

Add a guard to the delete endpoints for admin role:

```python
# In super_worker_delete_file and admin_worker_delete_file:
if section == 'common' and payload.get('role') != 'super_admin':
    raise HTTPException(status_code=403, detail='Only super_admin can delete from common data')
```

#### 4.1.5 Admin upload endpoint for common

The existing `super_worker_upload` resolves via `_resolve_admin_path_for_worker()`. Once `common` is added there (4.1.1), super_admin uploads work via:
```
POST /api/super/workers/{worker_id}/files/common/upload
```

For admin role, add a dedicated endpoint:

```python
@app.post('/api/admin/common/upload')
async def admin_common_upload(
    path: str = '',
    overwrite: bool = False,
    file: UploadFile = File(...),
    payload: dict = Depends(require_admin),
):
    """Upload a file to common data (admin + super_admin)."""
    worker = _get_admin_worker(payload)
    if not worker:
        workers = _load_workers()
        worker = workers[0] if workers else {}
    common_root = _resolve_worker_path(worker, 'common')
    folder = _resolve_worker_path(worker, 'common', path) if path else common_root
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / pathlib.Path(file.filename).name
    if dest.exists() and not overwrite:
        raise HTTPException(status_code=409, detail='File already exists')
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='File exceeds 50 MB limit')
    dest.write_bytes(content)
    build_index(str(common_root))
    stat = dest.stat()
    return {
        'path': str(dest.relative_to(common_root)).replace('\\', '/'),
        'size_bytes': stat.st_size,
    }
```

### 4.2 SAJHA — `document_search` Tool (`bm25_search_tool.py`)

#### 4.2.1 Add common_data as a third search directory

**Current:** `DocumentSearchTool.execute()` indexes two directories:
```python
domain_dir = self._domain_dir()
my_data_dir = self._my_data_dir()
cache_key = f"{domain_dir}|{my_data_dir}"
current_fp = _fingerprint([domain_dir, my_data_dir])
```

**Change:** Add `_common_dir()` method and include it in fingerprint + index build:

```python
def _common_dir(self) -> str:
    try:
        from flask import g as _g
        root = getattr(_g, 'worker_common_root', None)
        if root:
            return root.rstrip('/')
    except RuntimeError:
        pass
    return PropertiesConfigurator().get(
        'data.common_data.dir', './data/common'
    )

def execute(self, arguments: dict) -> dict:
    # ...
    domain_dir = self._domain_dir()
    my_data_dir = self._my_data_dir()
    common_dir = self._common_dir()
    cache_key = f"{domain_dir}|{my_data_dir}|{common_dir}"
    current_fp = _fingerprint([domain_dir, my_data_dir, common_dir])
    # ...
    bm25, docs = _build_index([domain_dir, my_data_dir, common_dir])
```

Common data is included in BM25 search **by default** — no section parameter needed. All three scopes are always searched together. The fingerprint-based cache invalidation automatically detects new files uploaded to common.

#### 4.2.2 application.properties

Add:
```properties
# Common Data (shared across all workers)
data.common_data.dir=./data/common
```

#### 4.2.3 Update tool description

**File:** `config/tools/document_search.json`

Change description to:
```
"BM25 full-text search across all worker documents (domain_data + my_data + common shared library). Returns ranked results with relevance scores and content excerpts..."
```

---

## 5. Frontend Changes

### 5.1 User Chat Sidebar (`mcp-agent.html`)

#### 5.1.1 Add "Shared Library" section

In `tab-panel-dw` (line ~2888), add between the Domain Data and My Data sections:

```html
<!-- Shared Library (common_data) — read-only for users -->
<div class="ft-section" id="ft-common">
  <div class="ft-header" onclick="ftToggle('common')">
    <div class="ft-header-left">
      <svg class="ft-chevron" id="ft-chevron-common" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2.5"
           stroke-linecap="round" stroke-linejoin="round">
        <polyline points="9 18 15 12 9 6"></polyline>
      </svg>
      <span class="ft-section-label">Shared Library</span>
      <span class="ft-count-badge" id="ft-badge-common">0</span>
    </div>
    <div class="ft-toolbar">
      <button class="ft-tool-btn" title="Refresh"
              onclick="event.stopPropagation();ftLoad('common')">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none"
             stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
      </button>
    </div>
  </div>
  <div class="ft-body" id="ft-body-common">
    <div class="ft-tree" id="ft-tree-common"></div>
  </div>
</div>
```

#### 5.1.2 Register in `_FT_SECTIONS` (line ~5154)

```javascript
var _FT_SECTIONS = {
  domain_data:   { label: 'Domain Data',       writable: false, wfSection: false },
  common:        { label: 'Shared Library',     writable: false, wfSection: false },
  uploads:       { label: 'My Data',            writable: true,  wfSection: false },
  verified:      { label: 'Verified Workflows', writable: false, wfSection: true  },
  my_workflows:  { label: 'My Workflows',       writable: true,  wfSection: true  },
};
```

### 5.2 Admin Panel (`admin.html`)

#### 5.2.1 Add "Common Data" nav item and section panel

In the sidebar nav "Data & Workflows" group, add a nav item. Add a section panel with:
- Upload button (admin + super_admin)
- Create folder button (admin + super_admin)
- Select/Delete buttons (super_admin only — hidden via `_user.role` check)
- BPulseFileTree instance: `section: 'common'`, `writable: true`

#### 5.2.2 Initialize BPulseFileTree

```javascript
window._bpft_common = new BPulseFileTree({
  containerId: 'tree-common',
  section: 'common',
  apiPrefix: _apiPrefix,
  writable: true,
  workflowSection: false,
  token: _getToken,
  onToast: _toast,
  onConfirm: _bpftConfirm,
  onFileClick: function(section, path, name) {
    if (typeof previewFile === 'function')
      previewFile({ stopPropagation: function(){} }, section, path, name);
  },
});
```

#### 5.2.3 Role-based delete visibility

```javascript
if (_user.role !== 'super_admin') {
  document.getElementById('common-delete-btn').style.display = 'none';
  document.getElementById('common-select-btn').style.display = 'none';
}
```

---

## 6. System Prompt Update

Add to the document search guidance in the worker system prompt:

```
Common Data (Shared Library) contains reference documents shared across all workers:
regulatory guidelines, corporate policies, templates, and reference data.
The document_search tool automatically includes common data in its search scope.
```

---

## 7. Implementation Stories

| Story | Description | Layer | Depends On |
|-------|-------------|-------|-----------|
| S0 | **Cleanup:** Delete stale `doc_*.json` configs and `doc_retrieval_tools.py` | Cleanup | — |
| S1 | Add `common` to `_admin_section_roots_for_worker()` | Backend | S0 |
| S2 | Verify `GET /api/fs/common/tree` works for user role | Backend | S1 |
| S3 | Add `/api/admin/common/upload` endpoint | Backend | S1 |
| S4 | Add delete protection: admin cannot delete from common | Backend | S1 |
| S5 | Add `_common_dir()` to `bm25_search_tool.py`, include in index + fingerprint | SAJHA | S0 |
| S6 | Update `document_search.json` description | SAJHA | S5 |
| S7 | Add `data.common_data.dir` to `application.properties` | SAJHA | — |
| S8 | Add "Shared Library" HTML + `_FT_SECTIONS` entry in `mcp-agent.html` | Frontend | S2 |
| S9 | Add "Common Data" panel in `admin.html` with BPulseFileTree + role-based delete | Frontend | S1 |
| S10 | Update system prompt | Config | S5 |
| S11 | Seed `data/common/` with test files (1× .md, 1× .pdf, 1× .csv) | Data | S1 |

---

## 8. QA Test Plan

### 8.1 Backend API Tests

| ID | Test | Expected |
|----|------|----------|
| CD-01 | `GET /api/fs/common/tree` as user | 200; returns tree |
| CD-02 | `GET /api/fs/common/file?path=test.md` as user | 200; file content |
| CD-03 | `POST /api/fs/common/upload` as user | 403; read-only |
| CD-04 | `POST /api/super/workers/{id}/files/common/upload` as super_admin | 200; file created |
| CD-05 | `POST /api/admin/common/upload` as admin | 200; file created |
| CD-06 | `DELETE .../common/file?path=...` as super_admin | 200; deleted |
| CD-07 | `DELETE .../common/file?path=...` as admin | 403; denied |
| CD-08 | `document_search(query="[term in common file]")` | Results include common file |
| CD-09 | Upload to common → `document_search` | New file in BM25 results (fingerprint refresh) |
| CD-10 | `GET /api/fs/common/tree` from Worker A and B | Same listing |
| CD-11 | Path traversal: `?path=../../config/users.json` | 400 |
| CD-12 | Upload 51 MB file | 413 |
| CD-13 | Upload duplicate without overwrite | 409 |

### 8.2 Playwright UI Tests

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| CD-UI-01 | Shared Library visible | Login as user → Data & Workflows tab | "Shared Library" between Domain Data and My Data |
| CD-UI-02 | User browses common | Expand Shared Library → click file | Preview opens |
| CD-UI-03 | No write buttons for user | Inspect toolbar | Only Refresh visible |
| CD-UI-04 | Admin panel shows common | Login as admin → admin panel | "Common Data" section with Upload + Folder buttons |
| CD-UI-05 | Admin uploads to common | Upload a file | File in tree, success toast |
| CD-UI-06 | Admin cannot delete | Inspect common section | No Delete/Select buttons |
| CD-UI-07 | Super admin can delete | Select + Delete | File removed |
| CD-UI-08 | Common in search results | Chat: search for term in common file | `document_search` results include the file |
| CD-UI-09 | Badge count | Expand Shared Library | Badge matches file count |

---

## 9. Acceptance Criteria

- [ ] Stale `doc_*.json` and `doc_retrieval_tools.py` deleted
- [ ] CD-01 through CD-13 pass
- [ ] CD-UI-01 through CD-UI-09 pass
- [ ] User sidebar: "Shared Library" read-only between Domain Data and My Data
- [ ] Admin panel: "Common Data" with upload + folder; delete only for super_admin
- [ ] `document_search` BM25 includes common files by default
- [ ] All workers resolve to same `./data/common/`
- [ ] No regressions in domain_data, my_data, or workflows

---

## 10. Out of Scope

- Per-worker common_data overrides
- OSFI data migration (users copy manually if desired)
- S3 backend for common data (see REQ-11)
- Common data quotas beyond 50 MB per-file cap
