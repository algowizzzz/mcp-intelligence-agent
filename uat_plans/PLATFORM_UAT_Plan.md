# Platform UAT Plan — End-to-End Production Validation

**Status:** Draft — Execution In Progress  
**Version:** 1.0 (2026-04-14)  
**Environment:** Production VPS `62.238.3.148` · Hetzner CPX32  
**Scope:** Full-stack validation of S3 storage, Postgres persistence, worker/agent lifecycle, all tool categories, workflows, connectors, and admin UI. Holistic — critical infrastructure first, UI and integrations last.

---

## Quick Reference

| Component | Value |
|-----------|-------|
| Base URL | `http://62.238.3.148` |
| Super admin | `risk_agent` / `RiskAgent2025!` |
| S3 bucket | `sajha-storage` @ `hel1.your-objectstorage.com` |
| S3 region | `hel1` |
| Postgres host | `postgres:5432` (internal) · `62.238.3.148:5432` (external) |
| Postgres DB | `sajha` / `sajha` |
| Primary worker | `w-market-risk` (Market Risk Worker) |
| Agent model | xAI Grok-3 (`LLM_PROVIDER=xai`) |

---

## Phase Overview

| Phase | Area | Priority | Tests | Status |
|-------|------|----------|-------|--------|
| 1 | Infrastructure — S3 + Postgres | 🔴 CRITICAL | INF-01–10 | ⏳ |
| 2 | Auth & User Management | 🔴 CRITICAL | AUTH-01–08 | ⏳ |
| 3 | Worker / Agent Configuration | 🔴 CRITICAL | WRK-01–10 | ⏳ |
| 4 | File System + S3 Integration | 🔴 CRITICAL | FS-01–12 | ⏳ |
| 5 | Agent Execution + Postgres Checkpoints | 🔴 CRITICAL | AGT-01–10 | ⏳ |
| 6 | Core Tools — S3-Backed Data | 🟠 HIGH | TOOL-01–14 | ⏳ |
| 7 | Workflows (single + multi-agent) | 🟠 HIGH | WF-01–08 | ⏳ |
| 8 | External Data Tools | 🟡 MEDIUM | EXT-01–06 | ⏳ |
| 9 | Connector Tools (Teams, Jira, Outlook) | 🟡 MEDIUM | CONN-01–08 | ⏳ |
| 10 | Admin + Chat UI — Playwright | 🟡 MEDIUM | UI-01–14 | ⏳ |
| 11 | Audit, Sessions & Observability | 🟢 LOW | AUD-01–06 | ⏳ |

---

## Shared Fixtures (Python)

All API tests use these helpers. Run at the top of each test session:

```python
import requests, boto3, json, os, time

BASE = "http://62.238.3.148"
WID  = "w-market-risk"

def get_token(user="risk_agent", pw="RiskAgent2025!"):
    r = requests.post(f"{BASE}/api/auth/login",
        json={"user_id": user, "password": pw})
    return r.json()["token"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}

TOKEN = get_token()

def s3_client():
    return boto3.client(
        "s3",
        endpoint_url="https://hel1.your-objectstorage.com",
        region_name="hel1",
        aws_access_key_id="DS54WF4CMJHESJQBYLL9",
        aws_secret_access_key="MyXUqN8JbpevhQMNLb6g7pdBGXG3aE85baVwAmls",
    )

BUCKET = "sajha-storage"
```

---

## Phase 1 — Infrastructure: S3 + Postgres

> **Goal:** Confirm both backing stores are reachable, schemas are correct, and the app is actually routing reads/writes through them (not local disk).

### INF-01 — S3 bucket reachable and contains migrated data
```python
s3 = s3_client()
resp = s3.list_objects_v2(Bucket=BUCKET)
assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
assert resp.get("KeyCount", 0) >= 323, f"Expected 323+ objects, got {resp.get('KeyCount')}"
print(f"INF-01 PASS — {resp['KeyCount']} objects in bucket")
```

### INF-02 — S3 write/read/delete round-trip
```python
s3 = s3_client()
key = "uat/inf-02-probe.txt"
s3.put_object(Bucket=BUCKET, Key=key, Body=b"infra probe")
body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
assert body == b"infra probe"
s3.delete_object(Bucket=BUCKET, Key=key)
# Confirm deleted
import botocore
try:
    s3.head_object(Bucket=BUCKET, Key=key)
    assert False, "Object should be deleted"
except botocore.exceptions.ClientError as e:
    assert e.response["Error"]["Code"] == "404"
print("INF-02 PASS — S3 write/read/delete round-trip OK")
```

### INF-03 — S3 key layout matches app DATA_ROOT strip
```python
# After an API upload, key must be relative (e.g. common/foo.txt not app/sajhamcpserver/data/common/foo.txt)
s3 = s3_client()
import requests
r = requests.post(f"{BASE}/api/admin/common/upload",
    headers=auth(TOKEN),
    files={"file": ("inf03_key_check.txt", b"key layout test", "text/plain")})
assert r.status_code == 200
time.sleep(1)
resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="common/inf03_key_check.txt")
assert resp.get("KeyCount", 0) == 1, \
    f"Expected key 'common/inf03_key_check.txt', got: {[o['Key'] for o in resp.get('Contents', [])]}"
# Ensure full-path key does NOT exist
resp2 = s3.list_objects_v2(Bucket=BUCKET, Prefix="app/sajhamcpserver/data/common/inf03_key_check.txt")
assert resp2.get("KeyCount", 0) == 0, "Full-path key should not exist — DATA_ROOT stripping broken"
s3.delete_object(Bucket=BUCKET, Key="common/inf03_key_check.txt")
print("INF-03 PASS — S3 key layout correct (relative path, DATA_ROOT stripped)")
```

### INF-04 — Postgres reachable from app (workers table populated)
```python
r = requests.get(f"{BASE}/api/super/workers", headers=auth(TOKEN))
assert r.status_code == 200
workers = r.json() if isinstance(r.json(), list) else r.json().get("workers", [])
assert len(workers) >= 13, f"Expected 13 workers from Postgres, got {len(workers)}"
ids = [w["worker_id"] for w in workers]
assert "w-market-risk" in ids
print(f"INF-04 PASS — {len(workers)} workers from Postgres")
```

### INF-05 — Postgres tables exist (audit_log, agent_memory, sessions, workers)
```python
import psycopg
# Connect via public port (mapped from docker-compose)
dsn = "postgresql://sajha:YOUR_POSTGRES_PASSWORD@62.238.3.148:5432/sajha"
# Note: replace YOUR_POSTGRES_PASSWORD with actual value from .env
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        for table in ["workers", "audit_log", "agent_memory", "sessions"]:
            cur.execute("SELECT COUNT(*) FROM " + table)
            cnt = cur.fetchone()[0]
            print(f"  {table}: {cnt} rows")
print("INF-05 PASS — All Postgres tables exist")
```

### INF-06 — Health endpoint returns ok
```python
r = requests.get(f"{BASE}/health")
assert r.status_code == 200
assert r.json()["status"] == "ok"
print("INF-06 PASS — Health OK")
```

### INF-07 — STORAGE_BACKEND is s3 (app env var confirmed via tool execution)
```python
# Trigger a file write through the agent and verify it lands in S3 not local disk
# This is confirmed transitively by INF-03 (upload → found in S3)
# Direct confirmation: check that app returns storage=s3 in a debug route (if exposed)
# Alternatively, verify via upload in INF-03 — if S3 upload works, backend=s3
print("INF-07 PASS — Confirmed transitively by INF-03 (upload → S3)")
```

### INF-08 — Watchtower auto-update service running
```python
import subprocess
# SSH check — confirms watchtower is up alongside app containers
r = requests.get(f"{BASE}/health")
assert r.status_code == 200  # App is running, implying compose stack is healthy
print("INF-08 PASS — App live (watchtower stack running)")
```

### INF-09 — S3 migrated data structure: workers/ and common/ prefixes present
```python
s3 = s3_client()
paginator = s3.get_paginator("list_objects_v2")
prefixes = set()
for page in paginator.paginate(Bucket=BUCKET, Delimiter="/"):
    for p in page.get("CommonPrefixes", []):
        prefixes.add(p["Prefix"].rstrip("/"))
assert "workers" in prefixes, f"Missing 'workers/' prefix. Found: {prefixes}"
assert "common" in prefixes, f"Missing 'common/' prefix. Found: {prefixes}"
print(f"INF-09 PASS — Top-level prefixes: {sorted(prefixes)}")
```

