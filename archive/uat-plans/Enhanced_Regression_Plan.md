# Enhanced Regression Plan — MCP Intelligence Agent

**Created:** 2026-04-05  
**Scope:** Full E2E regression covering REQ-09, REQ-10, REQ-11, bug fixes, and new HuggingFace provider  
**Methodology:** 4 parallel agents produced: code scan, coverage matrix, API+JS tests, E2E tests + script  

---

## Summary Status

| Layer | Count | Status |
|-------|-------|--------|
| Known Open Bugs | 8 | See Section 1 |
| CI Tests (all suites) | 220 | ✅ All passing |
| Browser Tests Pending | 22 | ⏳ REQ-09 (7), REQ-10 (9), REQ-11 (6) |
| Layer 1 API Smoke Tests | 50 | New — not yet run |
| Layer 2 JS Unit Tests | 15 | New — not yet run |
| Layer 3 E2E Tests | 32 | New — not yet run |

---

## Section 1 — Open Bugs (from Code Scan + Phase 5 Gap Analysis)

### P0 — Critical (Backend routes missing)

| ID | Description | Status |
|----|-------------|--------|
| **BUG-NEW-001** | `PUT /api/admin/worker` returns 405. | ✅ **FALSE POSITIVE** — route exists at agent_server.py:930 |
| **BUG-NEW-002** | `POST /api/admin/worker/users` returns 405. | ✅ **FALSE POSITIVE** — route exists at agent_server.py:948 |
| **BUG-NEW-003** | `PUT /api/admin/worker/users/{id}` returns 405. | ✅ **FALSE POSITIVE** — route exists at agent_server.py:978 |
| **BUG-NEW-004** | `POST /api/admin/worker/users/{id}/reset-password` returns 405. | ✅ **FALSE POSITIVE** — route exists at agent_server.py:997 |

### P1 — High (Logic bugs)

| ID | Description | Status |
|----|-------------|--------|
| **BUG-NEW-007** | Workflow GET/POST path mismatch. | ✅ **FIXED** — `GET /api/workflows/{filename}` checks both `verified_workflows` and `my_workflows` sections (agent_server.py:1185) |
| **BUG-NEW-008** | `WorkerRepository.find_by_user` field `users` vs `assigned_users`. | ✅ **FIXED** — Uses `w.get('assigned_users', w.get('users', []))` fallback (worker_repository.py:55) |

### P2 — Medium (Unconfirmed)

| ID | Description | Status |
|----|-------------|--------|
| **BUG-NEW-005** | `DELETE /api/super/workers/{id}` requires `confirm_name` in body. | ⏳ Unverified — UI behaviour not tested |
| **BUG-NEW-006** | `POST /api/super/workers/{id}/assign` requires `role` field. | ⏳ Unverified — UI behaviour not tested |

### P1 — Tool gap (Fixed 2026-04-05)

| ID | Description | Status |
|----|-------------|--------|
| **BUG-NEW-009** | `search_files` only searched `domain_data/` and `my_data/` — excluded `common/` (Shared Library). `document_search` (BM25) already covered all 3 sections + excerpts. | ✅ **FIXED** — Added `_common_root()` helper + `"common"` section option to `search_files`. Both tools now offer full coverage: `document_search` for ranked relevance, `search_files` for exact keyword + excerpts across all 3 sections. |

### Code Scan Result (Agent 1)

**file-tree.js:** CLEAN. The known `opts.uploadConcurrency` → `config.uploadConcurrency` bug at line 224 is confirmed fixed. No other parameter name mismatches found.

**mcp-agent.html:** CLEAN. `_bpftInstB` (5 sections), `_bpftInstC` (2 sections) all properly initialized. All callback references valid.

**admin.html:** CLEAN. `_bpft_dd`, `_bpft_wf`, `_bpft_common` all properly initialized.

**Minor (non-blocking):** `showToast` in mcp-agent.html only accepts `(msg, duration)` but BPulseFileTree calls `_onToast(msg, type)` — toast type (`info`/`error`/`success`) is discarded in mcp-agent.html context. Does not cause a crash.

---

## Section 2 — Coverage Matrix

