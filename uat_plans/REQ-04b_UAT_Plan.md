# REQ-04b UAT Plan — Extended Quantitative Finance Libraries

**Date:** 2026-04-04
**Requirement:** REQ-04b — Install and verify scikit-learn, arch, riskfolio-lib, QuantLib, xarray, networkx in the Python sandbox venv
**Related:** REQ-04a (base sandbox venv must be provisioned first)

---

## Scope

REQ-04b extends the Python sandbox with quantitative finance libraries beyond the base set (pandas, numpy, scipy, matplotlib, etc.) installed by REQ-04a. These libraries enable:
- GARCH volatility models (`arch`)
- Portfolio optimisation (`riskfolio-lib`, `cvxpy`)
- Fixed income / derivatives pricing (`QuantLib`)
- Scenario grids and stress test arrays (`xarray`)
- Counterparty network analysis (`networkx`)
- ML-based risk models (`scikit-learn`)

---

## Backend Tests (no LLM required)

Executed directly via `_run_sandboxed` from `sajha.tools.impl.python_executor`.

| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| PY-TEST-B-001 | GARCH(1,1) — fit on synthetic returns, check AIC/BIC | **PASS** | arch 8.0.0 |
| PY-TEST-B-002 | PCA (3 components) on 200x6 random matrix | **PASS** | sklearn 1.8.0 |
| PY-TEST-B-003 | QuantLib bond pricing — 5yr fixed-rate, clean/dirty price | **PASS** | QuantLib 1.41 |
| PY-TEST-B-004 | networkx DiGraph — betweenness centrality + PageRank | **PASS** | networkx 3.6.1 |

Full stdout and exit codes: see `REQ-04b_backend_test_results.md`.

---

## LLM-Based Tests (PENDING — user to run via agent UI)

These tests require a live agent session. Invoke via the chat interface at `public/index.html` (agent server on port 8000, SAJHA MCP on port 3002).

### PY-TEST-L-001 — GARCH volatility forecast

**Prompt:**
```
Run a GARCH(1,1) model on the following daily returns (in percent) and forecast
the next 5-day conditional volatility:
returns = [0.52, -0.31, 1.12, -0.88, 0.43, -0.67, 0.29, 1.54, -1.02, 0.76,
           -0.45, 0.33, -0.91, 0.64, 0.18, -1.23, 0.87, -0.55, 0.42, -0.38]
Print the model parameters and the 5-day volatility forecast.
```

**Expected:** Agent calls `python_execute`, fits GARCH(1,1) with `arch_model`, prints parameters (mu, omega, alpha[1], beta[1]) and 5-day forecast. No errors.

---

### PY-TEST-L-002 — PCA on yield curve tenors

**Prompt:**
```
I have monthly yield curve changes (bps) across 6 tenors (3M, 1Y, 2Y, 5Y, 10Y, 30Y)
for 60 months. Generate synthetic data with numpy seed 99, run PCA to extract the
first 3 principal components, and tell me what percentage of variance each explains.
```

**Expected:** Agent calls `python_execute`, uses `sklearn.decomposition.PCA`, reports explained variance ratios for PC1 (level), PC2 (slope), PC3 (curvature).

---

### PY-TEST-L-003 — QuantLib bond DV01

**Prompt:**
```
Price a 10-year semi-annual bond with face value $1,000,000, coupon rate 5%,
using a flat yield of 4.8%. Then bump the yield by 1bp and calculate the DV01.
Use QuantLib.
```

**Expected:** Agent calls `python_execute` with QuantLib, prints clean price at 4.8%, re-prices at 4.81%, calculates DV01 = (P_down - P_up) / 2 (or similar). No import errors.

---

### PY-TEST-L-004 — Counterparty network contagion

**Prompt:**
```
Build a directed exposure network for 5 banks using networkx:
- BankA owes BankB $500M, BankC $300M
- BankB owes BankD $200M, BankE $250M
- BankC owes BankD $400M
- BankD owes BankE $150M
Calculate betweenness centrality and identify the systemically most important bank.
```

**Expected:** Agent calls `python_execute`, builds `nx.DiGraph`, computes `betweenness_centrality`, identifies BankB as highest centrality node (0.125). Provides brief interpretation.

---

## Acceptance Criteria

- All 4 backend tests: PASS (achieved — see results file)
- All 4 LLM tests: agent must call `python_execute`, code must run with exit_code 0, output must be numerically plausible
- No `ImportError` for any of the 6 new libraries in the sandbox
- QuantLib available (not skipped) — confirmed: QuantLib 1.41 installed successfully

---

## Environment Notes

- Python 3.13 ARM (macOS Darwin 23.5.0) — `QuantLib-Python>=1.33` has no wheel; use package name `QuantLib` (no version constraint), which resolves to 1.41 via ABI3 wheel
- `riskfolio-lib` pip install requires care: it tries to downgrade pandas from 3.x to 2.x. Workaround: install with `--no-deps` then install deps individually. The `setup_sandbox_venv_extended.sh` script uses a single pip call which works if pandas is not yet installed (fresh venv) or if pip resolves correctly on first install
- Docker/Railway: Standard pip install should work on Python 3.11 or 3.12 images without workarounds

---

## Files Changed

| File | Change |
|------|--------|
| `sajhamcpserver/setup_sandbox_venv_extended.sh` | Updated: fixed `QuantLib` package name (no `>=1.33`), improved verify block |
| `agent/prompt.py` | Updated: `_PYTHON_ADDENDUM` now includes REQ-04b library list |
| `uat_plans/REQ-04b_backend_test_results.md` | Created: actual test stdout and versions |
| `uat_plans/REQ-04b_UAT_Plan.md` | Created: this file |