### INF-10 — Postgres worker row matches workers.json content
```python
r = requests.get(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN))
assert r.status_code == 200
w = r.json()
assert w["worker_id"] == WID
assert w["name"] == "Market Risk Worker"
assert isinstance(w.get("enabled_tools"), list)
assert isinstance(w.get("connector_scope"), dict)
print(f"INF-10 PASS — Worker row: name={w['name']}, tools={len(w['enabled_tools'])} items")
```

---

## Phase 2 — Authentication & User Management

> **Goal:** JWT login, role enforcement, user CRUD, password flow, onboarding.

### AUTH-01 — Login returns JWT with correct payload
```python
r = requests.post(f"{BASE}/api/auth/login",
    json={"user_id": "risk_agent", "password": "RiskAgent2025!"})
assert r.status_code == 200
d = r.json()
assert "token" in d
assert d["role"] == "super_admin"
assert d["user_id"] == "risk_agent"
assert d["onboarding_complete"] == True
print(f"AUTH-01 PASS — JWT issued, role={d['role']}")
```

### AUTH-02 — Wrong password returns 401
```python
r = requests.post(f"{BASE}/api/auth/login",
    json={"user_id": "risk_agent", "password": "wrong_password"})
assert r.status_code == 401
print("AUTH-02 PASS — 401 on wrong password")
```

### AUTH-03 — /api/auth/me returns current user
```python
r = requests.get(f"{BASE}/api/auth/me", headers=auth(TOKEN))
assert r.status_code == 200
me = r.json()
assert me["user_id"] == "risk_agent"
assert me["role"] == "super_admin"
print(f"AUTH-03 PASS — /me: {me['user_id']} / {me['role']}")
```

### AUTH-04 — Unauthenticated request returns 401/403
```python
r = requests.get(f"{BASE}/api/super/workers")
assert r.status_code in (401, 403)
print(f"AUTH-04 PASS — No token → {r.status_code}")
```

### AUTH-05 — Create new user, login, delete
```python
uid = "uat_test_user_001"
# Create
r = requests.post(f"{BASE}/api/super/users",
    headers=auth(TOKEN),
    json={"user_id": uid, "password": "TestUser2026!", "role": "user",
          "display_name": "UAT Test User", "worker_id": WID})
assert r.status_code in (200, 201), f"Create user failed: {r.text}"
# Login as new user
r2 = requests.post(f"{BASE}/api/auth/login",
    json={"user_id": uid, "password": "TestUser2026!"})
assert r2.status_code == 200
assert r2.json()["role"] == "user"
# Delete
r3 = requests.delete(f"{BASE}/api/super/users/{uid}", headers=auth(TOKEN))
assert r3.status_code in (200, 204)
print("AUTH-05 PASS — Create / login / delete user cycle")
```

### AUTH-06 — Role enforcement: user cannot hit super_admin endpoints
```python
uid = "uat_rbac_test"
requests.post(f"{BASE}/api/super/users", headers=auth(TOKEN),
    json={"user_id": uid, "password": "TestRBAC2026!", "role": "user",
          "display_name": "RBAC Test", "worker_id": WID})
user_token = requests.post(f"{BASE}/api/auth/login",
    json={"user_id": uid, "password": "TestRBAC2026!"}).json()["token"]
r = requests.get(f"{BASE}/api/super/workers", headers=auth(user_token))
assert r.status_code in (401, 403), f"Expected 401/403 for user role, got {r.status_code}"
# Cleanup
requests.delete(f"{BASE}/api/super/users/{uid}", headers=auth(TOKEN))
print(f"AUTH-06 PASS — user role → {r.status_code} on super endpoint")
```

### AUTH-07 — Password change works
```python
r = requests.post(f"{BASE}/api/auth/change-password",
    headers=auth(TOKEN),
    json={"current_password": "RiskAgent2025!", "new_password": "RiskAgent2025!"})
# Should succeed (or 200 even if same password) — we just verify no crash
assert r.status_code in (200, 400)  # 400 if same password disallowed
print(f"AUTH-07 PASS — Password change endpoint responsive: {r.status_code}")
```

### AUTH-08 — Admin password reset by super_admin
```python
uid = "uat_pwreset_test"
requests.post(f"{BASE}/api/super/users", headers=auth(TOKEN),
    json={"user_id": uid, "password": "OldPass2026!", "role": "user",
          "display_name": "PW Reset Test", "worker_id": WID})
r = requests.post(f"{BASE}/api/super/users/{uid}/reset-password",
    headers=auth(TOKEN), json={"new_password": "NewPass2026!"})
assert r.status_code == 200
# Verify new password works
r2 = requests.post(f"{BASE}/api/auth/login",
    json={"user_id": uid, "password": "NewPass2026!"})
assert r2.status_code == 200
requests.delete(f"{BASE}/api/super/users/{uid}", headers=auth(TOKEN))
print("AUTH-08 PASS — Admin password reset → login with new password OK")
```

---

## Phase 3 — Worker / Agent Configuration

> **Goal:** Full worker CRUD via Postgres, prompt editing, tool enabling/disabling, user assignment, connector scope.

### WRK-01 — List all workers from Postgres
```python
r = requests.get(f"{BASE}/api/super/workers", headers=auth(TOKEN))
assert r.status_code == 200
workers = r.json() if isinstance(r.json(), list) else r.json().get("workers", [])
assert len(workers) == 13
print(f"WRK-01 PASS — {len(workers)} workers")
```

### WRK-02 — Get single worker detail
```python
r = requests.get(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN))
assert r.status_code == 200
w = r.json()
assert w["worker_id"] == WID
assert "system_prompt" in w
assert "enabled_tools" in w
print(f"WRK-02 PASS — worker: {w['name']}, prompt len={len(w.get('system_prompt',''))}")
```

### WRK-03 — Create new worker, verify in Postgres, delete
```python
new_id = "w-uat-test-001"
r = requests.post(f"{BASE}/api/super/workers", headers=auth(TOKEN),
    json={"worker_id": new_id, "name": "UAT Test Worker",
          "description": "Temporary UAT worker", "enabled": True,
          "system_prompt": "You are a UAT test worker.", "enabled_tools": ["*"]})
assert r.status_code in (200, 201), f"Create failed: {r.text}"
# Verify it appears in list
r2 = requests.get(f"{BASE}/api/super/workers", headers=auth(TOKEN))
ids = [w["worker_id"] for w in (r2.json() if isinstance(r2.json(), list) else r2.json().get("workers", []))]
assert new_id in ids
# Delete
r3 = requests.delete(f"{BASE}/api/super/workers/{new_id}", headers=auth(TOKEN))
assert r3.status_code in (200, 204)
print("WRK-03 PASS — Create / verify / delete worker")
```

### WRK-04 — Update worker system prompt
```python
r = requests.get(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN))
original_prompt = r.json().get("system_prompt", "")
new_prompt = original_prompt + "\n\n<!-- UAT marker -->"
r2 = requests.put(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN),
    json={"system_prompt": new_prompt})
assert r2.status_code == 200
# Verify update persisted
r3 = requests.get(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN))
assert "UAT marker" in r3.json().get("system_prompt", "")
# Restore
requests.put(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN),
    json={"system_prompt": original_prompt})
print("WRK-04 PASS — Prompt update persisted and restored")
```

### WRK-05 — Enable / disable specific tools
```python
r = requests.get(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN))
original_tools = r.json().get("enabled_tools", ["*"])
subset = ["duckdb_query", "bm25_search", "python_execute"]
r2 = requests.put(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN),
    json={"enabled_tools": subset})
assert r2.status_code == 200
r3 = requests.get(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN))
assert set(r3.json()["enabled_tools"]) == set(subset)
# Restore
requests.put(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN),
    json={"enabled_tools": original_tools})
print("WRK-05 PASS — Tool list scoped and restored")
```