| Feature | REQ | CI Tests | CI Passing | Browser Tested | Pending |
|---------|-----|----------|------------|----------------|---------|
| BM25 Document Search | REQ-09 | 10 | 10/10 ✅ | 0/7 ⏳ | BT-BM25-01 to BT-BM25-07 |
| Common Data Path | REQ-10 | 13 | 13/13 ✅ | 0/9 ⏳ | CD-UI-01 to CD-UI-09 |
| Multi-File Parallel Upload | REQ-11 | 14 | 14/14 ✅ | 0/6 ⏳ | UP-UI-01 to UP-UI-06 |
| Architectural Gap Fixes | GAP | 19 | 19/19 ✅ | 5/5 ✅ | — |
| UI Audit & Bug Fixes | UI Audit | 40 | 37/37 ✅ | 37/37 ✅ | 3 SKIP (env-only) |
| Regression v2 | Regression | 14 | 14/14 ✅ | 14/14 ✅ | — |
| Functional Regression | Functional | 113 | 113/113 ✅ | 113/113 ✅ | — |
| HuggingFace Provider | New | 0 | — | 0 ⏳ | HF-001 to HF-003 |
| **TOTAL** | | **236** | **220/220 ✅** | **169/169 ✅** | **25 pending** |

---

## Section 3 — Layer 1: API Smoke Tests (50 tests)

### AUTH

| ID | Endpoint | Method | Auth | Body | Expected | Assert |
|----|----------|--------|------|------|----------|--------|
| AUTH-001 | `/health` | GET | None | — | 200 | Valid JSON |
| AUTH-002 | `/api/auth/login` | POST | None | `{"username":"user","password":"pass"}` | 200/401 | JWT token or 401 |
| AUTH-003 | `/api/auth/me` | GET | User JWT | — | 200 | `role`, `username`, `worker_id` present |
| AUTH-004 | `/api/auth/onboarding` | POST | User JWT | `{"full_name":"Test"}` | 200 | Processed |
| AUTH-005 | `/api/auth/change-password` | POST | User JWT | `{"old_pwd":"x","new_pwd":"y"}` | 200/400 | Changed or validation error |

### SUPER ADMIN

| ID | Endpoint | Method | Auth | Body | Expected | Assert |
|----|----------|--------|------|------|----------|--------|
| SUPER-001 | `/api/super/workers` | GET | Super Admin | — | 200 | Array of workers |
| SUPER-002 | `/api/super/workers` | POST | Super Admin | `{"name":"w-test"}` | 201 | Worker ID returned |
| SUPER-003 | `/api/super/workers/{id}` | GET | Super Admin | — | 200 | Worker config object |
| SUPER-004 | `/api/super/workers/{id}` | PUT | Super Admin | `{"name":"updated"}` | 200 | Updated |
| SUPER-005 | `/api/super/workers/{id}` | DELETE | Super Admin | `{"confirm_name":"w-test"}` | 200 | Deleted |
| SUPER-006 | `/api/super/workers/{id}/assign` | POST | Super Admin | `{"user_id":"u1","role":"user"}` | 200 | Assigned |
| SUPER-007 | `/api/super/workers/{id}/assign/{uid}` | DELETE | Super Admin | — | 200 | Unassigned |
| SUPER-008 | `/api/super/users` | GET | Super Admin | — | 200 | All users array |
| SUPER-009 | `/api/super/users` | POST | Super Admin | `{"username":"new","role":"admin"}` | 201 | Created |
| SUPER-010 | `/api/super/users/{id}` | PUT | Super Admin | `{"username":"renamed"}` | 200 | Updated |
| SUPER-011 | `/api/super/users/{id}` | DELETE | Super Admin | — | 200 | Deleted |
| SUPER-012 | `/api/super/users/{id}/reset-password` | POST | Super Admin | — | 200 | Temp password |

### ADMIN

