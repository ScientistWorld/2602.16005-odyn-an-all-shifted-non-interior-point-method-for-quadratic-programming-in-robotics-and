#!/usr/bin/env python3
"""Solve one benchmark QP instance with the reproduced ODYN solver.

Usage (the solver contract, see ``briefing/evaluation.md``)::

    python3 -m method.solve_cli --problem P.npz --output OUT.npz --tol 1e-6

ODYN runs with the paper's default hyper-parameters (Table II), relative
tolerance ``tol`` and absolute tolerance ``tol * 1e-2``, and an iteration cap of
3000 at medium accuracy (tol > 1e-8) or 5000 at high accuracy. The dense backend
is used whenever Q, A and G fit in 2 GB as dense arrays and n <= 1000, as in the
original reproduction; larger problems use the sparse backend.
"""

from __future__ import annotations

import argparse

import numpy as np

from data.qp_format import read_instance, write_solution
from method.odyn_solver import DenseOdynSolver, OdynParams, SparseOdynSolver

MAX_DENSE_GB = 2.0
MAX_DENSE_N = 1000


def default_max_iter(tol: float) -> int:
    return 3000 if tol > 1e-8 else 5000


def solve_instance(problem: dict, tol: float, max_iter: int, rho: float | None = None,
                   rho_min: float | None = None):
    n, m, p = problem["n"], problem["m"], problem["p"]
    dense_gb = 8.0 * n * (n + m + p) / 1e9
    dense = dense_gb <= MAX_DENSE_GB and n <= MAX_DENSE_N
    params = OdynParams()
    params.max_iter = int(max_iter)
    if rho is not None:
        params.rho = rho
    if rho_min is not None:
        params.rho_min = rho_min
    Q, A, G = problem["Q"], problem["A"], problem["G"]
    if dense:
        solver = DenseOdynSolver(params)
        Q = Q.toarray()
        A = A.toarray() if m > 0 else None
        G = G.toarray() if p > 0 else None
    else:
        solver = SparseOdynSolver(params)
        A = A if m > 0 else None
        G = G if p > 0 else None
    return solver.solve(
        Q,
        problem["c"],
        A,
        problem["b"] if m > 0 else None,
        G,
        problem["h"] if p > 0 else None,
        rtol=tol,
        atol=tol * 1e-2,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tol", type=float, required=True)
    parser.add_argument("--max-iter", type=int, default=None,
                        help="Iteration cap (default: 3000 at medium, 5000 at high accuracy).")
    parser.add_argument("--rho", type=float, default=None)
    parser.add_argument("--rho-min", type=float, default=None)
    args = parser.parse_args()

    problem = read_instance(args.problem)
    max_iter = args.max_iter if args.max_iter is not None else default_max_iter(args.tol)
    result = solve_instance(problem, args.tol, max_iter, args.rho, args.rho_min)
    y = result.y if result.y is not None else np.zeros(problem["m"])
    z = result.z if result.z is not None else np.zeros(problem["p"])
    write_solution(args.output, result.x, y, z, iterations=np.int64(result.iterations),
                   status=np.array(str(result.status)))


if __name__ == "__main__":
    main()