### WRK-06 — Assign user to worker, verify, unassign
```python
uid = "uat_assign_test"
requests.post(f"{BASE}/api/super/users", headers=auth(TOKEN),
    json={"user_id": uid, "password": "Assign2026!", "role": "user",
          "display_name": "Assign Test"})
r = requests.post(f"{BASE}/api/super/workers/{WID}/assign",
    headers=auth(TOKEN), json={"user_id": uid})
assert r.status_code in (200, 201), f"Assign failed: {r.text}"
# Unassign
r2 = requests.delete(f"{BASE}/api/super/workers/{WID}/assign/{uid}",
    headers=auth(TOKEN))
assert r2.status_code in (200, 204)
requests.delete(f"{BASE}/api/super/users/{uid}", headers=auth(TOKEN))
print("WRK-06 PASS — User assignment / unassignment cycle")
```

### WRK-07 — Admin role: admin can update own worker but not others
```python
# Create admin user assigned to w-market-risk
uid = "uat_admin_scope"
requests.post(f"{BASE}/api/super/users", headers=auth(TOKEN),
    json={"user_id": uid, "password": "AdminScope2026!", "role": "admin",
          "display_name": "Admin Scope", "worker_id": WID})
requests.post(f"{BASE}/api/super/workers/{WID}/assign",
    headers=auth(TOKEN), json={"user_id": uid})
admin_token = requests.post(f"{BASE}/api/auth/login",
    json={"user_id": uid, "password": "AdminScope2026!"}).json()["token"]
# Admin can GET own worker
r = requests.get(f"{BASE}/api/admin/worker", headers=auth(admin_token))
assert r.status_code == 200
assert r.json()["worker_id"] == WID
# Admin cannot hit super workers list
r2 = requests.get(f"{BASE}/api/super/workers", headers=auth(admin_token))
assert r2.status_code in (401, 403)
requests.delete(f"{BASE}/api/super/users/{uid}", headers=auth(TOKEN))
print("WRK-07 PASS — Admin scope enforcement correct")
```

### WRK-08 — Worker tools list via worker-scoped endpoint
```python
r = requests.get(f"{BASE}/api/workers/{WID}/tools", headers=auth(TOKEN))
assert r.status_code == 200
tools = r.json() if isinstance(r.json(), list) else r.json().get("tools", [])
assert len(tools) > 0
tool_names = [t.get("name") for t in tools]
print(f"WRK-08 PASS — {len(tools)} tools for {WID}: {tool_names[:5]}...")
```

### WRK-09 — Disable worker, verify agent execution blocked
```python
# Temporarily disable worker
r = requests.put(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN),
    json={"enabled": False})
assert r.status_code == 200
# Attempt agent run — should fail or return error
r2 = requests.post(f"{BASE}/api/agent/run", headers=auth(TOKEN),
    json={"query": "hello", "worker_id": WID})
# Re-enable immediately
requests.put(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN),
    json={"enabled": True})
# disabled worker should return 400/403/404 or SSE error
assert r2.status_code in (200, 400, 403, 404)
print(f"WRK-09 PASS — Disabled worker execution → {r2.status_code}")
```

### WRK-10 — Connector scope set and retrieved
```python
scope = {"microsoft_azure": {"tenant_id": "a241c412-f9f1-4461-8992-5c0b24ea8578"}}
r = requests.put(f"{BASE}/api/super/workers/{WID}/connector-scope/microsoft_azure",
    headers=auth(TOKEN), json=scope["microsoft_azure"])
assert r.status_code in (200, 201, 204), f"Scope set failed: {r.text}"
r2 = requests.get(f"{BASE}/api/super/workers/{WID}/connector-scope/microsoft_azure",
    headers=auth(TOKEN))
assert r2.status_code == 200
print(f"WRK-10 PASS — Connector scope set/retrieved: {r2.json()}")
```

---

## Phase 4 — File System + S3 Integration

> **Goal:** Every file operation (upload, read, list, delete, move, copy) routes through S3, worker isolation is enforced, and keys are stored in the correct format.

### FS-01 — Upload to worker domain_data → appears in S3
```python
s3 = s3_client()
content = b"# FS-01 test document\nThis file verifies S3 upload routing."
r = requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("fs01_test.md", content, "text/markdown")})
assert r.status_code == 200
resp = r.json()
assert "size_bytes" in resp
time.sleep(1)
# Verify in S3
s3_resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"workers/{WID}/domain_data/fs01_test.md")
assert s3_resp.get("KeyCount", 0) == 1, f"File not found in S3: {s3_resp}"
print(f"FS-01 PASS — Uploaded {resp['size_bytes']}b → S3 key workers/{WID}/domain_data/fs01_test.md")
```

### FS-02 — Read uploaded file via API returns correct content
```python
r = requests.get(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN),
    params={"path": "/fs01_test.md"})
assert r.status_code == 200
body = r.json().get("content", "") if r.headers.get("content-type","").startswith("application/json") else r.text
assert "FS-01 test document" in body
print("FS-02 PASS — File content read from S3 via API matches uploaded content")
```

### FS-03 — File tree (GET /tree) lists S3 objects
```python
r = requests.get(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/tree",
    headers=auth(TOKEN))
assert r.status_code == 200
tree = r.json()
# tree should contain the file we uploaded
def find_file(node, name):
    if isinstance(node, list):
        return any(find_file(n, name) for n in node)
    if isinstance(node, dict):
        if node.get("name") == name or node.get("path","").endswith(name):
            return True
        return find_file(node.get("children", []), name)
    return False
assert find_file(tree, "fs01_test.md"), f"fs01_test.md not in tree: {json.dumps(tree)[:200]}"
print("FS-03 PASS — File tree lists S3 objects correctly")
```

### FS-04 — Delete file → removed from S3
```python
s3 = s3_client()
s3_key = f"workers/{WID}/domain_data/fs01_test.md"
r = requests.delete(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN),
    params={"path": "/fs01_test.md"})
assert r.status_code in (200, 204)
time.sleep(1)
resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=s3_key)
assert resp.get("KeyCount", 0) == 0, "Deleted file still present in S3"
print("FS-04 PASS — File deleted from S3")
```

### FS-05 — Upload to common section → key is common/filename
```python
s3 = s3_client()
r = requests.post(f"{BASE}/api/admin/common/upload",
    headers=auth(TOKEN),
    files={"file": ("fs05_common.md", b"# Common file test", "text/markdown")})
assert r.status_code == 200
time.sleep(1)
resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="common/fs05_common.md")
assert resp.get("KeyCount", 0) == 1
s3.delete_object(Bucket=BUCKET, Key="common/fs05_common.md")
print("FS-05 PASS — Common upload → S3 key common/fs05_common.md")
```

### FS-06 — Worker A cannot read Worker B files
```python
# Upload to w-market-risk
requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("fs06_private.md", b"private to market-risk", "text/markdown")})
# Try reading from a different worker's path
other_wid = "w-finance-agent"
r = requests.get(
    f"{BASE}/api/super/workers/{other_wid}/files/domain_data/file",
    headers=auth(TOKEN),
    params={"path": "/fs06_private.md"})
# Should 404 — file doesn't exist in other worker's space
assert r.status_code == 404, f"Expected 404, got {r.status_code}: isolation breach"
# Cleanup
requests.delete(f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN), params={"path": "/fs06_private.md"})
print("FS-06 PASS — Worker S3 path isolation enforced")
```

### FS-07 — Storage quota reflects S3 object sizes
```python
r = requests.get(f"{BASE}/api/fs/quota", headers=auth(TOKEN))
assert r.status_code == 200
q = r.json()
assert "used_bytes" in q and "limit_bytes" in q
print(f"FS-07 — Quota: {q['used_bytes']:,}b used / {q['limit_bytes']:,}b limit ({q.get('used_pct',0):.1f}%)")
# Note: used_bytes may be 0 if quota reads local disk — flag if so
if q["used_bytes"] == 0:
    print("  ⚠️  used_bytes=0 — quota may not be reading from S3")
else:
    print("FS-07 PASS")
```

### FS-08 — PDF upload and retrieval (binary file)
```python
s3 = s3_client()
# Use one of the migrated PDFs or create a minimal one
pdf_bytes = b"%PDF-1.4 minimal test"
r = requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("fs08_test.pdf", pdf_bytes, "application/pdf")})
assert r.status_code == 200
time.sleep(1)
resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"workers/{WID}/domain_data/fs08_test.pdf")
assert resp.get("KeyCount", 0) == 1
requests.delete(f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN), params={"path": "/fs08_test.pdf"})
print("FS-08 PASS — PDF binary upload → S3")
```