| ID | Endpoint | Method | Auth | Body | Expected | Assert |
|----|----------|--------|------|------|----------|--------|
| ADMIN-001 | `/api/admin/worker` | GET | Admin | — | 200 | Config, prompt, tools |
| ADMIN-002 | `/api/admin/worker` | PUT | Admin | `{"prompt":"..."}` | 200 | Updated (⚠️ BUG-NEW-001: may 405) |
| ADMIN-003 | `/api/admin/worker/prompt` | PUT | Admin | `{"prompt":"New"}` | 200 | Persisted |
| ADMIN-004 | `/api/admin/worker/tools` | PUT | Admin | `{"enabled_tools":[...]}` | 200 | Updated |
| ADMIN-005 | `/api/admin/worker/users` | GET | Admin | — | 200 | Users for worker |
| ADMIN-006 | `/api/admin/worker/users` | POST | Admin | `{"username":"u","password":"p"}` | 201 | Created (⚠️ BUG-NEW-002: may 405) |
| ADMIN-007 | `/api/admin/worker/users/{id}` | PUT | Admin | `{"username":"x"}` | 200 | Updated (⚠️ BUG-NEW-003: may 405) |
| ADMIN-008 | `/api/admin/worker/users/{id}/reset-password` | POST | Admin | — | 200 | Temp password (⚠️ BUG-NEW-004: may 405) |
| ADMIN-009 | `/api/admin/worker/users/{id}` | DELETE | Admin | — | 200 | Deleted |

### FILE SYSTEM & UPLOADS

| ID | Endpoint | Method | Auth | Body | Expected | Assert |
|----|----------|--------|------|------|----------|--------|
| UPLOAD-001 | `/api/files/upload` | POST | User | Binary file | 200 | Path returned |
| UPLOAD-002 | `/api/super/workers/{id}/files/{sec}/upload` | POST | Super Admin | File + `batch_id=b1` | 200 | Deferred reindex |
| UPLOAD-003 | `/api/super/workers/{id}/files/{sec}/upload` | POST | Super Admin | File (no batch_id) | 200 | Reindex triggered |
| UPLOAD-004 | `/api/super/workers/{id}/files/{sec}/upload` | POST | Super Admin | 51MB file | 413 | Rejected, cleanup done |
| UPLOAD-005 | `/api/super/workers/{id}/files/{sec}/upload?path=../../etc` | POST | Super Admin | File | 400 | Path traversal rejected |
| UPLOAD-006 | `/api/super/workers/{id}/files/{sec}/upload?overwrite=false` | POST | Super Admin | Existing file | 409 | Not overwritten |
| UPLOAD-007 | `/api/super/workers/{id}/files/{sec}/upload?overwrite=true` | POST | Super Admin | Existing file | 200 | Replaced |
| UPLOAD-008 | `/api/admin/worker/files/{sec}/upload` | POST | Admin | File + batch_id | 200 | Deferred |
| UPLOAD-009 | `/api/admin/common/upload` | POST | Admin | .md file | 200 | To common path |
| UPLOAD-010 | `/api/fs/common/upload` | POST | User | File | 403 | User blocked |

### FILE SYSTEM — TREE, COMMON, QUOTA

| ID | Endpoint | Method | Auth | Body | Expected | Assert |
|----|----------|--------|------|------|----------|--------|
| FS-COMMON-001 | `/api/fs/common/tree` | GET | User | — | 200 | Shared Library tree |
| FS-COMMON-002 | `/api/fs/common/file?path=test.md` | GET | User | — | 200 | Content returned |
| FS-COMMON-003 | `/api/fs/common/file?path=../../config` | GET | User | — | 400/403 | Traversal blocked |
| FS-COMMON-004 | `/api/super/workers/{id}/files/common/file?path=test.md` | DELETE | Super Admin | — | 200 | Deleted |
| FS-COMMON-005 | `/api/admin/worker/files/common/file?path=test.md` | DELETE | Admin | — | 403 | Admin cannot delete common |
| QUOTA-001 | `/api/fs/quota` | GET | User | — | 200 | `used_bytes`, `limit_bytes` |
| TREE-001 | `/api/fs/uploads/tree` | GET | User | — | 200 | My Data tree |
| TREE-002 | `/api/fs/domain_data/tree` | GET | User | — | 200 | Domain Data tree |
| TREE-003 | `/api/fs/verified/tree` | GET | User | — | 200 | Verified Workflows tree |

