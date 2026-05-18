#!/bin/bash
# REQ-04b: Extended quantitative finance libraries for the Python sandbox venv
# Prerequisites: Run setup_sandbox_venv.sh first (REQ-04a)
set -e
VENV_DIR="$(dirname "$0")/python_sandbox_venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Basic sandbox venv not found at $VENV_DIR"
    echo "Run setup_sandbox_venv.sh first (REQ-04a)"
    exit 1
fi

echo "Installing extended quantitative finance libraries..."
"$VENV_DIR/bin/pip" install \
    "scikit-learn>=1.4" \
    "arch>=6.3" \
    "riskfolio-lib>=6.1" \
    "QuantLib" \
    "xarray>=2024.1" \
    "networkx>=3.2"

echo ""
echo "Verifying installs..."
"$VENV_DIR/bin/python" -c "
libs = ['sklearn', 'arch', 'riskfolio', 'xarray', 'networkx']
all_ok = True
for lib in libs:
    try:
        m = __import__(lib)
        v = getattr(m, '__version__', 'unknown')
        print(f'  OK  {lib}: {v}')
    except ImportError as e:
        print(f'  FAIL {lib}: {e}')
        all_ok = False
try:
    import QuantLib as ql
    print(f'  OK  QuantLib: {ql.__version__}')
except ImportError:
    print('  SKIP QuantLib: no wheel for this Python version — use QuantLib-Python 1.18 as fallback')
if all_ok:
    print('All core extended libraries verified.')
"

echo ""
echo "Docker/Railway deployment note:"
echo "  QuantLib uses pre-built wheels where available."
echo "  All other libraries are pure-Python or have pre-built wheels."
echo "Setup complete."