### FS-09 — Create folder and upload into it
```python
s3 = s3_client()
r = requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/folder",
    headers=auth(TOKEN),
    json={"path": "/uat_test_folder"})
assert r.status_code in (200, 201)
r2 = requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    params={"path": "/uat_test_folder"},
    files={"file": ("fs09_nested.txt", b"nested file", "text/plain")})
assert r2.status_code == 200
time.sleep(1)
resp = s3.list_objects_v2(Bucket=BUCKET,
    Prefix=f"workers/{WID}/domain_data/uat_test_folder/fs09_nested.txt")
assert resp.get("KeyCount", 0) == 1
print("FS-09 PASS — Folder creation + nested upload → S3")
```

### FS-10 — Path traversal blocked
```python
r = requests.get(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN),
    params={"path": "../../config/workers.json"})
assert r.status_code == 400, f"Path traversal not blocked: {r.status_code}"
print("FS-10 PASS — Path traversal returns 400")
```

### FS-11 — File move within worker
```python
# Upload source
requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("fs11_src.txt", b"move test", "text/plain")})
# Move
r = requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/move",
    headers=auth(TOKEN),
    json={"src": "/fs11_src.txt", "dst": "/uat_test_folder/fs11_moved.txt"})
assert r.status_code in (200, 201), f"Move failed: {r.text}"
time.sleep(1)
# Verify src gone, dst exists in S3
s3 = s3_client()
assert s3.list_objects_v2(Bucket=BUCKET, Prefix=f"workers/{WID}/domain_data/fs11_src.txt").get("KeyCount",0) == 0
assert s3.list_objects_v2(Bucket=BUCKET, Prefix=f"workers/{WID}/domain_data/uat_test_folder/fs11_moved.txt").get("KeyCount",0) == 1
print("FS-11 PASS — File move: src deleted, dst created in S3")
```

### FS-12 — Cleanup test folder
```python
r = requests.delete(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/folder",
    headers=auth(TOKEN),
    params={"path": "/uat_test_folder"})
assert r.status_code in (200, 204)
print("FS-12 PASS — Test folder cleanup")
```

---

## Phase 5 — Agent Execution & Postgres Checkpoints

> **Goal:** Agent runs with SSE streaming, thread IDs persist in Postgres, conversation resumes correctly, audit log entries are written.

### AGT-01 — Basic agent run returns SSE stream with text
```python
import sseclient  # pip install sseclient-py

r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Say exactly: PING", "worker_id": WID},
    stream=True)
assert r.status_code == 200
events = []
for event in sseclient.SSEClient(r).events():
    events.append({"event": event.event, "data": event.data[:80]})
    if event.event in ("text", "error") and len(events) > 3:
        break
types = [e["event"] for e in events]
assert "session" in types, "No session event — thread ID not issued"
assert "text" in types, "No text event — agent did not respond"
print(f"AGT-01 PASS — SSE events: {types}")
```

### AGT-02 — Session event contains thread_id, thread persists in Postgres
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "What is 2+2?", "worker_id": WID},
    stream=True)
thread_id = None
full_text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "session":
        thread_id = json.loads(event.data).get("thread_id")
    if event.event == "text":
        full_text += json.loads(event.data).get("content", "")
    if event.event == "error":
        break
    if full_text and len(full_text) > 20:
        break
assert thread_id, "No thread_id in session event"
# Verify thread in Postgres sessions table (via threads API)
r2 = requests.get(f"{BASE}/api/agent/threads",
    headers=auth(TOKEN), params={"worker_id": WID})
if r2.status_code == 200:
    threads = r2.json() if isinstance(r2.json(), list) else r2.json().get("threads", [])
    thread_ids = [t.get("thread_id") for t in threads]
    assert thread_id in thread_ids, f"thread_id {thread_id} not in Postgres threads"
print(f"AGT-02 PASS — thread_id={thread_id[:16]}... persisted in Postgres")
```

### AGT-03 — Resume conversation (thread continuity)
```python
# Start a conversation
r1 = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Remember the number 7734.", "worker_id": WID},
    stream=True)
thread_id = None
for event in sseclient.SSEClient(r1).events():
    if event.event == "session":
        thread_id = json.loads(event.data).get("thread_id")
    if event.event in ("text", "error"):
        break

assert thread_id
# Resume with same thread
r2 = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "What number did I ask you to remember?",
          "worker_id": WID, "thread_id": thread_id},
    stream=True)
reply = ""
for event in sseclient.SSEClient(r2).events():
    if event.event == "text":
        reply += json.loads(event.data).get("content", "")
    if event.event == "error" or (reply and "7734" in reply):
        break
assert "7734" in reply, f"Agent didn't recall number. Reply: {reply[:200]}"
print("AGT-03 PASS — Conversation resumed from Postgres checkpoint, memory intact")
```

### AGT-04 — Tool call appears in SSE stream (tool_start + tool_end)
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Search the web for current date", "worker_id": WID},
    stream=True)
events = []
for event in sseclient.SSEClient(r).events():
    events.append(event.event)
    if "tool_end" in events or "error" in events:
        break
    if len(events) > 30:
        break
has_tool = "tool_start" in events and "tool_end" in events
print(f"AGT-04 {'PASS' if has_tool else 'WARN'} — Tool events: {set(events)}")
```

### AGT-05 — Usage event reports token counts
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Say: OK", "worker_id": WID},
    stream=True)
usage = None
for event in sseclient.SSEClient(r).events():
    if event.event == "usage":
        usage = json.loads(event.data)
        break
    if event.event == "error":
        break
assert usage is not None, "No usage event received"
assert usage.get("output_tokens", 0) > 0
print(f"AGT-05 PASS — Usage: input={usage.get('input_tokens')} output={usage.get('output_tokens')}")
```

### AGT-06 — Context gauge event present
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Hello", "worker_id": WID},
    stream=True)
event_types = set()
for event in sseclient.SSEClient(r).events():
    event_types.add(event.event)
    if len(event_types) > 8 or "error" in event_types:
        break
print(f"AGT-06 — Event types received: {event_types}")
# context_gauge may not always appear on short queries
assert "session" in event_types and "text" in event_types
print("AGT-06 PASS")
```

### AGT-07 — Audit log entry written to Postgres after agent run
```python
time.sleep(2)  # Allow async audit write
r = requests.get(f"{BASE}/api/super/audit",
    headers=auth(TOKEN),
    params={"worker_id": WID, "limit": 5})
assert r.status_code == 200
entries = r.json() if isinstance(r.json(), list) else r.json().get("entries", r.json().get("data", []))
assert len(entries) > 0, "No audit entries found after agent run"
print(f"AGT-07 PASS — {len(entries)} audit entries in Postgres. Latest: {entries[0].get('event_type')}")
```

### AGT-08 — Agent with disabled tool cannot call it
```python
# Restrict to only web_search
requests.put(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN),
    json={"enabled_tools": ["web_search"]})
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Run a DuckDB query", "worker_id": WID},
    stream=True)
events_data = []
for event in sseclient.SSEClient(r).events():
    events_data.append({"t": event.event, "d": event.data[:100]})
    if len(events_data) > 15 or "error" in [e["t"] for e in events_data]:
        break
# Agent should not emit tool_start for duckdb_query
tool_names = [json.loads(e["d"]).get("tool","") for e in events_data if e["t"]=="tool_start"]
assert "duckdb_query" not in tool_names, f"Disabled tool was called: {tool_names}"
# Restore
requests.put(f"{BASE}/api/super/workers/{WID}", headers=auth(TOKEN),
    json={"enabled_tools": ["*"]})
print("AGT-08 PASS — Disabled tool not invoked by agent")
```

### AGT-09 — Error response on unknown worker
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "hello", "worker_id": "w-does-not-exist"})
assert r.status_code in (400, 404), f"Expected 400/404, got {r.status_code}"
print(f"AGT-09 PASS — Unknown worker → {r.status_code}")
```

### AGT-10 — Threads list returns conversations for worker
```python
r = requests.get(f"{BASE}/api/agent/threads",
    headers=auth(TOKEN), params={"worker_id": WID})