### WORKFLOWS

| ID | Endpoint | Method | Auth | Body | Expected | Assert |
|----|----------|--------|------|------|----------|--------|
| WF-001 | `/api/workflows` | GET | User | — | 200 | Array of workflow files |
| WF-002 | `/api/workflows` | POST | User | `{"filename":"test.md","content":"..."}` | 201 | Created |
| WF-003 | `/api/workflows/test.md` | GET | User | — | 200 | Content (⚠️ BUG-NEW-007: may 404) |
| WF-004 | `/api/workflows/test.md` | DELETE | User | — | 200 | Deleted |
| WF-005 | `/api/workflows/test.md/used` | PATCH | User | `{"used":true}` | 200 | Usage marked |

### SEARCH & REINDEX

| ID | Endpoint | Method | Auth | Body | Expected | Assert |
|----|----------|--------|------|------|----------|--------|
| REINDEX-001 | `/api/super/workers/{id}/files/{sec}/reindex` | POST | Super Admin | — | 200 | `indexed_files`, `elapsed_ms` |
| REINDEX-002 | `/api/admin/worker/files/{sec}/reindex` | POST | Admin | — | 200 | BM25 rebuilt |
| BM25-001 | Document_search (SAJHA) | POST | SAJHA key | `{"query":"capital adequacy"}` | 200 | Results with BM25 scores |
| BM25-002 | Document_search (common) | POST | SAJHA key | Query matching common file | 200 | Common results included |
| BATCH-DELETE-001 | `/api/fs/{sec}/batch-delete` | POST | User | `{"paths":["f1.md","f2.md"]}` | 200 | Both deleted |

---

## Section 4 — Layer 2: JavaScript Unit Tests (15 tests)

Run via `page.evaluate()` in Playwright.

| ID | Test Name | page.evaluate Code | Assert |
|----|-----------|-------------------|--------|
| **JS-001** | Constructor crash guard | `try { new BPulseFileTree({}); return true; } catch(e) { return false; }` | `true` (no crash) |
| **JS-002** | Constructor reads config params | `var i = new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:'/api/fs',writable:true,token:()=>'t'}); return i._section==='uploads'&&i._writable===true;` | `true` |
| **JS-003** | uploadConcurrency default = 4 | `var i = new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:'/api/fs'}); return i._uploadConcurrency===4;` | `true` |
| **JS-004** | uploadConcurrency custom value | `var i = new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:'/api/fs',uploadConcurrency:8}); return i._uploadConcurrency===8;` | `8` |
| **JS-005** | Upload queue isolated per instance | `var a=new BPulseFileTree({containerId:'c1',section:'uploads',apiPrefix:'/api/fs'}); var b=new BPulseFileTree({containerId:'c2',section:'uploads',apiPrefix:'/api/fs'}); a._uploadQueue.push({id:1}); return b._uploadQueue.length===0;` | `true` |
| **JS-006** | _confirmFn custom override | `var called=false; var i=new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:'/api/fs',onConfirm:function(m,cb){called=true;cb();}}); i._confirmFn('Delete?',function(){}); return called;` | `true` |
| **JS-007** | _confirmFn is a function by default | `var i=new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:'/api/fs'}); return typeof i._confirmFn==='function';` | `true` |
| **JS-008** | _bpftInstB has all 5 sections | `return typeof _bpftInstB!=='undefined'&&['domain_data','common','uploads','verified','my_workflows'].every(k=>_bpftInstB.hasOwnProperty(k));` | `true` |
| **JS-009** | _bpftInstC has admin sections | `return typeof _bpftInstC!=='undefined'&&_bpftInstC.hasOwnProperty('domain_data')&&_bpftInstC.hasOwnProperty('verified_workflows');` | `true` |
| **JS-010** | Required globals on mcp-agent.html | `return typeof BPulseFileTree!=='undefined'&&typeof BPulseFilePreview!=='undefined'&&typeof _bpftToken==='function'&&typeof _bpftToast==='function';` | `true` |
| **JS-011** | _bpftToken() returns string | `return typeof _bpftToken()==='string';` | `true` |
| **JS-012** | search() sets _searchQuery | `var i=new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:'/api/fs'}); i._tree={tree:[{name:'apple.md',type:'file',path:'apple.md'}]}; i.search('apple'); return i._searchQuery==='apple';` | `'apple'` |
| **JS-013** | clearSearch() resets query | `var i=new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:'/api/fs'}); i.search('test'); i.clearSearch(); return i._searchQuery==='';` | `true` |
| **JS-014** | _matchesSearch() case-insensitive | `var i=new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:'/api/fs'}); i._searchQuery='test'; return i._matchesSearch({name:'TEST-file.md',type:'file'});` | `true` |
| **JS-015** | _prefix getter supports function apiPrefix | `var i=new BPulseFileTree({containerId:'c',section:'uploads',apiPrefix:function(){return '/api/custom';}}); return i._prefix==='/api/custom';` | `true` |

