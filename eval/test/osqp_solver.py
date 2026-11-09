#!/usr/bin/env python3
"""Evaluator-owned OSQP baseline, run through the same solver contract as any method.

Usage: python3 -m eval.test.osqp_solver --problem P.npz --output OUT.npz --tol 1e-6

Settings are fixed by the evaluator: eps_abs = eps_rel = tol, OSQP's default
(no solution polishing), 4000 iterations at medium accuracy and 8000 at high
accuracy. The returned
point is verified by the evaluator like any other solver's output.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import scipy.sparse as spa


def _matrix(data, key: str, rows: int, cols: int) -> spa.csc_matrix:
    return spa.csc_matrix((data[f"{key}_data"], data[f"{key}_indices"], data[f"{key}_indptr"]), shape=(rows, cols))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tol", type=float, required=True)
    args = parser.parse_args()

    import osqp

    with np.load(args.problem, allow_pickle=False) as data:
        n, m, p = (int(data[k]) for k in ("n", "m", "p"))
        Q = _matrix(data, "Q", n, n)
        A = _matrix(data, "A", m, n)
        G = _matrix(data, "G", p, n)
        c = np.array(data["c"], dtype=float)
        b = np.array(data["b"], dtype=float)
        h = np.array(data["h"], dtype=float)

    C = spa.vstack([A, G], format="csc")
    lower = np.concatenate([b, np.full(p, -np.inf)])
    upper = np.concatenate([b, h])
    solver = osqp.OSQP()
    solver.setup(
        spa.triu(Q, format="csc"),
        c,
        C,
        lower,
        upper,
        eps_abs=args.tol,
        eps_rel=args.tol,
        max_iter=4000 if args.tol > 1e-8 else 8000,
        verbose=False,
    )
    result = solver.solve()
    x = np.asarray(result.x, dtype=float).reshape(-1) if result.x is not None else np.full(n, np.nan)
    multipliers = np.asarray(result.y, dtype=float).reshape(-1) if result.y is not None else np.full(m + p, np.nan)
    if x.shape[0] != n or multipliers.shape[0] != m + p:
        x = np.full(n, np.nan)
        multipliers = np.full(m + p, np.nan)
    # OSQP: Qx + c + C'w = 0 with w >= 0 on active upper bounds, i.e. the same
    # sign convention as Qx + c + A'y + G'z = 0, z >= 0.
    out = Path(args.output)
    tmp = out.with_name(out.name + ".partial.npz")
    np.savez(tmp, x=x, y=multipliers[:m], z=multipliers[m:],
             iterations=np.int64(getattr(result.info, "iter", -1)),
             status=np.array(str(getattr(result.info, "status", "unknown"))))
    os.replace(tmp, out)


if __name__ == "__main__":
    main()