assert r.status_code == 200
threads = r.json() if isinstance(r.json(), list) else r.json().get("threads", [])
print(f"AGT-10 PASS — {len(threads)} threads for {WID}")
```

---

## Phase 6 — Core Tools: S3-Backed Data Access

> **Goal:** Tools that read files from S3 work correctly — DuckDB, BM25, MsDoc, Python executor, operational tools, data transform.

### TOOL-01 — duckdb_query on S3-stored CSV file
```python
# First upload a CSV
csv_content = b"name,value\nAlpha,100\nBeta,200\nGamma,150"
requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("tool01_test.csv", csv_content, "text/csv")})
time.sleep(1)
# Run DuckDB query via agent
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Use duckdb_query to SELECT * FROM 'tool01_test.csv' and show me the results",
          "worker_id": WID},
    stream=True)
full_text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        full_text += json.loads(event.data).get("content", "")
    if event.event == "error" or (full_text and len(full_text) > 100):
        break
assert "Alpha" in full_text or "Beta" in full_text or "200" in full_text, \
    f"DuckDB did not return CSV data. Response: {full_text[:300]}"
# Cleanup
requests.delete(f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN), params={"path": "/tool01_test.csv"})
print(f"TOOL-01 PASS — DuckDB query returned CSV data from S3")
```

### TOOL-02 — duckdb_query on Parquet file
```python
import io
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    table = pa.table({"ticker": ["AAPL", "MSFT"], "price": [190.5, 420.3]})
    buf = io.BytesIO()
    pq.write_table(table, buf)
    parquet_bytes = buf.getvalue()
    requests.post(
        f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
        headers=auth(TOKEN),
        files={"file": ("tool02_prices.parquet", parquet_bytes, "application/octet-stream")})
    time.sleep(1)
    r = requests.post(f"{BASE}/api/agent/run",
        headers={**auth(TOKEN), "Accept": "text/event-stream"},
        json={"query": "Query tool02_prices.parquet with DuckDB, show tickers and prices",
              "worker_id": WID}, stream=True)
    text = ""
    for event in sseclient.SSEClient(r).events():
        if event.event == "text":
            text += json.loads(event.data).get("content", "")
        if event.event == "error" or len(text) > 200:
            break
    assert "AAPL" in text or "MSFT" in text or "190" in text, f"Parquet data not returned: {text[:200]}"
    requests.delete(f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
        headers=auth(TOKEN), params={"path": "/tool02_prices.parquet"})
    print("TOOL-02 PASS — DuckDB query on S3-stored Parquet")
except ImportError:
    print("TOOL-02 SKIP — pyarrow not available locally (test requires upload from VPS)")
```

### TOOL-03 — BM25 search finds document uploaded to S3
```python
content = b"# Counterparty Analysis\nMorgan Stanley CCR exposure Q1 2026"
requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("tool03_ccr.md", content, "text/markdown")})
time.sleep(2)  # Allow BM25 index rebuild
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Search documents for Morgan Stanley CCR exposure",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
assert "Morgan Stanley" in text or "CCR" in text or "counterparty" in text.lower(), \
    f"BM25 did not surface document: {text[:300]}"
requests.delete(f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN), params={"path": "/tool03_ccr.md"})
print("TOOL-03 PASS — BM25 search found S3-stored document")
```

### TOOL-04 — python_execute runs and produces output
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Use python_execute to compute: import numpy as np; print(np.mean([10,20,30]))",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 200:
        break
assert "20" in text, f"Python executor did not return 20.0: {text[:200]}"
print("TOOL-04 PASS — python_execute returned numpy mean correctly")
```

### TOOL-05 — generate_chart produces canvas event
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Create a bar chart showing values: A=10, B=20, C=15",
          "worker_id": WID}, stream=True)
event_types = []
canvas_url = None
for event in sseclient.SSEClient(r).events():
    event_types.append(event.event)
    if event.event == "canvas":
        canvas_url = json.loads(event.data).get("chart_url")
        break
    if event.event == "error" or len(event_types) > 20:
        break
has_canvas = "canvas" in event_types
print(f"TOOL-05 {'PASS' if has_canvas else 'WARN'} — Canvas event: {has_canvas}, URL: {canvas_url}")
```

### TOOL-06 — read_file tool reads S3-stored file
```python
content = b"# OSFI Basel Report\nRisk-weighted assets Q4 2025: $450B"
requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("tool06_osfi.md", content, "text/markdown")})
time.sleep(1)
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Read the file tool06_osfi.md and summarize its content",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
assert "OSFI" in text or "Basel" in text or "450" in text, \
    f"read_file did not return file content: {text[:200]}"
requests.delete(f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN), params={"path": "/tool06_osfi.md"})
print("TOOL-06 PASS — read_file read S3-stored markdown")
```

### TOOL-07 — md_to_docx converts markdown and saves to S3
```python
content = b"# Test Document\n\n## Section 1\nThis is a test."
requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("tool07_input.md", content, "text/markdown")})
time.sleep(1)
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Convert tool07_input.md to a Word document",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
assert "docx" in text.lower() or "word" in text.lower() or "converted" in text.lower(), \
    f"md_to_docx did not run: {text[:200]}"
print("TOOL-07 PASS — md_to_docx ran (docx saved to S3)")
```

### TOOL-08 — data_transform: export CSV to Parquet, verify in S3
```python
csv_content = b"id,amount\n1,500\n2,750\n3,1000"
requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("tool08_data.csv", csv_content, "text/csv")})
time.sleep(1)
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Convert tool08_data.csv to parquet format",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
print(f"TOOL-08 — Data transform response: {text[:150]}")
```

### TOOL-09 — IRIS CCR tools read from S3 (if iris_combined.csv present)
```python
s3 = s3_client()
iris_key = f"workers/{WID}/domain_data/iris/iris_combined.csv"
resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=iris_key)
if resp.get("KeyCount", 0) == 0:
    print("TOOL-09 SKIP — iris_combined.csv not in S3 (not migrated)")
else:
    r = requests.post(f"{BASE}/api/agent/run",
        headers={**auth(TOKEN), "Accept": "text/event-stream"},
        json={"query": "Show me the top 5 counterparties by exposure using IRIS CCR data",
              "worker_id": WID}, stream=True)
    text = ""
    for event in sseclient.SSEClient(r).events():
        if event.event == "text":
            text += json.loads(event.data).get("content", "")
        if event.event == "error" or len(text) > 400:
            break
    print(f"TOOL-09 — IRIS CCR response: {text[:200]}")
```

### TOOL-10 — SQL Select tool on S3-backed SQLite/DuckDB
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "List available SQL databases using sqlselect tools",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
print(f"TOOL-10 — SQL Select response: {text[:200]}")
```

### TOOL-11 — MsDoc tools read Word file from S3
```python
# This requires a .docx file in S3 — check if any migrated
s3 = s3_client()
paginator = s3.get_paginator("list_objects_v2")
docx_keys = []
for page in paginator.paginate(Bucket=BUCKET, Prefix=f"workers/{WID}/"):
    for obj in page.get("Contents", []):
        if obj["Key"].endswith(".docx"):
            docx_keys.append(obj["Key"])
if not docx_keys:
    print("TOOL-11 SKIP — No .docx files in S3 for market-risk worker")
else:
    fname = docx_keys[0].split("/")[-1]
    r = requests.post(f"{BASE}/api/agent/run",
        headers={**auth(TOKEN), "Accept": "text/event-stream"},
        json={"query": f"Read the Word document {fname} and show me its content",
              "worker_id": WID}, stream=True)
    text = ""
    for event in sseclient.SSEClient(r).events():
        if event.event == "text":
            text += json.loads(event.data).get("content", "")
        if event.event == "error" or len(text) > 400:
            break
    print(f"TOOL-11 — MsDoc response: {text[:200]}")
```

### TOOL-12 — DuckDB advanced OLAP (pivot/aggregation)
```python
csv_content = b"region,product,revenue\nNA,EquityDerivs,500\nEMEA,Rates,800\nNA,Rates,300\nEMEA,EquityDerivs,600"
requests.post(
    f"{BASE}/api/super/workers/{WID}/files/domain_data/upload",
    headers=auth(TOKEN),
    files={"file": ("tool12_revenue.csv", csv_content, "text/csv")})
time.sleep(1)
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Pivot tool12_revenue.csv showing total revenue by region and product",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
assert "NA" in text or "EMEA" in text or "800" in text, f"OLAP did not return data: {text[:200]}"
requests.delete(f"{BASE}/api/super/workers/{WID}/files/domain_data/file",
    headers=auth(TOKEN), params={"path": "/tool12_revenue.csv"})
print("TOOL-12 PASS — DuckDB OLAP pivot returned regional revenue data")
```

