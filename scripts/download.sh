#!/bin/bash
# Fetch the Maros-Meszaros QP test set (qpbenchmark MAT format) at a pinned
# upstream commit. The evaluators check every MAT file against SHA-256 hashes
# recorded in eval/*/manifest.json, so the commit must not float.
#
# Download size ~26 MB; ~31 MB on disk after extraction. Idempotent.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WORKSPACE_DIR"

COMMIT="afa738d9a66aca7f5ae223034c72f2e9c6866aff"
URL="https://github.com/qpsolvers/maros_meszaros_qpbenchmark/archive/${COMMIT}.zip"
ARCHIVE="data/downloads/maros_meszaros_qpbenchmark-${COMMIT}.zip"
EXTRACTED="data/downloads/maros_meszaros_qpbenchmark-${COMMIT}"
TARGET="data/maros_meszaros_qpbenchmark"

mkdir -p data/downloads
if [[ ! -f "$TARGET/data/AUG2D.mat" ]]; then
    if [[ ! -f "$ARCHIVE" ]]; then
        curl -L --fail "$URL" -o "$ARCHIVE.part"
        mv "$ARCHIVE.part" "$ARCHIVE"
    fi
    if [[ ! -d "$EXTRACTED" ]]; then
        python3 - "$ARCHIVE" <<'PY'
import sys
from zipfile import ZipFile

with ZipFile(sys.argv[1]) as zf:
    zf.extractall("data/downloads")
PY
    fi
    mkdir -p "$TARGET"
    cp -a "$EXTRACTED"/. "$TARGET"/
fi
echo "Maros-Meszaros data is available at $TARGET/data"
