# REQ-04b Backend Test Results

**Date:** 2026-04-04
**Environment:** Python 3.13.5 ARM (macOS Darwin 23.5.0)
**Sandbox venv:** `sajhamcpserver/python_sandbox_venv`
**Test runner:** `_run_sandboxed` (subprocess call to sandbox venv Python)

---

## Library Versions Installed

| Library | Version | Status |
|---------|---------|--------|
| scikit-learn | 1.8.0 | OK |
| arch | 8.0.0 | OK |
| riskfolio-lib | 7.2.1 | OK |
| QuantLib | 1.41 | OK |
| xarray | 2026.2.0 | OK |
| networkx | 3.6.1 | OK |

**Installation notes:**
- `QuantLib-Python>=1.33` (original REQ-04b package name) has no wheel for Python 3.13 ARM — PyPI tops out at 1.18. Fixed by using package name `QuantLib` (no version constraint), which resolved to 1.41 via `quantlib-1.41-cp38-abi3-macosx_11_0_arm64.whl` (ABI3 stable, compatible with Python 3.13).
- `riskfolio-lib` 7.2.1 pulled in `astropy` and `vectorbt` as required dependencies. These were installed separately after the initial pip run did not complete them. All resolved successfully.
- `setup_sandbox_venv_extended.sh` updated to use `QuantLib` (not `QuantLib-Python`) without a version pin.

---

## Test Results

### PY-TEST-B-001 — GARCH(1,1) volatility model

**Status: PASS**
**Exit code:** 0
**Elapsed:** 2.343 s

**stdout:**
```
GARCH(1,1) Parameters:
mu         -1.038770e-01
omega       8.165678e-01
alpha[1]    0.000000e+00
beta[1]     1.643589e-13
AIC: 271.5176
BIC: 281.9383
```

100 simulated daily returns (np.random.seed=42, scale=1%), fitted with `arch_model(returns, vol='Garch', p=1, q=1)`.

---

### PY-TEST-B-002 — riskfolio-lib import + scikit-learn PCA

**Status: PASS**
**Exit code:** 0
**Elapsed:** 1.816 s (PCA test)

**riskfolio import stdout:**
```
riskfolio version: 7.2.1
riskfolio import: OK
```

**PCA stdout:**
```
Explained variance ratio: [0.2898, 0.2498, 0.2446]
Cumulative: 0.7842
Components shape: (3, 4)
```

StandardScaler + PCA(n_components=3) on 100×4 random returns matrix (seed=42). Both riskfolio import and PCA execution confirmed working.

---

### PY-TEST-B-003 — QuantLib Bond Pricing

**Status: PASS**
**Exit code:** 0
**Elapsed:** 0.136 s

**stdout:**
```
Clean Price: 101.1393
Dirty Price: 101.1393
Modified Duration: 4.3478
```

5-year fixed-rate bond, face=1000, coupon=4.5%, flat yield=4.2%, semiannual schedule, TARGET calendar, ActualActual(ISDA) day count, DiscountingBondEngine. Clean price > par as expected (coupon > yield). Clean = Dirty because pricing date is a coupon date (no accrued interest).

---

### PY-TEST-B-004 — networkx counterparty network

**Status: PASS**
**Exit code:** 0
**Elapsed:** 0.423 s

**stdout:**
```
Betweenness Centrality:
  BankB: 0.1250
  BankD: 0.0833
  BankC: 0.0417
  BankA: 0.0000
  BankE: 0.0000
PageRank (systemic importance):
  BankE: 0.3802
  BankD: 0.2555
  BankB: 0.1449
  BankC: 0.1248
  BankA: 0.0946
```

DiGraph with 5 bank nodes, 6 weighted directed edges. BankB has highest betweenness (intermediary); BankE has highest PageRank (most links pointing to it — systemic sink).

---

## Summary

| Test | Description | Exit Code | Elapsed | Result |
|------|-------------|-----------|---------|--------|
| PY-TEST-B-001 | GARCH(1,1) via `arch` | 0 | 2.343 s | PASS |
| PY-TEST-B-002 | riskfolio import + PCA via `scikit-learn` | 0 | 1.816 s | PASS |
| PY-TEST-B-003 | Bond pricing via `QuantLib` | 0 | 0.136 s | PASS |
| PY-TEST-B-004 | Counterparty network via `networkx` | 0 | 0.423 s | PASS |

**4/4 backend tests PASS. 0 FAIL. 0 SKIP.**