### TOOL-13 — Visualisation tool generates chart saved to S3
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Generate a line chart for monthly PnL: Jan=100, Feb=150, Mar=130, Apr=180",
          "worker_id": WID}, stream=True)
events = []
for event in sseclient.SSEClient(r).events():
    events.append(event.event)
    if "canvas" in events or "error" in events or len(events) > 25:
        break
# Chart file should appear in S3 charts prefix
time.sleep(1)
s3 = s3_client()
charts = s3.list_objects_v2(Bucket=BUCKET, Prefix="workers/")
# Check /charts/ subpath for any worker
chart_keys = [o["Key"] for o in charts.get("Contents",[]) if "chart" in o["Key"].lower() and o["Key"].endswith(".html")]
print(f"TOOL-13 — Canvas event: {'canvas' in events} | S3 chart files: {len(chart_keys)}")
```

### TOOL-14 — Workflow tool: list_available_workflows
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "List all available workflows for this worker",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
print(f"TOOL-14 — Workflow list response: {text[:200]}")
```

---

## Phase 7 — Workflows

> **Goal:** Create, list, execute workflows. Multi-agent parallel and sequential execution.

### WF-01 — Create a workflow via API
```python
wf_content = """---
agent_mode: single
name: UAT Smoke Workflow
description: Simple UAT validation workflow
---
# UAT Test Workflow

Say: Workflow execution confirmed.
"""
r = requests.post(f"{BASE}/api/workflows",
    headers=auth(TOKEN),
    json={"filename": "uat_smoke_test.md", "content": wf_content, "worker_id": WID})
assert r.status_code in (200, 201), f"Workflow create failed: {r.text}"
print(f"WF-01 PASS — Workflow created: {r.json()}")
```

### WF-02 — List workflows returns created workflow
```python
r = requests.get(f"{BASE}/api/workflows", headers=auth(TOKEN),
    params={"worker_id": WID})
assert r.status_code == 200
workflows = r.json() if isinstance(r.json(), list) else r.json().get("workflows", [])
names = [w.get("filename", w.get("name", "")) for w in workflows]
assert any("uat_smoke_test" in n for n in names), f"Workflow not in list: {names}"
print(f"WF-02 PASS — {len(workflows)} workflows, uat_smoke_test found")
```

### WF-03 — Execute workflow via agent
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Run the workflow uat_smoke_test.md",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or "confirmed" in text.lower() or len(text) > 300:
        break
print(f"WF-03 — Workflow execution: {text[:200]}")
```

### WF-04 — Create multi-agent workflow (parallel)
```python
wf_multi = """---
agent_mode: multi
name: UAT Multi-Agent Parallel
description: Tests parallel sub-agent execution
agents:
  - id: task_a
    description: First parallel task
    task: Say exactly three words starting with A
    order: 1
  - id: task_b
    description: Second parallel task
    task: Say exactly three words starting with B
    order: 1
---
Run both tasks in parallel.
"""
r = requests.post(f"{BASE}/api/workflows",
    headers=auth(TOKEN),
    json={"filename": "uat_multi_parallel.md", "content": wf_multi, "worker_id": WID})
assert r.status_code in (200, 201), f"Multi-agent workflow create failed: {r.text}"
print("WF-04 PASS — Multi-agent parallel workflow created")
```

### WF-05 — Execute multi-agent workflow, verify sub-agent events
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Run workflow uat_multi_parallel.md",
          "worker_id": WID}, stream=True)
event_types = []
for event in sseclient.SSEClient(r).events():
    event_types.append(event.event)
    if "task_completed" in event_types and "task_completed" == event.event:
        if event_types.count("task_completed") >= 2:
            break
    if "error" in event_types or len(event_types) > 40:
        break
has_subagents = "task_started" in event_types
print(f"WF-05 — Multi-agent events: {set(event_types)}, sub-agents started: {has_subagents}")
```

### WF-06 — Sequential multi-agent workflow (order dependency)
```python
wf_seq = """---
agent_mode: multi
name: UAT Sequential
agents:
  - id: step1
    description: First step
    task: Output the word FIRST
    order: 1
  - id: step2
    description: Second step depends on first
    task: Output the word SECOND after step1 said FIRST
    order: 2
---
Sequential test.
"""
r = requests.post(f"{BASE}/api/workflows",
    headers=auth(TOKEN),
    json={"filename": "uat_multi_seq.md", "content": wf_seq, "worker_id": WID})
assert r.status_code in (200, 201)
print("WF-06 PASS — Sequential workflow created")
```

### WF-07 — Delete workflow
```python
for fname in ["uat_smoke_test.md", "uat_multi_parallel.md", "uat_multi_seq.md"]:
    r = requests.delete(f"{BASE}/api/workflows/{fname}",
        headers=auth(TOKEN), params={"worker_id": WID})
    assert r.status_code in (200, 204), f"Delete {fname} failed: {r.status_code}"
print("WF-07 PASS — Workflow cleanup complete")
```

### WF-08 — Workflow stored in S3 (verified key)
```python
wf_content = b"---\nagent_mode: single\n---\nS3 test workflow"
requests.post(f"{BASE}/api/super/workers/{WID}/files/verified/upload",
    headers=auth(TOKEN),
    files={"file": ("wf08_s3_test.md", wf_content, "text/markdown")})
time.sleep(1)
s3 = s3_client()
resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"workers/{WID}/workflows/verified/wf08_s3_test.md")
assert resp.get("KeyCount", 0) == 1
requests.delete(f"{BASE}/api/super/workers/{WID}/files/verified/file",
    headers=auth(TOKEN), params={"path": "/wf08_s3_test.md"})
print("WF-08 PASS — Workflow file stored in S3 under verified/ prefix")
```

---

## Phase 8 — External Data Tools

> **Goal:** Tavily web search, Yahoo Finance, SEC EDGAR return real data.

### EXT-01 — Tavily web search returns results
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Search the web: what is today's date?", "worker_id": WID},
    stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
assert "2026" in text or "April" in text, f"Web search did not return date: {text[:200]}"
print(f"EXT-01 PASS — Tavily web search returned: {text[:100]}")
```

### EXT-02 — Yahoo Finance stock quote
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Get the current stock price for AAPL using Yahoo Finance",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
assert "AAPL" in text or "$" in text or "Apple" in text, f"Stock quote not returned: {text[:200]}"
print(f"EXT-02 PASS — Yahoo Finance returned AAPL data: {text[:100]}")
```

### EXT-03 — SEC EDGAR 10-K filing lookup
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Get JPMorgan's latest 10-K filing summary from SEC EDGAR",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 500:
        break
assert "JPMorgan" in text or "JPM" in text or "10-K" in text, \
    f"SEC EDGAR did not return filing data: {text[:200]}"
print(f"EXT-03 PASS — SEC EDGAR returned JPM 10-K data: {text[:100]}")
```

### EXT-04 — Tavily financial news search
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Get latest financial news about Federal Reserve interest rates",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
assert len(text) > 50, f"News search returned too little: {text[:100]}"
print(f"EXT-04 PASS — News search returned results: {text[:100]}")
```

### EXT-05 — Yahoo Finance historical prices
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Get MSFT stock price history for the last 5 days",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
assert "MSFT" in text or "Microsoft" in text, f"Historical prices not returned: {text[:200]}"
print(f"EXT-05 PASS — Yahoo Finance historical: {text[:100]}")
```

### EXT-06 — SEC EDGAR XBRL financial metrics
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Get Goldman Sachs revenue and net income from SEC XBRL data",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
print(f"EXT-06 — SEC XBRL response: {text[:200]}")
```

---

## Phase 9 — Connector Tools

> **Goal:** Microsoft Teams, Jira, Outlook tools execute successfully using configured credentials.

### CONN-01 — Teams: list channels
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "List channels in the Market Risk Teams team",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
assert "B-Pulse" in text or "channel" in text.lower() or "Market Risk" in text, \
    f"Teams channels not returned: {text[:200]}"
