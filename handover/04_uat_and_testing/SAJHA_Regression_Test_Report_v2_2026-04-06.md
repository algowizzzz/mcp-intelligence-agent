# SAJHA Intelligence Platform

> **Source:** Converted from `SAJHA_Regression_Test_Report_v2_2026-04-06.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**SAJHA Intelligence Platform**

Regression Test Report — Suite v2

April 6, 2026 · Full UI + API · All Roles

> **Note (2026-05-17):** Historical test report. The Playwright runner scripts (`run_regression_v2_tests.mjs` et al.) referenced here were moved out of the active tree on 2026-05-17. This report is kept as evidence of what was tested and passed at the time of the handover, not as a re-runnable test plan.

|         |         |       |           |
|---------|---------|-------|-----------|
| **132** | **132** | **0** | **9 min** |

|             |        |        |          |
|-------------|--------|--------|----------|
| Total Tests | Passed | Failed | Duration |

1\. Executive Summary

The SAJHA Intelligence Platform v2 regression suite completed a full browser-based end-to-end test covering every UI screen, button, and API endpoint across three user roles: super_admin, admin, and user. All 132 tests passed with zero failures.

The suite validated the complete user journey including authentication, role-based navigation, file uploads across all data layers, worker management, connector configuration, audit logging, chat UI interactions, and cross-role data isolation.

2\. Test Coverage by Group

The 132 tests are organized into 18 functional groups (A–R):

| **Group** | **Description** | **Role** | **Pass** | **Total** |
|----|----|----|----|----|
| A | Authentication | All roles | 10 | 10 |
| B | Admin Panel — Navigation | admin | 14 | 14 |
| C | Admin Panel — Worker Config | admin | 6 | 6 |
| D | Admin Panel — Tools | admin | 4 | 4 |
| E | Admin Panel — Domain Data | admin | 10 | 10 |
| F | Admin Panel — Shared Library | admin | 5 | 5 |
| G | Admin Panel — Verified Workflows | admin | 8 | 8 |
| H | Admin Panel — User Management | admin + super_admin | 7 | 7 |
| I | My Data (uploads) — per-user isolation | All roles | 6 | 6 |
| J | Manage Workers | super_admin | 9 | 9 |
| K | Connectors | super_admin | 8 | 8 |
| L | Audit Log | super_admin | 5 | 5 |
| M | Chat UI — mcp-agent.html | user | 15 | 15 |
| N | Chat UI — Admin features | admin | 4 | 4 |
| O | Chat UI — Super Admin features | super_admin | 4 | 4 |
| P | File Access / Isolation (API) | All roles | 6 | 6 |
| Q | DOM Upload & Bulk Actions | admin + super_admin | 6 | 6 |
| R | End-to-End Cross-Role Visibility | All roles | 5 | 5 |

3\. Bugs Found and Fixed

During the regression process, 6 distinct issues were identified, root-caused, and resolved. Five were test contract issues; one was a genuine production bug in admin.html.

| **Test(s)** | **Issue** | **Root Cause & Fix** | **Result** |
|----|----|----|----|
| B03 / B04 | Nav visibility filter | qAll('.nav-item') scanned hidden \#super-nav elements; added .filter(e=\>e.offsetParent!==null) | PASS |
| F05 | Common data API path | Server maps 'common' not 'common_data'; corrected /api/fs/common/tree | PASS |
| H06 / H07 | Super-admin user list | Iframe ran as admin (403 on /api/super/users); reload as super_admin before test | PASS |
| E03 / F03 / G04 | 409 on repeat runs | Upload rejects duplicates; 409 added to accepted status codes with explanatory message | PASS |
| admin.html (prod) | Topbar worker badge | switchWorker() never updated \#topbar-worker-name; one-line fix applied to admin.html | FIXED |
| J05 | Worker cycle timer throttle | 11 dashboard reloads = 33 concurrent fetches; changed to direct badge update without showSection() | PASS |

4\. Test Methodology

4.1 Framework

All tests run entirely in the browser — no external test framework, no Selenium, no Playwright. The suite (regression_tests_v2.html) is a single self-contained HTML file served by the FastAPI agent server on port 8000.

Tests execute sequentially using JavaScript async/await. Each test function returns a detail string on success or throws an Error on failure. A hidden off-screen iframe loads the application UI (admin.html, mcp-agent.html) and receives JWT tokens injected into sessionStorage after programmatic login.

4.2 Role Coverage

Every test group specifies which role(s) it covers. The three roles tested are:

- super_admin (risk_agent) — full access including worker management, connectors, audit log, user admin

- admin — worker-scoped admin panel, file management, tool config, user management within worker

- user (test_user) — chat interface, personal file uploads, shared library read access

4.3 Key Test Scenarios

Upload isolation: Files uploaded as admin to domain_data are visible only to that worker's admin and assigned users, not to users of other workers. Files in common_data (Shared Library) are readable by all roles. Verified workflows are only accessible to admins and super_admin.

Role-based nav: The admin panel nav dynamically hides super_admin-only sections (Manage Workers, Connectors, Audit Log) from regular admins. This was validated by checking offsetParent visibility, not just DOM presence.

Worker switcher: super_admin can switch between all 11 configured workers using the dropdown. The topbar badge updates correctly on every switch — a production bug where it didn't was found and fixed during this test run.

5\. Environment

|                     |                                                 |
|---------------------|-------------------------------------------------|
| Test Date           | April 6, 2026                                   |
| Suite Version       | v2 (regression_tests_v2.html)                   |
| Agent Server        | FastAPI / Uvicorn — port 8000                   |
| MCP Server          | SAJHA Flask MCP — port 3002                     |
| Auth                | JWT Bearer — 3 roles (super_admin, admin, user) |
| Workers Configured  | 11 (including Regression Test Worker)           |
| Total Test Duration | ~9 minutes (540 seconds)                        |
| Result              | 132 / 132 PASS — 0 FAIL                         |

6\. Conclusion

The SAJHA Intelligence Platform passed all 132 regression tests across the full feature surface. The platform correctly enforces role-based access control, file isolation between workers, and admin panel functionality for all three user roles.

All bugs identified during the regression cycle have been resolved. The test suite itself is now stable and can be re-run at any time to validate future changes by navigating to http://localhost:8000/regression_tests_v2.html and clicking Run All Tests.