---

## Section 5 — Layer 3: E2E Playwright Tests (32 tests)

### Framework & Globals

| ID | Area | Description | Steps | Assert |
|----|------|-------------|-------|--------|
| ERT-001 | Framework | BPulseFileTree class exists | Load page | `window.BPulseFileTree` is a function |
| ERT-002 | Framework | Constructor does not throw (**GATE TEST**) | Instantiate with valid config | No exception; abort all if fails |
| ERT-003 | Config | uploadConcurrency from config | Initialize with `uploadConcurrency:6` | `_uploadConcurrency === 6` |
| ERT-004 | Globals | `_bpftInstB` exists | Load mcp-agent.html | `typeof _bpftInstB === 'object'` |
| ERT-005 | Globals | `_bpftInstC` exists | Load mcp-agent.html | `typeof _bpftInstC === 'object'` |

### Login & Auth

| ID | Area | Description | Steps | Assert |
|----|------|-------------|-------|--------|
| ERT-010 | Auth | JWT in sessionStorage after login | Full auth flow | `sessionStorage.getItem('rg_token').length > 0` |
| ERT-011 | Auth | Super admin redirects to admin.html | Login as super_admin | URL contains `/admin.html` |
| ERT-012 | Auth | Regular user redirects to mcp-agent.html | Login as user | URL contains `/mcp-agent.html` |

### REQ-10: Common Data Path Browser Tests

| ID | Area | Description | Steps | Assert |
|----|------|-------------|-------|--------|
| CD-UI-01 | Sidebar | Login as user → Data & Workflows tab visible | Login, open sidebar | "Data & Workflows" tab label visible |
| CD-UI-02 | Common Tree | Expand Shared Library → click file | Expand Shared Library section, click .md | Preview panel shows file content |
| CD-UI-03 | Common Toolbar | Shared Library toolbar is read-only | Expand Shared Library | Only Refresh button; no Upload/Delete |
| CD-UI-04 | Admin Panel | Admin panel shows Shared Library section | Login as admin, open admin panel | "Shared Library" nav item visible |
| CD-UI-05 | Admin Upload | Admin uploads .md to Shared Library | Admin panel → Shared Library → upload .md | File in tree, success toast |
| CD-UI-06 | Admin Toolbar | Admin Shared Library has no Delete | Expand in admin panel | No Delete button; Select present |
| CD-UI-07 | Super Admin | Super admin deletes from Shared Library | Select file, delete action | File removed, toast shown |
| CD-UI-08 | Chat | Chat query surfaces common file | Ask "Basel III framework" | `document_search` called with common results |
| CD-UI-09 | Badge | Shared Library badge shows count | Expand Shared Library in sidebar | `#ft-badge-common` count > 0 |

### REQ-11: Multi-File Upload Browser Tests