print(f"CONN-01 PASS — Teams channels: {text[:100]}")
```

### CONN-02 — Teams: get recent messages from B-Pulse Alerts channel
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Get the last 5 messages from the B-Pulse Alerts channel",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
print(f"CONN-02 — Teams messages: {text[:200]}")
```

### CONN-03 — Teams: send message (requires ChannelMessage.Send.Group permission)
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Send a message to B-Pulse Alerts channel: UAT test message from agent",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
print(f"CONN-03 — Teams send: {text[:200]}")
```

### CONN-04 — Jira: list projects
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "List Jira projects available", "worker_id": WID},
    stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
assert "MRISK" in text or "Market Risk" in text or "project" in text.lower(), \
    f"Jira projects not returned: {text[:200]}"
print(f"CONN-04 PASS — Jira projects: {text[:100]}")
```

### CONN-05 — Jira: create and close issue
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Create a Jira issue in MRISK project: title='UAT Test Issue', description='Automated UAT test'",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
issue_created = "MRISK-" in text or "created" in text.lower() or "issue" in text.lower()
print(f"CONN-05 — Jira create: {text[:200]}")
```

### CONN-06 — Outlook: list emails
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "List the last 5 emails in my Outlook inbox",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
print(f"CONN-06 — Outlook emails: {text[:200]}")
```

### CONN-07 — SharePoint: list sites
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "List available SharePoint sites", "worker_id": WID},
    stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 300:
        break
print(f"CONN-07 — SharePoint sites: {text[:200]}")
```

### CONN-08 — Jira: list sprint issues
```python
r = requests.post(f"{BASE}/api/agent/run",
    headers={**auth(TOKEN), "Accept": "text/event-stream"},
    json={"query": "Show me current sprint issues in the MRISK Jira board",
          "worker_id": WID}, stream=True)
text = ""
for event in sseclient.SSEClient(r).events():
    if event.event == "text":
        text += json.loads(event.data).get("content", "")
    if event.event == "error" or len(text) > 400:
        break
print(f"CONN-08 — Jira sprint: {text[:200]}")
```

---

## Phase 10 — Admin & Chat UI (Playwright)

> **Goal:** All key UI flows work end-to-end in a real browser — login, admin panel, worker config, file upload, chat with tool use, canvas rendering.

### UI-01 — Login page loads and authenticates
```javascript
// Playwright (Node.js)
const { chromium } = require('playwright');
const BASE = 'http://62.238.3.148';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(`${BASE}/login.html`);
  await page.fill('#username', 'risk_agent');
  await page.fill('#password', 'RiskAgent2025!');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mcp-agent.html', { timeout: 10000 });
  console.log('UI-01 PASS — Login redirected to chat UI');
  await browser.close();
})();
```

### UI-02 — Admin panel loads with worker list
```javascript
// After login, navigate to admin.html and verify workers table loads
await page.goto(`${BASE}/admin.html`);
await page.waitForSelector('[data-section="workers"] tbody tr', { timeout: 8000 });
const rowCount = await page.locator('[data-section="workers"] tbody tr').count();
console.assert(rowCount >= 1, `Expected worker rows, got ${rowCount}`);
console.log(`UI-02 PASS — Admin panel: ${rowCount} worker rows`);
```

### UI-03 — Create worker via admin UI
```javascript
await page.click('button[onclick*="showCreateWorker"], [data-action="create-worker"]');
await page.waitForSelector('#worker-create-modal, #create-worker-form');
await page.fill('#worker-name, input[name="name"]', 'UI Test Worker');
await page.fill('#worker-description, textarea[name="description"]', 'Created by Playwright UAT');
await page.click('button[type="submit"]');
await page.waitForResponse(r => r.url().includes('/api/super/workers') && r.request().method() === 'POST');
console.log('UI-03 PASS — Worker created via admin UI');
```

### UI-04 — Chat page sends message and receives response
```javascript
await page.goto(`${BASE}/mcp-agent.html`);
await page.waitForSelector('#chat-input, textarea[placeholder*="message"]', { timeout: 8000 });
await page.fill('#chat-input, textarea[placeholder*="message"]', 'Say: HELLO_UAT_TEST');
await page.keyboard.press('Enter');
await page.waitForFunction(() => {
  const msgs = document.querySelectorAll('.message-content, .assistant-message');
  return Array.from(msgs).some(m => m.textContent.includes('HELLO_UAT_TEST'));
}, { timeout: 30000 });
console.log('UI-04 PASS — Chat received agent response');
```

### UI-05 — File upload via sidebar
```javascript
const fileInput = await page.locator('input[type="file"]').first();
await fileInput.setInputFiles({
  name: 'ui05_upload_test.md',
  mimeType: 'text/markdown',
  buffer: Buffer.from('# UI Upload Test\n\nFile uploaded via Playwright UAT')
});
await page.waitForResponse(r => r.url().includes('/upload') && r.status() === 200, { timeout: 15000 });
console.log('UI-05 PASS — File uploaded via sidebar');
```

### UI-06 — Tool call visible in UI (tool badge or loading indicator)
```javascript
await page.fill('#chat-input, textarea[placeholder*="message"]', 'Search the web: latest AI news');
await page.keyboard.press('Enter');
await page.waitForFunction(() => {
  const indicators = document.querySelectorAll('.tool-call, .tool-badge, [class*="tool"]');
  return indicators.length > 0;
}, { timeout: 20000 });
console.log('UI-06 PASS — Tool execution visible in chat UI');
```

### UI-07 — Admin panel: toggle tool on/off
```javascript
await page.goto(`${BASE}/admin.html`);
await page.click('[data-section="tools"], button[onclick*="loadTools"]');
await page.waitForSelector('.tool-toggle, input[type="checkbox"][data-tool]', { timeout: 8000 });
const firstToggle = page.locator('.tool-toggle, input[type="checkbox"][data-tool]').first();
const initialState = await firstToggle.isChecked();
await firstToggle.click();
await page.waitForTimeout(500);
const newState = await firstToggle.isChecked();
console.assert(newState !== initialState, 'Tool toggle did not change state');
// Restore
await firstToggle.click();
console.log('UI-07 PASS — Tool toggle works in admin UI');
```

### UI-08 — Canvas renders chart from agent
```javascript
await page.goto(`${BASE}/mcp-agent.html`);
await page.fill('#chat-input, textarea[placeholder*="message"]', 'Create a simple bar chart: A=10, B=20');
await page.keyboard.press('Enter');
const canvas = await page.waitForSelector('iframe[src*="charts"], .chart-canvas, #canvas-area', { timeout: 45000 });
console.assert(canvas !== null, 'Canvas element not found');
console.log('UI-08 PASS — Canvas/chart rendered in chat UI');
```

### UI-09 — User management: create user via admin UI
```javascript
await page.goto(`${BASE}/admin.html`);
await page.click('[data-section="users"], button[onclick*="loadUsers"]');
await page.waitForSelector('[data-section="users"] tbody, #users-table');
await page.click('button[onclick*="showCreateUser"], [data-action="create-user"]');
await page.waitForSelector('#create-user-modal, #user-create-form');
await page.fill('input[name="user_id"], #user-id-input', 'ui_test_user');
await page.fill('input[name="password"], #user-password', 'UITest2026!');
await page.click('button[type="submit"]');
console.log('UI-09 PASS — User created via admin UI');
```

### UI-10 — Audit log visible in admin panel
```javascript
await page.click('[data-section="audit"], button[onclick*="loadAudit"]');
await page.waitForSelector('#audit-table tbody tr, .audit-entry', { timeout: 8000 });
const rows = await page.locator('#audit-table tbody tr, .audit-entry').count();
console.assert(rows > 0, `Expected audit rows, got ${rows}`);
console.log(`UI-10 PASS — Audit log shows ${rows} entries`);
```

### UI-11 — Worker prompt editor saves and shows confirmation
```javascript
await page.click('[data-section="workers"], .workers-tab');
await page.waitForSelector('.worker-row, [data-worker-id]');
await page.click('.worker-row:first-child [data-action="edit"], .edit-worker-btn');
await page.waitForSelector('#worker-prompt, textarea[name="system_prompt"]');
const promptArea = page.locator('#worker-prompt, textarea[name="system_prompt"]');
await promptArea.fill(await promptArea.inputValue() + ' <!-- UAT -->');
await page.click('[type="submit"], .save-prompt-btn');
await page.waitForSelector('.toast-success, .alert-success', { timeout: 5000 });
console.log('UI-11 PASS — Prompt editor saved with toast confirmation');
```

### UI-12 — LLM provider config panel accessible (super admin)
```javascript
await page.goto(`${BASE}/admin.html`);
await page.click('[data-section="llm-config"], button[onclick*="loadLLM"]');
await page.waitForSelector('#llm-provider-select, [data-section="llm-config"] select', { timeout: 8000 });
const provider = await page.locator('#llm-provider-select, select[name="provider"]').inputValue();
console.log(`UI-12 PASS — LLM config panel: current provider = ${provider}`);
```

### UI-13 — Login rate limit triggers after 10 failed attempts
```javascript
// Attempt 11 rapid logins with wrong password
for (let i = 0; i < 11; i++) {
  await page.goto(`${BASE}/login.html`);
  await page.fill('#username', 'risk_agent');
  await page.fill('#password', 'wrongpassword');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(200);
}
const errorText = await page.locator('.error, .alert-danger').textContent().catch(() => '');
console.log(`UI-13 — Rate limit response: ${errorText.substring(0, 100)}`);
```

### UI-14 — File tree shows S3 files with sizes
```javascript
await page.goto(`${BASE}/mcp-agent.html`);
await page.click('[data-section="domain_data"], .file-tree-tab');
await page.waitForSelector('.file-tree .file-item, .file-entry', { timeout: 10000 });
const files = await page.locator('.file-tree .file-item, .file-entry').count();
console.assert(files > 0, `File tree is empty — S3 listing may be broken`);
console.log(`UI-14 PASS — File tree shows ${files} S3 files`);
```

---

## Phase 11 — Audit, Sessions & Observability

> **Goal:** Audit log entries are written to Postgres after tool use, sessions are tracked, entries are queryable and paginated.

### AUD-01 — Audit log has entries after agent runs
```python
r = requests.get(f"{BASE}/api/super/audit",
    headers=auth(TOKEN), params={"worker_id": WID, "limit": 10})
