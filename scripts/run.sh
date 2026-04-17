#!/bin/bash
# Broader CPU run for the corrected ODYN reproduction.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

PROBLEMS=(
    HS21 HS35 HS35MOD HS51 HS52 HS53 HS76 GENHS28 HUES-MOD HUESTIS
    S268 QAFIRO QADLITTL QPCBLEND QPTEST QSC205 QSCAGR7 QSCSD1 QSCSD6
    QSCSD8 QSEBA QSHARE1B QSHARE2B QSTANDAT QBRANDY QCAPRI QE226
    QETAMACR QFORPLAN QGROW7 QISRAEL QRECIPE QSCORPIO QSHELL STADAT1
    STADAT2 STADAT3 VALUES YAO ZECEVIC2
)

echo "=== ODYN broader Maros-Meszaros benchmark, medium tolerance ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 400 \
    --timeout 90 \
    --problems "${PROBLEMS[@]}" \
    --output /home/user/tmp/results/odyn_broad_medium.json

echo "=== ODYN broader Maros-Meszaros benchmark, high tolerance ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-9 \
    --max-iter 600 \
    --timeout 90 \
    --skip-degenerate \
    --problems "${PROBLEMS[@]}" \
    --output /home/user/tmp/results/odyn_broad_high.json

bash scripts/evaluate.sh \
    --results /home/user/tmp/results/odyn_broad_medium.json /home/user/tmp/results/odyn_broad_high.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
