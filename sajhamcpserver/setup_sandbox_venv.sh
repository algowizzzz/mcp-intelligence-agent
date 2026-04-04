#!/bin/bash
# REQ-04a: Create the Python sandbox virtual environment with basic data science libraries.
# Run from the repo root or from within sajhamcpserver/.
set -e

VENV_DIR="$(dirname "$0")/python_sandbox_venv"

echo "Creating sandbox venv at $VENV_DIR ..."
python3 -m venv "$VENV_DIR"

echo "Upgrading pip ..."
"$VENV_DIR/bin/pip" install --upgrade pip

echo "Installing basic library set (REQ-04a) ..."
"$VENV_DIR/bin/pip" install \
    "pandas>=2.0" \
    "numpy>=1.26" \
    "scipy>=1.12" \
    "matplotlib>=3.8" \
    "plotly>=5.19" \
    "openpyxl>=3.1" \
    "pyarrow>=14.0" \
    "statsmodels>=0.14"

echo ""
echo "Sandbox venv created at $VENV_DIR"
echo "Python: $VENV_DIR/bin/python"
echo ""
echo "To verify: $VENV_DIR/bin/python -c \"import pandas, numpy, scipy, matplotlib, plotly, openpyxl, pyarrow, statsmodels; print('All OK')\""
