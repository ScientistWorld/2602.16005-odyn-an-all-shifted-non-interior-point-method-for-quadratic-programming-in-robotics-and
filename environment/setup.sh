#!/bin/bash
# Python dependency installation for the QP-solver benchmark container.
# Versions are pinned so the evaluator, the OSQP baseline, and the reference
# solver see identical numerics on every rebuild.

set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    python3 -m pip install --break-system-packages uv
fi

export UV_SYSTEM_PYTHON=1
export UV_BREAK_SYSTEM_PACKAGES=1

uv pip install --system "numpy==2.5.4" "scipy==1.18.1" "osqp==1.1.3"
