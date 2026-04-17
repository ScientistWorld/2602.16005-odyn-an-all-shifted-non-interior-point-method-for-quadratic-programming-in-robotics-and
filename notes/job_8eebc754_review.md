# Job 8eebc754-99a Review

The high-iteration broad-subset run completed successfully and `validate.py --compare`
passed. Increasing ODYN iteration budgets from 1000/1500 to 3000/5000 solved
several previously remaining max-iteration cases.

Final ODYN broad-subset failures:

- Medium tolerance: QFORPLAN, QRECIPE, QSHARE1B.
- High tolerance: QBRANDY, QFORPLAN, QRECIPE, QSHARE1B.

Final reproduced failure rates are 10.345% at medium tolerance and 13.793% at
high tolerance on 29 dense-feasible Maros-Meszaros problems. The paper reports
9.7% and 15.5% for ODYN on the full benchmark. OSQP on the same local subset
remains at 41.379% for both tolerances.

This supports closing the reproduction at `secondary_claims`: the environment
now covers the paper's main robustness comparison plus the degenerate-QP
pathology comparison, with reusable scoring and packaged scripts.
