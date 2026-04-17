#!/bin/bash
# End-to-end reproduction entry point.

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

echo "=== ODYN QP Solver Reproduction ==="
echo "[1/4] ODYN medium-accuracy broad subset"
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 3000 \
    --timeout 240 \
    --problems "${ODYN_BROAD_PROBLEMS[@]}" \
    --output /home/user/tmp/results/odyn_broad_medium.json

echo "[2/4] ODYN high-accuracy broad subset"
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-9 \
    --max-iter 5000 \
    --timeout 240 \
    --skip-degenerate \
    --problems "${ODYN_BROAD_PROBLEMS[@]}" \
    --output /home/user/tmp/results/odyn_broad_high.json

echo "[3/4] OSQP comparison on ODYN-attempted subset"
python3 -m baseline.run_osqp \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 4000 \
    --problems "${OSQP_COMPARISON_PROBLEMS[@]}" \
    --output /home/user/tmp/results/osqp_broad_medium.json

python3 -m baseline.run_osqp \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-9 \
    --max-iter 8000 \
    --skip-degenerate \
    --problems "${OSQP_COMPARISON_PROBLEMS[@]}" \
    --output /home/user/tmp/results/osqp_broad_high.json

echo "[4/4] Scoring"
bash scripts/evaluate.sh \
    --results \
        /home/user/tmp/results/odyn_broad_medium.json \
        /home/user/tmp/results/odyn_broad_high.json \
        /home/user/tmp/results/osqp_broad_medium.json \
        /home/user/tmp/results/osqp_broad_high.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
