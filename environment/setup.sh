#!/bin/bash
# Setup script for ODYN QP solver environment
#
# This script runs inside the container with internet access.
# Install all Python dependencies here.

set -e

# Use uv for faster installation
pip install --break-system-packages uv 2>/dev/null || true
export UV_SYSTEM_PYTHON=1
export UV_BREAK_SYSTEM_PACKAGES=1

# Core numerical libraries
uv pip install --system numpy scipy 2>/dev/null || pip install numpy scipy 2>/dev/null || true

# QP solver libraries (if available on PyPI)
uv pip install --system proxsuite 2>/dev/null || pip install proxsuite 2>/dev/null || true

# Note: OSQP has known issues with limited disk space
# If osqp fails to import, the eval script will handle it gracefully