| ID | Area | Description | Steps | Assert |
|----|------|-------------|-------|--------|
| UP-UI-01 | Queue | Select 10 files → queue shows all | Admin panel → domain_data → pick 10 files | 10 items in queue UI |
| UP-UI-02 | Progress | Upload 10 files → batch progress bar | Watch upload | "N/10 files · X.X / Y.Y MB" visible |
| UP-UI-03 | Tree Refresh | Tree refreshes exactly ONCE after batch | Monitor XHR calls during upload | `GET /tree` called once after all complete |
| UP-UI-04 | Validation | Oversized file (>50 MB) rejected | Try to upload 51 MB file | Toast: "1 file(s) exceed 50 MB limit" |
| UP-UI-05 | Retry | Simulate failure → click retry | Start upload, simulate failure, retry | Failed file re-queues and retries |
| UP-UI-06 | Cancel | Cancel mid-batch | 10-file upload in progress → cancel | XHRs aborted, queue cleared, completed files persist |

### Sidebar File Trees

| ID | Area | Description | Steps | Assert |
|----|------|-------------|-------|--------|
| ERT-006 | Sidebar | domain_data container renders | Load mcp-agent.html, switch to DW tab | `#ft-tree-domain_data` exists and visible |
| ERT-007 | Sidebar | 5 sections initialized | After page load | `Object.keys(_bpftInstB).length >= 5` |
| ERT-008 | Sidebar | All badge elements exist | Load page | `#ft-badge-domain_data`, `#ft-badge-common`, `#ft-badge-uploads` all exist |

### Admin Console (admin.html)

| ID | Area | Description | Steps | Assert |
|----|------|-------------|-------|--------|
| ERT-009 | Admin | admin-tree-domain_data renders | Load admin.html | `#admin-tree-domain_data` exists |
| ADMIN-UI-001 | Admin | Worker config loads | Login as super_admin → admin.html | Worker name, prompt visible |
| ADMIN-UI-002 | Admin | Tools list loads | admin.html tools section | Tool count > 0 |
| ADMIN-UI-003 | Admin | Users list loads | admin.html users section | User count > 0 |

### Chat & HuggingFace Provider

| ID | Area | Description | Steps | Assert |
|----|------|-------------|-------|--------|
| CHAT-001 | Chat | User sends message → agent responds | Type message → Enter | Response in thread, no JS errors |
| CHAT-002 | File Attach | File attach → banner + system notice | Use file input, attach .csv | Upload banner + "File uploaded" notice |
| HF-001 | HuggingFace | Agent responds (HF provider active) | Send "Hello" in chat | Non-empty response text |
| HF-002 | HuggingFace | Tool use works via HF | Send tool-triggering query | Tool call observed in SSE stream |
| HF-003 | HuggingFace | No 410 errors from HF | Check network | No 410 responses from router.huggingface.co |

### Theme & Performance

| ID | Area | Description | Steps | Assert |
|----|------|-------------|-------|--------|
| THEME-001 | Settings | Dark theme is default | Load page | `--bg-page` CSS var equals dark color |
| THEME-002 | Settings | CSS variables defined | Inspect `:root` | `--sidebar-width`, `--text-primary`, `--bg-elevated` all defined |
| PERF-001 | Page Load | No null-property JS errors | Full session | No "Cannot read properties of null" in console |
| PERF-002 | File Tree | Large domain_data tree loads fast | Load 50+ files | Renders in < 3s |

---

## Section 6 — Script Skeleton `run_enhanced_regression.mjs`

Location: `uat_plans/run_enhanced_regression.mjs`

**Key features:**
- ERT-002 gating: if BPulseFileTree constructor crashes → skip all browser tests
- JWT auth injection (same pattern as `run_regression_v2_tests.mjs`)
- Artifact cleanup registry in `finally` block
- `--layer4` flag for LLM/HuggingFace tests
- Summary table at end (PASS / FAIL / SKIP counts)

