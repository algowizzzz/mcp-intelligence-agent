# REQ-04b — Python Execution Tool: Heavy Quantitative Finance Libraries
**Status:** Pending Implementation (after REQ-04a is complete and stable)
**Version:** 1.0 (2026-04-04)
**Scope:** Extend the Python sandbox (REQ-04a) with heavy quantitative finance and machine learning libraries. Do not start until REQ-04a is fully deployed and tested.

---

## Prerequisite

REQ-04a must be complete and stable:
- `python_execute` and `python_run_script` tools are live
- Basic sandbox venv is working
- All REQ-04a acceptance criteria met
- No sandbox escape or timeout issues observed in production

---

## 1. Additional Libraries

Extend `sajhamcpserver/python_sandbox_venv/` with:

| Library | Version | Use Case |
|---|---|---|
| `scikit-learn` | >=1.4 | ML models, PCA, clustering for portfolio analysis |
| `statsmodels` | >=0.14 | Already in REQ-04a — confirm included |
| `arch` | >=6.3 | GARCH/EGARCH volatility models for market risk |
| `riskfolio-lib` | >=6.1 | Portfolio optimisation (mean-variance, CVaR, HRP) |
| `QuantLib-Python` | >=1.33 | Interest rate curves, derivatives pricing, bond analytics |
| `xarray` | >=2024.1 | Multi-dimensional labelled arrays (useful for scenario analysis) |
| `networkx` | >=3.2 | Graph analytics for counterparty network risk |

---

## 2. Updated Setup Script Addition

Append to `sajhamcpserver/setup_sandbox_venv.sh` (or create `setup_sandbox_venv_extended.sh`):

```bash
#!/bin/bash
set -e
VENV_DIR="$(dirname "$0")/python_sandbox_venv"

# Must run setup_sandbox_venv.sh first (REQ-04a)
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Basic venv not found. Run setup_sandbox_venv.sh first."
    exit 1
fi

echo "Installing heavy quantitative finance libraries..."
"$VENV_DIR/bin/pip" install \
    scikit-learn>=1.4 \
    arch>=6.3 \
    riskfolio-lib>=6.1 \
    QuantLib-Python>=1.33 \
    xarray>=2024.1 \
    networkx>=3.2

echo "Extended quant libraries installed."
```

> **Note:** QuantLib-Python and riskfolio-lib require C++ build tools on the host. On Railway/Docker, ensure `build-essential` and `python3-dev` are installed.

---

## 3. Updated System Prompt

Extend the Python execution section in `agent/prompt.py`:

```
Additional libraries available (extended mode):
- scikit-learn: ML models, dimensionality reduction, clustering
- arch: GARCH, EGARCH volatility modelling
- riskfolio-lib: Portfolio optimisation — mean-variance, CVaR, HRP, risk budgeting
- QuantLib: Interest rate curve building, bond pricing, derivatives, day count conventions
- xarray: Multi-dimensional labelled arrays for scenario grids and stress tests
- networkx: Counterparty network graphs, contagion analysis

Use QuantLib for:
- Zero curve construction (QuantLib.FlatForward, QuantLib.PiecewiseYieldCurve)
- Bond analytics (dirty/clean price, duration, convexity, YTM)
- Vanilla derivatives pricing (European options, swaps)
```

---

## 4. Additional Tests

### PY-TEST-B-001 — GARCH Volatility Model

Prompt: `"Fit a GARCH(1,1) model to [0.01, -0.02, 0.015, ...] daily returns using arch"`

Expected: GARCH params returned in stdout, convergence information shown.

### PY-TEST-B-002 — Portfolio Optimisation

Prompt: `"Using riskfolio-lib, find the minimum CVaR portfolio for 4 assets with returns in my data"`

Expected: Optimal weights returned, possibly a pie chart generated via Plotly.

### PY-TEST-B-003 — QuantLib Bond Pricing

Prompt: `"Price a 5-year bond with 4.5% coupon, face value 1000, at a 4.2% flat yield using QuantLib"`

Expected: Clean price, dirty price, duration, convexity returned in stdout.

### PY-TEST-B-004 — scikit-learn PCA

Prompt: `"Run PCA on my exposure matrix to find the top 3 principal components"`

Expected: Explained variance ratio shown, loadings optionally plotted.

---

## 5. Acceptance Criteria

- [ ] All REQ-04a criteria still passing after extending the venv
- [ ] PY-TEST-B-001 through PY-TEST-B-004 pass
- [ ] QuantLib imports successfully in sandbox (no missing C++ dependencies)
- [ ] riskfolio-lib imports successfully
- [ ] System prompt updated with extended library list
- [ ] `setup_sandbox_venv_extended.sh` documented and tested
- [ ] Build dependencies documented for Docker/Railway deployment

---

## Deployment Note

QuantLib-Python requires compilation. For Docker deployments (Railway), add to `Dockerfile`:

```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*
```

This significantly increases image build time. Run the extended setup as a separate Docker layer so it can be cached.
