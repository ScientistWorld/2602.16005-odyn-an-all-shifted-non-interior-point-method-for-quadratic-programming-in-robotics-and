#!/bin/bash
# Python dependency installation for the ODYN reproduction container.

set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    python3 -m pip install --break-system-packages uv
fi

export UV_SYSTEM_PYTHON=1
export UV_BREAK_SYSTEM_PACKAGES=1

uv pip install --system numpy scipy proxsuite osqp

