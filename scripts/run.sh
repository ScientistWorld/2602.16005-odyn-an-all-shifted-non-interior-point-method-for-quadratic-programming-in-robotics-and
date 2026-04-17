#!/bin/bash
# Stabilized ODYN broad-subset rerun plus same-subset OSQP comparison.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

ODYN_BROAD_PROBLEMS=(
    HS21 HS35 HS35MOD HS51 HS52 HS53 HS76 GENHS28 HUES-MOD HUESTIS
    S268 QAFIRO QADLITTL QPCBLEND QPTEST QSC205 QSCAGR7 QSCSD1 QSCSD6
    QSCSD8 QSEBA QSHARE1B QSHARE2B QSTANDAT QBRANDY QCAPRI QE226
    QETAMACR QFORPLAN QGROW7 QISRAEL QRECIPE QSCORPIO QSHELL STADAT1
    STADAT2 STADAT3 VALUES YAO ZECEVIC2
)

OSQP_COMPARISON_PROBLEMS=(
    GENHS28 HS21 HS35 HS35MOD HS51 HS52 HS53 HS76 QADLITTL QAFIRO
    QBRANDY QCAPRI QE226 QETAMACR QFORPLAN QGROW7 QISRAEL QPCBLEND
    QPTEST QRECIPE QSC205 QSCAGR7 QSCORPIO QSCSD1 QSHARE1B QSHARE2B
    S268 VALUES ZECEVIC2
)

echo "=== ODYN stabilized broader Maros-Meszaros benchmark, medium tolerance ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 1000 \
    --timeout 120 \
    --problems "${ODYN_BROAD_PROBLEMS[@]}" \
    --output /home/user/tmp/results/odyn_broad_medium.json

echo "=== ODYN stabilized broader Maros-Meszaros benchmark, high tolerance ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-9 \
    --max-iter 1500 \
    --timeout 120 \
    --skip-degenerate \
    --problems "${ODYN_BROAD_PROBLEMS[@]}" \
    --output /home/user/tmp/results/odyn_broad_high.json

echo "=== OSQP baseline on ODYN-attempted broad subset, medium tolerance ==="
python3 -m baseline.run_osqp \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 4000 \
    --problems "${OSQP_COMPARISON_PROBLEMS[@]}" \
    --output /home/user/tmp/results/osqp_broad_medium.json

echo "=== OSQP baseline on ODYN-attempted broad subset, high tolerance ==="
python3 -m baseline.run_osqp \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-9 \
    --max-iter 8000 \
    --skip-degenerate \
    --problems "${OSQP_COMPARISON_PROBLEMS[@]}" \
    --output /home/user/tmp/results/osqp_broad_high.json

bash scripts/evaluate.sh \
    --results \
        /home/user/tmp/results/odyn_broad_medium.json \
        /home/user/tmp/results/odyn_broad_high.json \
        /home/user/tmp/results/osqp_broad_medium.json \
        /home/user/tmp/results/osqp_broad_high.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
