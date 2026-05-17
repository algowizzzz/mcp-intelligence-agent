# UAT Results — module9

**Run ID:** `module9_2026-04-03_17-56-03`  
**Generated:** 2026-04-03 22:56:07 UTC  

## Summary

| Status | Count |
|--------|-------|
| ✓ PASS  | 45  |
| ✗ FAIL  | 0  |
| ○ SKIP  | 0  |
| ! ERROR | 5 |
| **Total** | **50** |

**Pass rate: 90% (45/50)**

## Module 9G — application.properties

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| PG-APP-01 | data.root points to w-market-risk worker-scoped path | ✓ PASS |  |  |
| PG-APP-02 | data.duckdb.dir points to w-market-risk | ✓ PASS |  |  |
| PG-APP-03 | data.sqlselect.dir points to w-market-risk | ✓ PASS |  |  |
| PG-APP-04 | data.iris_combined_csv points to w-market-risk | ✓ PASS |  |  |
| PG-APP-05 | data.osfi_docs_dir points to w-market-risk | ✓ PASS |  |  |
| PG-APP-06 | data.uploads_dir points to w-market-risk/my_data/risk_a | ✓ PASS |  |  |
| PG-APP-07 | data.my_data.dir points to w-market-risk/my_data/risk_a | ✓ PASS |  |  |

*7/7 passed*

## Module 9H — Filesystem

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| PH-01 | MR domain_data/osfi/ exists | ✓ PASS |  |  |
| PH-02 | MR duckdb_analytics.db exists | ✓ PASS |  |  |
| PH-03 | MR iris_combined.csv exists | ✓ PASS |  |  |
| PH-04 | MR domain_data/sqlselect/ exists | ✓ PASS |  |  |
| PH-05 | MR workflows/verified/ exists | ✓ PASS |  |  |
| PH-06 | CCR workflows/verified/ exists | ✓ PASS |  |  |
| PH-07 | MR my_data/ exists | ✓ PASS |  |  |
| PH-08 | MR workflows/verified/ contains exactly 12 expected .md | ✓ PASS |  |  |
| PH-09 | CCR my_data does not contain risk_agent user files (no  | ✓ PASS |  |  |

*9/9 passed*

## Module 9A — Super Admin File Tree

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| PA-01 | MR domain_data tree shows migrated subdirs (osfi/duckdb | ✓ PASS |  |  |
| PA-01b | iris/iris_combined.csv present in domain_data tree | ✓ PASS |  |  |
| PA-02 | MR verified_workflows returns 12 workflow .md files | ✓ PASS |  |  |
| PA-03 | CCR verified_workflows has no MR workflows (worker isol | ✓ PASS |  |  |
| PA-04 | CCR domain_data does not contain MR-specific data (no c | ✓ PASS |  |  |
| PA-05 | GET /files/my_data returns HTTP 400 (not in admin white | ✓ PASS |  |  |
| PA-06 | GET /files/common returns HTTP 400 (common_data not in  | ✓ PASS |  |  |
| PA-07 | Upload test .csv to MR domain_data returns 200 (or 409  | ✓ PASS |  |  |
| PA-07b | Uploaded file _uat9a_test_a31af8.csv appears in domain_ | ✓ PASS |  |  |
| PA-09 | Upload .md to MR verified_workflows returns 200 | ✓ PASS |  |  |
| PA-10 | Read uploaded workflow file returns content | ✓ PASS |  |  |
| PA-10b | Rename workflow file in verified_workflows returns 200 | ✓ PASS |  |  |
| PA-11 | Delete workflow file from verified_workflows returns 20 | ✓ PASS |  |  |
| PA-11b | Deleted workflow file is absent from verified_workflows | ✓ PASS |  |  |

*14/14 passed*

## Module 9B — Admin Role File Tree

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| PB-01 | Admin GET /api/admin/worker returns own worker (MR) wit | ✓ PASS |  |  |
| PB-02 | Admin domain_data tree shows osfi/duckdb/iris/sqlselect | ✓ PASS |  |  |
| PB-03 | Admin verified_workflows shows 12 workflow files | ✓ PASS |  |  |
| PB-04 | Admin token returns HTTP 403 on super admin endpoint | ✓ PASS |  |  |
| PB-05 | Admin upload to own domain_data returns 200 | ✓ PASS |  |  |
| PB-06 | Admin GET /files/my_data — super admin blocks it (HTTP  | ✓ PASS |  |  |

*6/6 passed*

## Module 9C — User Role RBAC

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| PC-01 | User JWT returns 403 on /api/admin/worker and file tree | ✓ PASS |  |  |
| PC-02 | User JWT returns 403 on super admin endpoint | ✓ PASS |  |  |
| PC-03 | User JWT can access /api/agent/run (200 streaming) | ✓ PASS |  |  |
| PC-04 | Unauthenticated requests return 401 on admin endpoints | ✓ PASS |  |  |

*4/4 passed*

## Module 9D — Data Migration via Agent

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| PD-01 | OSFI list tools read from worker domain_data | ! ERROR | Agent error: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_requ | 947 |
| PD-02 | DuckDB list tables uses MR worker database | ! ERROR | Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', ' | 271 |
| PD-03 | IRIS dates returned from MR worker iris path | ! ERROR | Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', ' | 293 |
| PD-04 | Workflow list returns from MR worker path | ! ERROR | Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', ' | 389 |
| PD-05 | md_save writes to user-scoped my_data | ! ERROR | Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', ' | 371 |

*0/5 passed*

## Module 9E — Worker Clone Isolation

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| PE-01 | Cloned worker my_data is empty (no user files copied) | ✓ PASS |  |  |
| PE-02 | Cloned worker domain_data is populated (copy from MR) | ✓ PASS |  |  |

*2/2 passed*

## Module 9F — Section Key Regressions

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| PF-04 | Delete multiple files from verified_workflows (section  | ✓ PASS |  |  |
| PF-05 | Rename in verified_workflows returns 200 (section key a | ✓ PASS |  |  |
| PF-06 | Admin rename in verified_workflows returns 200 (section | ✓ PASS |  |  |

*3/3 passed*

## Failures & Errors

### [PD-01] OSFI list tools read from worker domain_data
- **Status:** ERROR
- **Detail:** `Agent error: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011CZhfQeVktCpayVGfBeedx'}`
- **Timestamp:** 2026-04-03T22:56:05.854964Z

### [PD-02] DuckDB list tables uses MR worker database
- **Status:** ERROR
- **Detail:** `Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011CZhfQgz5NGoNMcGf8fC9S'}`
- **Timestamp:** 2026-04-03T22:56:06.128789Z

### [PD-03] IRIS dates returned from MR worker iris path
- **Status:** ERROR
- **Detail:** `Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011CZhfQi8Y33LMHZiWSi45o'}`
- **Timestamp:** 2026-04-03T22:56:06.424501Z

### [PD-04] Workflow list returns from MR worker path
- **Status:** ERROR
- **Detail:** `Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011CZhfQjiHRnRHjcCB5MpdR'}`
- **Timestamp:** 2026-04-03T22:56:06.814082Z

### [PD-05] md_save writes to user-scoped my_data
- **Status:** ERROR
- **Detail:** `Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011CZhfQmJ2ziKNqbZ6Rb3v3'}`
- **Timestamp:** 2026-04-03T22:56:07.186943Z