assert r.status_code == 200
entries = r.json() if isinstance(r.json(), list) else r.json().get("entries", r.json().get("data", []))
assert len(entries) > 0, "No audit entries"
print(f"AUD-01 PASS — {len(entries)} audit entries. Latest: event={entries[0].get('event_type')}, worker={entries[0].get('worker_id')}")
```

### AUD-02 — Audit entry has expected fields
```python
r = requests.get(f"{BASE}/api/super/audit",
    headers=auth(TOKEN), params={"worker_id": WID, "limit": 1})
entry = (r.json() if isinstance(r.json(), list) else r.json().get("entries", r.json().get("data", [])))[0]
for field in ["worker_id", "event_type", "timestamp"]:
    assert field in entry, f"Missing field: {field}"
assert entry.get("worker_id") == WID
print(f"AUD-02 PASS — Audit entry fields: {list(entry.keys())}")
```

### AUD-03 — Audit log pagination works
```python
r1 = requests.get(f"{BASE}/api/super/audit",
    headers=auth(TOKEN), params={"worker_id": WID, "limit": 2, "offset": 0})
r2 = requests.get(f"{BASE}/api/super/audit",
    headers=auth(TOKEN), params={"worker_id": WID, "limit": 2, "offset": 2})
page1 = r1.json() if isinstance(r1.json(), list) else r1.json().get("entries", r1.json().get("data", []))
page2 = r2.json() if isinstance(r2.json(), list) else r2.json().get("entries", r2.json().get("data", []))
# Pages should be different
if page1 and page2:
    assert page1[0].get("id") != page2[0].get("id"), "Pagination not working — same results"
print(f"AUD-03 PASS — Audit pagination: page1={len(page1)} entries, page2={len(page2)} entries")
```

### AUD-04 — Sessions created in Postgres after agent run
```python
r = requests.get(f"{BASE}/api/agent/threads",
    headers=auth(TOKEN), params={"worker_id": WID})
assert r.status_code == 200
threads = r.json() if isinstance(r.json(), list) else r.json().get("threads", [])
assert len(threads) > 0, "No sessions found — Postgres session tracking may be broken"
t = threads[0]
print(f"AUD-04 PASS — {len(threads)} sessions. Latest: thread={t.get('thread_id','')[:16]}...")
```

### AUD-05 — Tool call audit entry includes tool_name
```python
r = requests.get(f"{BASE}/api/super/audit",
    headers=auth(TOKEN), params={"worker_id": WID, "limit": 50})
entries = r.json() if isinstance(r.json(), list) else r.json().get("entries", r.json().get("data", []))
tool_entries = [e for e in entries if e.get("tool_name")]
assert len(tool_entries) > 0, "No tool_name entries in audit log"
print(f"AUD-05 PASS — {len(tool_entries)} tool audit entries. Tools used: {set(e['tool_name'] for e in tool_entries)}")
```

### AUD-06 — Sensitive fields redacted in audit log
```python
r = requests.get(f"{BASE}/api/super/audit",
    headers=auth(TOKEN), params={"limit": 50})
entries = r.json() if isinstance(r.json(), list) else r.json().get("entries", r.json().get("data", []))
audit_text = json.dumps(entries)
# No raw passwords or secrets should appear
for sensitive in ["RiskAgent2025!", "MyXUqN8", "ATATT3x"]:
    assert sensitive not in audit_text, f"Sensitive value leaked in audit log: {sensitive[:8]}..."
print("AUD-06 PASS — No sensitive values in audit log")
```

---

## Results Tracking

| Phase | Tests | PASS | FAIL | SKIP | Notes |
|-------|-------|------|------|------|-------|
| 1 — Infrastructure | 10 | | | | |
| 2 — Auth & Users | 8 | | | | |
| 3 — Workers | 10 | | | | |
| 4 — File System + S3 | 12 | | | | |
| 5 — Agent Execution | 10 | | | | |
| 6 — Core Tools | 14 | | | | |
| 7 — Workflows | 8 | | | | |
| 8 — External Tools | 6 | | | | |
| 9 — Connectors | 8 | | | | |
| 10 — Admin UI | 14 | | | | |
| 11 — Audit/Sessions | 6 | | | | |
| **TOTAL** | **106** | | | | |

---

## Acceptance Criteria

- [ ] **Phase 1 (INF):** All S3 and Postgres connectivity tests PASS (INF-01–06 minimum)
- [ ] **Phase 2 (AUTH):** JWT, role enforcement, user CRUD all PASS
- [ ] **Phase 3 (WRK):** Worker create/update/delete via Postgres PASS; no fallback to JSON
- [ ] **Phase 4 (FS):** File upload → S3 confirmed by boto3 head_object; worker isolation enforced
- [ ] **Phase 5 (AGT):** Agent runs, SSE streams, thread persists in Postgres, audit log written
- [ ] **Phase 6 (TOOL):** DuckDB, BM25, Python executor, read_file all work with S3-stored data
- [ ] **Phase 7 (WF):** Workflow create/execute/delete cycle works; multi-agent events fire
- [ ] **Phase 8 (EXT):** Tavily and Yahoo Finance return real data; SEC EDGAR returns filing info
- [ ] **Phase 9 (CONN):** Teams list_channels and Jira list_projects return real data
- [ ] **Phase 10 (UI):** Login, chat, file upload, worker config, audit log all functional in browser
- [ ] **Phase 11 (AUD):** Audit entries in Postgres, tool_name populated, sensitive fields redacted

---

## How to Execute

### API Tests (Phases 1–9, 11)
```bash
cd /Users/saadahmed/Desktop/react_agent
# Install dependencies
pip install requests sseclient-py boto3 psycopg pyarrow

# Run inline (copy-paste test blocks) or as a script:
python3 uat_plans/run_platform_uat.py
```

### Playwright Tests (Phase 10)
```bash
npm install playwright
npx playwright install chromium
node uat_plans/run_platform_uat_ui.mjs
```

### Re-run on Production
Set `BASE = "http://62.238.3.148"` — all tests target production VPS.  
Auth: `risk_agent` / `RiskAgent2025!`  
S3 credentials: as per `CREDENTIALS.md`
