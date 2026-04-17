#!/bin/bash
# Download all external resources needed by this reproduction.
#
# Estimated total download size: ~35 MB
# Estimated disk usage after extraction: ~40 MB

set -euo pipefail

cd /home/user

mkdir -p data/downloads

ARCHIVE="data/downloads/maros_meszaros_qpbenchmark-main.zip"
EXTRACTED="data/downloads/maros_meszaros_qpbenchmark-main"
TARGET="data/maros_meszaros_qpbenchmark"
URL="https://github.com/qpsolvers/maros_meszaros_qpbenchmark/archive/refs/heads/main.zip"

if [[ ! -d "$TARGET/data" ]]; then
    if [[ ! -f "$ARCHIVE" ]]; then
        curl -L "$URL" -o "$ARCHIVE"
    fi
    if [[ ! -d "$EXTRACTED" ]]; then
        python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile

archive = Path("data/downloads/maros_meszaros_qpbenchmark-main.zip")
with ZipFile(archive) as zf:
    zf.extractall("data/downloads")
PY
    fi
    rm -rf "$TARGET"
    cp -a "$EXTRACTED" "$TARGET"
fi

echo "Maros-Meszaros data is available at $TARGET/data"