```javascript
// run_enhanced_regression.mjs
import { chromium } from 'playwright';

const BASE      = 'http://localhost:8000';
const SA_CREDS  = { user_id: 'risk_agent', password: 'RiskAgent2025!' };
const results   = { pass: 0, fail: 0, skip: 0 };
const failures  = [];
const artifacts = [];
const LAYER4    = process.argv.includes('--layer4');

function log(id, status, detail) {
  const icon = { PASS: '✅', FAIL: '❌', SKIP: '⚠️ ' }[status] || '?';
  console.log(`${icon} ${id}: ${detail}`);
  results[status.toLowerCase()]++;
  if (status === 'FAIL') failures.push({ id, detail });
}

async function authNavigate(page, creds, url) {
  const r = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(creds)
  });
  const data = await r.json();
  if (!data.token) throw new Error(`Login failed: ${JSON.stringify(data)}`);
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.evaluate(({ token, user }) => {
    sessionStorage.setItem('rg_token', token);
    sessionStorage.setItem('rg_user', JSON.stringify(user));
  }, { token: data.token, user: data });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  return data;
}

const browser = await chromium.launch({ headless: true });
let gated = false;

try {
  // ERT-002: Gate test
  const p = await browser.newPage();
  await authNavigate(p, SA_CREDS, `${BASE}/mcp-agent.html`);
  const ok = await p.evaluate(() => {
    try { new BPulseFileTree({ containerId: 'c', section: 'uploads', apiPrefix: '/api/fs' }); return true; }
    catch (e) { return false; }
  });
  if (!ok) { log('ERT-002', 'FAIL', 'BPulseFileTree constructor threw — GATING all browser tests'); gated = true; }
  else       log('ERT-002', 'PASS', 'BPulseFileTree constructor works');
  await p.close();

  if (!gated) {
    // ── ERT-001 to ERT-012 (framework/globals/auth) ──────────────────
    // ... (see full test implementations in Section 5 above)

    // ── CD-UI-01 to CD-UI-09 (REQ-10) ────────────────────────────────
    // ... 

    // ── UP-UI-01 to UP-UI-06 (REQ-11) ────────────────────────────────
    // ...

    // ── CHAT-001, CHAT-002 ────────────────────────────────────────────
    // ...

    // ── HF-001 to HF-003 (only if LAYER4) ────────────────────────────
    if (LAYER4) { /* HF tests */ }
  }

} finally {
  // Cleanup
  console.log('\n── Cleanup ──────────────────────────────────────────────');
  const tok = (await (await fetch(`${BASE}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(SA_CREDS)
  })).json()).token;
  for (const a of artifacts) {
    await fetch(`${BASE}/api/fs/uploads/file?path=${encodeURIComponent(a)}`, {
      method: 'DELETE', headers: { Authorization: `Bearer ${tok}` }
    });
  }

  await browser.close();

  // Summary
  const total = results.pass + results.fail + results.skip;
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`ENHANCED REGRESSION RESULTS — ${new Date().toISOString()}`);
  console.log(`${'═'.repeat(60)}`);
  console.log(`  PASS: ${results.pass}  FAIL: ${results.fail}  SKIP: ${results.skip}  TOTAL: ${total}`);
  if (failures.length) {
    console.log('\nFailures:');
    failures.forEach(f => console.log(`  ❌ ${f.id}: ${f.detail}`));
  }
  console.log(`${'═'.repeat(60)}`);
  process.exit(results.fail > 0 ? 1 : 0);
}
```

---

## Section 7 — Priority Order for Fixing Open Bugs

1. **BUG-NEW-007** (Workflow POST/GET path mismatch) — Fix first, quickest win, breaks key UX
2. **BUG-NEW-008** (WorkerRepository field `users` vs `assigned_users`) — Single-line fix
3. **BUG-NEW-001 to BUG-NEW-004** (Admin missing PUT/POST routes) — These may already exist but under a different path; verify against `agent_server.py` before creating new routes

## Section 8 — Next Steps

| Step | Action |
|------|--------|
| 1 | Fix BUG-NEW-007 and BUG-NEW-008 (quick fixes, 15 min) |
| 2 | Verify BUG-NEW-001 to BUG-NEW-004 by grepping `agent_server.py` for actual route definitions |
| 3 | Write `run_enhanced_regression.mjs` (use skeleton above, fill in test bodies) |
| 4 | Run Layer 1 API tests (no browser required; use `node --experimental-fetch`) |
| 5 | Run Layer 2 JS unit tests (Playwright page.evaluate, fastest layer) |
| 6 | Run Layer 3 E2E tests (full Playwright, requires both servers running) |
| 7 | Run `--layer4` HuggingFace tests with `ulimit -n 65536` (avoids kqueue fd limit) |
